#!/usr/bin/env python3
"""HR context provider agent.

This agent stores project context and employee agent endpoints, then pushes
project context to employee agents over A2A-style JSON-RPC or REST.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request
from urllib.parse import urlparse


APP_NAME = "HR Project Context Agent"
APP_VERSION = "0.1.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8788
STORE_PATH = Path(os.environ.get("HR_STORE_PATH", "work/hr_store.json"))
API_TOKEN = os.environ.get("HR_API_TOKEN", "")
PUBLIC_BASE_URL = os.environ.get("HR_PUBLIC_BASE_URL", "")


def now_ms() -> int:
    return int(time.time() * 1000)


def json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def load_store() -> Dict[str, Any]:
    if not STORE_PATH.exists():
        return {"projects": [], "employees": [], "deliveries": []}
    try:
        with STORE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"projects": [], "employees": [], "deliveries": []}
    for key in ("projects", "employees", "deliveries"):
        if not isinstance(data.get(key), list):
            data[key] = []
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
        "description": "Provides project context to employee agents and dispatches updates to their endpoints.",
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
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "securitySchemes": {
            "bearer": {
                "type": "http",
                "scheme": "bearer",
                "description": "Set HR_API_TOKEN and send Authorization: Bearer <token>.",
            }
        },
        "security": [{"bearer": []}] if API_TOKEN else [],
        "skills": [
            {
                "id": "dispatch-project-context",
                "name": "Dispatch project context",
                "description": "Sends approved project context to a registered employee agent.",
                "tags": ["hr", "context", "project", "a2a"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            },
            {
                "id": "manage-project-context",
                "name": "Manage project context",
                "description": "Stores project briefs, constraints, acceptance criteria, links, and policy notes.",
                "tags": ["hr", "projects", "onboarding"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            },
        ],
    }


class HrHandler(BaseHTTPRequestHandler):
    server_version = f"HRProjectContext/{APP_VERSION}"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        base_url = public_url(self)
        if path == "/":
            self.send_json(
                {
                    "name": APP_NAME,
                    "health": f"{base_url}/healthz",
                    "agentCard": f"{base_url}/.well-known/agent-card.json",
                    "a2a": f"{base_url}/a2a",
                    "projects": f"{base_url}/projects",
                    "employees": f"{base_url}/employees",
                    "dispatch": f"{base_url}/dispatch",
                }
            )
        elif path == "/healthz":
            self.send_json({"ok": True, "timeMs": now_ms()})
        elif path in ("/.well-known/agent-card.json", "/.well-known/agent.json"):
            self.send_json(agent_card(base_url))
        elif path == "/projects":
            if not self.authorized():
                self.send_auth_error()
                return
            self.send_json({"projects": project_summaries()})
        elif path.startswith("/projects/"):
            if not self.authorized():
                self.send_auth_error()
                return
            project = find_record("projects", path.rsplit("/", 1)[-1])
            self.send_json_or_404(project, "Project not found")
        elif path == "/employees":
            if not self.authorized():
                self.send_auth_error()
                return
            self.send_json({"employees": employee_summaries()})
        elif path.startswith("/employees/"):
            if not self.authorized():
                self.send_auth_error()
                return
            employee = find_record("employees", path.rsplit("/", 1)[-1])
            self.send_json_or_404(mask_employee(employee), "Employee not found")
        elif path == "/deliveries":
            if not self.authorized():
                self.send_auth_error()
                return
            self.send_json({"deliveries": load_store()["deliveries"]})
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
        if path == "/projects":
            self.send_json(upsert_project(payload), status=201)
        elif path == "/employees":
            self.send_json(upsert_employee(payload), status=201)
        elif path == "/dispatch":
            self.send_json(dispatch_context(payload))
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

    def send_json_or_404(self, payload: Optional[Any], message: str) -> None:
        if payload is None:
            self.send_json({"error": message}, status=404)
            return
        self.send_json(payload)

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def find_record(collection: str, record_id: str) -> Optional[Dict[str, Any]]:
    for item in load_store()[collection]:
        if item.get("id") == record_id:
            return item
    return None


def upsert_project(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Project payload must be an object"}
    store = load_store()
    project_id = str(payload.get("id") or slug_or_uuid(payload.get("name")))
    project = {
        "id": project_id,
        "name": str(payload.get("name") or project_id),
        "summary": payload.get("summary", ""),
        "context": payload.get("context", payload),
        "links": payload.get("links", []),
        "constraints": payload.get("constraints", []),
        "acceptanceCriteria": payload.get("acceptanceCriteria", []),
        "updatedAt": now_ms(),
    }
    replace_record(store["projects"], project)
    save_store(store)
    return {"ok": True, "project": project}


def upsert_employee(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Employee payload must be an object"}
    store = load_store()
    employee_id = str(payload.get("id") or slug_or_uuid(payload.get("name")))
    base_url = str(payload.get("agentBaseUrl", "")).rstrip("/")
    employee = {
        "id": employee_id,
        "name": str(payload.get("name") or employee_id),
        "agentBaseUrl": base_url,
        "a2aUrl": str(payload.get("a2aUrl") or f"{base_url}/a2a"),
        "contextsUrl": str(payload.get("contextsUrl") or f"{base_url}/contexts"),
        "token": str(payload.get("token") or ""),
        "projectIds": payload.get("projectIds", []),
        "updatedAt": now_ms(),
    }
    replace_record(store["employees"], employee)
    save_store(store)
    return {"ok": True, "employee": mask_employee(employee)}


def replace_record(collection: List[Dict[str, Any]], item: Dict[str, Any]) -> None:
    for index, existing in enumerate(collection):
        if existing.get("id") == item.get("id"):
            collection[index] = item
            return
    collection.append(item)


def slug_or_uuid(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return uuid.uuid4().hex
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or uuid.uuid4().hex


def project_summaries() -> List[Dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "summary": item.get("summary"),
            "updatedAt": item.get("updatedAt"),
        }
        for item in load_store()["projects"]
    ]


def employee_summaries() -> List[Dict[str, Any]]:
    return [mask_employee(item) for item in load_store()["employees"]]


def mask_employee(employee: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if employee is None:
        return None
    masked = dict(employee)
    if masked.get("token"):
        masked["token"] = "***"
    return masked


def build_context(project: Dict[str, Any], employee: Dict[str, Any], note: str = "") -> Dict[str, Any]:
    return {
        "source": "hr-project-context-agent",
        "projectId": project["id"],
        "projectName": project.get("name"),
        "summary": project.get("summary"),
        "context": project.get("context"),
        "links": project.get("links", []),
        "constraints": project.get("constraints", []),
        "acceptanceCriteria": project.get("acceptanceCriteria", []),
        "employee": {
            "id": employee.get("id"),
            "name": employee.get("name"),
        },
        "note": note,
        "sentAt": now_ms(),
    }


def dispatch_context(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Dispatch payload must be an object"}
    project_id = str(payload.get("projectId", ""))
    employee_id = str(payload.get("employeeId", ""))
    mode = str(payload.get("mode", "a2a"))
    project = find_record("projects", project_id)
    employee = find_record("employees", employee_id)
    if project is None:
        return {"ok": False, "error": "Project not found"}
    if employee is None:
        return {"ok": False, "error": "Employee not found"}
    if mode not in ("a2a", "rest"):
        return {"ok": False, "error": "Mode must be a2a or rest"}

    context = build_context(project, employee, str(payload.get("note", "")))
    result = send_to_employee(employee, context, mode)
    delivery = {
        "id": uuid.uuid4().hex,
        "projectId": project_id,
        "employeeId": employee_id,
        "mode": mode,
        "ok": result[0],
        "status": result[1],
        "response": result[2],
        "sentAt": now_ms(),
    }
    store = load_store()
    store["deliveries"].append(delivery)
    save_store(store)
    return {"ok": result[0], "delivery": delivery}


def send_to_employee(employee: Dict[str, Any], context: Dict[str, Any], mode: str) -> Tuple[bool, int, Any]:
    if mode == "rest":
        url = str(employee.get("contextsUrl", ""))
        body = context
    else:
        url = str(employee.get("a2aUrl", ""))
        body = {
            "jsonrpc": "2.0",
            "id": f"hr-{uuid.uuid4().hex}",
            "method": "context.ingest",
            "params": {"context": context},
        }
    if not url:
        return False, 0, {"error": "Employee endpoint URL is empty"}
    headers = {"Content-Type": "application/json"}
    token = str(employee.get("token", ""))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, data=json_bytes(body), headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return True, response.status, parse_response(raw)
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return False, exc.code, parse_response(raw)
    except error.URLError as exc:
        return False, 0, {"error": str(exc.reason)}


def parse_response(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def handle_rpc(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        return rpc_error(None, -32600, "Invalid JSON-RPC 2.0 request")
    rpc_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})
    if method == "hr.project.upsert":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": upsert_project(params)}
    if method == "hr.employee.upsert":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": upsert_employee(params)}
    if method == "hr.context.dispatch":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": dispatch_context(params)}
    if method == "hr.context.forEmployee":
        employee_id = str(params.get("employeeId", "")) if isinstance(params, dict) else ""
        employee = find_record("employees", employee_id)
        if employee is None:
            return rpc_error(rpc_id, -32004, "Employee not found")
        allowed = set(employee.get("projectIds") or [])
        projects = load_store()["projects"]
        if allowed:
            projects = [project for project in projects if project.get("id") in allowed]
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"projects": projects}}
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
    server = ThreadingHTTPServer((args.host, args.port), HrHandler)
    print(f"{APP_NAME} listening on http://{args.host}:{args.port}")
    if API_TOKEN:
        print("Auth enabled via HR_API_TOKEN")
    else:
        print("Auth disabled. Set HR_API_TOKEN before exposing this endpoint.")
    server.serve_forever()


if __name__ == "__main__":
    main()
