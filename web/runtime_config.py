from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping


@dataclass
class WebRuntimeConfig:
    goal: str
    next_step_ideas: str = ""
    proof_steps: List[str] = field(default_factory=list)
    max_steps: int = 100
    step_delay_ms: int = 60
    step_log_enabled: bool = True
    step_log_path: str = ""
    step_log_truncate_on_start: bool = True
    run_config: Dict[str, Any] = field(default_factory=dict)

    def form_payload(self) -> Dict[str, str]:
        return {
            "goal": self.goal,
            "next_step_ideas": self.next_step_ideas,
            "proof_steps": "\n".join(self.proof_steps),
        }


def _coerce_int(value: Any, *, default: int, minimum: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return max(minimum, default)
    return max(minimum, parsed)


def _read_proof_steps(raw: Any) -> List[str]:
    if isinstance(raw, str):
        return [line for line in raw.splitlines() if line.strip()]
    if isinstance(raw, list):
        lines: List[str] = []
        for item in raw:
            text = str(item).strip()
            if text:
                lines.append(text)
        return lines
    return []


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _merge_env_overrides(config_env: Mapping[str, Any] | None) -> Dict[str, str]:
    env_overrides: Dict[str, str] = {
        "SAPLINGS_ENABLE_ONLINE_GENERATION": "1",
        "SAPLINGS_ENABLE_BENCHMARK_PRIORS": "0",
        "SAPLINGS_PRIMARY_MODEL": "gpt-5.2",
        "SAPLINGS_CHEAP_MODEL": "gpt-5-mini",
        "SAPLINGS_BOOTSTRAP_MODEL": "gpt-5-mini",
        "SAPLINGS_BLOCK_THEOREMS": "A0K0",
    }
    for key, value in (config_env or {}).items():
        env_overrides[str(key)] = str(value)
    # Force UI policy: always run online generation, priors off.
    env_overrides["SAPLINGS_ENABLE_ONLINE_GENERATION"] = "1"
    env_overrides["SAPLINGS_ENABLE_BENCHMARK_PRIORS"] = "0"
    return env_overrides


def load_runtime_config(path: Path) -> WebRuntimeConfig:
    if not path.exists():
        return WebRuntimeConfig(
            goal="Modus ponens combined with a double syllogism inference.",
            next_step_ideas="",
            proof_steps=[],
            max_steps=100,
            step_delay_ms=60,
            step_log_enabled=True,
            step_log_path=str((path.parent / "../out/web_steps_log.jsonl").resolve()),
            step_log_truncate_on_start=True,
            run_config={
                "requested_patch_sets": 2,
                "max_depth": 13,
                "step_max_turns": 8,
                "env_overrides": _merge_env_overrides({}),
            },
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Runtime config must be a JSON object")

    search_payload = payload.get("search") or {}
    auto_payload = payload.get("auto_run") or {}
    log_payload = payload.get("step_log") or {}
    env_payload = payload.get("env") or {}

    goal = str(payload.get("goal") or "").strip()
    if not goal:
        raise ValueError("Config must contain non-empty 'goal'")

    raw_log_path = str(log_payload.get("path") or "../out/web_steps_log.jsonl").strip()
    log_path = str((path.parent / raw_log_path).resolve()) if raw_log_path else ""

    return WebRuntimeConfig(
        goal=goal,
        next_step_ideas=str(payload.get("next_step_ideas") or "").strip(),
        proof_steps=_read_proof_steps(payload.get("proof_steps")),
        max_steps=_coerce_int(auto_payload.get("max_steps"), default=100, minimum=1),
        step_delay_ms=_coerce_int(auto_payload.get("step_delay_ms"), default=60, minimum=0),
        step_log_enabled=_coerce_bool(log_payload.get("enabled"), default=True),
        step_log_path=log_path,
        step_log_truncate_on_start=_coerce_bool(log_payload.get("truncate_on_start"), default=True),
        run_config={
            "requested_patch_sets": _coerce_int(search_payload.get("requested_patch_sets"), default=2, minimum=1),
            "max_depth": _coerce_int(search_payload.get("max_depth"), default=13, minimum=1),
            "step_max_turns": _coerce_int(search_payload.get("step_max_turns"), default=8, minimum=1),
            "env_overrides": _merge_env_overrides(env_payload if isinstance(env_payload, dict) else {}),
        },
    )
