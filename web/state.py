from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from saplings.dtos.node import Node
from saplings.dtos.tasks.patches.patch_set import PatchSet
from saplings.dtos.tasks.patches.patch_theorem_state_op import serialize_theorem_op
from saplings.dtos.tasks.patches.patch_proof_state_op import serialize_proof_op
from saplings.saplings_agents.a_star import AStar


class SearchState:
    """In-memory search session controller for stepping through A*."""

    def __init__(self, root_builder: Callable[[], Node]):
        self.root_builder = root_builder
        self.reset()

    def set_builder(self, root_builder: Callable[[], Node]) -> None:
        self.root_builder = root_builder

    def reset(self, *, root: Optional[Node] = None) -> None:
        self.algo = AStar()
        self.root = root or self.root_builder()
        self.algo._init_root_node(self.root)
        self.iterator = iter(self.algo.run_iter(self.root))
        self.nodes: Dict[int, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.finished = False
        self.last_result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self._register_node(self.root)

    def _register_node(self, node: Node) -> None:
        self.nodes[node.id] = self._node_payload(node)
        if node.parent_node is not None:
            edge = self._edge_payload(node.parent_node, node)
            self.edges.append(edge)

    def _node_payload(self, node: Node) -> Dict[str, Any]:
        score = node.node_score.score if node.node_score else None
        node_score = node.node_score
        theorem = node.created_node_task.theorem
        proof = node.created_node_task.proof
        next_step_ideas = node.created_node_task.next_step_ideas
        return {
            "id": str(node.id),
            "label": node.created_node_task.goal or theorem.label or f"Node {node.id}",
            "score": score,
            "depth": node_score.depth if node_score else 0,
            "stage": node_score.stage if node_score else "",
            "verify_progress": node_score.verify_progress if node_score else 0.0,
            "structural_progress": node_score.structural_progress if node_score else 0.0,
            "reasoning": node_score.reasoning if node_score else "",
            "goal": node.created_node_task.goal,
            "next_step_ideas": next_step_ideas,
            "theorem_label": theorem.label,
            "assertion": theorem.assertion,
            "floating_args": theorem.floating_args,
            "essential_args": theorem.essential_args,
            "required_theorem_premises": [
                {"left": req.left, "right": req.right} for req in theorem.required_theorem_premises
            ],
            "proof_steps": [
                {"left": step.left, "right": step.right, "comment": step.comment} for step in proof.steps
            ],
        }

    def _patch_payload(self, patch_set: PatchSet | None) -> Optional[Dict[str, Any]]:
        if patch_set is None:
            return None
        return {
            "change_description": patch_set.change_description,
            "next_step_ideas": patch_set.next_step_ideas,
            "theorem_ops": [
                serialize_theorem_op(op) for op in patch_set.theorem_ops
            ],
            "proof_ops": [
                serialize_proof_op(op) for op in patch_set.proof_ops
            ],
        }

    def _patch_label(self, patch_set: PatchSet | None) -> str:
        if patch_set is None:
            return ""
        return patch_set.change_description or ""

    def _edge_payload(self, parent: Node, child: Node) -> Dict[str, Any]:
        patch_set = child.created_from_patch_set
        label = patch_set.change_description if patch_set else ""
        return {
            "id": f"{parent.id}->{child.id}",
            "source": str(parent.id),
            "target": str(child.id),
            "label": label,
            "patch": self._patch_payload(patch_set),
        }

    def _trajectory_payload(self, transitions: list[Any]) -> list[Dict[str, Any]]:
        trajectory: list[Dict[str, Any]] = []
        for transition in transitions:
            trajectory.append(
                {
                    "goal_before": transition.task_before.goal,
                    "goal_after": transition.task_after.goal,
                    "patch": self._patch_payload(transition.patch_set),
                }
            )
        return trajectory

    def _final_result_payload(self, final_item: Any) -> Dict[str, Any]:
        trajectory, score, is_solution, node_score = final_item
        return {
            "score": score,
            "is_solution": is_solution,
            "reasoning": node_score.reasoning if node_score else "",
            "trajectory": self._trajectory_payload(trajectory),
        }

    def _elements(self) -> List[Dict[str, Dict[str, Any]]]:
        node_elements = [{"data": data} for data in self.nodes.values()]
        edge_elements = [{"data": data} for data in self.edges]
        return node_elements + edge_elements

    def snapshot(self) -> Dict[str, Any]:
        status = "error" if self.error else ("finished" if self.finished else "running")
        patch_stats = self.algo.candidate_generator.stats()
        return {
            "status": status,
            "error": self.error,
            "elements": self._elements(),
            "last_result": self.last_result,
            "counts": {
                "nodes": len(self.nodes),
                "edges": len(self.edges),
                "patches_accepted": patch_stats.get("accepted", 0),
                "patches_rejected": patch_stats.get("rejected", 0),
            },
        }

    def step(self) -> Dict[str, Any]:
        if self.finished or self.error:
            return self.snapshot()

        try:
            item = next(self.iterator)
        except StopIteration:
            self.finished = True
            return self.snapshot()
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            self.finished = True
            self.last_result = {"error": str(exc)}
            return self.snapshot()

        if isinstance(item, Node):
            self._register_node(item)
        else:
            self.finished = True
            self.last_result = self._final_result_payload(item)
        return self.snapshot()
