from __future__ import annotations

import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

from .llm import DEFAULT_MODEL, LlmClientError
from .workflow import generate_direct_html, structure_problem_text


class DirectHtmlHandler(BaseHTTPRequestHandler):
    root: Path

    def log_message(self, format: str, *args: Any) -> None:
        print("[%s] %s" % (self.log_date_time_string(), format % args))

    def send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path in ("/", "/index.html"):
            return self.send_file(self.root / "web" / "index.html")
        if path.startswith("/outputs/"):
            target = (self.root / path.lstrip("/")).resolve()
            outputs_root = (self.root / "outputs").resolve()
            if outputs_root == target or outputs_root in target.parents:
                return self.send_file(target)
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/generate":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = self.handle_generate(payload)
            self.send_json(200, result)
        except (ValueError, LlmClientError) as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})

    def handle_generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        problem_text = str(payload.get("problemText") or "").strip()
        if not problem_text:
            raise ValueError("题目文本为空")

        model = str(payload.get("model") or DEFAULT_MODEL)
        api_key: Optional[str] = str(payload.get("apiKey") or "").strip() or None
        max_tokens = int(payload.get("maxTokens") or 384000)
        temperature = float(payload.get("temperature") or 0.25)
        attempts = int(payload.get("attempts") or 2)

        stamp = time.strftime("%Y%m%d-%H%M%S")
        output_dir = self.root / "outputs" / stamp
        prompt_path = self.root / "prompt.txt"

        problem = structure_problem_text(problem_text, api_key=api_key, model=model)
        result = generate_direct_html(
            problem,
            prompt_path=prompt_path,
            output_dir=output_dir,
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            attempts=attempts,
        )

        html_rel = "/" + result.output.relative_to(self.root).as_posix()
        report_rel = "/" + (output_dir / "direct-html-report.json").relative_to(self.root).as_posix()
        problem_rel = "/" + result.problem_json.relative_to(self.root).as_posix()
        page_plan_rel = "/" + result.page_plan_json.relative_to(self.root).as_posix()
        return {
            "ok": not result.audit_errors,
            "problem": problem,
            "htmlUrl": html_rel,
            "reportUrl": report_rel,
            "problemJsonUrl": problem_rel,
            "pagePlanUrl": page_plan_rel,
            "report": result.report,
            "auditErrors": result.audit_errors,
        }

    def send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if path.suffix.lower() in (".html", ".css", ".js", ".json", ".txt"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def run_server(*, host: str, port: int, root: Path) -> None:
    DirectHtmlHandler.root = root.resolve()
    server = ThreadingHTTPServer((host, port), DirectHtmlHandler)
    print("Direct HTML workflow UI: http://%s:%s" % (host, port))
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
