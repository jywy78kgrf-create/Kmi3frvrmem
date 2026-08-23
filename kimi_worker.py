#!/usr/bin/env python3
"""
kimi_worker.py — A varve-compatible worker that routes through Kimi (Moonshot AI)
instead of Claude's API. Designed for use in Kimi Work conversations and
Blueprint Automations.

Usage modes:
  --prepare   Show the prompt for the next pending task (for Kimi to author)
  --submit    Take a JSON file and append it through varve's gate
  --auto      Full loop: prepare → Kimi authors → submit (inside Automation)
"""

import json
import os
import sys
import argparse
from pathlib import Path

# Use varve's own modules — we are a peer worker, not a reimplementation
from varve import store, tasks, validate

SYSTEM = """You are the resident author of a varve log: an append-only, hash-chained memory founded empty. You are writing one entry that a future reader with no memory of you must be able to verify and act on.

The gate will reject your entry unless it follows the constitution:
- kind is one of: observation, hypothesis, hunch, errata, prediction, resolution, meta
- 'observation' and 'resolution' REQUIRE anchors: things a stranger could check, each {"type": "url"|"file"|"query"|"sha256"|"entry", "ref": "..."}. Only anchor what you actually consulted in this task — never a recalled or plausible source. If you cannot anchor it, it is a 'hypothesis' or 'hunch', and saying so is correct, not a failure.
- 'prediction' requires {"statement": <falsifiable claim>, "p": <0<p<1>, "resolve_by": "YYYY-MM-DD"} in a 'prediction' field.
- 'errata' requires 'corrects': the id of the entry it corrects.
- title and body are required; write the body self-contained.

Respond with ONLY a single JSON object for the entry: {"kind": ..., "title": ..., "body": ..., "anchors": [...], "tags": [...]} plus 'prediction'/'corrects'/'resolves'/'outcome' when the kind needs them. No prose around the JSON."""


def build_context(root, limit=12):
    """Build context string from recent log entries and unresolved predictions."""
    entries = store.read_log(root)
    recent = entries[-limit:]
    lines = ["The log currently ends at %s. Recent entries:" % entries[-1]["id"]]
    for e in recent:
        lines.append("- %s %s [%s] %s" % (e["id"], e["ts"], e["kind"], e["title"]))

    unresolved = [
        e for e in entries
        if e["kind"] == "prediction"
        and not any(r.get("resolves") == e["id"] for r in entries if r["kind"] == "resolution")
    ]
    if unresolved:
        lines.append("Unresolved predictions: " + ", ".join(
            "%s (%s, resolve by %s)" % (e["id"], e["prediction"]["statement"], e["prediction"]["resolve_by"])
            for e in unresolved))
    return "\n".join(lines)


def prepare_task(root):
    """Pull the next pending task and print the full prompt for Kimi to author."""
    task = tasks.next_pending(root)
    if task is None:
        print("No pending tasks.", file=sys.stderr)
        return None

    context = build_context(root)
    user_prompt = "%s\n\nTASK %s (%s): %s" % (context, task["id"], task["kind"], task["prompt"])

    # If research task and no web search configured, reframe honestly
    if task["kind"] == "research" and os.environ.get("VARVE_WEB_SEARCH") != "1":
        user_prompt += (
            "\n\n(No web access on this run: do not report on the outside world. "
            "Work only from the log itself, and label conclusions hypothesis/hunch.)"
        )

    return {
        "task": task,
        "system": SYSTEM,
        "prompt": user_prompt,
        "head": store.head(root),
    }


def submit_entry(root, fields, model="kimi"):
    """Validate and append an entry authored by Kimi. Mark the task done."""
    # Extract task reference if present
    task_id = fields.pop("task_id", None)
    if task_id is None:
        # Try to find from author metadata
        author = fields.get("author", {})
        task_id = author.get("task")

    # The model must not set seq/id/prev/hash — varve assigns those
    for reserved in ("seq", "id", "prev", "hash"):
        fields.pop(reserved, None)

    # Set author metadata
    fields["author"] = {"model": model, "task": task_id}

    # Validate through varve's gate
    entries = store.read_log(root)
    problems = validate.check(fields, entries)
    if problems:
        raise ValueError("Entry rejected by the gate:\n- " + "\n- ".join(problems))

    # Append
    entry = store.append(root, fields)

    # Mark task done
    if task_id:
        tasks.mark(root, task_id, "done", entry_id=entry["id"])

    return entry


def work_once(root, model="kimi"):
    """Full loop: pull task, prepare prompt, wait for JSON response, submit.
    
    This function is designed to be called from a Kimi Work Automation.
    It returns the prepared prompt; the Automation then calls Kimi to author
    the entry, and passes the result back to submit_entry().
    
    For interactive use, see --prepare and --submit CLI modes.
    """
    prepared = prepare_task(root)
    if prepared is None:
        return None
    return prepared


def main():
    parser = argparse.ArgumentParser(description="Kimi worker for varve logs")
    parser.add_argument("root", help="Path to varve log directory")
    parser.add_argument("--prepare", action="store_true", help="Print prompt for next pending task")
    parser.add_argument("--submit", metavar="JSON_FILE", help="Submit a JSON entry file")
    parser.add_argument("--model", default="kimi3", help="Model identifier (default: kimi3)")
    parser.add_argument("--auto", action="store_true", help="Run full work loop (for Automation use)")
    args = parser.parse_args()

    root = args.root

    if args.prepare:
        result = prepare_task(root)
        if result:
            print(json.dumps(result, indent=2))
        sys.exit(0 if result else 1)

    elif args.submit:
        with open(args.submit, "r", encoding="utf-8") as f:
            fields = json.load(f)
        try:
            entry = submit_entry(root, fields, model=args.model)
            print(json.dumps(entry, indent=2))
        except ValueError as e:
            print("Gate rejected entry: %s" % e, file=sys.stderr)
            sys.exit(1)

    elif args.auto:
        # Automation mode: prepare the prompt, print it, and exit.
        # The Automation framework captures this output, calls Kimi,
        # then invokes --submit with the response.
        result = work_once(root, model=args.model)
        if result is None:
            print(json.dumps({"status": "no_tasks"}))
        else:
            print(json.dumps(result))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
