"""Integration tests for :mod:`database.opensearch_wrapper`."""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

pytest.importorskip(
    "opensearchpy",
    reason="opensearch-py is required to exercise the OpenSearch wrapper.",
)

from database.opensearch_wrapper import (
    SearchResult,
    TheoremSearchClient,
    _highlight_anchor_candidates,
)


@pytest.fixture(scope="module")
def search_client() -> Iterator[TheoremSearchClient]:
    host = os.getenv("OPENSEARCH_HOST", "localhost")
    port = int(os.getenv("OPENSEARCH_PORT", "9200"))
    client = TheoremSearchClient(host=host, port=port, index_name="test-metamath-theorems")

    try:
        if not client.ping():
            pytest.skip("OpenSearch instance is not reachable. Run the Docker image from database/Dockerfile first.")
    except Exception as exc:  # pragma: no cover - network setup is environment specific
        pytest.skip(f"Unable to communicate with OpenSearch: {exc}")

    client.ensure_index(force=True)
    yield client
    client.delete_index()


def test_index_caching(search_client: TheoremSearchClient) -> None:
    """`ensure_index` should become a no-op when nothing changed."""

    indexed = search_client.ensure_index()
    assert indexed is False


def test_list_documents_includes_examples(search_client: TheoremSearchClient) -> None:
    """The example dataset should be discoverable by default."""

    documents = search_client.list_documents()
    assert any(doc.endswith("classes/A1WQA.py") for doc in documents)


def test_search_returns_relevant_snippet(search_client: TheoremSearchClient) -> None:
    """A natural language query should surface matching snippets."""

    results = search_client.search("class A definition", top_k=3)
    assert results, "Expected at least one search result"
    assert isinstance(results[0], SearchResult)
    assert "class A" in (results[0].snippet or "")


def test_search_preserves_identifier_integrity(search_client: TheoremSearchClient) -> None:
    """Identifiers with underscores should remain searchable as a unit."""

    results = search_client.search("class A1WQA_proof", top_k=3, phrase_slop=0)
    assert results, "Expected at least one search result"
    assert "class A1WQA_proof" in (results[0].snippet or "")


def test_search_handles_camel_case_sequences(search_client: TheoremSearchClient) -> None:
    """CamelCase names and method calls should be discoverable."""

    results = search_client.search("MTFCX call", top_k=3, phrase_slop=0)
    assert results, "Expected at least one search result"
    snippet = results[0].snippet or ""
    assert "MTFCX().call" in snippet


def test_anchor_context_retrieval(search_client: TheoremSearchClient) -> None:
    """`get_context_by_anchor` should provide a focused window around a step."""

    first_result = search_client.search("Define class B", top_k=1)[0]
    context = search_client.get_context_by_anchor(first_result.path, "class B", window=20)
    assert context is not None
    assert "class B" in context["text"]
    assert context["end_line"] - context["start_line"] <= 20


def test_highlight_anchor_candidates_include_em_tokens() -> None:
    """Highlighted fragments should yield anchors for emphasized tokens."""

    fragment = '<em>A1WQA_proof</em>(A1WQA):\n    def proof(self):\n        x_1 = "<em>class</em> A"'
    candidates = _highlight_anchor_candidates(fragment)
    assert "A1WQA_proof(A1WQA):" in candidates
    assert "def proof(self):" in candidates
    assert "A1WQA_proof" in candidates


def test_expand_highlight_falls_back_to_emphasized_token() -> None:
    """When the raw fragment fails, emphasized tokens should anchor the context."""

    fragment = '<em>A1WQA_proof</em>(A1WQA):\n    def proof(self):'

    client = TheoremSearchClient.__new__(TheoremSearchClient)

    def fake_get_context(self: TheoremSearchClient, rel_path: str, anchor: str, *, window: int):
        if anchor == "A1WQA_proof":
            return {"text": "class A1WQA_proof(A1WQA):\n    def proof(self):"}
        return None

    client.get_context_by_anchor = types.MethodType(fake_get_context, client)

    expanded = client._expand_highlight("dummy/path.py", fragment, window=10)
    assert "class A1WQA_proof" in expanded

