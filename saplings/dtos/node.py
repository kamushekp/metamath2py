from __future__ import annotations

import math
from collections import deque
from typing import Generator, List, Optional

from saplings.dtos.trajectory_step import TrajectoryStep
from saplings.dtos.evaluations.evaluation import Evaluation
from saplings.dtos.tasks.task import Task
from saplings.dtos.tasks.task_result import TaskResult


class Node(object):
    def __init__(
        self,
        task: Task,
        result: Optional[TaskResult] = None,
        parent: Optional["Node"] = None,
        context_items: Optional[list] = None,
    ):
        self.id = id(self)
        self.task = task
        self.result = result
        self.parent = parent
        self.children: List["Node"] = []
        self.depth = parent.depth + 1 if parent else 1
        self.visits = 0
        self.is_solved = False
        self._value = self.score
        self.context_items = context_items

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        tab = "   "
        bold = "\033[1m"
        red = "\033[91m"
        yellow = "\033[93m"
        green = "\033[92m"
        reset = "\033[0m"

        value_color = red
        if self.value >= 0.33 and self.value < 0.67:
            value_color = yellow
        elif self.value >= 0.67:
            value_color = green

        messages_str = f"{tab}Goal: {self.task.goal}"
        assertion = getattr(self.task.theorem, "assertion", None)
        if assertion:
            messages_str += f"\n{tab}Assertion: {assertion}"
        if self.result:
            messages_str += f"\n{tab}Result: {self.result.summary}"

        node_str = f"{bold}NODE({reset}\n"
        node_str += f"{tab}{bold}ID:{reset} {self.id}"
        node_str += (
            f"\n{tab}{bold}PARENT ID:{reset} {self.parent.id if self.parent else -1}\n"
        )
        node_str += messages_str
        node_str += f"\n{tab}{bold}DEPTH:{reset} {self.depth}"
        node_str += f"\n{tab}{bold}VALUE:{reset} {value_color}{self.value}{reset}"
        node_str += (
            f"\n{tab}{bold}REFLECTION:{reset} {value_color}{self.evaluation.reasoning}{reset}"
        if self.evaluation
            else ""
        )
        node_str += f"\n{bold}){reset}"

        return node_str

    def __lt__(self, other):
        # NOTE: Used by heapq to compare nodes
        return self.score < other.score

    @property
    def score(self) -> float:
        evaluation = self.evaluation
        return evaluation.score if evaluation else 0.0

    @property
    def value(self) -> float:
        """
        Returns the value of this node. For A* and BFS, this is equivalent to self.score.
        For MCTS, this is the score modified by backpropagation.
        """

        return self._value

    @property
    def is_leaf(self) -> bool:
        """
        Returns whether this node is a leaf node.
        """

        return not self.children

    # Removed unused is_user_input accessor

    def set_result(self, result: TaskResult):
        self.result = result
        if result.evaluation:
            self._value = result.evaluation.score
        else:
            self._value = 0.0

    def attach_evaluation(self, evaluation: Evaluation):
        if not self.result:
            raise ValueError("Cannot attach evaluation without a task result.")
        self.result.evaluation = evaluation
        self._value = evaluation.score if evaluation else 0.0

    @property
    def evaluation(self) -> Optional[Evaluation]:
        if not self.result:
            return None
        return self.result.evaluation

    def get_trajectory(self) -> List[TrajectoryStep]:
        steps: List[TrajectoryStep] = []
        node: Optional["Node"] = self
        while node:
            steps.append(TrajectoryStep(task=node.task, result=node.result))
            node = node.parent
        return list(reversed(steps))

    def add_children(self, children: List["Node"]):
        self.children.extend(children)

    def get_best_child(self) -> Optional["Node"]:
        if not self.children:
            return None

        return max(self.children, key=lambda child: child.value)

    def get_leaf_nodes(self) -> Generator["Node", None, None]:
        """
        Get all the leaf nodes rooted at this node.
        """

        nodes = deque([self])
        while nodes:
            node = nodes.popleft()
            if node.is_leaf:
                yield node
            else:
                nodes.extend(node.children)

    def bfs(self) -> Generator["Node", None, None]:
        nodes = deque()
        nodes.append(self)
        while nodes:
            node = nodes.popleft()
            yield node
            for n in node.children:
                nodes.append(n)

    def upper_confidence_bound(self, exploration_weight=1.0):
        """
        Calculates the UCT score. Helps balance exploration vs. exploitation of a branch.
        """

        if not self.parent:
            raise Exception("Root node has no parent")

        if self.visits == 0:
            return self.value

        # TODO: Double-check that division by self.visits is correct here
        exploitation_term = self.value / self.visits
        exploration_term = math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation_term + exploration_weight * exploration_term

    def mark_as_solved(self):
        """
        Marks this node as solved and then marks the whole tree
        as solved.
        """

        node = self
        while node:
            node.is_solved = True
            node = node.parent

    def backpropagate(self):
        """
        Updates the value of this node and its parents.
        """

        reward = self.value
        node = self
        while node:
            node.visits += 1
            node._value = (node.value * (node.visits - 1) + reward) / node.visits
            node = node.parent
