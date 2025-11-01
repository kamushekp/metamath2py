from __future__ import annotations

from typing import Any, Dict, List, Optional, Annotated

from agents import FunctionTool, function_tool

from database.opensearch_wrapper import TheoremSearchClient
from verification import verify_proof


def _format_search_results(output: Any) -> str:
    if not output:
        return "No results."
    lines: List[str] = []
    for i, r in enumerate(output, start=1):
        loc = ""
        if r.get("start_line") and r.get("end_line"):
            loc = f" [{r['start_line']}-{r['end_line']}]"
        lines.append(
            f"{i}. {r['path']} (score={r['score']:.2f}){loc}\n{(r.get('snippet') or '').strip()}"
        )
    return "\n\n".join(lines)


def create_search_theorems_tool(
    client: TheoremSearchClient,
    *,
    name: str = "search_theorems",
) -> FunctionTool:
    @function_tool(name_override=name)
    async def search_theorems(
        query: Annotated[str, "Natural-language query or target expression."],
        top_k: Annotated[int, "Max number of results to return."] = 5,
        context_window: Annotated[int, "Snippet size in lines."] = 40,
        highlight: Annotated[bool, "Whether to use OpenSearch highlighting."] = True,
    ) -> List[Dict[str, Any]]:
        results = client.search(
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

    tool = search_theorems
    setattr(tool, "saplings_is_terminal", False)
    setattr(tool, "saplings_format_output", _format_search_results)
    return tool


def _format_verification(output: Any) -> str:
    if not isinstance(output, dict):
        return str(output)
    if output.get("success"):
        return f"Verification OK: {output.get('statement_name')}"
    return (
        f"Verification FAIL at stage {output.get('stage')}: "
        f"{output.get('error_message') or ''}"
    )


def create_verify_proof_tool(
    *,
    default_package: str = "metamath2py.proofs",
    name: str = "verify_proof",
) -> FunctionTool:
    def _derive_module_name(path: str, default_pkg: str) -> str:
        norm = path.replace("\\", "/")
        if "/metamath2py/proofs/" in norm:
            stem = norm.split("/metamath2py/proofs/")[-1].rsplit(".", 1)[0]
            return stem.replace("/", ".")
        return norm.rsplit("/", 1)[-1].rsplit(".", 1)[0]

    @function_tool(name_override=name)
    async def verify(
        path_to_pyfile: Annotated[str, "Filesystem path to the proof .py file."],
        package: Annotated[
            Optional[str], "Python package that contains the module."
        ] = None,
    ) -> Dict[str, Any]:
        module_name = _derive_module_name(path_to_pyfile, package or default_package)
        result = verify_proof(module_name)
        return {
            "statement_name": result.statement_name,
            "success": result.success,
            "stage": result.stage,
            "error_message": result.error_message,
        }

    tool = verify
    setattr(tool, "saplings_is_terminal", True)
    setattr(tool, "saplings_format_output", _format_verification)
    return tool
