from __future__ import annotations

from typing import Any, Dict, List, Annotated

from agents import function_tool

from database.opensearch_wrapper import TheoremSearchClient
from verification import verify_proof

theorem_search_client = TheoremSearchClient()

@function_tool()
async def search_theorems(
    query: Annotated[str, "Natural-language query or target expression."],
    top_k: Annotated[int, "Max number of results to return."] = 5,
    context_window: Annotated[int, "Snippet size in lines."] = 40,
    highlight: Annotated[bool, "Whether to use OpenSearch highlighting."] = True,
) -> List[Dict[str, Any]]:
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


def _derive_module_name(path: str, default_pkg: str) -> str:
    norm = path.replace("\\", "/")
    if "/metamath2py/proofs/" in norm:
        stem = norm.split("/metamath2py/proofs/")[-1].rsplit(".", 1)[0]
        return stem.replace("/", ".")
    return norm.rsplit("/", 1)[-1].rsplit(".", 1)[0]

@function_tool()
async def verify(path_to_pyfile: Annotated[str, "Filesystem path to the proof .py file."]) -> Dict[str, Any]:
    module_name = _derive_module_name(path_to_pyfile, "metamath2py.proofs")
    result = verify_proof(module_name)
    return {
        "statement_name": result.statement_name,
        "success": result.success,
        "stage": result.stage,
        "error_message": result.error_message,
    }
