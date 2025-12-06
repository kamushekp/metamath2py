from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from flask import Flask, Response, jsonify, request

from web.builders import build_default_root_node, build_node_from_form
from web.state import SearchState


INDEX_PATH = Path(__file__).with_name("index.html")


def _index_html() -> str:
    return INDEX_PATH.read_text(encoding="utf-8")


def _snapshot_or_error(search_state: SearchState, *, error: str) -> tuple[Dict[str, Any], int]:
    snapshot = search_state.snapshot()
    snapshot["status"] = "error"
    snapshot["error"] = error
    return snapshot, 400


def create_app(root_builder=None) -> Flask:
    builder = root_builder or build_default_root_node
    search_state = SearchState(builder)
    app = Flask(__name__)

    @app.get("/")
    def index():
        return Response(_index_html(), mimetype="text/html")

    @app.get("/state")
    def state():
        return jsonify(search_state.snapshot())

    @app.post("/next")
    def next_step():
        return jsonify(search_state.step())

    @app.post("/reset")
    def reset():
        search_state.reset()
        return jsonify(search_state.snapshot())

    @app.post("/configure")
    def configure():
        try:
            # Snapshot to reuse on future resets.
            form_data: Dict[str, str] = {key: value for key, value in request.form.items()}
            node = build_node_from_form(form_data)
        except Exception as exc:  # noqa: BLE001
            payload, code = _snapshot_or_error(search_state, error=str(exc))
            return jsonify(payload), code

        search_state.set_builder(lambda form_snapshot=form_data: build_node_from_form(form_snapshot))
        search_state.reset(root=node)
        return jsonify(search_state.snapshot())

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
