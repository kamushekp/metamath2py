from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


SearchAlgo = Literal["astar", "greedy", "mcts", "cot"]


@dataclass
class AgentConfig:
    """Configuration for the proof-search agent.

    - algorithm: selects the saplings search strategy. Use "astar" by default.
    - b_factor: branching factor (candidate tool calls per expansion).
    - max_depth: maximum search depth.
    - threshold: score threshold to consider a node a solution.
    - model: LLM model id passed to saplings Model (via liteLLM).
    - verbose: enable saplings logs.
    - tool_choice: LLM tool choice policy ("auto" or "required").
    - parallel_tool_calls: whether to allow parallel tool calls.
    - index_name: OpenSearch index name to query (read-only expected).
    - dataset_preference: dataset selection for TheoremSearchClient.
    """

    algorithm: SearchAlgo = "astar"
    b_factor: int = 3
    max_depth: int = 6
    threshold: float = 1.0
    model: str = "gpt-5-mini"
    verbose: bool = True
    tool_choice: str = "auto"
    parallel_tool_calls: bool = False

    # Theorem search settings
    index_name: str = "metamath-theorems"
    dataset_preference: str = "auto"
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False
    opensearch_http_auth: Optional[tuple[str, str]] = None

