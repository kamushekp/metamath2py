from __future__ import annotations

from typing import Any, Dict, List, Optional

from saplings.abstract.Tool import Tool

from database.opensearch_wrapper import TheoremSearchClient
from verification import verify_proof


class SearchTheoremsTool(Tool):
    """Function-style tool to search the fixed Metamath theorem corpus.

    Aligned with OpenAI Agents function tools: has name/description/parameters and
    returns string-formatted output while preserving a structured raw representation
    for downstream evaluators.
    """

    def __init__(
        self,
        client: TheoremSearchClient,
        *,
        name: str = "search_theorems",
        description: str = (
            "Search the fixed Metamath theorem corpus and return relevant snippets."
        ),
    ) -> None:
        self._client = client
        self.name = name
        self.description = description
        self.parameters = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language query or target expression.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Max number of results to return.",
                },
                "context_window": {
                    "type": "integer",
                    "description": "Snippet size in lines.",
                },
                "highlight": {
                    "type": "boolean",
                    "description": "Whether to use OpenSearch highlighting.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        }
        self.is_terminal = False

    async def run(
        self,
        *,
        query: str,
        top_k: int = 5,
        context_window: int = 40,
        highlight: bool = True,
        trajectory: Optional[list] = None,
    ) -> Any:
        results = self._client.search(
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

    def format_output(self, output: Any) -> str:
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


class VerifyProofTool(Tool):
    """Function-style tool to verify a proof module given a file path.

    Returns both a compact human string and a structured result for evaluators.
    Marked as terminal since a success typically ends the search.
    """

    def __init__(
        self,
        *,
        default_package: str = "metamath2py.proofs",
        name: str = "verify_proof",
        description: str = (
            "Import the given proof module and execute its proof() method."
        ),
    ) -> None:
        self._default_package = default_package
        self.name = name
        self.description = description
        self.parameters = {
            "type": "object",
            "properties": {
                "path_to_pyfile": {
                    "type": "string",
                    "description": "Filesystem path to the proof .py file.",
                },
                "package": {
                    "type": "string",
                    "description": "Python package that contains the module.",
                },
            },
            "required": ["path_to_pyfile"],
            "additionalProperties": False,
        }
        self.is_terminal = True

    async def run(
        self,
        *,
        path_to_pyfile: str,
        package: Optional[str] = None,
        trajectory: Optional[list] = None,
    ) -> Any:
        module_name = self._derive_module_name(path_to_pyfile, package or self._default_package)
        result = verify_proof(module_name, package=package or self._default_package)
        return {
            "statement_name": result.statement_name,
            "success": result.success,
            "stage": result.stage,
            "error_message": result.error_message,
        }

    def format_output(self, output: Any) -> str:
        if not isinstance(output, dict):
            return str(output)
        if output.get("success"):
            return f"Verification OK: {output.get('statement_name')}"
        return (
            f"Verification FAIL at stage {output.get('stage')}: "
            f"{output.get('error_message') or ''}"
        )

    @staticmethod
    def _derive_module_name(path: str, default_package: str) -> str:
        norm = path.replace("\\", "/")
        if "/metamath2py/proofs/" in norm:
            stem = norm.split("/metamath2py/proofs/")[-1].rsplit(".", 1)[0]
            return stem.replace("/", ".")
        return norm.rsplit("/", 1)[-1].rsplit(".", 1)[0]

