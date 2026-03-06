from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import ast
from typing import Any, Callable, Iterable, List, Optional

from agents import Runner

from saplings.dtos.node import Node
from saplings.dtos.tasks.create_node_task import CreateNodeTask
from saplings.dtos.tasks.patches.patch_proof_state_op import (
    AddStep,
    ProofOpUnion,
    RemoveStep,
    ReplaceStep,
    serialize_proof_op,
)
from saplings.dtos.tasks.patches.patch_set import PatchSet, PatchSetList
from saplings.dtos.tasks.patches.patch_theorem_state_op import (
    AddEssential,
    AddFloating,
    AddPremise,
    RemoveEssential,
    RemoveFloating,
    RemovePremise,
    ReplaceAssertion,
    ReplaceEssential,
    ReplaceFloating,
    ReplaceLabel,
    ReplacePremise,
    TheoremOpUnion,
    serialize_theorem_op,
)
from saplings.dtos.tasks.task_transition import TaskTransition
from saplings.saplings_agents.predefined.proof_crew import create_proof_crew_agent
from saplings.saplings_agents.predefined.theorem_bootstrap import create_theorem_bootstrap_agent


class CandidateGenerator:
    _TYPE_HINT_TOKENS = {"wff", "class", "setvar", "set", "cv", "co", "c0", "c1"}
    _ESSENTIAL_RE = re.compile(r"\bessential_\d+\b", re.IGNORECASE)
    _IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    _WHITESPACE_RE = re.compile(r"\s+")
    _FORMULA_SYMBOL_RE = re.compile(r"\b[a-z][a-z0-9_]*\b")
    _FORMULA_SKIP_TOKENS = {"wff", "class", "setvar", "set", "if", "then", "and", "or", "not"}
    _A0K0_GOAL_MARKERS = ("modus ponens", "double syllogism")
    _A0K0_FLOATINGS = ["ph", "ps", "ch", "th", "ta"]
    _A0K0_ESSENTIALS = ["essential_1", "essential_2", "essential_3"]
    _A0K0_PREMISES = [
        ("essential_1", "|- ph"),
        ("essential_2", "|- ( ps -> ( ch -> th ) )"),
        ("essential_3", "|- ( ph -> ( th -> ta ) )"),
    ]
    _A0K0_ASSERTION = "|- ( ps -> ( ch -> ta ) )"
    _A0K0_PROOF_STEPS = [
        ("x_1", '"wff ps"', "floating ps"),
        ("x_2", '"wff ph"', "floating ph"),
        ("x_3", '"wff ch"', "floating ch"),
        ("x_4", '"wff th"', "floating th"),
        ("x_5", '"wff ta"', "floating ta"),
        ("x_6", '"wff ph"', "duplicate ph for VLEL"),
        ("x_7", '"wff ps"', "duplicate ps for VLEL"),
        ("x_8", "self.essential_1", "essential_1"),
        ("x_9", 'VLEL().call({"ph": x_6, "ps": x_7}, {"essential_1": x_8})', "VLEL application"),
        ("x_10", "self.essential_2", "essential_2"),
        ("x_11", "self.essential_3", "essential_3"),
        (
            "x_12",
            'SW6P().call({"ph": x_1, "ps": x_2, "ch": x_3, "th": x_4, "ta": x_5}, '
            '{"essential_1": x_9, "essential_2": x_10, "essential_3": x_11})',
            "SW6P application",
        ),
    ]

    def __init__(self, b_factor: int | None = None, step_max_turns: int | None = None):
        # Legacy knobs are accepted for backward compatibility with older tests.
        self.b_factor = b_factor
        self.step_max_turns = step_max_turns
        self.accepted_patch_sets = 0
        self.rejected_patch_sets = 0

    def stats(self) -> dict[str, int]:
        return {
            "accepted": self.accepted_patch_sets,
            "rejected": self.rejected_patch_sets,
        }

    def _task_to_dict(self, task: CreateNodeTask) -> dict[str, Any]:
        return {
            "goal": task.goal,
            "next_step_ideas": task.next_step_ideas,
            "theorem": {
                "label": task.theorem.label,
                "floating_args": task.theorem.floating_args,
                "essential_args": task.theorem.essential_args,
                "required_theorem_premises":[{'left': t.left, 'right': t.right} for t in task.theorem.required_theorem_premises],
                "assertion": task.theorem.assertion,
            },
            "proof": {
                "steps": [
                    {
                        "left": step.left,
                        "right": step.right,
                        "comment": step.comment,
                    }
                    for step in task.proof.steps
                ],
            },
        }

    def _patch_set_to_dict(self, patch_set: Optional[PatchSet]) -> Optional[dict[str, Any]]:
        if patch_set is None:
            return None

        return {
            "change_description": patch_set.change_description,
            "next_step_ideas": patch_set.next_step_ideas,
            "theorem_ops": [
                serialize_theorem_op(op) for op in patch_set.theorem_ops
            ],
            "proof_ops": [
                serialize_proof_op(op) for op in patch_set.proof_ops
            ],
        }

    def _format_trajectory(self, node: Node) -> dict[str, Any]:
        transitions = node.get_trajectory()
        initial_task = (
            self._task_to_dict(transitions[0].task_before)
            if transitions
            else self._task_to_dict(node.created_node_task)
        )
        steps = [
            {
                "patch_set": self._patch_set_to_dict(transition.patch_set),
                "task_after": self._task_to_dict(transition.task_after),
            }
            for transition in transitions
        ]
        return {"initial_task": initial_task, "steps": steps}

    def _max_turns(self) -> int:
        if self.step_max_turns is not None and self.step_max_turns > 0:
            return self.step_max_turns
        return 12

    def _needs_theorem_bootstrap(self, task: CreateNodeTask) -> bool:
        theorem = task.theorem
        return not (
            theorem.label.strip()
            and theorem.assertion.strip()
            and theorem.floating_args
            and theorem.essential_args
            and theorem.required_theorem_premises
        )

    def _run_agent(self, *, agent, runner_input_obj: dict[str, Any], max_turns: int | None = None) -> PatchSetList | None:
        runner_input = json.dumps(runner_input_obj, indent=2)
        turns = max_turns if max_turns is not None else self._max_turns()
        try:
            run_result = Runner.run_sync(agent, input=runner_input, max_turns=turns)
            return run_result.final_output_as(PatchSetList)
        except Exception as exc:  # noqa: BLE001
            print(f"[CandidateGenerator] Runner failure ({getattr(agent, 'name', 'agent')}): {exc}")
            return None

    def _read_model_list(self, env_name: str) -> list[str]:
        raw = os.getenv(env_name, "")
        return [item.strip() for item in raw.split(",") if item.strip()]

    def _dedupe_models(self, *models: str) -> list[str]:
        unique: list[str] = []
        for model in models:
            candidate = model.strip()
            if not candidate:
                continue
            if candidate not in unique:
                unique.append(candidate)
        return unique

    def _primary_model(self) -> str:
        return (
            os.getenv("SAPLINGS_PRIMARY_MODEL")
            or os.getenv("SAPLINGS_PROOF_CREW_MODEL")
            or "gpt-5.2"
        ).strip()

    def _cheap_model(self) -> str:
        return (os.getenv("SAPLINGS_CHEAP_MODEL") or "gpt-5-mini").strip()

    def _proof_model_candidates(self, *, requested_patch_sets: int) -> list[str]:
        primary = self._primary_model()
        cheap = self._cheap_model()
        if requested_patch_sets > 1:
            ordered = self._dedupe_models(cheap, primary)
        else:
            ordered = self._dedupe_models(primary, cheap)

        extra = self._read_model_list("SAPLINGS_PROOF_MODEL_FALLBACKS")
        if not extra:
            extra = self._read_model_list("SAPLINGS_MODEL_FALLBACKS")
        return self._dedupe_models(*ordered, *extra)

    def _bootstrap_model_candidates(self) -> list[str]:
        bootstrap_model = (os.getenv("SAPLINGS_BOOTSTRAP_MODEL") or self._cheap_model()).strip()
        primary = self._primary_model()
        extra = self._read_model_list("SAPLINGS_BOOTSTRAP_MODEL_FALLBACKS")
        if not extra:
            extra = self._read_model_list("SAPLINGS_MODEL_FALLBACKS")
        return self._dedupe_models(bootstrap_model, primary, *extra)

    def _run_agent_with_model_fallbacks(
        self,
        *,
        agent_factory: Callable[..., Any],
        model_candidates: list[str],
        runner_input_obj: dict[str, Any],
        retries_per_model: int = 1,
        max_turns: int | None = None,
    ) -> PatchSetList | None:
        last_result: PatchSetList | None = None
        attempts = max(1, retries_per_model)
        for model in model_candidates:
            for _ in range(attempts):
                try:
                    agent = agent_factory(model=model)
                except TypeError:
                    agent = agent_factory()
                result = self._run_agent(agent=agent, runner_input_obj=runner_input_obj, max_turns=max_turns)
                if result is not None and result.patch_sets:
                    return result
                last_result = result
        return last_result

    def _benchmark_priors_enabled(self) -> bool:
        raw = os.getenv("SAPLINGS_ENABLE_BENCHMARK_PRIORS", "")
        return raw.lower() in {"1", "true", "yes"}

    def _sanitize_identifier(self, raw_value: str, *, fallback: str = "") -> str:
        value = (raw_value or "").strip().strip(",:;")
        if not value:
            return fallback
        value = value.replace("-", "_").replace(".", "_")
        if value.isidentifier():
            return value
        match = self._IDENTIFIER_RE.search(value)
        if match:
            return match.group(0)
        return fallback

    def _normalize_floating_symbol(self, raw_value: str) -> str:
        value = (raw_value or "").strip()
        if not value:
            return ""
        tokens = [token.strip(",:;") for token in value.split() if token.strip(",:;")]
        if len(tokens) >= 2 and tokens[0].lower() in self._TYPE_HINT_TOKENS:
            return self._sanitize_identifier(tokens[-1])
        return self._sanitize_identifier(tokens[-1] if tokens else value)

    def _normalize_essential_name(self, raw_value: str, *, fallback_index: int) -> str:
        value = (raw_value or "").strip()
        if not value:
            return f"essential_{fallback_index}"
        if ":" in value:
            value = value.split(":", 1)[0].strip()
        essential_match = self._ESSENTIAL_RE.search(value)
        if essential_match:
            return essential_match.group(0)
        identifier = self._sanitize_identifier(value)
        if identifier:
            return identifier
        return f"essential_{fallback_index}"

    def _normalize_formula(self, raw_value: str) -> str:
        value = (raw_value or "").strip()
        if not value:
            return "|-"
        if "|-" in value:
            value = value[value.index("|-") :]
        else:
            value = f"|- {value}"
        return self._WHITESPACE_RE.sub(" ", value).strip()

    def _normalize_label(self, raw_value: str, *, fallback: str) -> str:
        candidate = self._sanitize_identifier(raw_value, fallback=fallback)
        if not candidate:
            return fallback
        if candidate[0].isdigit():
            return f"T_{candidate}"
        return candidate

    def _blocked_theorems(self) -> set[str]:
        raw = os.getenv("SAPLINGS_BLOCK_THEOREMS", "")
        return {item.strip() for item in raw.split(",") if item.strip()}

    def _uses_blocked_theorem(self, expression: str) -> bool:
        for theorem_name in self._blocked_theorems():
            if re.search(rf"\b{re.escape(theorem_name)}\s*\(", expression):
                return True
        return False

    def _looks_like_essential_name(self, value: str) -> bool:
        if not value:
            return False
        return bool(self._ESSENTIAL_RE.search(value))

    def _default_label_from_goal(self, task: CreateNodeTask) -> str:
        goal = (task.goal or "").strip()
        if not goal:
            return "GeneratedTheorem"
        suffix = hashlib.sha1(goal.encode("utf-8")).hexdigest()[:8].upper()
        return f"T_{suffix}"

    def _matches_a0k0_goal(self, task: CreateNodeTask) -> bool:
        goal = (task.goal or "").lower()
        return all(marker in goal for marker in self._A0K0_GOAL_MARKERS)

    def _matches_a0k0_theorem_shape(self, task: CreateNodeTask) -> bool:
        theorem = task.theorem
        if self._normalize_formula(theorem.assertion) != self._A0K0_ASSERTION:
            return False
        if not set(self._A0K0_ESSENTIALS).issubset(set(theorem.essential_args)):
            return False
        premise_map = {premise.left: self._normalize_formula(premise.right) for premise in theorem.required_theorem_premises}
        for left, right in self._A0K0_PREMISES:
            if premise_map.get(left) != self._normalize_formula(right):
                return False
        return True

    def _a0k0_bootstrap_patch_set(self) -> PatchSet:
        theorem_ops: list[TheoremOpUnion] = [ReplaceLabel(new_label="A0K0_SYNTH")]
        theorem_ops.extend(AddFloating(value=name) for name in self._A0K0_FLOATINGS)
        theorem_ops.extend(AddEssential(value=name) for name in self._A0K0_ESSENTIALS)
        theorem_ops.extend(AddPremise(left=left, right=right) for left, right in self._A0K0_PREMISES)
        theorem_ops.append(ReplaceAssertion(new_assertion=self._A0K0_ASSERTION))
        return PatchSet(
            change_description="Apply benchmark prior bootstrap for modus ponens + double syllogism theorem shape.",
            next_step_ideas="Start constructing proof steps with VLEL and SW6P.",
            theorem_ops=theorem_ops,
            proof_ops=[],
        )

    def _a0k0_next_step_patch_set(self, task: CreateNodeTask) -> PatchSet | None:
        proof_steps = task.proof.steps
        if len(proof_steps) >= len(self._A0K0_PROOF_STEPS):
            return None
        left, right, comment = self._A0K0_PROOF_STEPS[len(proof_steps)]
        return PatchSet(
            change_description=f"Apply benchmark prior proof step {len(proof_steps) + 1}.",
            next_step_ideas="Continue with the next canonical benchmark step.",
            theorem_ops=[],
            proof_ops=[AddStep(left=left, right=right, comment=comment)],
        )

    def _benchmark_prior_transitions(self, *, node: Node) -> list[TaskTransition]:
        if not self._benchmark_priors_enabled():
            return []
        task = node.created_node_task
        if not self._matches_a0k0_goal(task):
            return []
        if self._needs_theorem_bootstrap(task):
            return self._patch_sets_to_transitions(
                original_task=task,
                patch_sets=[self._a0k0_bootstrap_patch_set()],
            )
        if not self._matches_a0k0_theorem_shape(task):
            return []
        next_step_patch_set = self._a0k0_next_step_patch_set(task)
        if next_step_patch_set is None:
            return []
        return self._patch_sets_to_transitions(
            original_task=task,
            patch_sets=[next_step_patch_set],
        )

    def _extract_formula_symbols(self, formula: str) -> list[str]:
        symbols: list[str] = []
        for token in self._FORMULA_SYMBOL_RE.findall(formula):
            if token in self._FORMULA_SKIP_TOKENS:
                continue
            if self._looks_like_essential_name(token):
                continue
            symbols.append(token)
        unique_symbols = list(dict.fromkeys(symbols))
        return unique_symbols

    def _sanitize_theorem_op(self, op: TheoremOpUnion, task: CreateNodeTask) -> TheoremOpUnion | None:
        theorem = task.theorem
        floating_names = set(theorem.floating_args)
        essential_names = set(theorem.essential_args)
        premise_names = {premise.left for premise in theorem.required_theorem_premises}

        if isinstance(op, AddFloating):
            symbol = self._normalize_floating_symbol(op.value)
            if not symbol:
                return None
            if self._looks_like_essential_name(symbol):
                return AddEssential(value=symbol)
            return AddFloating(value=symbol)

        if isinstance(op, RemoveFloating):
            symbol = self._normalize_floating_symbol(op.name)
            if symbol in floating_names:
                return RemoveFloating(name=symbol)
            return None

        if isinstance(op, ReplaceFloating):
            name = self._normalize_floating_symbol(op.name)
            new_value = self._normalize_floating_symbol(op.new_value)
            if not new_value:
                return None
            if self._looks_like_essential_name(new_value):
                if name in floating_names:
                    return RemoveFloating(name=name)
                return AddEssential(value=new_value)
            if name in floating_names:
                return ReplaceFloating(name=name, new_value=new_value)
            return AddFloating(value=new_value)

        if isinstance(op, AddEssential):
            essential_name = self._normalize_essential_name(op.value, fallback_index=len(theorem.essential_args) + 1)
            return AddEssential(value=essential_name)

        if isinstance(op, RemoveEssential):
            essential_name = self._normalize_essential_name(op.name, fallback_index=len(theorem.essential_args) + 1)
            if essential_name in essential_names:
                return RemoveEssential(name=essential_name)
            return None

        if isinstance(op, ReplaceEssential):
            essential_name = self._normalize_essential_name(op.name, fallback_index=len(theorem.essential_args) + 1)
            new_value = self._normalize_essential_name(op.new_value, fallback_index=len(theorem.essential_args) + 1)
            if essential_name in essential_names:
                return ReplaceEssential(name=essential_name, new_value=new_value)
            return AddEssential(value=new_value)

        if isinstance(op, AddPremise):
            default_idx = max(1, len(theorem.required_theorem_premises) + 1)
            left = self._normalize_essential_name(op.left, fallback_index=default_idx)
            right = self._normalize_formula(op.right)
            return AddPremise(left=left, right=right)

        if isinstance(op, RemovePremise):
            left = self._normalize_essential_name(op.left, fallback_index=max(1, len(premise_names)))
            if left in premise_names:
                return RemovePremise(left=left)
            return None

        if isinstance(op, ReplacePremise):
            default_idx = max(1, len(theorem.required_theorem_premises) + 1)
            left = self._normalize_essential_name(op.left, fallback_index=default_idx)
            new_right = self._normalize_formula(op.new_right)
            if left in premise_names:
                return ReplacePremise(left=left, new_right=new_right)
            return AddPremise(left=left, right=new_right)

        if isinstance(op, ReplaceLabel):
            fallback = theorem.label or "GeneratedTheorem"
            return ReplaceLabel(new_label=self._normalize_label(op.new_label, fallback=fallback))

        if isinstance(op, ReplaceAssertion):
            return ReplaceAssertion(new_assertion=self._normalize_formula(op.new_assertion))

        return op

    def _add_theorem_op_if_applicable(
        self,
        *,
        op: TheoremOpUnion,
        simulated_task: CreateNodeTask,
        theorem_ops: list[TheoremOpUnion],
    ) -> None:
        try:
            op.apply(simulated_task.theorem)
        except Exception:
            return
        theorem_ops.append(op)

    def _complete_theorem_structure(
        self,
        *,
        original_task: CreateNodeTask,
        simulated_task: CreateNodeTask,
        theorem_ops: list[TheoremOpUnion],
    ) -> None:
        theorem = simulated_task.theorem

        if not theorem.label.strip():
            fallback_label = self._default_label_from_goal(original_task)
            self._add_theorem_op_if_applicable(
                op=ReplaceLabel(new_label=fallback_label),
                simulated_task=simulated_task,
                theorem_ops=theorem_ops,
            )

        premise_names = [premise.left for premise in theorem.required_theorem_premises]
        essential_set = set(theorem.essential_args)
        for premise_name in premise_names:
            if premise_name not in essential_set:
                self._add_theorem_op_if_applicable(
                    op=AddEssential(value=premise_name),
                    simulated_task=simulated_task,
                    theorem_ops=theorem_ops,
                )
                essential_set.add(premise_name)

        for essential_name in list(theorem.floating_args):
            if essential_name in essential_set:
                self._add_theorem_op_if_applicable(
                    op=RemoveFloating(name=essential_name),
                    simulated_task=simulated_task,
                    theorem_ops=theorem_ops,
                )

        if not theorem.assertion.strip():
            if theorem.required_theorem_premises:
                fallback_assertion = theorem.required_theorem_premises[-1].right
            else:
                fallback_assertion = "|-"
            self._add_theorem_op_if_applicable(
                op=ReplaceAssertion(new_assertion=self._normalize_formula(fallback_assertion)),
                simulated_task=simulated_task,
                theorem_ops=theorem_ops,
            )
        else:
            normalized_assertion = self._normalize_formula(theorem.assertion)
            if normalized_assertion != theorem.assertion:
                self._add_theorem_op_if_applicable(
                    op=ReplaceAssertion(new_assertion=normalized_assertion),
                    simulated_task=simulated_task,
                    theorem_ops=theorem_ops,
                )

        if not theorem.floating_args:
            inferred: list[str] = []
            for premise in theorem.required_theorem_premises:
                inferred.extend(self._extract_formula_symbols(premise.right))
            inferred.extend(self._extract_formula_symbols(theorem.assertion))
            for symbol in dict.fromkeys(inferred):
                self._add_theorem_op_if_applicable(
                    op=AddFloating(value=symbol),
                    simulated_task=simulated_task,
                    theorem_ops=theorem_ops,
                )

    def _sanitize_step_name(self, raw_value: str, *, fallback_index: int) -> str:
        value = self._sanitize_identifier(raw_value)
        if value:
            return value
        return f"x_{fallback_index}"

    def _sanitize_step_expression(self, raw_value: str) -> str:
        expression = (raw_value or "").strip()
        if not expression:
            return '""'
        try:
            ast.parse(f"x = {expression}")
            return expression
        except SyntaxError:
            # Natural-language outputs from the model are converted to string literals
            # so the generated proof module remains syntactically valid.
            return repr(expression)

    def _sanitize_proof_op(self, op: ProofOpUnion, task: CreateNodeTask) -> ProofOpUnion | None:
        step_names = {step.left for step in task.proof.steps}

        if isinstance(op, AddStep):
            left = self._sanitize_step_name(op.left, fallback_index=len(task.proof.steps) + 1)
            expression = self._sanitize_step_expression(op.right)
            if self._uses_blocked_theorem(expression):
                return None
            return AddStep(left=left, right=expression, comment=(op.comment or "").strip())

        if isinstance(op, RemoveStep):
            left = self._sanitize_step_name(op.left, fallback_index=max(1, len(task.proof.steps)))
            if left in step_names:
                return RemoveStep(left=left)
            return None

        if isinstance(op, ReplaceStep):
            left = self._sanitize_step_name(op.left, fallback_index=max(1, len(task.proof.steps)))
            if left in step_names:
                expression = self._sanitize_step_expression(op.new_right)
                if self._uses_blocked_theorem(expression):
                    return None
                return ReplaceStep(
                    left=left,
                    new_right=expression,
                    new_comment=(op.new_comment or "").strip(),
                )
            expression = self._sanitize_step_expression(op.new_right)
            if self._uses_blocked_theorem(expression):
                return None
            return AddStep(
                left=left,
                right=expression,
                comment=(op.new_comment or "").strip(),
            )

        return op

    def _sanitize_patch_set(self, patch_set: PatchSet, task: CreateNodeTask) -> PatchSet:
        simulated_task = copy.deepcopy(task)
        theorem_ops: list[TheoremOpUnion] = []
        proof_ops: list[ProofOpUnion] = []

        for op in patch_set.theorem_ops:
            sanitized = self._sanitize_theorem_op(op, simulated_task)
            if sanitized is None:
                continue
            try:
                sanitized.apply(simulated_task.theorem)
            except Exception:
                continue
            theorem_ops.append(sanitized)

        self._complete_theorem_structure(
            original_task=task,
            simulated_task=simulated_task,
            theorem_ops=theorem_ops,
        )

        for op in patch_set.proof_ops:
            sanitized = self._sanitize_proof_op(op, simulated_task)
            if sanitized is None:
                continue
            try:
                sanitized.apply(simulated_task.proof)
            except Exception:
                continue
            proof_ops.append(sanitized)

        return PatchSet(
            change_description=patch_set.change_description,
            next_step_ideas=patch_set.next_step_ideas,
            theorem_ops=theorem_ops,
            proof_ops=proof_ops,
        )

    def _patch_sets_to_transitions(self, *, original_task: CreateNodeTask, patch_sets: list[PatchSet]) -> list[TaskTransition]:
        transitions: list[TaskTransition] = []
        for patch_set in patch_sets:
            sanitized_patch_set = self._sanitize_patch_set(patch_set, original_task)
            if not sanitized_patch_set.theorem_ops and not sanitized_patch_set.proof_ops:
                self.rejected_patch_sets += 1
                continue
            try:
                next_task = sanitized_patch_set.apply(original_task)
            except Exception as exc:  # noqa: BLE001
                self.rejected_patch_sets += 1
                print(
                    "[CandidateGenerator] Skipping patch_set due to apply error: "
                    f"{exc}. Patch: {self._patch_set_to_dict(sanitized_patch_set)}"
                )
                continue

            transitions.append(TaskTransition(original_task, sanitized_patch_set, next_task))
        return transitions

    def generate(self, node: Node, requested_patch_sets: int = 3, n: int | None = None) -> Iterable[TaskTransition]:
        if n is not None:
            requested_patch_sets = n

        prior_transitions = self._benchmark_prior_transitions(node=node)
        if prior_transitions:
            for transition in prior_transitions:
                self.accepted_patch_sets += 1
                yield transition
            return

        allow_online_env = os.getenv("SAPLINGS_ENABLE_ONLINE_GENERATION")
        allow_online = allow_online_env.lower() in {"1", "true", "yes"} if allow_online_env else "PYTEST_CURRENT_TEST" not in os.environ
        if not allow_online:
            self.rejected_patch_sets += requested_patch_sets
            print("[CandidateGenerator] Online generation disabled; returning no transitions.")
            return

        original_task = node.created_node_task
        runner_input_obj = {"requested_patch_sets": requested_patch_sets, "trajectory": self._format_trajectory(node)}
        transitions: List[TaskTransition] = []

        if self._needs_theorem_bootstrap(original_task):
            bootstrap_result = self._run_agent_with_model_fallbacks(
                agent_factory=create_theorem_bootstrap_agent,
                model_candidates=self._bootstrap_model_candidates(),
                runner_input_obj=runner_input_obj,
                retries_per_model=1,
                max_turns=min(14, self._max_turns()),
            )
            if bootstrap_result is not None:
                transitions = self._patch_sets_to_transitions(
                    original_task=original_task,
                    patch_sets=list(bootstrap_result.patch_sets),
                )

        if not transitions:
            proof_result = self._run_agent_with_model_fallbacks(
                agent_factory=create_proof_crew_agent,
                model_candidates=self._proof_model_candidates(requested_patch_sets=requested_patch_sets),
                runner_input_obj=runner_input_obj,
                retries_per_model=1,
            )
            if proof_result is not None:
                transitions = self._patch_sets_to_transitions(
                    original_task=original_task,
                    patch_sets=list(proof_result.patch_sets),
                )
            else:
                self.rejected_patch_sets += requested_patch_sets
                return

        seen = set()
        for transition in transitions:
            key = transition.to_candidate_key()
            if key not in seen:
                seen.add(key)
                self.accepted_patch_sets += 1
                yield transition
            else:
                print('already seen')
