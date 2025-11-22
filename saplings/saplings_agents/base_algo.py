from __future__ import annotations

from typing import Any, Iterable, List, Optional

from saplings.dtos.trajectory_step import TrajectoryStep
from saplings.saplings_agents.candidate_generator import CandidateGenerator
from saplings.dtos.node import Node
from saplings.prompts import AGENT_PROMPT
from saplings.tools.metamath_tools import theorem_search_client


class BaseAlgo(object):
    def __init__(self):
        self.model_name = 'gpt-5-mini'
        self.prompt = AGENT_PROMPT
        self.b_factor = 3
        self.max_depth = 5
        self.threshold = 1.0
        self.max_tool_call_tokens = 2048
        self.step_max_turns = 2
        self._theorem_search_client = theorem_search_client
        self._candidate_generator = CandidateGenerator(
            b_factor=self.b_factor,
            step_max_turns=self.step_max_turns,
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

    def expand(
        self,
        node: Node,
        prefix_steps: Optional[List[TrajectoryStep]] = None,
    ):
        if self.is_terminal_node(node):
            return

        trajectory = list(prefix_steps or []) + node.get_trajectory()
        self.update_prompts(trajectory)

        transitions = self._candidate_generator.generate(node, prefix_steps)
        if not transitions:
            return

        children: List[Node] = []
        for transition in transitions:
            child = Node(
                transition.task,
                result=transition.result,
                parent=node,
            )
            children.append(child)

        for child in children:
            if child.result:
                yield child.result

        node.add_children(children)

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
