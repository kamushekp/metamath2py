"""Integration tests for :mod:`database.opensearch_wrapper`."""
from __future__ import annotations

import os
import sys
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

from database.opensearch_wrapper import SearchResult, TheoremSearchClient


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


def test_anchor_context_retrieval(search_client: TheoremSearchClient) -> None:
    """`get_context_by_anchor` should provide a focused window around a step."""

    first_result = search_client.search("Define class B", top_k=1)[0]
    context = search_client.get_context_by_anchor(first_result.path, "class B", window=20)
    assert context is not None
    assert "class B" in context["text"]
    assert context["end_line"] - context["start_line"] <= 20

