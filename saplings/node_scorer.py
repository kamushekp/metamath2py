from __future__ import annotations

from math import log1p
from typing import Optional

from saplings.dtos.evaluations.node_score import NodeScore
from saplings.dtos.node import Node
from saplings.tools.theorem_recovery import TheoremRecoveryRunner
from verification import ProofCheckResult

class NodeScorer:
    """
    Compute a heuristic utility score for a Node based on:
    - verification progress using TheoremRecoveryRunner / ProofCheckResult
    - simple structural progress signals from theorem/proof state
    - a mild penalty for depth (longer paths without progress are worse)

    Higher scores indicate more promising nodes.
    """

    def __init__(
        self,
        w_verify: float = 0.7,
        w_structural: float = 0.25,
        w_depth: float = 0.05,
    ):
        self.w_verify = w_verify
        self.w_structural = w_structural
        self.w_depth = w_depth

    def score(self, node: Node) -> NodeScore:
        """Compute a NodeScore for the given node."""

        depth = len(node.traverse_to_root()) - 1

        theorem_state = node.created_node_task.theorem
        proof_state = node.created_node_task.proof

        verify_result: Optional[ProofCheckResult] = None
        try:
            runner = TheoremRecoveryRunner(theorem_state, proof_state)
            verify_result = runner.verify()
        except Exception:
            verify_result = None

        verify_progress = self._verify_progress(verify_result)
        structural_progress = self._structural_progress(node)
        depth_penalty = log1p(depth)

        utility = (
            self.w_verify * verify_progress
            + self.w_structural * structural_progress
            - self.w_depth * depth_penalty
        )

        reasoning_parts = [
            f"depth={depth}",
            f"verify_progress={verify_progress:.3f}",
            f"structural_progress={structural_progress:.3f}",
        ]
        if verify_result is not None:
            reasoning_parts.append(f"stage={verify_result.stage}")
        reasoning = "; ".join(reasoning_parts)

        return NodeScore(
            score=utility,
            reasoning=reasoning,
            depth=depth,
            verify_progress=verify_progress,
            structural_progress=structural_progress,
            stage=verify_result.stage if verify_result is not None else "",
        )

    def _verify_progress(self, result: Optional[ProofCheckResult]) -> float:
        if result is None:
            return 0.0

        if result.success:
            return 1.0

        stage_weights = {
            "import": 0.1,
            "lookup": 0.2,
            "construction": 0.4,
            "execution": 0.7,
            "success": 1.0,
        }
        return stage_weights.get(result.stage, 0.0)

    def _structural_progress(self, node: Node) -> float:
        theorem = node.created_node_task.theorem
        proof = node.created_node_task.proof

        total_required = len(theorem.required_theorem_premise_premises)
        if total_required == 0:
            base_ratio = 0.0
        else:
            right_values = {req.right for req in theorem.required_theorem_premise_premises}
            used = sum(1 for step in proof.steps if step.right in right_values)
            base_ratio = used / total_required

        depth = len(node.traverse_to_root()) - 1
        max_depth_for_bonus = 10
        depth_factor = min(depth, max_depth_for_bonus) / max_depth_for_bonus

        return 0.7 * base_ratio + 0.3 * depth_factor
