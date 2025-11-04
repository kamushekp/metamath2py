# Standard library
import heapq
from math import inf
from typing import List

from saplings.agents.BaseAlgo import BaseAlgo
from saplings.dtos import Node, Task, TrajectoryStep


class AStarAgent(BaseAlgo):

    def should_terminate(self, node: Node) -> bool:
        return self.is_solution_node(node)

    def run_iter(self, prompt: str, steps: List[TrajectoryStep] | None = None):
        steps = list(steps or [])
        root_task = Task.from_goal(prompt)
        root_node = Node(root_task)
        best_score = -inf  # Negative scores for max behavior
        frontier = []
        heapq.heappush(frontier, (0, root_node))

        while frontier:
            neg_score, curr_node = heapq.heappop(frontier)
            curr_score = -neg_score  # Convert back to positive score
            if curr_score > best_score:
                best_score = curr_score

            if self.should_terminate(curr_node):
                break

            for item in self.expand(curr_node, steps):
                yield item
            for child in curr_node.children:
                heapq.heappush(frontier, (-child.score, child))
        else:
            pass

        best_node = self.get_best_node(root_node)
        trajectory, score, is_solution = (
            best_node.get_trajectory(),
            best_node.score,
            self.is_solution_node(best_node),
        )

        yield (trajectory, score, is_solution)
