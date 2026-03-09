from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Flask, Response, jsonify, request

from web.auto_runner import AutoRunner
from web.builders import build_node_from_form
from web.runtime_config import load_runtime_config
from web.step_logger import StepJsonlLogger
from web.state import SearchState


WEB_DIR = Path(__file__).parent
INDEX_PATH = WEB_DIR / "index.html"
DEFAULT_SESSION_CONFIG_PATH = WEB_DIR / "session_config.json"


def _index_html() -> str:
    return INDEX_PATH.read_text(encoding="utf-8")


def _asset(name: str, *, mimetype: str) -> Response:
    path = WEB_DIR / name
    return Response(path.read_text(encoding="utf-8"), mimetype=mimetype)


def _snapshot_or_error(snapshot_fn, *, error: str) -> tuple[Dict[str, Any], int]:
    snapshot = snapshot_fn()
    snapshot["status"] = "error"
    snapshot["error"] = error
    return snapshot, 400


def create_app(root_builder=None) -> Flask:
    config_path = Path(os.getenv("SAPLINGS_WEB_CONFIG", str(DEFAULT_SESSION_CONFIG_PATH)))
    runtime_config = load_runtime_config(config_path)
    form_data = runtime_config.form_payload()
    builder = root_builder or (lambda form_snapshot=form_data: build_node_from_form(form_snapshot))
    initial_root = root_builder() if root_builder is not None else build_node_from_form(form_data)
    search_state = SearchState(builder)
    search_state.configure_run(runtime_config.run_config)
    search_state.reset(root=initial_root)
    state_lock = threading.RLock()
    step_logger = None
    if runtime_config.step_log_enabled and runtime_config.step_log_path:
        step_logger = StepJsonlLogger(
            Path(runtime_config.step_log_path),
            truncate_on_start=runtime_config.step_log_truncate_on_start,
        )

    def snapshot_locked() -> Dict[str, Any]:
        with state_lock:
            return search_state.snapshot()

    def step_locked() -> Dict[str, Any]:
        with state_lock:
            snapshot = search_state.step()
        if step_logger is not None:
            step_logger.log_step_snapshot(snapshot)
        return snapshot

    auto_runner = AutoRunner(
        step_fn=step_locked,
        max_steps=runtime_config.max_steps,
        step_delay_ms=runtime_config.step_delay_ms,
    )
    if step_logger is not None:
        step_logger.log_session_start(
            session_config_path=str(config_path),
            runtime_config={
                "goal": runtime_config.goal,
                "next_step_ideas": runtime_config.next_step_ideas,
                "proof_steps": runtime_config.proof_steps,
                "max_steps": runtime_config.max_steps,
                "step_delay_ms": runtime_config.step_delay_ms,
                "run_config": runtime_config.run_config,
                "step_log_path": runtime_config.step_log_path,
            },
            initial_snapshot=snapshot_locked(),
        )
    app = Flask(__name__)

    @app.get("/")
    def index():
        return Response(_index_html(), mimetype="text/html")

    @app.get("/web-static/persistence.js")
    def persistence_js():
        return _asset("persistence.js", mimetype="application/javascript")

    @app.get("/state")
    def state():
        auto_runner.ensure_started()
        payload = snapshot_locked()
        payload["auto_run"] = auto_runner.status()
        payload["session_config"] = {
            "path": str(config_path),
            "goal": runtime_config.goal,
            "step_log_path": runtime_config.step_log_path,
        }
        return jsonify(payload)

    @app.post("/next")
    def next_step():
        payload, code = _snapshot_or_error(snapshot_locked, error="Manual stepping is disabled in auto mode")
        return jsonify(payload), code

    @app.post("/reset")
    def reset():
        payload, code = _snapshot_or_error(snapshot_locked, error="Reset is disabled in auto mode")
        return jsonify(payload), code

    @app.post("/configure")
    def configure():
        payload, code = _snapshot_or_error(snapshot_locked, error="Configure is disabled in auto mode")
        return jsonify(payload), code

    @app.get("/session/export")
    def export_state():
        with state_lock:
            payload = search_state.export_state()
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"saplings_graph_{stamp}.json"
        headers = {"Content-Disposition": f'attachment; filename=\"{filename}\"'}
        return Response(content, mimetype="application/json", headers=headers)

    @app.post("/session/import")
    def import_state():
        uploaded = request.files.get("file")
        if not uploaded:
            payload, code = _snapshot_or_error(snapshot_locked, error="Файл не получен")
            return jsonify(payload), code

        try:
            data = json.loads(uploaded.read())
            with state_lock:
                search_state.load_state(data)
                payload = search_state.snapshot()
            payload["auto_run"] = auto_runner.status()
            return jsonify(payload)
        except Exception as exc:  # noqa: BLE001
            payload, code = _snapshot_or_error(snapshot_locked, error=str(exc))
            return jsonify(payload), code

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
