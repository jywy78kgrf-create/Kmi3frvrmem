#!/usr/bin/env python3
"""Seed varve with demo tasks using the native varve task system."""
import os
import sys

# Add parent to path for varve import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from varve import tasks

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "varve_log")

tasks.add(ROOT, "research", "Analyze whether chain-of-thought prompting improves reasoning accuracy", priority=3)
tasks.add(ROOT, "predict", "Hierarchical reasoning structures (Hi-CoT style) will become the dominant prompting paradigm for math and code tasks by end of 2026", priority=2)
tasks.add(ROOT, "reflect", "Review the CoT observation entry and identify what I got wrong or overstated", priority=3)

print("Seeded 3 tasks into varve queue")
