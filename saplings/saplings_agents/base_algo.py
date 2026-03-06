from __future__ import annotations

from typing import Any, Iterable, List

from saplings.dtos.node import Node
from saplings.node_scorer import NodeScorer
from saplings.saplings_agents.candidate_generator import CandidateGenerator
from verification import ProofCheckStage


class BaseAlgo(object):
    def __init__(
        self,
        *,
        requested_patch_sets: int = 3,
        max_depth: int = 5,
        step_max_turns: int | None = None,
    ):
        self.requested_patch_sets = requested_patch_sets
        self.max_depth = max_depth
        self.candidate_generator = CandidateGenerator(step_max_turns=step_max_turns)
        self.node_scorer = NodeScorer()

    def _node_depth(self, node: Node) -> int:
        return len(node.traverse_to_root()) - 1

    def is_terminal_node(self, node: Node) -> bool:
        if self.is_solution_node(node):
            return True
        if self._node_depth(node) >= self.max_depth:
            return True
        return False

    def is_solution_node(self, node: Node) -> bool:
        node_score = node.node_score
        if node_score is None:
            raise ValueError("Node must be scored before solution check")
        if node_score.verify_progress >= 1.0 or node_score.stage == ProofCheckStage.SUCCESS:
            return True
        return False

    def get_best_node(self, root: Node) -> Node:
        if root.node_score is None:
            self._score_node(root)

        best_leaf = root
        best_leaf_score = root.node_score.score
        best_verified: Node | None = None

        stack = [root]
        while stack:
            current = stack.pop()
            if current.children:
                stack.extend(current.children)
                continue

            if current.node_score is None:
                self._score_node(current)
            node_score = current.node_score
            score = node_score.score

            if node_score and node_score.verify_progress >= 1.0:
                if best_verified is None or score > best_verified.node_score.score:
                    best_verified = current

            if score > best_leaf_score:
                best_leaf_score = score
                best_leaf = current

        return best_verified or best_leaf

    def _score_node(self, node: Node) -> None:
        node.node_score = self.node_scorer.score(node)

    def expand(
        self,
        node: Node,
    ) -> Iterable[Node]:
        if self.is_terminal_node(node):
            return

        transitions = list(self.candidate_generator.generate(node, requested_patch_sets=self.requested_patch_sets))
        if not transitions:
            return

        children: List[Node] = []
        for transition in transitions:
            child = Node(
                created_node_task=transition.task_after,
                parent_node=node,
                created_from_patch_set=transition.patch_set,
            )
            self._score_node(child)
            children.append(child)

        node.children.extend(children)

        for child in children:
            yield child

    def run(self, root: Node) -> Any:
        last_item = None
        for item in self.run_iter(root):
            last_item = item
        return last_item

    def run_iter(self, root: Node) -> Iterable[Any]:
        raise NotImplementedError
