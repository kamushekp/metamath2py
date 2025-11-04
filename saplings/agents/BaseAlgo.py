from __future__ import annotations

from typing import Any, Callable, Iterable, List, Optional, Sequence

from agents import RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded

from saplings.agents.CandidateGenerator import CandidateGenerator
from saplings.agents.factories import serialize_trajectory_for_runner
from saplings.agents.predefined import TaskResultPayload, create_evaluation_crew_agent
from saplings.dtos.Node import Node, TrajectoryStep
from saplings.prompts import AGENT_PROMPT
from saplings.agents.types import Candidate


class BaseAlgo(object):
    def __init__(
        self,
        *,
        model_name: Optional[str] = None,
        prompt: str = AGENT_PROMPT,
        b_factor: int = 3,
        max_depth: int = 5,
        threshold: float = 1.0,
        evaluation_agent: Optional[Any] = None,
        tools: Optional[Sequence[Any]] = None,
        parallel_tool_calls: bool = False,
        max_tool_call_tokens: int = 2048,
    ):
        self.model_name = model_name
        self.prompt = prompt
        self.b_factor = b_factor
        self.max_depth = max_depth
        self.threshold = threshold
        self.max_tool_call_tokens = max_tool_call_tokens
        self.step_max_turns = 2
        self.eval_max_turns = 2
        self.tools: Sequence[Any] = tuple(tools or ())
        self.parallel_tool_calls = parallel_tool_calls
        self.evaluation_agent = evaluation_agent or create_evaluation_crew_agent(
            model_name=self.model_name,
            max_output_tokens=1024,
        )
        # Candidate generation is delegated to a dedicated helper
        self._candidate_generator = CandidateGenerator(
            model_name=self.model_name,
            tools=self.tools,
            max_output_tokens=self.max_tool_call_tokens,
            b_factor=self.b_factor,
            step_max_turns=self.step_max_turns,
            parallel_tool_calls=self.parallel_tool_calls
        )

    def is_terminal_node(self, node: Node) -> bool:
        if self.is_solution_node(node):
            return True
        if node.result and node.result.terminal:
            return True
        if node.depth >= self.max_depth:
            return True
        return False

    def is_solution_node(self, node: Node) -> bool:
        return (
            node.result is not None
            and node.result.terminal
            and node.score >= self.threshold
        )

    def get_best_node(self, root: Node) -> Node:
        best_score, best_output_score = 0.0, 0.0
        best_node, best_output_node = root, None
        for node in root.bfs():
            if not node.is_leaf:
                continue

            if node.result is not None:
                if node.score >= best_output_score:
                    best_output_score, best_output_node = node.score, node

            if node.score >= best_score:
                best_score, best_node = node.score, node

        if best_output_node:
            return best_output_node

        return best_node

    def update_prompts(self, trajectory: List[TrajectoryStep]):
        self.prompt = self.update_system_prompt(trajectory)
        self._candidate_generator.update_prompt_builder(self.update_system_prompt)

    # ------------------------------------------------------------------
    # Search helpers
    # ------------------------------------------------------------------
    def generate_candidates(
        self, node: Node, prefix_steps: Optional[List[TrajectoryStep]] = None, n: Optional[int] = None
    ) -> List[Candidate]:
        """Deprecated: use the dedicated CandidateGenerator. Kept for compatibility."""
        return self._candidate_generator.generate(node, prefix_steps, n)

    def evaluate(
        self, node: Node, prefix_steps: Optional[List[TrajectoryStep]] = None
    ) -> Node:
        if not node.result:
            return node
        if node.result.evaluation:
            return node

        trajectory = list(prefix_steps or []) + node.get_trajectory()
        runner_input = serialize_trajectory_for_runner(trajectory)
        try:
            run_result = Runner.run_sync(
                self.evaluation_agent,
                input=runner_input,
                config=RunConfig(max_turns=self.eval_max_turns),
            )
        except MaxTurnsExceeded:
            return node
        payload = run_result.final_output_as(TaskResultPayload)
        evaluation_result = self._candidate_generator.payload_to_task_result(payload)

        target = node.result
        if evaluation_result.evaluation:
            target.evaluation = evaluation_result.evaluation
        if evaluation_result.verification and not target.verification:
            target.verification = evaluation_result.verification
        if evaluation_result.metadata:
            target.metadata.update(evaluation_result.metadata)
        if evaluation_result.summary and "evaluation_summary" not in target.metadata:
            target.metadata["evaluation_summary"] = evaluation_result.summary
        if evaluation_result.artifacts:
            target.artifacts.update(evaluation_result.artifacts)
        return node

    def expand(
        self,
        node: Node,
        prefix_steps: Optional[List[TrajectoryStep]] = None,
    ):
        if self.is_terminal_node(node):
            return

        trajectory = list(prefix_steps or []) + node.get_trajectory()
        self.update_prompts(trajectory)

        candidates = self.generate_candidates(node, prefix_steps)
        if not candidates:
            return

        children: List[Node] = []
        for candidate in candidates:
            transition = candidate.transition
            child = Node(
                transition.task,
                result=transition.result,
                parent=node,
                context_items=list(candidate.context_items),
            )
            children.append(child)

        for child in children:
            if child.result and not child.result.evaluation:
                self.evaluate(child, prefix_steps)
            if child.result:
                yield child.result

        node.add_children(children)

    # ------------------------------------------------------------------
    # Execution entrypoints
    # ------------------------------------------------------------------
    def run(
        self, prompt: str, steps: Optional[List[TrajectoryStep]] = None, **kwargs
    ) -> Any:
        last_item = None
        for item in self.run_iter(prompt, steps or [], **kwargs):
            last_item = item
        return last_item

    def run_iter(
        self, prompt: str, steps: Optional[List[TrajectoryStep]] = None, **kwargs
    ) -> Iterable[Any]:
        raise NotImplementedError
