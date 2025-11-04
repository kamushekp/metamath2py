from __future__ import annotations

from database.opensearch_wrapper import TheoremSearchClient
from saplings.agents.AStar import AStarAgent
from saplings.agents.Greedy import GreedyAgent
from saplings.agents.MonteCarlo import MonteCarloAgent
from saplings.tools.metamath_tools import (
    create_search_theorems_tool,
    create_verify_proof_tool,
)
from .config import AgentConfig


def _make_tools(cfg: AgentConfig) -> list:
    client = TheoremSearchClient(
        host=cfg.opensearch_host,
        port=cfg.opensearch_port,
        index_name=cfg.index_name,
        dataset_preference=cfg.dataset_preference,
        use_ssl=cfg.opensearch_use_ssl,
        verify_certs=cfg.opensearch_verify_certs,
        http_auth=cfg.opensearch_http_auth,
    )
    return [
        create_search_theorems_tool(client),
        create_verify_proof_tool(),
    ]


def build_agent(cfg: AgentConfig):
    tools = _make_tools(cfg)

    common_kwargs = dict(
        model_name=cfg.model,
        b_factor=cfg.b_factor,
        max_depth=cfg.max_depth,
        threshold=cfg.threshold,
        tools=tools,
        parallel_tool_calls=cfg.parallel_tool_calls,
    )

    algo = cfg.algorithm.lower()
    if algo == "astar":
        return AStarAgent(**common_kwargs)
    if algo == "greedy":
        return GreedyAgent(**common_kwargs)
    if algo == "mcts":
        return MonteCarloAgent(**common_kwargs)
    raise ValueError(f"Unsupported algorithm: {cfg.algorithm}")


def run_proof_search(goal: str, cfg: AgentConfig):
    """Run a search and return (trajectory, score, is_solution). No logging."""

    agent = build_agent(cfg)
    trajectory = []
    score = 0.0
    is_solution = False
    last = None
    for item in agent.run_iter(goal):
        last = item
    if last is not None:
        trajectory, score, is_solution = last
    return trajectory, score, is_solution
