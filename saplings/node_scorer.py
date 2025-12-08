from __future__ import annotations

from math import log1p
from typing import Optional

from saplings.dtos.evaluations.node_score import NodeScore
from saplings.dtos.node import Node
from saplings.tools.theorem_recovery import TheoremRecoveryRunner
from verification import ProofCheckResult, ProofCheckStage

class NodeScorer:
    """
    Compute a heuristic utility score for a Node based on:
    - verification progress using TheoremRecoveryRunner / ProofCheckResult
    - simple structural progress signals from theorem/proof state
    - a mild penalty for depth (longer paths without progress are worse)

    Higher scores indicate more promising nodes.
    """

    def __init__(self):
        self.w_verify, self.w_structural, self.w_depth = 0.7, 0.25, 0.05

    def score(self, node: Node) -> NodeScore:
        """Compute a NodeScore for the given node."""

        depth = len(node.traverse_to_root()) - 1

        theorem_state = node.created_node_task.theorem
        proof_state = node.created_node_task.proof

        runner = TheoremRecoveryRunner(theorem_state, proof_state)
        verify_result = runner.verify()

        verify_progress = self._verify_progress(verify_result)
        structural_progress = self._structural_progress(node)
        depth_penalty = log1p(depth)

        utility = self.w_verify * verify_progress + self.w_structural * structural_progress - self.w_depth * depth_penalty

        reasoning_parts = [f"depth={depth}", f"verify_progress={verify_progress:.3f}",
                           f"structural_progress={structural_progress:.3f}", f"stage={verify_result.stage.value}"]
        reasoning = "; ".join(reasoning_parts)

        return NodeScore(
            score=utility,
            reasoning=reasoning,
            depth=depth,
            verify_progress=verify_progress,
            structural_progress=structural_progress,
            stage=verify_result.stage,
        )

    def _verify_progress(self, result: ProofCheckResult) -> float:
        if result is None:
            return 0.0

        if result.success:
            return 1.0

        stage_weights: dict[ProofCheckStage, float] = {
            ProofCheckStage.IMPORT: 0.1,
            ProofCheckStage.LOOKUP: 0.2,
            ProofCheckStage.CONSTRUCTION: 0.4,
            ProofCheckStage.EXECUTION: 0.7,
            ProofCheckStage.SUCCESS: 1.0,
        }

        score = stage_weights[result.stage]
        return score

    def _structural_progress(self, node: Node) -> float:
        theorem = node.created_node_task.theorem
        proof = node.created_node_task.proof

        required = theorem.required_theorem_premises
        if not required:
            return 0.0

        used_hypotheses: set[str] = set()
        for hypothesis in required:
            for step in proof.steps:
                step_right = step.right
                if (
                    step_right == hypothesis.right
                    or f"self.{hypothesis.left}" in step_right
                    or f'"{hypothesis.left}"' in step_right
                    or f"'{hypothesis.left}'" in step_right
                ):
                    used_hypotheses.add(hypothesis.left)
                    break

        return len(used_hypotheses) / len(required)
