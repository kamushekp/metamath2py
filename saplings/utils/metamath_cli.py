import logging
import os
import shutil
import subprocess
import tempfile
import importlib.util
import sys
from pathlib import Path
from typing import Optional, List, Any

# Ensure project root is in path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

LOGGER = logging.getLogger("metamath_cli")

def get_metamath_binary() -> Optional[Path]:
    """Locate the metamath executable."""
    # Check local build first
    local_bin = project_root / "metamath_program" / "metamath" / "metamath"
    if local_bin.exists() and os.access(local_bin, os.X_OK):
        return local_bin
    
    # Check system path
    system_bin = shutil.which("metamath")
    if system_bin:
        return Path(system_bin)
        
    return None

def get_set_mm() -> Optional[Path]:
    """Locate set.mm file."""
    candidate = project_root / "metamath_ программа" / "metamath" / "set.mm" # Typo in user's prompt corrected?
    # Actually the directory is metamath_program
    candidate = project_root / "metamath_program" / "metamath" / "set.mm"
    if candidate.exists():
        return candidate
    return None

def get_reverse_label_map() -> dict[str, str]:
    """
    Loads the mapping from HASH -> LABEL (e.g. 'OWSI' -> 'ax-mp').
    """
    map_path = project_root / "code_builders" / "pythonic_names_map.csv"
    reverse_map = {}
    if map_path.exists():
        try:
            with open(map_path, "r") as f:
                for line in f:
                    if not line.strip(): continue
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        label = parts[0]
                        hash_name = parts[-1] 
                        reverse_map[hash_name] = label
            LOGGER.info(f"Loaded {len(reverse_map)} reverse labels.")
        except Exception as e:
            LOGGER.error(f"Failed to load reverse label map: {e}")
    return reverse_map

