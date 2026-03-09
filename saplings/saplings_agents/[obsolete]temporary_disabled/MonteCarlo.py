# Standard library
from typing import Callable, List, Optional

# Local
from saplings.saplings_agents.base_algo import BaseAlgo
from saplings.dtos import Node, Task, TaskTransition
from saplings.prompts import AGENT_PROMPT
from database.opensearch_wrapper import TheoremSearchClient


class MonteCarloAgent(BaseAlgo):
    def __init__(
        self,
        *,
        model_name: Optional[str] = None,
        prompt: str = AGENT_PROMPT,
        b_factor: int = 3,
        max_depth: int = 5,
        threshold: float = 1.0,
        max_rollouts: int = 10,
        update_prompt: Optional[Callable[[List[TaskTransition]], str]] = None,
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
        self.max_rollouts = max_rollouts

    def should_terminate(self, tree: Node, num_rollouts: int) -> bool:
        if tree.is_solved:
            return True

        if num_rollouts >= self.max_rollouts:
            return True

        return False

    def generate_root_node(self, prompt: str, steps: List[TaskTransition]):
        """Generates and evaluates the root node in the search tree."""

        node = Node(Task.from_goal(prompt))
        for item in self.expand(node, steps):
            yield item
        yield node

    def has_non_terminal_leaves(self, root: Node) -> bool:
        leaf_nodes = root.get_leaf_nodes()
        return any(not self.is_terminal_node(node) for node in leaf_nodes)

    def select(self, root: Node) -> Optional[Node]:
        """
        Selects the best (leaf) node to expand using the UCB algorithm. If all paths in
        the tree have been exhausted, this returns `None`.
        """

        node = root
        while node and not node.is_leaf:
            non_terminal_children = (
                child for child in node.children if not self.is_terminal_node(child)
            )
            viable_children = (
                child
                for child in non_terminal_children
                if self.has_non_terminal_leaves(child) or child.is_leaf
            )  # Leaf nodes, or subtrees with non-terminal leaves
            node = max(
                viable_children,
                key=lambda child: child.upper_confidence_bound(),
                default=None,
            )

        return node

    def simulate(self, node: Node, steps: List[TaskTransition] | None = None):
        """
        Simulates a rollout from the given node until a terminal node is reached.
        If the terminal node is a solution node, then we mark the tree as solved.
        Otherwise, we backpropagate the score up the tree and a self-reflection.
        """

        steps = list(steps or [])
        curr_node = node.get_best_child()
        if not curr_node:
            return
        while not self.is_terminal_node(curr_node):
            for item in self.expand(curr_node, steps):
                yield item
            curr_node = curr_node.get_best_child()
            if not curr_node:
                break

        if not curr_node:
            return

        # No logging

        if self.is_solution_node(curr_node):
            curr_node.mark_as_solved()
        else:
            # curr_node.self_reflect() # TODO
            curr_node.backpropagate()

    def run_iter(self, prompt: str, steps: List[TaskTransition] | None = None):
        steps = list(steps or [])
        root = None
        for item in self.generate_root_node(prompt, steps):
            root = item
            yield item

        if root is None:
            yield ([], 0.0, False)
            return

        num_rollouts = 0
        while not self.should_terminate(root, num_rollouts):
            node = self.select(root)
            if not node:  # All paths exhausted
                break

            for item in self.expand(node, steps):
                yield item

            for item in self.simulate(node, steps):
                yield item

            num_rollouts += 1

        # No logging

        best_node = self.get_best_node(root)
        trajectory, score, is_solution = (
            best_node.get_trajectory(),
            best_node.score,
            self.is_solution_node(best_node),
        )

        # No logging

        yield (trajectory, score, is_solution)
