"""Utilities for indexing and searching theorem files with OpenSearch."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from opensearchpy import OpenSearch, helpers

LOGGER = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Container for a single search result."""

    path: str
    score: float
    category: str
    line_count: int
    snippet: Optional[str] = None


class TheoremSearchClient:
    """Thin wrapper around :mod:`opensearchpy` tailored for LLM usage.

    The client knows how to ingest the theorem/proof files that live under
    ``database/data`` and exposes a compact API that is convenient for LLM
    agents.  Documents are indexed once and re-used between queries to avoid
    expensive re-ingestion.
    """

    INDEX_STATE_FILENAME = ".index_state.json"

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 9200,
        index_name: str = "metamath-theorems",
        data_dir: Optional[Path] = None,
        dataset_preference: str = "auto",
        http_auth: Optional[Sequence[str]] = None,
        use_ssl: bool = False,
        verify_certs: bool = False,
        ssl_assert_hostname: bool = False,
        ssl_show_warn: bool = False,
    ) -> None:
        """Create a new client.

        Parameters
        ----------
        host, port:
            OpenSearch connection details.
        index_name:
            Name of the index that will store theorem and proof files.
        data_dir:
            Directory that contains a ``data`` folder with the datasets.  When
            omitted, the directory that contains this module is used.
        dataset_preference:
            ``"auto"`` (default) selects ``data/origin`` when it exists and
            falls back to ``data/Examples`` otherwise.  Pass ``"origin"`` or
            ``"examples"`` to force a particular dataset.
        http_auth, use_ssl, verify_certs, ssl_assert_hostname, ssl_show_warn:
            Forwarded to :class:`opensearchpy.OpenSearch` to support secured
            deployments.
        """

        if dataset_preference not in {"auto", "origin", "examples"}:
            raise ValueError(
                "dataset_preference must be 'auto', 'origin' or 'examples'"
            )

        base_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent
        self.data_dir = base_dir / "data"
        self.dataset_preference = dataset_preference
        self.index_name = index_name

        self.client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=http_auth,
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            ssl_assert_hostname=ssl_assert_hostname,
            ssl_show_warn=ssl_show_warn,
        )

        self._data_root = self._resolve_data_root()
        self._state_path = self.data_dir / self.INDEX_STATE_FILENAME

    # ------------------------------------------------------------------
    # Dataset discovery helpers
    # ------------------------------------------------------------------
    def _resolve_data_root(self) -> Path:
        """Return the directory that stores the active dataset."""

        origin = self.data_dir / "origin"
        examples = self.data_dir / "Examples"

        if self.dataset_preference == "origin":
            if not origin.exists():
                raise FileNotFoundError("Requested origin dataset but it does not exist")
            return origin
        if self.dataset_preference == "examples":
            if not examples.exists():
                raise FileNotFoundError("Examples dataset is missing from data directory")
            return examples

        if origin.exists():
            LOGGER.info("Using dataset from %s", origin)
            return origin
        LOGGER.info("Using dataset from %s", examples)
        return examples

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------
    def ensure_index(self, *, force: bool = False) -> bool:
        """Ensure that OpenSearch contains an up-to-date index of all files.

        Returns ``True`` when re-indexing happened, otherwise ``False``.
        """

        self._data_root = self._resolve_data_root()
        current_state = self._load_index_state()
        expected_state = self._collect_dataset_state()

        if not force and current_state == expected_state and self._index_exists():
            LOGGER.debug("Index %s is already up to date", self.index_name)
            return False

        if self._index_exists():
            LOGGER.info("Deleting stale index %s", self.index_name)
            self.client.indices.delete(index=self.index_name)

        LOGGER.info("Creating index %s", self.index_name)
        self.client.indices.create(index=self.index_name, body=self._index_mapping())

        LOGGER.info("Indexing %d files", len(expected_state["files"]))
        helpers.bulk(self.client, self._iter_index_actions())
        self.client.indices.refresh(index=self.index_name)

        self._write_index_state(expected_state)
        return True

    def _index_exists(self) -> bool:
        return bool(self.client.indices.exists(index=self.index_name))

    def _index_mapping(self) -> Dict[str, object]:
        return {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "code_analyzer": {
                            "type": "custom",
                            "tokenizer": "code_tokenizer",
                            "filter": ["code_shingle"],
                        },
                        "code_search_analyzer": {
                            "type": "custom",
                            "tokenizer": "code_tokenizer",
                            "filter": ["code_shingle"],
                        },
                    },
                    "tokenizer": {
                        "code_tokenizer": {
                            "type": "pattern",
                            "pattern": "[^A-Za-z0-9_]+",
                        }
                    },
                    "filter": {
                        "code_shingle": {
                            "type": "shingle",
                            "min_shingle_size": 2,
                            "max_shingle_size": 3,
                            "output_unigrams": True,
                            "token_separator": " ",
                        }
                    },
                }
            },
            "mappings": {
                "properties": {
                    "path": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "code_analyzer",
                        "search_analyzer": "code_search_analyzer",
                        "term_vector": "with_positions_offsets",
                    },
                    "line_count": {"type": "integer"},
                }
            },
        }

    def _collect_dataset_state(self) -> Dict[str, object]:
        files_state: Dict[str, Dict[str, float]] = {}
        for file_path in self._iter_files():
            rel_path = file_path.relative_to(self._data_root).as_posix()
            stat_result = file_path.stat()
            files_state[rel_path] = {
                "mtime": stat_result.st_mtime,
                "size": stat_result.st_size,
            }
        return {
            "index_name": self.index_name,
            "source_root": self._data_root.as_posix(),
            "files": files_state,
        }

    def _iter_files(self) -> Iterable[Path]:
        if not self._data_root.exists():
            raise FileNotFoundError(f"Dataset directory {self._data_root} is missing")
        for file_path in sorted(self._data_root.rglob("*.py")):
            if file_path.is_file():
                yield file_path

    def _iter_index_actions(self) -> Iterable[Dict[str, object]]:
        for file_path in self._iter_files():
            relative = file_path.relative_to(self._data_root)
            rel_path = relative.as_posix()
            category = relative.parts[0] if relative.parts else "unknown"
            content = file_path.read_text(encoding="utf-8")
            line_count = content.count("\n") + 1 if content else 0
            yield {
                "_index": self.index_name,
                "_id": rel_path,
                "_source": {
                    "path": rel_path,
                    "category": category,
                    "content": content,
                    "line_count": line_count,
                },
            }

    def _load_index_state(self) -> Optional[Dict[str, object]]:
        if not self._state_path.exists():
            return None
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("Failed to decode %s; rebuilding index", self._state_path)
            return None

    def _write_index_state(self, state: Dict[str, object]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        context_window: int = 40,
        highlight: bool = True,
        phrase_slop: int = 1,
    ) -> List[SearchResult]:
        """Execute a semantic search query and return matches.

        Parameters
        ----------
        query:
            Natural language text (for example an LLM request).
        top_k:
            Maximum number of documents to return.
        context_window:
            Number of lines to return around the first match for each result.
        highlight:
            When ``True`` the snippet will include basic highlight markup.
        phrase_slop:
            Maximum allowed distance between tokens when evaluating phrase matches.
        """

        body = {
            "size": top_k,
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "content": {
                                    "query": query,
                                    "boost": 4.0,
                                }
                            }
                        },
                        {
                            "match_phrase": {
                                "content": {
                                    "query": query,
                                    "slop": max(0, phrase_slop),
                                    "boost": 6.0,
                                }
                            }
                        },
                        {"match": {"path": {"query": query, "boost": 1.5}}},
                    ],
                    "minimum_should_match": 1,
                }
            },
        }
        if highlight:
            body["highlight"] = {
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"],
                "fields": {"content": {"fragment_size": 400, "number_of_fragments": 1}},
            }

        response = self.client.search(index=self.index_name, body=body)
        results: List[SearchResult] = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            rel_path = source.get("path")
            snippet = None
            if highlight:
                snippet = self._extract_highlight(hit)
            if snippet is None:
                snippet = self._build_context_from_file(rel_path, window=context_window)
            else:
                snippet = self._expand_highlight(rel_path, snippet, window=context_window)
            results.append(
                SearchResult(
                    path=rel_path,
                    score=hit.get("_score", 0.0),
                    category=source.get("category", "unknown"),
                    line_count=source.get("line_count", 0),
                    snippet=snippet,
                )
            )
        return results

    def _extract_highlight(self, hit: Dict[str, object]) -> Optional[str]:
        highlight = hit.get("highlight")
        if not isinstance(highlight, dict):
            return None
        fragments = highlight.get("content")
        if not fragments:
            return None
        return fragments[0]

    def _expand_highlight(self, rel_path: Optional[str], fragment: str, *, window: int) -> str:
        if not rel_path:
            return fragment
        anchor = _strip_highlight_markup(fragment)
        context = self.get_context_by_anchor(rel_path, anchor, window=window)
        if context is None:
            return fragment
        return context["text"]

    def _build_context_from_file(self, rel_path: Optional[str], *, window: int) -> Optional[str]:
        if not rel_path:
            return None
        context = self.get_context(rel_path, center_line=None, window=window)
        if context is None:
            return None
        return context["text"]

    def get_context(
        self,
        rel_path: str,
        *,
        center_line: Optional[int],
        window: int = 40,
    ) -> Optional[Dict[str, object]]:
        """Return a slice of the file around ``center_line``.

        When ``center_line`` is ``None`` the first ``window`` lines are returned.
        """

        file_path = self._data_root / rel_path
        if not file_path.exists():
            LOGGER.warning("Context requested for missing file %s", rel_path)
            return None

        lines = file_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return {"path": rel_path, "start_line": 1, "end_line": 0, "text": ""}

        if center_line is None:
            start_line = 1
        else:
            start_line = max(center_line - window // 2, 1)
        end_line = min(start_line + window - 1, len(lines))
        snippet = "\n".join(lines[start_line - 1 : end_line])
        return {
            "path": rel_path,
            "start_line": start_line,
            "end_line": end_line,
            "text": snippet,
        }

    def get_context_by_anchor(
        self,
        rel_path: str,
        anchor: str,
        *,
        window: int = 40,
    ) -> Optional[Dict[str, object]]:
        """Return context around the first occurrence of ``anchor`` in ``rel_path``."""

        file_path = self._data_root / rel_path
        if not file_path.exists():
            LOGGER.warning("Context requested for missing file %s", rel_path)
            return None
        lines = file_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return None

        for idx, line in enumerate(lines, start=1):
            if anchor in line:
                return self.get_context(rel_path, center_line=idx, window=window)
        return None

    def list_documents(self, *, category: Optional[str] = None) -> List[str]:
        """List the indexed documents optionally filtered by category."""

        self.ensure_index()
        query: Dict[str, object]
        if category:
            query = {"term": {"category": category}}
        else:
            query = {"match_all": {}}

        scan = helpers.scan(
            self.client,
            index=self.index_name,
            query={"query": query, "_source": ["path"]},
        )
        return [hit["_source"]["path"] for hit in scan]

    def delete_index(self) -> None:
        """Delete the index and forget stored state."""

        if self._index_exists():
            self.client.indices.delete(index=self.index_name)
        if self._state_path.exists():
            self._state_path.unlink()

    def ping(self) -> bool:
        """Return ``True`` when OpenSearch responds to a ping request."""

        return bool(self.client.ping())


def _strip_highlight_markup(fragment: str) -> str:
    """Remove OpenSearch highlight markup from ``fragment``."""

    return fragment.replace("<em>", "").replace("</em>", "")

