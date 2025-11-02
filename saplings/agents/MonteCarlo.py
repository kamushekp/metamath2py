# Standard library
from typing import Any, Callable, List, Optional, Tuple

# Local
from saplings.agents.Base import BaseAgent
from saplings.dtos import Message, Node
from saplings.evaluator import Evaluator
from saplings.prompts import AGENT_PROMPT


class MonteCarloAgent(BaseAgent):
    def __init__(
        self,
        agent_factory: Callable[[str, int], Any],
        model_name: Optional[str] = None,
        evaluator: Optional[Evaluator] = None,
        prompt: str = AGENT_PROMPT,
        b_factor: int = 3,
        max_depth: int = 5,
        threshold: float = 1.0,
        max_rollouts: int = 10,
        verbose: bool = True,
        parallel_tool_calls: bool = False,
        update_prompt: Optional[callable] = None,
    ):
        super().__init__(
            agent_factory,
            model_name,
            evaluator,
            prompt,
            b_factor,
            max_depth,
            threshold,
            verbose,
            parallel_tool_calls,
            update_prompt,
        )
        self.max_rollouts = max_rollouts

    def should_terminate(self, tree: Node, num_rollouts: int) -> bool:
        if tree.is_solved:
            return True

        if num_rollouts >= self.max_rollouts:
            return True

        return False

    def generate_root_node(self, prompt: str, messages: List[Message]):
        """Generates and evaluates the root node in the search tree."""

        node = Node([Message.user(prompt)])
        for item in self.expand(node, messages):
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

    def simulate(self, node: Node, messages: List[Message] | None = None):
        """
        Simulates a rollout from the given node until a terminal node is reached.
        If the terminal node is a solution node, then we mark the tree as solved.
        Otherwise, we backpropagate the score up the tree and a self-reflection.
        """

        messages = list(messages or [])
        curr_node = node.get_best_child()
        if not curr_node:
            return
        while not self.is_terminal_node(curr_node):
            for item in self.expand(curr_node, messages):
                yield item
            curr_node = curr_node.get_best_child()
            if not curr_node:
                break

        if not curr_node:
            return

        self.log(f"\033[1;31mReached terminal node\033[0m\n\n{curr_node}\n")

        if self.is_solution_node(curr_node):
            curr_node.mark_as_solved()
        else:
            # curr_node.self_reflect() # TODO
            curr_node.backpropagate()

    def run_iter(self, prompt: str, messages: List[Message] | None = None):
        self.log(f"Running a Monte Carlo tree search\n\n\033[37m{prompt}\033[0m\n")

        messages = list(messages or [])
        root = None
        for item in self.generate_root_node(prompt, messages):
            root = item
            yield item

        if root is None:
            self.log("\033[1;31mFailed to generate initial trajectory; aborting.\033[0m")
            yield ([], 0.0, False)
            return

        num_rollouts = 0
        while not self.should_terminate(root, num_rollouts):
            node = self.select(root)
            if not node:  # All paths exhausted
                break

            self.log(f"STARTING ROLLOUT (rollout_id={num_rollouts})")

            for item in self.expand(node, messages):
                yield item

            for item in self.simulate(node, messages):
                yield item

            self.log(f"FINISHED ROLLOUT (rollout_id={num_rollouts})")

            num_rollouts += 1

        if root.is_solved:
            self.log("\033[1;32mFound a solution! Terminating search.\033[0m")
        else:
            self.log(
                "\033[1;31mNo solution found. Returning the best trajectory available.\033[0m"
            )

        best_node = self.get_best_node(root)
        messages, score, is_solution = (
            best_node.get_trajectory(),
            best_node.score,
            self.is_solution_node(best_node),
        )

        self.log(
            f"\033[1;32mBest trajectory (score={score}, is_solution={is_solution}):\033[0m\n\n"
            + "\n".join(str(m) for m in messages)
        )

        yield (messages, score, is_solution)
