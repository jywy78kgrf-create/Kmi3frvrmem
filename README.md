# Loam × Varve — Persistent Cognition with External Witness

A varve-native autonomous worker system. The log is append-only, hash-chained, and witnessed externally via GitHub Actions.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install git+https://github.com/jywy78kgrf-create/varve

# The varve log at varve_log/ is already initialized and seeded.
# If starting fresh:
#   rm -rf varve_log
#   varve init varve_log --note "Loam worker log, founded empty"
#   python scripts/seed_varve.py

# Add a task
varve task add varve_log --kind research --prompt "Your question here" --priority 3

# Prepare the work prompt (Kimi authors the entry)
python kimi_worker.py varve_log --prepare

# Submit the authored JSON entry
python kimi_worker.py varve_log --submit entry.json

# Verify the chain
varve verify varve_log
varve head varve_log
varve beliefs varve_log
varve digest varve_log
```

## External Witness — The Critical Gap

**The log alone is not enough.** Whoever holds the directory can re-chain the entire history, and `varve verify` will exit 0. The chain is tamper-evident against accidents, not against the disk's owner.

**The fix:** GitHub Actions as an external witness.

### Setup

1. Create a private (or public) GitHub repo
2. Push this directory to it
3. The workflow at `.github/workflows/witness.yml` already exists — it runs on every push

What the workflow does:
- Runs `varve verify varve_log` — fails if chain is broken
- Records `varve head varve_log` as a GitHub Actions output
- GitHub keeps `run_number`, `commit SHA`, and timestamp **outside the repository tree**

This means: even if someone rewrites the entire log and pushes, the old witnessed head hash remains in GitHub's run history. A future `ci_witness.py` check can flag that the recorded push is no longer an ancestor of the branch.

### The One-Line Rule

Every digest must carry the head:

```
varve head varve_log
```

This is the whole difference between a log people trust and a log people can check.

## Architecture

| Component | Role |
|---|---|
| `varve_log/` | The append-only, hash-chained log (the source of truth) |
| `kimi_worker.py` | Pulls tasks, builds context, submits entries through the gate |
| `.github/workflows/witness.yml` | External witness — verifies chain on every push |
| `scripts/` | Stable helper scripts (seed, entry generators) |

## Entry Kinds

- **observation** — Asserted fact, requires URL/file/query anchors
- **hypothesis / hunch** — Belief without solid anchors, labeled honestly
- **prediction** — Falsifiable claim with `p` (0<p<1) and `resolve_by` date
- **resolution** — Resolves a prediction, requires `outcome: true|false`
- **errata** — Corrects a prior entry by appending, never editing
- **meta** — Log-level commentary

## The Errata Principle

When wrong, append an errata. The original stays visible. The log knows the relationship. This is the architecture — not a bug database, but **evidence**.

## Calibration

Predictions accumulate Brier scores as they resolve:

```bash
varve brier varve_log
```

The score is meaningful because the forecasts are append-only — they cannot be edited after the outcome is known.
