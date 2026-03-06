from __future__ import annotations

import hashlib
from math import log1p
import re

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
        self.tie_break_span = 0.01  # keep tiny to only break ties

    def score(self, node: Node) -> NodeScore:
        """Compute a NodeScore for the given node."""

        depth = len(node.traverse_to_root()) - 1

        theorem_state = node.created_node_task.theorem
        proof_state = node.created_node_task.proof

        runner = TheoremRecoveryRunner(theorem_state, proof_state)
        verify_result = runner.verify()

        verify_progress = self._verify_progress(verify_result)
        structural_progress, structural_details = self._structural_progress(node)
        depth_penalty = log1p(depth)

        tie_break = self._tie_breaker(node)
        utility = (
            self.w_verify * verify_progress
            + self.w_structural * structural_progress
            - self.w_depth * depth_penalty
            + tie_break
        )

        reasoning_parts = [
            f"depth={depth}",
            f"verify_progress={verify_progress:.3f}",
            f"structural_progress={structural_progress:.3f}",
            f"premise_coverage={structural_details['premise_coverage']:.3f}",
            f"dependency_consistency={structural_details['dependency_consistency']:.3f}",
            f"proof_growth={structural_details['proof_growth']:.3f}",
            f"stage={verify_result.stage.value}",
            f"tie_break={tie_break:.4f}",
        ]
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

        return stage_weights[result.stage]

    def _tie_breaker(self, node: Node) -> float:
        """
        Deterministic, tiny jitter in [-tie_break_span/2, tie_break_span/2] to break score ties.
        Based on a stable hash of the node's goal/theorem label/proof steps so equal content yields equal jitter.
        """

        task = node.created_node_task
        proof_repr = "|".join(f"{step.left}->{step.right}#{step.comment or ''}" for step in task.proof.steps)
        base = f"{task.goal}|{task.theorem.label}|{proof_repr}"

        digest = hashlib.sha256(base.encode("utf-8")).digest()
        normalized = int.from_bytes(digest[:8], "big") / (1 << 64)
        return (normalized - 0.5) * self.tie_break_span

    def _structural_progress(self, node: Node) -> tuple[float, dict[str, float]]:
        theorem = node.created_node_task.theorem
        proof = node.created_node_task.proof

        premise_coverage = self._premise_coverage(theorem=theorem, proof=proof)
        dependency_consistency = self._dependency_consistency(proof=proof)
        proof_growth = self._proof_growth(theorem=theorem, proof=proof)

        # Weighted blend that better separates nodes with identical verifier stage.
        structural_progress = (
            0.5 * premise_coverage
            + 0.3 * dependency_consistency
            + 0.2 * proof_growth
        )
        return structural_progress, {
            "premise_coverage": premise_coverage,
            "dependency_consistency": dependency_consistency,
            "proof_growth": proof_growth,
        }

    def _premise_coverage(self, *, theorem, proof) -> float:
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

    def _dependency_consistency(self, *, proof) -> float:
        """
        Fraction of intermediate variable references that point to already-defined steps.
        """

        defined_steps: set[str] = set()
        total_refs = 0
        resolved_refs = 0

        for step in proof.steps:
            refs = re.findall(r"\bx_?\d+\b", step.right)
            for ref in refs:
                total_refs += 1
                if ref in defined_steps:
                    resolved_refs += 1
            defined_steps.add(step.left)

        if total_refs == 0:
            return 1.0 if proof.steps else 0.0
        return resolved_refs / total_refs

    def _proof_growth(self, *, theorem, proof) -> float:
        """
        Smooth progress estimate based on proof length and theorem shape.
        """

        step_count = len(proof.steps)
        target_steps = max(1, len(theorem.floating_args) + len(theorem.essential_args) + 1)
        return min(1.0, log1p(step_count) / log1p(target_steps))
