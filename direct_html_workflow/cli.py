from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from .llm import DEFAULT_MODEL
from .server import run_server
from .workflow import audit_direct_html, generate_from_problem_text, read_json, structure_problem_text, write_json


ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def cmd_serve(args: argparse.Namespace) -> int:
    load_dotenv(Path(args.env))
    run_server(host=args.host, port=args.port, root=ROOT)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    load_dotenv(Path(args.env))
    text = Path(args.input).read_text(encoding="utf-8")
    result = generate_from_problem_text(
        text,
        prompt_path=Path(args.prompt),
        output_dir=Path(args.output),
        api_key=args.api_key,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        attempts=args.attempts,
    )
    print("html:", result.output)
    print("problem json:", result.problem_json)
    print("page plan json:", result.page_plan_json)
    print("audit:", result.report["auditStatus"])
    if result.audit_errors:
        for error in result.audit_errors:
            print("-", error, file=sys.stderr)
        return 1
    return 0


def cmd_structure(args: argparse.Namespace) -> int:
    load_dotenv(Path(args.env))
    text = Path(args.input).read_text(encoding="utf-8")
    problem = structure_problem_text(text, api_key=args.api_key, model=args.model)
    write_json(Path(args.output), problem)
    print("problem json:", args.output)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    problem = read_json(Path(args.problem))
    errors = audit_direct_html(Path(args.html), problem)
    if errors:
        print("failed:", args.html)
        for error in errors:
            print("-", error)
        return 1
    print("passed:", args.html)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Direct HTML algorithm lesson generator")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="start the local web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--env", default=".env")
    serve.set_defaults(func=cmd_serve)

    generate = sub.add_parser("generate", help="generate HTML from pasted problem text")
    generate.add_argument("input", help="UTF-8 text file containing one LeetCode problem")
    generate.add_argument("--prompt", default=str(ROOT / "prompt.txt"))
    generate.add_argument("--output", default="outputs/cli-run")
    generate.add_argument("--model", default=DEFAULT_MODEL)
    generate.add_argument("--max-tokens", type=int, default=384000)
    generate.add_argument("--temperature", type=float, default=0.25)
    generate.add_argument("--attempts", type=int, default=2)
    generate.add_argument("--api-key", default=None)
    generate.add_argument("--env", default=".env")
    generate.set_defaults(func=cmd_generate)

    structure = sub.add_parser("structure", help="only convert problem text to JSON")
    structure.add_argument("input")
    structure.add_argument("--output", default="outputs/problem.json")
    structure.add_argument("--model", default=DEFAULT_MODEL)
    structure.add_argument("--api-key", default=None)
    structure.add_argument("--env", default=".env")
    structure.set_defaults(func=cmd_structure)

    check = sub.add_parser("check", help="audit a generated direct HTML file")
    check.add_argument("html")
    check.add_argument("--problem", required=True)
    check.set_defaults(func=cmd_check)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
