from __future__ import annotations

from database.opensearch_wrapper import TheoremSearchClient
from saplings.agents.AStar import AStarAgent
from saplings.agents.temporary_disabled.Greedy import GreedyAgent
from saplings.agents.temporary_disabled.MonteCarlo import MonteCarloAgent
from .config import AgentConfig


def _make_search_client(cfg: AgentConfig) -> TheoremSearchClient:
    return TheoremSearchClient(
        host=cfg.opensearch_host,
        port=cfg.opensearch_port,
        index_name=cfg.index_name,
        dataset_preference=cfg.dataset_preference,
        use_ssl=cfg.opensearch_use_ssl,
        verify_certs=cfg.opensearch_verify_certs,
        http_auth=cfg.opensearch_http_auth,
    )


def build_agent(cfg: AgentConfig):
    search_client = _make_search_client(cfg)

    common_kwargs = dict(
        model_name=cfg.model,
        b_factor=cfg.b_factor,
        max_depth=cfg.max_depth,
        threshold=cfg.threshold,
        theorem_search_client=search_client,
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
