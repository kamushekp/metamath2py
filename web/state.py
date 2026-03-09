from __future__ import annotations

import heapq
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from saplings.dtos.evaluations.node_score import NodeScore
from saplings.dtos.node import Node
from saplings.dtos.proof_state import ProofState, ProofStep
from saplings.dtos.search_result import SearchResult
from saplings.dtos.tasks.create_node_task import CreateNodeTask
from saplings.dtos.tasks.patches.patch_set import PatchSet
from saplings.dtos.tasks.patches.patch_theorem_state_op import (
    AddEssential,
    AddFloating,
    AddPremise,
    RemoveEssential,
    RemoveFloating,
    RemovePremise,
    ReplaceAssertion,
    ReplaceEssential,
    ReplaceFloating,
    ReplaceLabel,
    ReplacePremise,
    serialize_theorem_op,
)
from saplings.dtos.tasks.patches.patch_proof_state_op import (
    AddStep,
    RemoveStep,
    ReplaceStep,
    serialize_proof_op,
)
from saplings.dtos.theorem_state import RequiredTheoremPremises, TheoremState
from saplings.saplings_agents.a_star import AStar
from verification import ProofCheckStage


@dataclass
class SearchRunConfig:
    requested_patch_sets: int = 2
    max_depth: int = 13
    step_max_turns: int = 8
    env_overrides: Dict[str, str] = field(default_factory=dict)


