#!/usr/bin/env python3
"""Generate a prediction entry JSON for varve."""
import json
import sys

data = {
    "kind": "prediction",
    "title": "Hi-CoT-style hierarchical reasoning will dominate math and code prompting by end of 2026",
    "body": "Hierarchical Chain-of-Thought (Hi-CoT) and similar structured reasoning approaches show strong empirical results: 6.2% average accuracy gains with 13.9% shorter traces across 13 model configurations, reaching 100% on AMC and MATH500 when format adherence is strict. The key question is whether this will be adopted as the default paradigm versus remaining a niche research method.\n\nFactors increasing likelihood: (1) major labs are already investing in reasoning optimization as a primary competitive axis, (2) the structure improves both accuracy AND efficiency, which matters for API costs, (3) it requires no fine-tuning - zero-shot inference-time only.\n\nFactors decreasing likelihood: (1) the field moves fast and dominant paradigms often emerge from unexpected directions, (2) Hi-CoT requires strict format adherence which limits gains for smaller models, (3) dominant is vague - even if widely used, it may coexist rather than replace simpler CoT.",
    "anchors": [],
    "tags": ["hierarchical-reasoning", "prompting", "forecast"],
    "prediction": {
        "statement": "Hierarchical reasoning structures (Hi-CoT style) will become the dominant prompting paradigm for math and code tasks by end of 2026",
        "p": 0.55,
        "resolve_by": "2026-12-31"
    },
    "task_id": "t000002"
}

json.dump(data, sys.stdout, indent=2)
