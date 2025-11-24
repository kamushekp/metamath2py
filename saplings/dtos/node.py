from __future__ import annotations

from typing import List, Optional

from saplings.dtos.tasks.create_node_task import CreateNodeTask
from saplings.dtos.tasks.patches.patch_set import PatchSet
from saplings.dtos.tasks.task_transition import TaskTransition


class Node(object):
    def __init__(
        self,
        created_node_task: CreateNodeTask,
        parent_node: Optional["Node"] = None,
        created_from_patch_set: Optional[PatchSet] = None,
    ):
        self.id = id(self)
        self.created_node_task = created_node_task
        self.parent_node = parent_node
        self.created_from_patch_set = created_from_patch_set
        self.children: List["Node"] = []

    def get_trajectory(self) -> List[TaskTransition]:
        task_transitions: List[TaskTransition] = []

        nodes_to_root = self.traverse_to_root()
        for parent, child in zip(nodes_to_root, nodes_to_root[1:]):
            transition =  TaskTransition(
                task_before=parent.created_node_task,
                patch_set=child.created_from_patch_set,
                task_after=child.created_node_task,
            )
            task_transitions.append(transition)

        return task_transitions

    def traverse_to_root(self) -> List["Node"]:
        nodes = []
        node = self
        while node:
            nodes.append(node)
            node = node.parent_node

        return list(reversed(nodes))
