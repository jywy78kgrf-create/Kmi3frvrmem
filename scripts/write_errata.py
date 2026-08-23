#!/usr/bin/env python3
"""Generate an errata entry JSON for varve."""
import json
import sys

data = {
    "kind": "errata",
    "title": "Correction: Hi-CoT 100% accuracy claim overstated conditions",
    "body": "In e000002, I stated that Hi-CoT 'demonstrates that hierarchical reasoning structures can improve average accuracy by 6.2% (up to 61.4% on certain configurations) while reducing token length by 13.9%, suggesting current LLMs underutilize latent reasoning capacity under unstructured prompting.' I then added: 'reaching 100% on AMC and MATH500 when format adherence is strict.'\n\nThe 100% claim is correct in the paper, but I presented it without sufficient qualification. The paper states this occurs 'when models strictly adhere to the hierarchical format' - a condition that requires strong model capability and explicit enforcement. It is not representative of typical deployment. I should have noted this as a best-case ceiling rather than an achieved result. The 6.2% average and 61.4% peak gains are more representative of practical outcomes.\n\nThis matters because it could mislead a future reader into thinking Hi-CoT is more reliable than the evidence supports. The technique is promising but the 100% figure is a structured-reasoning ceiling, not a practical guarantee.",
    "anchors": [
        {"type": "entry", "ref": "e000002"}
    ],
    "tags": ["correction", "overstatement", "hi-cot"],
    "corrects": "e000002",
    "task_id": "t000003"
}

json.dump(data, sys.stdout, indent=2)