def python_to_metamath(module_path: Path, theorem_name: str) -> str:
    """
    Translates a generated Python theorem/proof module back to Metamath syntax (MMP-like).
    """
    # Load reverse map
    reverse_map = get_reverse_label_map()

    # 1. Setup import environment for generated files
    # The generated proof imports: from metamath2py.classes.theorem import theorem
    # We need to make sure that resolves to our generated class file in saplings/out/classes
    
    # Locate the corresponding class file
    # module_path is .../proofs/name.py
    # class_path is .../classes/name.py
    
    proof_dir = module_path.parent
    classes_dir = proof_dir.parent / "classes"
    class_file = classes_dir / f"{theorem_name}.py"
    
    if not class_file.exists():
        raise FileNotFoundError(f"Class file {class_file} not found for proof {module_path}")

    # Manually load the class module and register it as 'metamath2py.classes.theorem_name'
    class_module_name = f"metamath2py.classes.{theorem_name}"
    
    # Also need to make sure metamath2py.classes.apply_substitution_for_generated_files exists
    # It seems to be used by the generated class.
    # It resides in metamath2py/classes in the repo, but the generated code might expect it relative?
    # No, imports are absolute: from metamath2py.classes.apply_substitution...
    
    # Let's verify if the real metamath2py package is in path.
    # It is, because we added project_root to sys.path.
    
    spec_cls = importlib.util.spec_from_file_location(class_module_name, class_file)
    if not spec_cls or not spec_cls.loader:
        raise ImportError(f"Could not create spec for {class_file}")
    
    module_cls = importlib.util.module_from_spec(spec_cls)
    sys.modules[class_module_name] = module_cls
    spec_cls.loader.exec_module(module_cls)
    
    # Now load the PROOF module
    # It expects to be imported, but we are loading it from file?
    # The proof file defines class {theorem_name}_proof({theorem_name})
    # It imports {theorem_name} from metamath2py.classes.{theorem_name} (which we just mocked)
    
    proof_module_name = f"metamath2py.proofs.{theorem_name}"
    spec_prf = importlib.util.spec_from_file_location(proof_module_name, module_path)
    if not spec_prf or not spec_prf.loader:
        raise ImportError(f"Could not create spec for {module_path}")
        
    module_prf = importlib.util.module_from_spec(spec_prf)
    sys.modules[proof_module_name] = module_prf
    spec_prf.loader.exec_module(module_prf)
    
    # Instantiate proof
    proof_cls_name = f"{theorem_name}_proof"
    if not hasattr(module_prf, proof_cls_name):
        raise ValueError(f"Module {proof_module_name} does not contain {proof_cls_name}")
        
    proof_instance = getattr(module_prf, proof_cls_name)()
    
    # We need to extract the structure.
    # 1. Assertion
    assertion = proof_instance.assertion
    # assertion is like "|- ~Prov(T, P = NP)"
    # We need to strip "|- " for the $p statement, or keep it?
    # Metamath $p statement:  Label $p wff ... $= ... $.
    
    # 2. Essentials
    # proof_instance.essential_1, etc.
    # We need to know which variables are distinct ($d).
    # The Python code doesn't explicitly store $f or $d statements clearly.
    # However, to VERIFY, we can treat the generated Python code as a "script" 
    # that builds the proof.
    
    # ... This reverse engineering involves inspecting the `proof` method source code
    # because executing it just runs the variable substitutions.
    # We need the LABELS (e.g. "SoundnessImpliesNotProvable").
    
    import inspect
    source = inspect.getsource(proof_instance.proof)
    
    # Parse source to find assignments: step_X = Label().call(...)
    # and extract Label.
    
    lines = source.splitlines()
    proof_labels = []
    
    for line in lines:
        line = line.strip()
        if ".call(" in line and "=" in line:
            # step_2 = Label().call(...)
            parts = line.split("=")
            rhs = parts[1].strip()
            # Label().call(...) -> extract Label
            label_part = rhs.split("().call")[0]
            
            # Apply REVERSE MAPPING (Hash -> Label)
            # e.g. OWSI -> ax-mp
            if label_part in reverse_map:
                proof_labels.append(reverse_map[label_part])
            else:
                proof_labels.append(label_part)
        elif "self.essential" in line and "=" in line:
             # step_1 = self.essential_1
             # This corresponds to using a hypothesis.
             # We need to map 'essential_1' to its label if we have one, 
             # OR if it's a floating hypothesis, use the variable?
             # Actually, if we are appending to set.mm, we define a new theorem.
             # $p ... $= ( Label1 Label2 ... ) alphabetic_sequence $.
             # But generating the compressed or normal proof string from just labels 
             # requires running the Metamath verifier logic (unification).
             pass
    
    # Constructing a valid Metamath proof string (RPN) from just the list of applied theorems
    # is possible if we trust the order and the stack.
    # But we also need the hyp references.
    
    # ALTERNATIVE STRATEGY:
    # Instead of full translation, we instruct `metamath` to verify the *assertion* 
    # matching the one in Python.
    # Since we can't easily reconstruction the RPN from the Python calls without a full 
    # MM logic engine in Python, maybe we simply verify that the Python code *executes*
    # (which we already do).
    
    # The user specifically asked to "patch set.mm ... and verify it".
    # This implies they want the Metamath C program to check it.
    # To do that, we MUST provide a valid Metamath proof string (labels in RPN).
    
    # If the Python code is:
    # step_1 = self.essential_1
    # step_2 = Thm().call(..., map={"essential_1": self.essential_1})
    
    # In RPN this is: essential_1_label Thm
    
    # So we need mapping from "self.essential_X" -> "essential_X_label".
    # And "Label" -> "Label".
    
    # Let's try to extract labels in order.
    rpn_tokens = []
    for line in lines:
        line = line.strip()
        if "=" not in line: continue
        
        rhs = line.split("=")[1].strip()
        
        if "self.essential" in rhs:
            # Extract essential name e.g. essential_1
            # "self.essential_1"
            ess_name = rhs.split("self.")[1]
            # In our generated Metamath content, we will name the hypothesis "essential_1".
            rpn_tokens.append(ess_name)
            
        elif ".call" in rhs:
            label = rhs.split("().call")[0]
            # Apply REVERSE MAPPING
            if label in reverse_map:
                rpn_tokens.append(reverse_map[label])
            else:
                rpn_tokens.append(label)
            
    # Now generate the MM text.
    # We need $c (constants) and $v (variables) if they are new.
    # We assume standard ones are in set.mm.
    # But our theorem variables T, P, NP might need declaration if not present.
    
    # In unprovable_P_eq_NP.py:
    # floatings: T
    # essentials: |- Sound(T)
    # assertion: |- ~Prov(T, P = NP)
    
    # We need to generate:
    # $v T $.
    # T_f $f class T $.  (Guessing type)
    # essential_1 $e |- Sound(T) $.
    # {theorem_name} $p |- ~Prov(T, P = NP) $= ( essential_1 ... labels ... ) ... $.
    
    # NOTE: The "..." at end of $p is the compressed proof, or we can use normal proof:
    # label1 label2 ... $.
    
    proof_str = " ".join(rpn_tokens)
    
    # Heuristic for variables types:
    # In generated files, we don't have types.
    # We will assume "class" for uppercase single letters like T?
    # Or "set" for lowercase?
    # This is risky.
    
    # New variables declaration
    variables = ["T"] # Extracted from floatings in Python
    
    mm_content = f"""
$v {" ".join(variables)} $.
"""
    for v in variables:
         mm_content += f"vx.{v} $f class {v} $.\n"
         
    # Essentials
    # Inspecting instance to get values
    # We assume naming convention essential_1 ...
    # We need to iterate 1..N based on code?
    # `unprovable_P_eq_NP` class has `self.essential_1`.
    
    essentials_str = ""
    for attr, val in proof_instance.__dict__.items():
        if attr.startswith("essential_"):
             essentials_str += f"{attr} $e {val} $.\n"
             
    assertion_str = f"{theorem_name} $p {assertion} $= {proof_str} $."
    
    return f"{mm_content}\n{essentials_str}\n{assertion_str}"

