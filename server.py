#!/usr/bin/env python3
"""Tiny A2A-friendly context intake endpoint.

This server intentionally uses only the Python standard library so it can run
in a fresh Codex workspace without installing dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


APP_NAME = "Codex Context Intake Agent"
APP_VERSION = "0.1.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
STORE_PATH = Path(os.environ.get("CONTEXT_STORE_PATH", "work/context_store.json"))
API_TOKEN = os.environ.get("CONTEXT_API_TOKEN", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")


def now_ms() -> int:
    return int(time.time() * 1000)


def json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def load_store() -> Dict[str, Any]:
    if not STORE_PATH.exists():
        return {"contexts": []}
    try:
        with STORE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"contexts": []}
    if not isinstance(data, dict) or not isinstance(data.get("contexts"), list):
        return {"contexts": []}
    return data


def save_store(store: Dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STORE_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(store, handle, ensure_ascii=False, indent=2)
    tmp_path.replace(STORE_PATH)


def public_url(handler: BaseHTTPRequestHandler) -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL.rstrip("/")
    host = handler.headers.get("Host", f"{DEFAULT_HOST}:{DEFAULT_PORT}")
    scheme = "https" if host.endswith(".ngrok-free.app") or host.endswith(".ngrok.app") else "http"
    return f"{scheme}://{host}"


def agent_card(base_url: str) -> Dict[str, Any]:
    return {
        "name": APP_NAME,
        "description": "Receives project context from an external employer agent and exposes it to Codex workflows.",
        "url": f"{base_url}/a2a",
        "version": APP_VERSION,
        "protocolVersion": "1.0",
        "supportedInterfaces": [
            {
                "url": f"{base_url}/a2a",
                "protocolBinding": "JSONRPC",
                "protocolVersion": "1.0",
            }
        ],
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["application/json", "text/plain"],
        "defaultOutputModes": ["application/json"],
        "securitySchemes": {
            "bearer": {
                "type": "http",
                "scheme": "bearer",
                "description": "Set CONTEXT_API_TOKEN and send Authorization: Bearer <token>.",
            }
        },
        "security": [{"bearer": []}] if API_TOKEN else [],
        "skills": [
            {
                "id": "ingest-project-context",
                "name": "Ingest project context",
                "description": "Accepts structured context, requirements, URLs, tickets, notes, and source metadata.",
                "tags": ["context", "onboarding", "codex", "a2a"],
                "examples": [
                    "Store onboarding context for a Codex agent.",
                    "Provide current project requirements, links, constraints, and acceptance criteria.",
                ],
                "inputModes": ["application/json", "text/plain"],
                "outputModes": ["application/json"],
            }
        ],
    }


def openapi_doc(base_url: str) -> Dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {"title": APP_NAME, "version": APP_VERSION},
        "servers": [{"url": base_url}],
        "paths": {
            "/healthz": {"get": {"summary": "Health check"}},
            "/.well-known/agent-card.json": {"get": {"summary": "A2A agent card"}},
            "/contexts": {
                "get": {"summary": "List received context bundles"},
                "post": {"summary": "Ingest a context bundle"},
            },
            "/contexts/{id}": {"get": {"summary": "Read one context bundle"}},
            "/a2a": {"post": {"summary": "A2A-style JSON-RPC endpoint"}},
        },
    }


class ContextHandler(BaseHTTPRequestHandler):
    server_version = f"CodexContextIntake/{APP_VERSION}"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        base_url = public_url(self)
        if path == "/":
            self.send_json(
                {
                    "name": APP_NAME,
                    "health": f"{base_url}/healthz",
                    "agentCard": f"{base_url}/.well-known/agent-card.json",
                    "legacyAgentCard": f"{base_url}/.well-known/agent.json",
                    "a2a": f"{base_url}/a2a",
                    "contexts": f"{base_url}/contexts",
                }
            )
        elif path == "/healthz":
            self.send_json({"ok": True, "timeMs": now_ms()})
        elif path in ("/.well-known/agent-card.json", "/.well-known/agent.json"):
            self.send_json(agent_card(base_url))
        elif path == "/openapi.json":
            self.send_json(openapi_doc(base_url))
        elif path == "/contexts":
            if not self.authorized():
                self.send_auth_error()
                return
            store = load_store()
            summaries = [
                {
                    "id": item.get("id"),
                    "receivedAt": item.get("receivedAt"),
                    "source": item.get("source"),
                    "summary": item.get("summary"),
                }
                for item in store["contexts"]
            ]
            self.send_json({"contexts": summaries})
        elif path.startswith("/contexts/"):
            if not self.authorized():
                self.send_auth_error()
                return
            context_id = path.rsplit("/", 1)[-1]
            item = find_context(context_id)
            if item is None:
                self.send_json({"error": "Context not found"}, status=404)
                return
            self.send_json(item)
        else:
            self.send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not self.authorized():
            self.send_auth_error()
            return
        payload = self.read_json_body()
        if payload is None:
            return
        if path == "/contexts":
            self.send_json(ingest_context(payload), status=201)
        elif path == "/a2a":
            self.send_json(handle_rpc(payload))
        else:
            self.send_json({"error": "Not found"}, status=404)

    def read_json_body(self) -> Optional[Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json({"error": "Invalid Content-Length"}, status=400)
            return None
        raw_body = self.rfile.read(length)
        if not raw_body:
            return {}
        content_type = self.headers.get("Content-Type", "")
        if content_type.startswith("text/plain"):
            return {"text": raw_body.decode("utf-8")}
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self.send_json({"error": f"Invalid JSON: {exc.msg}"}, status=400)
            return None

    def authorized(self) -> bool:
        if not API_TOKEN:
            return True
        auth = self.headers.get("Authorization", "")
        api_key = self.headers.get("X-API-Key", "")
        return auth == f"Bearer {API_TOKEN}" or api_key == API_TOKEN

    def send_auth_error(self) -> None:
        self.send_response(401)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("WWW-Authenticate", "Bearer")
        self.end_headers()
        self.wfile.write(json_bytes({"error": "Unauthorized"}))

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def find_context(context_id: str) -> Optional[Dict[str, Any]]:
    store = load_store()
    for item in store["contexts"]:
        if item.get("id") == context_id:
            return item
    return None


def summarize(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("summary", "title", "project", "task", "text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:240]
        return ", ".join(sorted(str(key) for key in payload.keys()))[:240]
    if isinstance(payload, str):
        return payload.strip()[:240]
    return type(payload).__name__


def ingest_context(payload: Any, source: str = "http") -> Dict[str, Any]:
    item = {
        "id": uuid.uuid4().hex,
        "receivedAt": now_ms(),
        "source": source,
        "summary": summarize(payload),
        "payload": payload,
    }
    store = load_store()
    store["contexts"].append(item)
    save_store(store)
    return {"ok": True, "context": item}


def extract_a2a_context(params: Any) -> Any:
    if not isinstance(params, dict):
        return params
    if "context" in params:
        return params["context"]
    message = params.get("message")
    if not isinstance(message, dict):
        return params
    parts = message.get("parts")
    if not isinstance(parts, list):
        return message
    extracted = []
    for part in parts:
        if not isinstance(part, dict):
            extracted.append(part)
            continue
        if "text" in part:
            extracted.append(part["text"])
        elif "data" in part:
            extracted.append(part["data"])
        else:
            extracted.append(part)
    return {"message": message, "parts": extracted}


def handle_rpc(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        return rpc_error(None, -32600, "Invalid JSON-RPC 2.0 request")

    rpc_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if method in ("context.ingest", "message/send", "tasks/send"):
        result = ingest_context(extract_a2a_context(params), source=f"a2a:{method}")
        context = result["context"]
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "id": context["id"],
                "kind": "task",
                "status": {"state": "completed", "timestamp": context["receivedAt"]},
                "artifacts": [
                    {
                        "artifactId": context["id"],
                        "name": "Stored context",
                        "parts": [{"kind": "data", "data": context}],
                    }
                ],
            },
        }
    if method == "context.list":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": load_store()["contexts"]}
    if method == "context.get":
        context_id = params.get("id") if isinstance(params, dict) else None
        item = find_context(str(context_id)) if context_id else None
        if item is None:
            return rpc_error(rpc_id, -32004, "Context not found")
        return {"jsonrpc": "2.0", "id": rpc_id, "result": item}
    return rpc_error(rpc_id, -32601, f"Method not found: {method}")


def rpc_error(rpc_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--host", default=os.environ.get("HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ContextHandler)
    print(f"{APP_NAME} listening on http://{args.host}:{args.port}")
    if API_TOKEN:
        print("Auth enabled via CONTEXT_API_TOKEN")
    else:
        print("Auth disabled. Set CONTEXT_API_TOKEN before exposing this endpoint.")
    server.serve_forever()


if __name__ == "__main__":
    main()
