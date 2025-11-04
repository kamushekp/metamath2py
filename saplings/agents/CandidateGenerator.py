from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence

from agents import RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded

from saplings.agents.factories import serialize_trajectory_for_runner
from saplings.agents.predefined import TaskResultPayload, create_proof_crew_agent
from saplings.agents.types import Candidate
from saplings.dtos import VerificationOutcome
from saplings.dtos.evaluations.Evaluation import Evaluation
from saplings.dtos.Node import Node, TrajectoryStep
from saplings.dtos.tasks.Patch import PatchSet, apply_patch
from saplings.dtos.tasks.Task import Task
from saplings.dtos.tasks.TaskResult import TaskResult
from saplings.dtos.tasks.TaskTransition import TaskTransition



class CandidateGenerator:
    """
    Encapsulates generation of child candidates for a search node using
    an OpenAI Agents SDK agent.

    The generator handles all payload transformations internally so callers only
    need to provide basic agent configuration data.
    """

    def __init__(
        self,
        *,
        b_factor: int,
        step_max_turns: int
    ) -> None:
        self._b_factor = b_factor
        self._step_max_turns = step_max_turns

    def update_prompt(self, trajectory: List[TrajectoryStep]) -> str:
        return ''

    def _build_agent(self, history: List[TrajectoryStep]) -> Any:
        instructions = self.update_prompt(history)
        return create_proof_crew_agent(
            instructions=instructions,
        )

    def generate(
        self,
        node: Node,
        prefix_steps: Optional[List[TrajectoryStep]] = None,
        n: Optional[int] = None,
    ) -> List[Candidate]:
        sample_count = n if n else self._b_factor
        history = self._build_history(node, prefix_steps)
        agent = self._build_agent(history)
        runner_input = self._prepare_runner_input(node, history)

        candidates: List[Candidate] = []
        seen: set[tuple[Any, ...]] = set()
        attempts = max(sample_count * 3, sample_count)

        for _ in range(attempts):
            try:
                run_result = Runner.run_sync(
                    agent,
                    input=runner_input,
                    config=RunConfig(max_turns=self._step_max_turns),
                )
            except MaxTurnsExceeded:
                continue

            payload = run_result.final_output_as(TaskResultPayload)
            task_result = self._payload_to_task_result(payload)
            transition = self._build_transition(node, task_result)
            if transition is None:
                continue

            key = transition.to_candidate_key()
            if key in seen:
                continue
            seen.add(key)

            candidate = Candidate(
                transition=transition,
                context_items=run_result.to_input_list(),
            )
            candidates.append(candidate)

            if len(candidates) >= sample_count:
                break

        return candidates

    def payload_to_task_result(self, payload: TaskResultPayload) -> TaskResult:
        return self._payload_to_task_result(payload)

    def _build_history(
        self, node: Node, prefix_steps: Optional[List[TrajectoryStep]]
    ) -> List[TrajectoryStep]:
        return list(prefix_steps or []) + node.get_trajectory()

    def _prepare_runner_input(
        self,
        node: Node,
        history: List[TrajectoryStep],
    ) -> List[Any]:
        if node.context_items is not None:
            return list(node.context_items)

        if not history:
            return []

        return serialize_trajectory_for_runner(history)

    def _evaluation_from_payload(
        self, payload: Optional[Any]
    ) -> Optional[Evaluation]:
        if not payload:
            return None
        score = max(0.0, min(payload.score, 10.0)) / 10.0
        return Evaluation(score=score, reasoning=payload.reasoning)

    def _verification_from_payload(
        self, payload: Optional[Any]
    ) -> Optional[VerificationOutcome]:
        if not payload:
            return None
        return VerificationOutcome(
            success=payload.success,
            stage=payload.stage,
            error_message=payload.error_message,
            metadata=dict(payload.metadata),
        )

    def _payload_to_task_result(self, payload: TaskResultPayload) -> TaskResult:
        evaluation = self._evaluation_from_payload(payload.evaluation)
        verification = self._verification_from_payload(payload.verification)
        patch = None
        if getattr(payload, "patch", None):
            patch_items = [p.model_dump() for p in payload.patch]  # type: ignore[attr-defined]
            patch = PatchSet.from_list(patch_items)
        return TaskResult(
            summary=payload.summary,
            patch=patch,
            used_theorems=list(payload.used_theorems),
            verification=verification,
            evaluation=evaluation,
            terminal=payload.terminal,
            artifacts=dict(payload.artifacts),
            metadata=dict(payload.metadata),
        )

    def _build_transition(
        self, node: Node, result: TaskResult
    ) -> Optional[TaskTransition]:
        if not result.patch:
            return None
        task_dict = node.task.to_dict()
        patched = apply_patch(task_dict, result.patch)
        next_task = Task.from_dict(patched)
        return TaskTransition(task=next_task, result=result)
