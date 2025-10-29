from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple

from saplings.agents.AStar import AStarAgent
from saplings.agents.Greedy import GreedyAgent
from saplings.agents.MonteCarlo import MonteCarloAgent
from saplings.agents.COT import COTAgent
from saplings.dtos import Message
from saplings.model import Model

from database.opensearch_wrapper import TheoremSearchClient

from .config import AgentConfig
from .tools import SearchTheoremsTool, VerifyProofTool
from .evaluators import ProofEvaluator


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
        SearchTheoremsTool(client),
        VerifyProofTool(),
    ]


def build_agent(cfg: AgentConfig):
    tools = _make_tools(cfg)
    model = Model(cfg.model)
    evaluator = ProofEvaluator()

    common_kwargs = dict(
        tools=tools,
        model=model,
        evaluator=evaluator,
        b_factor=cfg.b_factor,
        max_depth=cfg.max_depth,
        threshold=cfg.threshold,
        verbose=cfg.verbose,
        tool_choice=cfg.tool_choice,
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


def run_proof_search(goal: str, cfg: AgentConfig, *, out_dir: Path | None = None):
    """Run a search and persist a minimal JSONL log of the trajectory.

    Returns a tuple of (messages, score, is_solution, run_path)
    """

    agent = build_agent(cfg)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out_root = out_dir or Path("out") / "agent_runs" / run_id
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
                    "tool_calls": [
                        getattr(tc, "__dict__", str(tc)) for tc in (item.tool_calls or [])
                    ],
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
                            "tool_calls": [
                                getattr(tc, "__dict__", str(tc))
                                for tc in (m.tool_calls or [])
                            ],
                            "score": m.score,
                        }
                        for m in messages
                    ],
                }
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    return messages, score, is_solution, out_root

