"""One structured call to the model, recorded so it never has to be made twice.

An agent's judgment here is a JSON document that matches a schema. The request (model, prompts,
schema) is hashed; the answer is kept under that hash in research/cassettes, so a rebuild replays
the same judgment byte for byte, the checks stage runs with no key and no cost, and a live
second call on the same document (`--verify` in the callers) shows whether the judgment holds.
Keys come from the environment, else from the local env files, and are never printed.

    python research/tools/llm.py --selfcheck
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASSETTES = ROOT / "research" / "cassettes"
ENV_FILES = (ROOT / ".env", Path.home() / "chromie" / ".env.local", Path.home() / "chromie" / ".env.development.local")
MODEL = "gpt-5.4-mini"
ENDPOINT = "https://api.openai.com/v1/responses"


def env_value(name: str) -> str:
    """The variable from the environment, else the first local env file that sets it; empty when none does."""
    if os.environ.get(name):
        return os.environ[name].strip()
    for path in ENV_FILES:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def request_key(model: str, system: str, user: str, schema: dict) -> str:
    return hashlib.sha256(json.dumps({"model": model, "system": system, "user": user, "schema": schema},
                                     sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def structured(system: str, user: str, schema: dict, name: str, model: str = MODEL, *,
               cassettes: Path = CASSETTES, replay_only: bool = False, fresh: bool = False) -> tuple[dict, dict]:
    """The model's answer as a dict, and how it was had: `{"cassette", "replayed", "model", "usage"}`.
    `replay_only` refuses the network (the checks stage); `fresh` refuses the cassette (a verify run)."""
    key = request_key(model, system, user, schema)
    path = cassettes / f"{key[:16]}.json"
    if path.exists() and not fresh:
        saved = json.loads(path.read_text(encoding="utf-8"))
        return json.loads(saved["output_text"]), {"cassette": path.name, "replayed": True, "model": saved["model"], "usage": saved["usage"]}
    if replay_only:
        raise LookupError(f"no cassette for this request ({path.name}); run without --check to make the call")
    api_key = env_value("OPENAI_API_KEY")
    if not api_key:
        raise LookupError("OPENAI_API_KEY is not set in the environment or the local env files")
    body = {"model": model, "reasoning": {"effort": "low"},
            "input": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "text": {"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}}}
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode("utf-8"),
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    # A name lookup or a throttle fails a whole run otherwise; three tries, then the error as it came.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                answer = json.loads(resp.read())
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"model call failed: HTTP {exc.code} {exc.read()[:300]!r}") from None
        except urllib.error.URLError:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    text = next(c["text"] for o in answer.get("output", []) if o.get("type") == "message"
                for c in o.get("content", []) if c.get("type") == "output_text")
    usage = {k: answer.get("usage", {}).get(k) for k in ("input_tokens", "output_tokens")}
    record = {"request_key": key, "model": answer.get("model", model), "requested_model": model, "name": name,
              "called_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "usage": usage,
              "system_sha256": hashlib.sha256(system.encode()).hexdigest()[:16],
              "user_sha256": hashlib.sha256(user.encode()).hexdigest()[:16], "output_text": text}
    if not fresh:
        cassettes.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return json.loads(text), {"cassette": path.name, "replayed": False, "model": record["model"], "usage": usage}


def selfcheck() -> int:
    import tempfile
    schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False}
    k1, k2 = request_key("m", "s", "u", schema), request_key("m", "s", "u2", schema)
    assert k1 != k2 and k1 == request_key("m", "s", "u", schema)
    with tempfile.TemporaryDirectory() as tmp:
        box = Path(tmp)
        try:
            structured("s", "u", schema, "t", model="m", cassettes=box, replay_only=True)
            raise AssertionError("replay-only must refuse the network")
        except LookupError:
            pass
        (box / f"{k1[:16]}.json").write_text(json.dumps({"output_text": '{"a": "x"}', "model": "m-2026", "usage": {"input_tokens": 1, "output_tokens": 1}}))
        out, meta = structured("s", "u", schema, "t", model="m", cassettes=box, replay_only=True)
        assert out == {"a": "x"} and meta["replayed"] and meta["model"] == "m-2026", (out, meta)
        assert env_value("THIS_VARIABLE_IS_NOT_SET_ANYWHERE_X") == ""
        os.environ["LLM_SELFCHECK_PROBE"] = " v "
        assert env_value("LLM_SELFCHECK_PROBE") == "v"
    print("llm selfcheck ok")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv[1:] else print(__doc__) or 2)
