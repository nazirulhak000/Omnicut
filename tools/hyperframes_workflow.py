"""Trusted local API client for an external AI session; never writes stores."""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit, quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def local_api_url(value):
    parts = urlsplit(value)
    host = parts.hostname or ""
    try:
        local = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host == "localhost"
    if parts.scheme != "http" or not local or parts.username or parts.password or parts.query or parts.fragment or parts.path not in {"", "/"}:
        raise argparse.ArgumentTypeError("Use an HTTP loopback API origin without credentials, paths or query parameters")
    return value.rstrip("/")


def request_api(base_url, channel, job_id, action, payload=None, *, key="", opener=urlopen):
    suffix = {"status": "", "handoff": "/handoff"}.get(action, "/" + action)
    url = local_api_url(base_url) + "/api/hyperframes/authoring-jobs/" + quote(job_id, safe="") + suffix
    headers = {"Content-Type": "application/json", "X-OmniCut-Channel": channel}
    if key:
        headers["X-API-Key"] = key
    request = Request(url, data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode(), headers=headers, method="GET" if action in {"status", "handoff"} else "POST")
    with opener(request, timeout=60) as response:
        return json.load(response)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "handoff", "claim", "heartbeat", "checkpoint", "submit"))
    parser.add_argument("--channel", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--base-url", type=local_api_url, default="http://127.0.0.1:8000")
    parser.add_argument("--executor")
    parser.add_argument("--generation", type=int)
    parser.add_argument("--fence")
    parser.add_argument("--checkpoint-file", type=Path)
    args = parser.parse_args(argv)
    from scripts.channel_store import is_valid_channel_id
    from scripts.auth import get_configured_api_key
    if not is_valid_channel_id(args.channel):
        parser.error("Invalid channel ID")
    payload = None
    if args.action == "claim":
        if not args.executor or args.generation is None:
            parser.error("claim requires --executor and --generation (the handoff generation)")
        payload = {"executor_id": args.executor, "expected_generation": args.generation}
    elif args.action in {"heartbeat", "checkpoint", "submit"}:
        if not args.executor or args.generation is None or not args.fence:
            parser.error("Use the exact executor, generation and fence returned by claim")
        payload = {"executor_id": args.executor, "generation": args.generation, "fence": args.fence}
        if args.action == "checkpoint":
            if not args.checkpoint_file:
                parser.error("checkpoint requires --checkpoint-file containing a JSON object")
            checkpoint = json.loads(args.checkpoint_file.read_text(encoding="utf-8"))
            if not isinstance(checkpoint, dict):
                parser.error("Checkpoint must be a JSON object")
            payload["checkpoint"] = checkpoint
    result = request_api(args.base_url, args.channel, args.job, args.action, payload, key=get_configured_api_key())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
