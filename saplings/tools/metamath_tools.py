from __future__ import annotations

from typing import Any, Dict, List, Annotated

from agents import function_tool

from database.opensearch_wrapper import TheoremSearchClient
from saplings.dtos.proof_state import ProofState
from saplings.dtos.theorem_state import TheoremState
from saplings.tools.theorem_recovery import TheoremRecoveryRunner
from verification import ProofCheckResult

from saplings.utils.tool_logger import log_tool_call

theorem_search_client = TheoremSearchClient()

@function_tool()
@log_tool_call
async def search_tool(query: str, top_k: int = 5, context_window: int = 40, highlight: bool = True) -> List[Dict[str, Any]]:
    results = theorem_search_client.search(
        query,
        top_k=top_k,
        context_window=context_window,
        highlight=highlight,
    )
    return [
        {
            "path": r.path,
            "score": r.score,
            "category": r.category,
            "line_count": r.line_count,
            "start_line": r.start_line,
            "end_line": r.end_line,
            "snippet": r.snippet,
        }
        for r in results
    ]


@function_tool()
@log_tool_call
async def verify_tool(theorem_state: TheoremState, proof_state: ProofState) -> ProofCheckResult:
    """
    Verify a theorem/proof by materializing temporary modules via TheoremRecoveryRunner.
    """

    runner = TheoremRecoveryRunner(theorem_state, proof_state)
    result = runner.verify()
    return result
