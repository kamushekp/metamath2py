from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from database.opensearch_wrapper import TheoremSearchClient
from paths import agent_runs_folder_path
from saplings.agents.AStar import AStarAgent
from saplings.agents.COT import COTAgent
from saplings.agents.Greedy import GreedyAgent
from saplings.agents.MonteCarlo import MonteCarloAgent
from saplings.agents.factories import create_agent
from saplings.dtos import Message
from saplings.evaluator import Evaluator
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


def _make_search_agent_factory(cfg: AgentConfig, tools: list):
    def factory(prompt: str, max_output_tokens: int):
        return create_agent(
            name="Saplings Search Agent",
            instructions=prompt,
            tools=tools,
            model_name=cfg.model,
            max_output_tokens=max_output_tokens,
            temperature=1.0,
            parallel_tool_calls=cfg.parallel_tool_calls,
        )

    return factory


def build_agent(cfg: AgentConfig):
    tools = _make_tools(cfg)
    evaluator = Evaluator(model_name=cfg.model)
    agent_factory = _make_search_agent_factory(cfg, tools)

    common_kwargs = dict(
        agent_factory=agent_factory,
        model_name=cfg.model,
        evaluator=evaluator,
        b_factor=cfg.b_factor,
        max_depth=cfg.max_depth,
        threshold=cfg.threshold,
        verbose=cfg.verbose,
        parallel_tool_calls=cfg.parallel_tool_calls,
    )

    algo = cfg.algorithm.lower()
    if algo == "astar":
        return AStarAgent(**common_kwargs)
    if algo == "greedy":
        return GreedyAgent(**common_kwargs)
    if algo == "mcts":
        return MonteCarloAgent(**common_kwargs)
    if algo == "cot":
        # ReAct/CoT style – no evaluator
        common_kwargs.pop("evaluator", None)
        return COTAgent(**common_kwargs)
    raise ValueError(f"Unsupported algorithm: {cfg.algorithm}")


def run_proof_search(goal: str, cfg: AgentConfig):
    """Run a search and persist a minimal JSONL log of the trajectory.

    Returns a tuple of (messages, score, is_solution, run_path)
    """

    agent = build_agent(cfg)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out_root = Path(agent_runs_folder_path) / run_id
    out_root.mkdir(parents=True, exist_ok=True)

    (Path(out_root) / "config.json").write_text(
        json.dumps(asdict(cfg), indent=2), encoding="utf-8"
    )
    log_path = Path(out_root) / "log.jsonl"

    with log_path.open("w", encoding="utf-8") as fp:
        for item in agent.run_iter(goal):
            if isinstance(item, Message):
                record = {
                    "event": "tool" if item.role == "tool" else "assistant",
                    "content": item.content,
                    "score": item.score,
                }
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            else:
                # Final result: (messages, score, is_solution)
                messages, score, is_solution = item
                record = {
                    "event": "final",
                    "score": score,
                    "is_solution": bool(is_solution),
                    "messages": [
                        {
                            "role": m.role,
                            "content": m.content,
                            "score": m.score,
                        }
                        for m in messages
                    ],
                }
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    return messages, score, is_solution, out_root
