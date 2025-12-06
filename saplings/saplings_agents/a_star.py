# Standard library
import heapq
from itertools import count
from typing import Iterable

from saplings.dtos.node import Node
from saplings.saplings_agents.base_algo import BaseAlgo


class AStar(BaseAlgo):

    def _init_root_node(self, root: Node) -> Node:
        if root.node_score is None:
            self._score_node(root)
        return root

    def run_iter(
        self,
        root: Node,
    ) -> Iterable[object]:
        root_node = self._init_root_node(root)

        tiebreaker = count()
        frontier: list[tuple[float, int, Node]] = []
        heapq.heappush(frontier, (-root_node.node_score.score, next(tiebreaker), root_node))

        best_node = root_node

        while frontier:
            _, _, curr_node = heapq.heappop(frontier)
            if self.is_solution_node(curr_node):
                best_node = curr_node
                break

            for child in self.expand(curr_node):
                yield child

            for child in curr_node.children:
                priority = -child.node_score.score
                heapq.heappush(frontier, (priority, next(tiebreaker), child))

        if not self.is_solution_node(best_node):
            best_node = self.get_best_node(root_node)

        trajectory = best_node.get_trajectory()
        score = best_node.node_score.score
        node_score = best_node.node_score
        is_solution = self.is_solution_node(best_node)

        yield (trajectory, score, is_solution, node_score)
