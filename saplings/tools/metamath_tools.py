from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from agents import function_tool

from database.opensearch_wrapper import TheoremSearchClient
from saplings.dtos.proof_state import ProofState
from saplings.dtos.theorem_state import TheoremState
from saplings.tools.theorem_recovery import TheoremRecoveryRunner
from verification import ProofCheckResult

_theorem_search_client: TheoremSearchClient | None = None


def _blocked_theorems() -> set[str]:
    raw = os.getenv("SAPLINGS_BLOCK_THEOREMS", "")
    return {item.strip().upper() for item in raw.split(",") if item.strip()}


def _is_blocked_result(path: str) -> bool:
    blocked = _blocked_theorems()
    if not blocked:
        return False
    theorem_name = Path(path).stem.upper()
    return theorem_name in blocked


def _get_search_client() -> TheoremSearchClient | Any:
    """
    Lazily initialize OpenSearch client with fallback to SimpleSearchClient.
    """
    global _theorem_search_client
    if _theorem_search_client is None:
        try:
            client = TheoremSearchClient()
            # Test connection
            if not client.ping():
                 raise ConnectionError("OpenSearch ping failed")
            _theorem_search_client = client
        except Exception as e:
            print(f"Warning: OpenSearch unavailable ({e}). Falling back to SimpleSearchClient.")
            try:
                from saplings.tools.simple_search_client import SimpleSearchClient
                _theorem_search_client = SimpleSearchClient()
            except ImportError:
                 # Should not happen
                raise RuntimeError("Failed to import SimpleSearchClient fallback")

    return _theorem_search_client

@function_tool()
async def search_tool(query: str, top_k: int = 5, context_window: int = 40, highlight: bool = True) -> List[Dict[str, Any]]:
    results = _get_search_client().search(
        query,
        # Fetch extra candidates before filtering blocked theorem ids.
        top_k=max(top_k * 3, top_k + 5),
        context_window=context_window,
        highlight=highlight,
    )
    filtered = [r for r in results if not _is_blocked_result(r.path)]
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
        for r in filtered[:top_k]
    ]


@function_tool()
async def verify_tool(theorem_state: TheoremState, proof_state: ProofState) -> ProofCheckResult:
    """
    Verify a theorem/proof by materializing temporary modules via TheoremRecoveryRunner.
    """

    runner = TheoremRecoveryRunner(theorem_state, proof_state)
    result = runner.verify()
    return result