class SearchState:
    """In-memory search session controller for stepping through A*."""

    THEOREM_OP_TYPES = {
        "AddFloating": AddFloating,
        "RemoveFloating": RemoveFloating,
        "ReplaceFloating": ReplaceFloating,
        "AddEssential": AddEssential,
        "RemoveEssential": RemoveEssential,
        "ReplaceEssential": ReplaceEssential,
        "AddPremise": AddPremise,
        "RemovePremise": RemovePremise,
        "ReplacePremise": ReplacePremise,
        "ReplaceLabel": ReplaceLabel,
        "ReplaceAssertion": ReplaceAssertion,
    }
    PROOF_OP_TYPES = {
        "AddStep": AddStep,
        "RemoveStep": RemoveStep,
        "ReplaceStep": ReplaceStep,
    }

    def __init__(self, root_builder: Callable[[], Node], run_config: Optional[SearchRunConfig] = None):
        self.root_builder = root_builder
        self.run_config = run_config or SearchRunConfig()
        self.reset()

    def set_builder(self, root_builder: Callable[[], Node]) -> None:
        self.root_builder = root_builder

    def configure_run(self, run_config: Dict[str, Any]) -> None:
        self.run_config = SearchRunConfig(
            requested_patch_sets=max(1, int(run_config.get("requested_patch_sets", self.run_config.requested_patch_sets))),
            max_depth=max(1, int(run_config.get("max_depth", self.run_config.max_depth))),
            step_max_turns=max(1, int(run_config.get("step_max_turns", self.run_config.step_max_turns))),
            env_overrides={k: str(v) for k, v in (run_config.get("env_overrides") or {}).items()},
        )

    def _apply_env_overrides(self) -> None:
        for key, value in self.run_config.env_overrides.items():
            os.environ[key] = value

    def reset(self, *, root: Optional[Node] = None) -> None:
        self._apply_env_overrides()
        self.algo = AStar(
            requested_patch_sets=self.run_config.requested_patch_sets,
            max_depth=self.run_config.max_depth,
            step_max_turns=self.run_config.step_max_turns,
        )
        self.root = root or self.root_builder()
        self.algo._init_root_node(self.root)
        self.frontier: list[tuple[float, int, Node]] = []
        heapq.heappush(self.frontier, (-self.root.node_score.score, 0, self.root))
        self._tiebreaker = 1
        self.step_index = 0
        self.pending_children: list[Node] = []
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.finished = False
        self.last_result: Optional[Dict[str, Any]] = None
        self.last_event: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self._register_node(self.root)

    def _register_node(self, node: Node) -> None:
        self.nodes[str(node.id)] = self._node_payload(node)
        if node.parent_node is not None:
            edge = self._edge_payload(node.parent_node, node)
            self.edges.append(edge)

    def _node_payload(self, node: Node) -> Dict[str, Any]:
        score = node.node_score.score if node.node_score else None
        node_score = node.node_score
        theorem = node.created_node_task.theorem
        proof = node.created_node_task.proof
        next_step_ideas = node.created_node_task.next_step_ideas
        patch_payload = self._patch_payload(node.created_from_patch_set)
        patch_str = json.dumps(patch_payload or {}, ensure_ascii=False, separators=(",", ":"))
        desc = node.created_from_patch_set.change_description if node.created_from_patch_set else ""
        label_parts = [desc, "----------", patch_str, "----------"]
        if score is not None:
            label_parts.append(f"score={score:.3f}")
        label = "\n".join(label_parts)
        stage_value = node_score.stage.name if node_score and node_score.stage else ""
        return {
            "id": str(node.id),
            "label": label,
            "score": score,
            "depth": node_score.depth if node_score else 0,
            "stage": stage_value,
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
            "theorem_ops": [serialize_theorem_op(op) for op in patch_set.theorem_ops],
            "proof_ops": [serialize_proof_op(op) for op in patch_set.proof_ops],
        }

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

    def _final_result_payload(self, final_item: SearchResult) -> Dict[str, Any]:
        trajectory = final_item.trajectory
        node_score = final_item.node_score
        is_solution = final_item.is_solution
        return {
            "score": node_score.score,
            "is_solution": is_solution,
            "reasoning": node_score.reasoning if node_score else "",
            "trajectory": self._trajectory_payload(trajectory),
        }

    def _elements(self) -> List[Dict[str, Dict[str, Any]]]:
        node_elements = [{"data": data} for data in self.nodes.values()]
        edge_elements = [{"data": data} for data in self.edges]
        return node_elements + edge_elements

    def _run_config_payload(self) -> Dict[str, Any]:
        return {
            "requested_patch_sets": self.run_config.requested_patch_sets,
            "max_depth": self.run_config.max_depth,
            "step_max_turns": self.run_config.step_max_turns,
            "env_overrides": self.run_config.env_overrides,
        }

    def snapshot(self) -> Dict[str, Any]:
        status = "error" if self.error else ("finished" if self.finished else "running")
        patch_stats = self.algo.candidate_generator.stats()
        return {
            "status": status,
            "error": self.error,
            "elements": self._elements(),
            "last_result": self.last_result,
            "last_event": self.last_event,
            "run_config": self._run_config_payload(),
            "runtime": {
                "step_index": self.step_index,
                "frontier_size": len(self.frontier),
                "pending_children": len(self.pending_children),
            },
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

        self.step_index += 1

        if self.pending_children:
            next_child = self.pending_children.pop(0)
            self._register_node(next_child)
            self.last_event = {
                "kind": "reveal_pending_child",
                "step_index": self.step_index,
                "node_id": str(next_child.id),
                "parent_id": str(next_child.parent_node.id) if next_child.parent_node else None,
            }
            return self.snapshot()

        skipped_dead_ends = 0
        while self.frontier:
            _, _, current = heapq.heappop(self.frontier)

            if self.algo.is_solution_node(current):
                result = SearchResult(
                    trajectory=current.get_trajectory(),
                    node_score=current.node_score,
                    is_solution=True,
                )
                self.finished = True
                self.last_result = self._final_result_payload(result)
                self.last_event = {
                    "kind": "solution_found",
                    "step_index": self.step_index,
                    "node_id": str(current.id),
                    "skipped_dead_ends": skipped_dead_ends,
                }
                return self.snapshot()

            accepted_before = self.algo.candidate_generator.accepted_patch_sets
            rejected_before = self.algo.candidate_generator.rejected_patch_sets
            children = list(self.algo.expand(current) or [])
            if not children:
                skipped_dead_ends += 1
                continue

            for child in children:
                priority = -child.node_score.score if child.node_score else 0.0
                heapq.heappush(self.frontier, (priority, self._tiebreaker, child))
                self._tiebreaker += 1

            self.pending_children = children[1:]
            self._register_node(children[0])
            accepted_after = self.algo.candidate_generator.accepted_patch_sets
            rejected_after = self.algo.candidate_generator.rejected_patch_sets
            self.last_event = {
                "kind": "expanded_node",
                "step_index": self.step_index,
                "expanded_node_id": str(current.id),
                "new_children": len(children),
                "first_child_id": str(children[0].id),
                "accepted_delta": accepted_after - accepted_before,
                "rejected_delta": rejected_after - rejected_before,
                "skipped_dead_ends": skipped_dead_ends,
            }
            return self.snapshot()

        # No more frontier: report best node found.
        best_node = self.algo.get_best_node(self.root)
        result = SearchResult(
            trajectory=best_node.get_trajectory(),
            node_score=best_node.node_score,
            is_solution=self.algo.is_solution_node(best_node),
        )
        self.finished = True
        self.last_result = self._final_result_payload(result)
        self.last_event = {
            "kind": "frontier_exhausted",
            "step_index": self.step_index,
            "best_node_id": str(best_node.id),
            "is_solution": result.is_solution,
            "skipped_dead_ends": skipped_dead_ends,
        }
        return self.snapshot()

    # --- Persistence helpers ---

    def _serialize_task(self, task: CreateNodeTask) -> Dict[str, Any]:
        return {
            "goal": task.goal,
            "next_step_ideas": task.next_step_ideas,
            "theorem": {
                "label": task.theorem.label,
                "floating_args": task.theorem.floating_args,
                "essential_args": task.theorem.essential_args,
                "required_theorem_premises": [
                    {"left": req.left, "right": req.right} for req in task.theorem.required_theorem_premises
                ],
                "assertion": task.theorem.assertion,
            },
            "proof": {
                "steps": [
                    {"left": step.left, "right": step.right, "comment": step.comment}
                    for step in task.proof.steps
                ],
            },
        }

    def _serialize_node_score(self, node_score: NodeScore | None) -> Dict[str, Any]:
        if node_score is None:
            return {}
        return {
            "score": node_score.score,
            "reasoning": node_score.reasoning,
            "depth": node_score.depth,
            "verify_progress": node_score.verify_progress,
            "structural_progress": node_score.structural_progress,
            "stage": node_score.stage.name if node_score.stage else None,
        }

    def _serialize_node(self, node: Node) -> Dict[str, Any]:
        return {
            "id": str(node.id),
            "parent_id": str(node.parent_node.id) if node.parent_node else None,
            "task": self._serialize_task(node.created_node_task),
            "created_from_patch_set": self._patch_payload(node.created_from_patch_set),
            "node_score": self._serialize_node_score(node.node_score),
        }

    def export_state(self) -> Dict[str, Any]:
        nodes = self._collect_nodes()
        frontier_payload = [
            {"node_id": str(node.id), "priority": priority, "order": order}
            for priority, order, node in self.frontier
        ]
        pending_ids = [str(node.id) for node in self.pending_children]
        candidate_stats = self.algo.candidate_generator.stats()
        return {
            "version": 1,
            "finished": self.finished,
            "error": self.error,
            "last_result": self.last_result,
            "last_event": self.last_event,
            "step_index": self.step_index,
            "tiebreaker": self._tiebreaker,
            "frontier": frontier_payload,
            "pending_children": pending_ids,
            "nodes": [self._serialize_node(node) for node in nodes],
            "candidate_stats": candidate_stats,
            "run_config": self._run_config_payload(),
        }

    def load_state(self, payload: Dict[str, Any]) -> None:
        base_payload = payload.get("payload", payload) if isinstance(payload, dict) else {}
        if not isinstance(base_payload, dict):
            raise ValueError("Некорректный формат файла: ожидался JSON-объект")

        if "nodes" not in base_payload:
            self._load_snapshot_only(base_payload)
            return

        run_config_payload = base_payload.get("run_config") or {}
        if isinstance(run_config_payload, dict):
            self.configure_run(run_config_payload)
        self._apply_env_overrides()

        node_objs: dict[str, Node] = {}
        parent_ids: dict[str, Optional[str]] = {}

        for node_data in base_payload.get("nodes", []):
            node_id = str(node_data["id"])
            parent_ids[node_id] = str(node_data.get("parent_id")) if node_data.get("parent_id") else None
            task = self._deserialize_task(node_data["task"])
            patch_set = self._deserialize_patch_set(node_data.get("created_from_patch_set"))
            node = Node(created_node_task=task, parent_node=None, created_from_patch_set=patch_set)
            node.node_score = self._deserialize_node_score(node_data.get("node_score"))
            try:
                node.id = int(node_id)
            except ValueError:
                node.id = node_id  # type: ignore[assignment]
            node_objs[node_id] = node

        for node_id, parent_id in parent_ids.items():
            node = node_objs[node_id]
            if parent_id is None:
                continue
            parent = node_objs.get(parent_id)
            if parent is None:
                raise ValueError(f"Parent '{parent_id}' for node '{node_id}' not found in save file")
            node.parent_node = parent
            parent.children.append(node)

        roots = [node for node in node_objs.values() if node.parent_node is None]
        if len(roots) != 1:
            raise ValueError("Ожидался один корень графа в сохраненном файле")
        self.algo = AStar(
            requested_patch_sets=self.run_config.requested_patch_sets,
            max_depth=self.run_config.max_depth,
            step_max_turns=self.run_config.step_max_turns,
        )
        for node in node_objs.values():
            if node.node_score is None:
                self.algo._score_node(node)
        self.root = roots[0]
        self.nodes = {}
        self.edges = []
        self.pending_children = []
        self.finished = bool(base_payload.get("finished", False))
        self.error = base_payload.get("error")
        self.last_result = base_payload.get("last_result")
        self.last_event = base_payload.get("last_event")
        self.step_index = int(base_payload.get("step_index", 0))
        self._tiebreaker = int(base_payload.get("tiebreaker", 0))

        if self._tiebreaker <= 0:
            self._tiebreaker = 1

        # Populate nodes/edges in a stable order (depth-first).
        for node in self._collect_nodes():
            self._register_node(node)

        frontier_items = base_payload.get("frontier", [])
        self.frontier = []
        for item in frontier_items:
            node_id = str(item.get("node_id"))
            node = node_objs.get(node_id)
            if node is None:
                continue
            priority = float(item.get("priority", -node.node_score.score if node.node_score else 0.0))
            order = int(item.get("order", self._tiebreaker))
            heapq.heappush(self.frontier, (priority, order, node))
            self._tiebreaker = max(self._tiebreaker, order + 1)

        self.pending_children = []
        for child_id in base_payload.get("pending_children", []):
            node = node_objs.get(str(child_id))
            if node:
                self.pending_children.append(node)

        stats = base_payload.get("candidate_stats") or {}
        self.algo.candidate_generator.accepted_patch_sets = stats.get("accepted", 0)
        self.algo.candidate_generator.rejected_patch_sets = stats.get("rejected", 0)

        if (self.frontier or self.pending_children) and not self.error:
            self.finished = False

    def _load_snapshot_only(self, payload: Dict[str, Any]) -> None:
        """Fallback for legacy files that only contain UI snapshot."""
        self.reset()
        snapshot_payload = payload.get("payload", payload) if isinstance(payload, dict) else {}
        elements = snapshot_payload.get("elements", []) if isinstance(snapshot_payload, dict) else []
        self.nodes = {}
        self.edges = []
        for element in elements:
            data = element.get("data", {})
            if "source" in data and "target" in data:
                self.edges.append(data)
            elif "id" in data:
                self.nodes[data["id"]] = data
        self.last_result = snapshot_payload.get("last_result") if isinstance(snapshot_payload, dict) else None
        self.last_event = snapshot_payload.get("last_event") if isinstance(snapshot_payload, dict) else None
        self.step_index = int(snapshot_payload.get("runtime", {}).get("step_index", 0)) if isinstance(snapshot_payload, dict) else 0
        self.error = snapshot_payload.get("error") if isinstance(snapshot_payload, dict) else None
        self.finished = True
        self.frontier = []
        self.pending_children = []

    def _collect_nodes(self) -> List[Node]:
        seen: set[str] = set()
        ordered: list[Node] = []
        stack = [self.root]
        while stack:
            node = stack.pop()
            node_key = str(node.id)
            if node_key in seen:
                continue
            seen.add(node_key)
            ordered.append(node)
            stack.extend(node.children)
        return ordered

    def _deserialize_task(self, payload: Dict[str, Any]) -> CreateNodeTask:
        theorem_payload = payload.get("theorem", {})
        proof_payload = payload.get("proof", {})
        theorem = TheoremState(
            label=theorem_payload.get("label", ""),
            floating_args=list(theorem_payload.get("floating_args", [])),
            essential_args=list(theorem_payload.get("essential_args", [])),
            required_theorem_premises=[
                RequiredTheoremPremises(left=item.get("left", ""), right=item.get("right", ""))
                for item in theorem_payload.get("required_theorem_premises", [])
            ],
            assertion=theorem_payload.get("assertion", ""),
        )
        proof = ProofState(
            steps=[
                ProofStep(left=step.get("left", ""), right=step.get("right", ""), comment=step.get("comment"))
                for step in proof_payload.get("steps", [])
            ]
        )
        return CreateNodeTask(
            goal=payload.get("goal", ""),
            theorem=theorem,
            proof=proof,
            next_step_ideas=payload.get("next_step_ideas", ""),
        )

    def _deserialize_node_score(self, payload: Dict[str, Any] | None) -> NodeScore | None:
        if not payload or payload.get("score") is None:
            return None
        stage_value = payload.get("stage")
        stage = None
        if stage_value:
            try:
                stage = ProofCheckStage[stage_value]
            except KeyError:
                try:
                    stage = ProofCheckStage(stage_value)
                except Exception:
                    stage = None
        return NodeScore(
            score=payload.get("score", 0.0),
            reasoning=payload.get("reasoning"),
            depth=payload.get("depth", 0),
            verify_progress=payload.get("verify_progress", 0.0),
            structural_progress=payload.get("structural_progress", 0.0),
            stage=stage,
        )

    def _deserialize_patch_set(self, payload: Dict[str, Any] | None) -> PatchSet | None:
        if payload is None:
            return None
        theorem_ops = [self._deserialize_theorem_op(op) for op in payload.get("theorem_ops", [])]
        proof_ops = [self._deserialize_proof_op(op) for op in payload.get("proof_ops", [])]
        return PatchSet(
            change_description=payload.get("change_description", ""),
            next_step_ideas=payload.get("next_step_ideas", ""),
            theorem_ops=theorem_ops,
            proof_ops=proof_ops,
        )

    def _deserialize_theorem_op(self, payload: Dict[str, Any]) -> Any:
        op_type = payload.get("type")
        cls = self.THEOREM_OP_TYPES.get(op_type)
        if cls is None:
            raise ValueError(f"Неизвестный theorem op '{op_type}'")
        data = {k: v for k, v in payload.items() if k != "type"}
        return cls(**data)

    def _deserialize_proof_op(self, payload: Dict[str, Any]) -> Any:
        op_type = payload.get("type")
        cls = self.PROOF_OP_TYPES.get(op_type)
        if cls is None:
            raise ValueError(f"Неизвестный proof op '{op_type}'")
        data = {k: v for k, v in payload.items() if k != "type"}
        return cls(**data)
