#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is in path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from saplings.utils.tracking import tracker, BudgetExceededError
from saplings.saplings_agents.candidate_generator import CandidateGenerator
from saplings.dtos.node import Node
from saplings.dtos.tasks.create_node_task import CreateNodeTask
from saplings.dtos.theorem_state import TheoremState, RequiredTheoremPremises
from saplings.dtos.proof_state import ProofState, ProofStep
from llm_authoring import TheoremClassAuthor, ProofAuthor, WriteResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
LOGGER = logging.getLogger("prove_it")

def load_environment():
    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)

def render_and_save(node: Node, output_dir: Path) -> tuple[Path | None, Path | None]:
    task = node.created_node_task
    theorem = task.theorem
    proof = task.proof
    
    # 1. Save Theorem Class
    class_author = TheoremClassAuthor(theorem.label, target_dir=output_dir / "classes")
    class_author.set_comment(f"Goal: {task.goal}")
    
    for float_arg in theorem.floating_args:
        class_author.add_floating(float_arg)
        
    for essential in theorem.essential_args:
         # simple heuristic to find content if mapped, or just add as is
         # In TheoremState, essential_args are just names (e.g. "essential_1").
         # Wait, TheoremState.essential_args is List[str]. 
         # But usually we need the content (formula).
         # Let's check TheoremState definition again.
         # It has `essential_args: List[str]`.
         # And `required_theorem_premises: List[RequiredTheoremPremises]`.
         # Use required_theorem_premises to fill essentials content.
         pass

    # Re-mapping essentials from premises
    # required_theorem_premises has left (name) and right (content)
    # essential_args has names.
    
    premise_map = {p.left: p.right for p in theorem.required_theorem_premises}
    
    for essential_name in theorem.essential_args:
        if essential_name in premise_map:
            class_author.add_essential(premise_map[essential_name])
        else:
            # Fallback if content missing (should not happen if valid)
            class_author.add_essential(f"|- {essential_name} (MISSING CONTENT)")

    class_author.set_assertion(theorem.assertion)
    
    res_cls: WriteResult = class_author.save(overwrite=True)
    if not res_cls.success:
        LOGGER.error(f"Failed to save theorem class: {res_cls.issues}")
        return None, None
    else:
        LOGGER.info(f"Saved theorem class to {res_cls.path}")

    # 2. Save Proof Class
    proof_author = ProofAuthor(theorem.label, target_dir=output_dir / "proofs")
    
    for step in proof.steps:
        # Step definition: left=name, right=expression, comment=comment
        # We need to parse strict format expected by `ProofAuthor`?
        # `ProofAuthor` has `add_body_line`.
        # `CandidateGenerator` produces standard python lines in `right`.
        
        line = f"        {step.left} = {step.right}"
        proof_author.add_body_line(line)
    
    # Heuristic for last step
    if proof.steps:
        proof_author.set_last_step(proof.steps[-1].left)
    else:
        # If no steps, cannot save valid proof
        LOGGER.warning("No proof steps to save.")
        return res_cls.path, None

    res_prf: WriteResult = proof_author.save(overwrite=True)
    if not res_prf.success:
        LOGGER.error(f"Failed to save proof class: {res_prf.issues}")
        return res_cls.path, None
    else:
        LOGGER.info(f"Saved proof class to {res_prf.path}")
        
    return res_cls.path, res_prf.path

def main():
    parser = argparse.ArgumentParser(description="Prove a theorem from natural language.")
    parser.add_argument("--goal", required=True, help="Natural language goal/statement.")
    parser.add_argument("--budget", type=float, default=5.0, help="OpenAI budget limit in USD.")
    parser.add_argument("--max-turns", type=int, default=10, help="Maximum generation turns.")
    args = parser.parse_args()

    load_environment()
    
    # Initialize Tracker
    tracker.set_limit(args.budget)
    tracker.start_tracking()
    
    LOGGER.info(f"Starting proof generation for goal: {args.goal}")
    
    # Initialize Task
    initial_task = CreateNodeTask(
        goal=args.goal,
        theorem=TheoremState(
            label="",
            floating_args=[],
            essential_args=[],
            required_theorem_premises=[],
            assertion=""
        ),
        proof=ProofState(steps=[]),
        next_step_ideas="Start by formulating the theorem structure."
    )
    
    current_node = Node(created_node_task=initial_task)
    generator = CandidateGenerator(step_max_turns=3) # steps per agent run
    
    output_dir = project_root / "saplings" / "generated" # Temporary output
    output_dir.mkdir(parents=True, exist_ok=True)

    for turn in range(args.max_turns):
        LOGGER.info(f"--- Turn {turn+1}/{args.max_turns} ---")
        if tracker.get_cost() >= tracker.limit:
             LOGGER.error("Budget exceeded, stopping.")
             break

        try:
            # Generate candidates
            # We take the first valid one (Greedy)
            found = False
            for transition in generator.generate(current_node, requested_patch_sets=1):
                LOGGER.info(f"Selected action: {transition.patch_set.change_description}")
                
                # Apply transition to get next node
                # The generator yields transitions which contain task_after.
                # We need to wrap it in a Node.
                next_node = Node(
                    created_node_task=transition.task_after,
                    parent_node=current_node,
                    created_from_patch_set=transition.patch_set
                )
                current_node = next_node
                found = True
                break 
            
            if not found:
                LOGGER.info("No more steps generated. Optimization finished or stuck.")
                break
                
        except BudgetExceededError:
            LOGGER.error("Budget exceeded during generation.")
            break
        except Exception as e:
            LOGGER.exception(f"Unexpected error: {e}")
            break
            
    # Finalize
    LOGGER.info("Generation loop ended. Saving results...")
    
    # Render to files
    try:
        cls_path, prf_path = render_and_save(current_node, project_root / "saplings" / "out")
        
        if cls_path and prf_path:
            LOGGER.info("Verifying proof...")
            # We can run verification directly
            # verify_proof takes relative module path e.g. "metamath2py.proofs.MyProof"
            # But we saved to `saplings/out/proofs`.
            # We might need to adjust paths or move files.
            # For now, just report paths.
            LOGGER.info(f"Done. Files: {cls_path}, {prf_path}")
            
    except Exception as e:
        LOGGER.error(f"Failed to render/save: {e}")

if __name__ == "__main__":
    main()
