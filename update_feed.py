#!/usr/bin/env python3
"""
Reads the local airmonitor sensor server (http://localhost:8080/current)
and commits the latest reading as latest.json in this repo, pushing to
GitHub — so the public site's HP100 widget can fetch a stable, always-
reachable raw.githubusercontent.com URL instead of hitting the VPS's own
public IP directly (which isn't reliably reachable from outside: it's a
proxy in front of the VPS with only one port forwarded, and the public IP
is being retired).

Commits are attributed to a dedicated bot identity via GIT_AUTHOR_*/
GIT_COMMITTER_* environment variables (never via `git config`, which would
change this repo's persistent settings) so they don't count toward the
founder's personal GitHub contribution graph — GitHub only credits a
commit to an account when the author email matches a verified email on
that account, and this bot email intentionally isn't one.

Run standalone once (for a manual test) or with --loop to run forever,
polling every UPDATE_INTERVAL_SECONDS — see hp100-feed.service for how
this is meant to run in production (systemd, not this flag, normally;
--loop exists mainly for an nohup smoke test before that's installed).
"""
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

AIRMONITOR_URL = "http://localhost:8080/current"
REPO_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = REPO_DIR / "latest.json"
UPDATE_INTERVAL_SECONDS = 300

BOT_NAME = "hp100-bot"
BOT_EMAIL = "hp100-bot@localhost"

# The board's field names -> the JSON keys we publish. Only the fields the
# lending2 HP100 widget actually shows (see lib/hp100-live.ts's FIELD_MAP).
FIELD_MAP = {
    "co2": "co2",
    "temp": "temperature",
    "hum": "humidity",
    "pm25": "dust",
}


def fetch_current() -> dict:
    with urllib.request.urlopen(AIRMONITOR_URL, timeout=10) as resp:
        text = resp.read().decode("utf-8")
    values = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        raw = raw.strip()
        if raw == "":
            continue
        try:
            values[key] = float(raw)
        except ValueError:
            continue
    return values


def build_payload(raw: dict) -> dict:
    payload = {out_key: raw[src_key] for src_key, out_key in FIELD_MAP.items() if src_key in raw}
    payload["updated"] = datetime.now(timezone.utc).isoformat()
    return payload


def run_git(*args: str) -> subprocess.CompletedProcess:
    import os

    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = BOT_NAME
    env["GIT_AUTHOR_EMAIL"] = BOT_EMAIL
    env["GIT_COMMITTER_NAME"] = BOT_NAME
    env["GIT_COMMITTER_EMAIL"] = BOT_EMAIL
    return subprocess.run(
        ["git", *args], cwd=REPO_DIR, env=env, capture_output=True, text=True
    )


def commit_and_push(payload: dict) -> None:
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    status = run_git("status", "--porcelain", "--", "latest.json")
    if status.returncode != 0:
        print(f"git status failed: {status.stderr}", file=sys.stderr)
        return
    if not status.stdout.strip():
        print("No change in reading, skipping commit.")
        return

    run_git("add", "latest.json")
    commit = run_git("commit", "-m", f"Update reading: {payload}")
    if commit.returncode != 0:
        print(f"git commit failed: {commit.stderr}", file=sys.stderr)
        return

    push = run_git("push")
    if push.returncode != 0:
        print(f"git push failed: {push.stderr}", file=sys.stderr)
        return
    print(f"Pushed update: {payload}")


def tick() -> None:
    try:
        raw = fetch_current()
    except Exception as exc:  # noqa: BLE001 — best-effort poller, log and retry next tick
        print(f"Failed to fetch sensor data: {exc}", file=sys.stderr)
        return
    payload = build_payload(raw)
    commit_and_push(payload)


def main() -> None:
    if "--loop" in sys.argv:
        while True:
            tick()
            time.sleep(UPDATE_INTERVAL_SECONDS)
    else:
        tick()


if __name__ == "__main__":
    main()
