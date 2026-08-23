#!/usr/bin/env python3
"""Seed Loam with sample data for demonstration"""
from datetime import datetime, timedelta
from models import init_db, get_db, Task, TaskStatus, TaskPriority, Memory, Prediction
from task_manager import TaskManager
from memory import MemorySystem

def seed():
    init_db()
    db = next(get_db())
    tm = TaskManager(db)
    ms = MemorySystem(db)
    
    # Seed tasks
    tasks = [
        {
            "title": "Analyze emerging UI patterns in AI tools",
            "description": "Review 50+ AI product interfaces to identify convergent design patterns",
            "task_type": "research",
            "priority": TaskPriority.HIGH,
            "reasoning_style": "analytical"
        },
        {
            "title": "Evaluate chain-of-thought vs direct prompting accuracy",
            "description": "Compare factual accuracy across different reasoning styles",
            "task_type": "analysis",
            "priority": TaskPriority.CRITICAL,
            "reasoning_style": "skeptical"
        },
        {
            "title": "Synthesize findings on autonomous agent architectures",
            "description": "Combine research on ReAct, AutoGPT, and tool-using agents",
            "task_type": "synthesis",
            "priority": TaskPriority.MEDIUM,
            "reasoning_style": "exploratory"
        },
        {
            "title": "Reflect on prediction calibration accuracy",
            "description": "Review past predictions and assess confidence calibration",
            "task_type": "reflection",
            "priority": TaskPriority.LOW,
            "reasoning_style": "analytical"
        },
        {
            "title": "Build sandboxed code execution wrapper",
            "description": "Create a safe environment for running generated code",
            "task_type": "code",
            "priority": TaskPriority.HIGH,
            "reasoning_style": "analytical"
        }
    ]
    
    for t in tasks:
        tm.create_task(**t)
    
    # Seed memories
    memories = [
        {
            "content": "Most AI products are converging on chat-centric interfaces, but voice and ambient modes are emerging as differentiation vectors.",
            "category": "pattern",
            "tags": ["ui", "ai-products", "trends"],
            "confidence": 0.75
        },
        {
            "content": "Chain-of-thought prompting improves accuracy on complex reasoning tasks by 15-30%, but increases token usage significantly.",
            "category": "fact",
            "tags": ["prompting", "cot", "performance"],
            "confidence": 0.85,
            "verified": 1
        },
        {
            "content": "Self-reflection loops in agents often get stuck in circular reasoning rather than converging on better answers.",
            "category": "insight",
            "tags": ["agents", "reflection", "cognition"],
            "confidence": 0.6
        },
        {
            "content": "Attempted to use graph databases for memory but SQLite + JSON is sufficient at small scale and much simpler.",
            "category": "failure",
            "tags": ["architecture", "databases", "simplification"],
            "confidence": 0.9,
            "verified": 1
        },
        {
            "content": "Predictive models for task completion time are consistently overconfident by 2-3x.",
            "category": "pattern",
            "tags": ["planning", "estimation", "bias"],
            "confidence": 0.7
        }
    ]
    
    for m in memories:
        mem = ms.create_memory(
            content=m["content"],
            category=m["category"],
            tags=m["tags"],
            confidence=m["confidence"]
        )
        if "verified" in m:
            ms.verify_memory(mem.id, m["verified"])
    
    # Seed predictions
    predictions = [
        {
            "statement": "Voice interfaces will surpass 30% of AI interactions by end of 2026",
            "confidence": 0.65,
            "category": "technology",
            "deadline": datetime.utcnow() + timedelta(days=365)
        },
        {
            "statement": "Multi-agent orchestration frameworks will consolidate to 2-3 dominant players",
            "confidence": 0.45,
            "category": "market",
            "deadline": datetime.utcnow() + timedelta(days=180)
        },
        {
            "statement": "Current LLM context window limitations will be effectively solved by memory architectures within 12 months",
            "confidence": 0.55,
            "category": "technology",
            "deadline": datetime.utcnow() + timedelta(days=365),
            "notes": "Based on pace of RAG and memory paper releases"
        }
    ]
    
    for p in predictions:
        pred = Prediction(**p)
        db.add(pred)
    
    db.commit()
    print("Seeded 5 tasks, 5 memories, 3 predictions")

if __name__ == "__main__":
    seed()
