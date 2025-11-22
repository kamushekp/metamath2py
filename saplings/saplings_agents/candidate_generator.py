from __future__ import annotations

from typing import Any, List, Optional

from agents import RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded

from database.opensearch_wrapper import TheoremSearchClient
from saplings.saplings_agents.factories import serialize_trajectory_for_runner
from saplings.saplings_agents.predefined import TaskResultPayload, create_proof_crew_agent
from saplings.saplings_agents.types import Candidate
from saplings.dtos.evaluations.evaluation import Evaluation
from saplings.dtos.evaluations.verification_outcome import VerificationOutcome
from saplings.dtos.node import Node
from saplings.dtos.tasks.patch import PatchSet, apply_patch
from saplings.dtos.tasks.task import Task
from saplings.dtos.tasks.task_result import TaskResult
from saplings.dtos.tasks.task_transition import TaskTransition
from saplings.dtos.trajectory_step import TrajectoryStep


class CandidateGenerator:

    def __init__(self, theorem_search_client: TheoremSearchClient):
        self._theorem_search_client = theorem_search_client

    def generate(self, node: Node, required_steps: int, prefix_steps: List[TrajectoryStep]) -> List[Candidate]:
        history = self._build_history(node, prefix_steps)
        agent = self._build_agent(history)
        runner_input = self._prepare_runner_input(node, history)

        candidates: List[Candidate] = []
        seen: set[tuple[Any, ...]] = set()

        run_result = Runner.run_sync(
            agent,
            input=runner_input
        )

        payload = run_result.final_output_as(TaskResultPayload)
        task_result = self._payload_to_task_result(payload)
        transition = self._build_transition(node, task_result)

        key = transition.to_candidate_key()
        seen.add(key)

        candidate = Candidate(
            transition=transition,
            context_items=run_result.to_input_list(),
        )
        candidates.append(candidate)
        return candidates

    def _build_prompt(self, history) -> str:
        return ''

    def _build_agent(self, history: List[TrajectoryStep]) -> Any:
        return create_proof_crew_agent(
            theorem_search_client=self._theorem_search_client,
            instructions=self._build_prompt(history) or None,
        )

    def _build_history(self, node: Node, prefix_steps: Optional[List[TrajectoryStep]]
    ) -> List[TrajectoryStep]:
        return list(prefix_steps or []) + node.get_trajectory()

    def _prepare_runner_input(self, node: Node, history: List[TrajectoryStep]) -> List[Any]:
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

    def _build_transition(self, node: Node, result: TaskResult) -> Optional[TaskTransition]:
        if not result.patch:
            return None
        task_dict = node.task.to_dict()
        patched = apply_patch(task_dict, result.patch)
        next_task = Task.from_dict(patched)
        return TaskTransition(task=next_task, result=result)
