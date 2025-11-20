# Standard library
from typing import Callable, List, Optional

# Local
from saplings.saplings_agents.base_algo import BaseAlgo
from saplings.dtos import Node, Task, TrajectoryStep
from saplings.prompts import AGENT_PROMPT
from database.opensearch_wrapper import TheoremSearchClient


class GreedyAgent(BaseAlgo):
    def __init__(
        self,
        *,
        model_name: Optional[str] = None,
        prompt: str = AGENT_PROMPT,
        b_factor: int = 3,
        max_depth: int = 5,
        threshold: float = 1.0,
        update_prompt: Optional[Callable[[List[TrajectoryStep]], str]] = None,
        theorem_search_client: TheoremSearchClient,
        parallel_tool_calls: bool = False,
        max_tool_call_tokens: int = 2048,
    ):
        super().__init__(
            model_name=model_name,
            prompt=prompt,
            b_factor=b_factor,
            max_depth=max_depth,
            threshold=threshold,
            update_prompt=update_prompt,
            theorem_search_client=theorem_search_client,
            parallel_tool_calls=parallel_tool_calls,
            max_tool_call_tokens=max_tool_call_tokens,
        )

    def should_terminate(self, node: Node) -> bool:
        return self.is_terminal_node(node)

    def run_iter(self, prompt: str, steps: List[TrajectoryStep] | None = None):
        steps = list(steps or [])
        best_node = Node(Task.from_goal(prompt))
        while not self.should_terminate(best_node):
            for item in self.expand(best_node, steps):
                yield item

            best_node = self.get_best_node(best_node)

        trajectory, score, is_solution = (
            best_node.get_trajectory(),
            best_node.score,
            self.is_solution_node(best_node),
        )

        # No logging

        yield (trajectory, score, is_solution)
