from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openai import OpenAI
from openai import OpenAIError
from dotenv import load_dotenv


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _default_models() -> list[str]:
    return _dedupe(
        [
            os.getenv("SAPLINGS_PRIMARY_MODEL", "gpt-5.2"),
            os.getenv("SAPLINGS_CHEAP_MODEL", "gpt-5-mini"),
            os.getenv("SAPLINGS_BOOTSTRAP_MODEL", "gpt-5-mini"),
        ]
    )


def _mask(value: str | None) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


@dataclass
class ProbeResult:
    model: str
    ok: bool
    latency_sec: float
    output: str
    error_type: str
    error: str


def _probe_model(client: OpenAI, model: str) -> ProbeResult:
    started = time.time()
    try:
        response = client.responses.create(
            model=model,
            input="Reply with exactly: OK",
            max_output_tokens=12,
        )
        latency = time.time() - started
        text = getattr(response, "output_text", "") or ""
        return ProbeResult(model=model, ok=True, latency_sec=latency, output=text.strip(), error_type="", error="")
    except Exception as exc:  # noqa: BLE001
        latency = time.time() - started
        return ProbeResult(
            model=model,
            ok=False,
            latency_sec=latency,
            output="",
            error_type=type(exc).__name__,
            error=str(exc),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check availability of configured LLM models.")
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Optional explicit model list. Default: SAPLINGS_PRIMARY_MODEL, SAPLINGS_CHEAP_MODEL, SAPLINGS_BOOTSTRAP_MODEL.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=12.0,
        help="HTTP timeout per request in seconds (default: 12).",
    )
    args = parser.parse_args()

    dotenv_path = Path(__file__).resolve().parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)

    models = _dedupe(args.models or _default_models())
    if not models:
        print("No models to probe.")
        return 2

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or "<default>"

    print("LLM availability probe")
    print(f"OPENAI_API_KEY: {_mask(api_key)}")
    print(f"OPENAI_BASE_URL: {base_url}")
    print(f"Models: {', '.join(models)}")
    print("-" * 72)

    try:
        client = OpenAI(timeout=args.timeout, max_retries=0)
    except OpenAIError as exc:
        print(f"FAIL client_init error={type(exc).__name__}: {exc}")
        print("------------------------------------------------------------------------")
        print("Summary: 0/0 models reachable")
        return 1

    results = [_probe_model(client, model) for model in models]

    success_count = 0
    for result in results:
        if result.ok:
            success_count += 1
            output_preview = result.output if result.output else "<empty output>"
            print(f"OK   model={result.model:20} latency={result.latency_sec:5.2f}s output={output_preview}")
        else:
            print(
                f"FAIL model={result.model:20} latency={result.latency_sec:5.2f}s "
                f"error={result.error_type}: {result.error}"
            )

    print("-" * 72)
    print(f"Summary: {success_count}/{len(results)} models reachable")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