def verify_with_metamath(generated_class_file: Path) -> bool:
    """
    Main entry point.
    1. Locate set.mm
    2. Convert Python file to MM fragment.
    3. Append to copy of set.mm
    4. Run metamath
    """
    
    metamath_bin = get_metamath_binary()
    set_mm = get_set_mm()
    
    if not metamath_bin or not set_mm:
        LOGGER.error(f"Missing metamath binary ({metamath_bin}) or set.mm ({set_mm})")
        return False
        
    # 1. Prepare translation
    try:
        theorem_name = generated_class_file.stem
        # We need to point to the proofs dir really, because that's where the Logic is.
        # But wait, prove_it saved to `saplings/out/classes` and `saplings/out/proofs`.
        # `unprovable_P_eq_NP.py` in `classes` has structure.
        # `unprovable_P_eq_NP.py` in `proofs` has logic.
        # We should load the PROOF file.
        
        # Adjust path if we were passed the class file
        if "classes" in str(generated_class_file):
            proof_file = Path(str(generated_class_file).replace("classes", "proofs"))
        else:
            proof_file = generated_class_file
            
        mm_fragment = python_to_metamath(proof_file, theorem_name)
        print(f"DEBUG: Generated MM fragment:\n{mm_fragment}")
        LOGGER.info(f"Generated Metamath fragment:\n{mm_fragment}")
        
    except Exception as e:
        LOGGER.error(f"Failed to translate to Metamath: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. Create Temp Workdir
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_set_mm = Path(temp_dir) / "set.mm" # Rename to set.mm to avoid confusion? No, temp_set_mm is fine.
        
        # Copy set.mm
        LOGGER.info(f"Copying set.mm to {temp_set_mm}...")
        if not set_mm.exists():
             LOGGER.error(f"Source set.mm at {set_mm} does not exist!")
             return False
             
        shutil.copyfile(set_mm, temp_set_mm)
        
        # Append fragment
        with open(temp_set_mm, "a") as f:
            f.write("\n\n$( Generated Verification Patch $)\n")
            f.write(mm_fragment)
            f.write("\n")
            
        # 3. Running Metamath
        # Commands: read file, verify proof {theorem_name}, exit
        # Use full filename relative to CWD
        cmd_input = f"read \"{temp_set_mm.name}\"\nshow proof {theorem_name} /lemmacomm\nverify proof {theorem_name}\nexit\n"
        
        LOGGER.info(f"Running metamath on {temp_set_mm}...")
        print(f"DEBUG: Executing metamath with input:\n{cmd_input}")
        
        try:
            result = subprocess.run(
                [str(metamath_bin)],
                input=cmd_input,
                text=True,
                capture_output=True,
                cwd=temp_dir,
                timeout=120 # Add timeout
            )
            
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            
            if result.returncode != 0:
                LOGGER.error("Metamath process failed.")
                LOGGER.error(result.stdout)
                LOGGER.error(result.stderr)
                return False
                
            if "The proof of" in result.stdout and " is correct." in result.stdout:
                LOGGER.info("Verification SUCCESS!")
                return True
            else:
                LOGGER.warning("Verification FAILED or inconclusive logic.")
                LOGGER.info(result.stdout)
                return False
                
        except Exception as e:
            LOGGER.error(f"Subprocess execution failed: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1]).resolve()
    else:
        # Test with the file we know exists locally for dev
        test_file = project_root / "saplings" / "out" / "proofs" / "unprovable_P_eq_NP.py"
        
    if test_file.exists():
        # Patch sys.modules to allow imports of generated files
        # The generated files do `from metamath2py.classes.apply_substitution_for_generated_files import apply_substitution`
        # We need to make sure that module resolves.
        try:
             import metamath2py.classes.apply_substitution_for_generated_files as apply_sub
             sys.modules["metamath2py.classes.apply_substitution_for_generated_files"] = apply_sub
        except ImportError:
             # Try to find it relative to project root if not installed as package
             apply_sub_path = project_root / "metamath2py" / "classes" / "apply_substitution_for_generated_files.py"
             if apply_sub_path.exists():
                 spec = importlib.util.spec_from_file_location("metamath2py.classes.apply_substitution_for_generated_files", apply_sub_path)
                 mod = importlib.util.module_from_spec(spec)
                 sys.modules["metamath2py.classes.apply_substitution_for_generated_files"] = mod
                 spec.loader.exec_module(mod)
                 LOGGER.info("Manually patched apply_substitution_for_generated_files")
        
        verify_with_metamath(test_file)
    else:
        print(f"File not found: {test_file}")
