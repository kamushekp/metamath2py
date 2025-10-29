from __future__ import annotations

from typing import List, Optional

from saplings.abstract.Evaluator import Evaluator as BaseEvaluator

try:
    from saplings.dtos import Message, Evaluation
except Exception:  # pragma: no cover - import path variations
    from saplings.dtos.Message import Message
    from saplings.dtos.Evaluation import Evaluation


class ProofEvaluator(BaseEvaluator):
    """Evaluator that prioritizes verification outcomes when present.

    If the last tool interaction in the trajectory is a verify_proof call,
    produce a deterministic score:
    - success -> 1.0
    - failure at execution -> 0.3
    - failure at construction/lookup -> 0.2
    - failure at import -> 0.1

    Otherwise, return a neutral mid score with a brief reasoning. This keeps
    the interface compatible with saplings agents and avoids extra LLM calls.
    """

    def __init__(self) -> None:
        pass

    async def run(self, trajectory: List[Message]) -> Evaluation:
        # Find the latest tool output and the preceding tool call
        last_tool_idx = None
        for i in range(len(trajectory) - 1, -1, -1):
            if getattr(trajectory[i], "role", None) == "tool":
                last_tool_idx = i
                break

        if last_tool_idx is None:
            return Evaluation(0.5, "No tool output to evaluate yet.")

        tool_msg = trajectory[last_tool_idx]
        call_msg: Optional[Message] = None
        if last_tool_idx > 0:
            call_msg = trajectory[last_tool_idx - 1]

        # Heuristic: match verify_proof by the tool call name when available
        tool_name = None
        if call_msg and getattr(call_msg, "tool_calls", None):
            try:
                tool_name = call_msg.tool_calls[0].name
            except Exception:
                tool_name = None

        if tool_name == "verify_proof" and getattr(tool_msg, "raw_output", None):
            raw = tool_msg.raw_output
            if isinstance(raw, dict):
                if raw.get("success"):
                    return Evaluation(1.0, "Proof verified successfully.")
                stage = (raw.get("stage") or "").lower()
                if stage == "execution":
                    return Evaluation(0.3, "Execution failed during proof run.")
                if stage in {"construction", "lookup"}:
                    return Evaluation(0.2, f"Failure during {stage} stage.")
                if stage == "import":
                    return Evaluation(0.1, "Import failed for proof module.")
                return Evaluation(0.2, "Verification failed.")

        return Evaluation(0.5, "Awaiting verification or insufficient signal.")

