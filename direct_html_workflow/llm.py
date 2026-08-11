from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


class LlmClientError(RuntimeError):
    pass


def chat_completion(
    prompt: str,
    *,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 600,
    system: str = "Return only the requested content.",
    max_tokens: int = 4096,
    temperature: float = 0.2,
    json_output: bool = False,
    thinking: Optional[str] = None,
) -> Dict[str, Any]:
    token = api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not token:
        raise LlmClientError("DEEPSEEK_API_KEY is not set")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_output:
        payload["response_format"] = {"type": "json_object"}
    if thinking:
        payload["thinking"] = {"type": thinking}

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LlmClientError("DeepSeek HTTP %s: %s" % (exc.code, detail)) from exc
    except urllib.error.URLError as exc:
        raise LlmClientError("DeepSeek request failed: %s" % exc.reason) from exc


def first_message_text(response: Dict[str, Any]) -> str:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return str(message.get("content") or "")
