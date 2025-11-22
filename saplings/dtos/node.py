from __future__ import annotations

from typing import List, Optional, Iterable

from saplings.dtos.tasks import TaskTransition, PatchSet, CreateNodeTask


class Node(object):
    def __init__(self, created_node_task: CreateNodeTask, parent_node: Optional["Node"] = None, created_from_patch_set: Optional[PatchSet] = None):
        self.id = id(self)
        self.created_node_task = created_node_task
        self.parent_node =  parent_node
        self.created_from_patch_set = created_from_patch_set
        self.children: List["Node"] = []

    def get_trajectory(self) -> List[TaskTransition]:
        task_transitions: List[TaskTransition] = []

        for node in self.traverse_to_root():
            pass


    def traverse_to_root(self) -> List["Node"]:
        nodes = []
        node = self
        while node:
            nodes.append(node)
            node = node.parent_node

        return list(reversed(nodes))
