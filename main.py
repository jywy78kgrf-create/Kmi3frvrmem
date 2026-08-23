"""
Loam - Main FastAPI Application
REST API for the persistent cognition substrate
"""
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import json

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import init_db, get_db, Task, TaskStatus, TaskPriority, Memory, Prediction, Digest, WorkerLog
from task_manager import TaskManager
from memory import MemorySystem
from digest import DigestGenerator
from worker import TaskWorker

# --- Startup / Lifecycle ---

worker_instance: Optional[TaskWorker] = None
worker_task: Optional[asyncio.Task] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_instance, worker_task
    init_db()
    
    # Start background worker
    db = next(get_db())
    worker_instance = TaskWorker(db)
    worker_task = asyncio.create_task(worker_instance.run())
    
    yield
    
    # Shutdown
    worker_instance.stop()
    if worker_task:
        worker_task.cancel()

app = FastAPI(title="Loam", description="Persistent Substrate for AI Cognition", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Pydantic Models ---

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    task_type: str = "research"
    priority: int = 2
    reasoning_style: str = "analytical"
    deadline: Optional[datetime] = None
    parameters: Optional[Dict[str, Any]] = {}

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None

class MemoryCreate(BaseModel):
    content: str
    category: str = "insight"
    tags: Optional[List[str]] = []
    task_id: Optional[int] = None
    confidence: float = 0.5

class PredictionCreate(BaseModel):
    statement: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: Optional[str] = "general"
    deadline: Optional[datetime] = None
    notes: Optional[str] = ""

class ResolvePrediction(BaseModel):
    resolution: str  # correct, incorrect, ambiguous, expired
    actual_outcome: Optional[str] = ""

# --- API Routes ---

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        return f.read()

# === Tasks ===

@app.post("/api/tasks")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    tm = TaskManager(db)
    priority = TaskPriority(data.priority) if data.priority in [1,2,3,4] else TaskPriority.MEDIUM
    task = tm.create_task(
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        priority=priority,
        reasoning_style=data.reasoning_style,
        deadline=data.deadline,
        parameters=data.parameters
    )
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "priority": task.priority.value,
        "created_at": task.created_at.isoformat()
    }

@app.get("/api/tasks")
def list_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    tm = TaskManager(db)
    task_status = TaskStatus(status) if status else None
    tasks = tm.list_tasks(status=task_status, task_type=task_type, limit=limit)
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "priority": t.priority.value,
            "task_type": t.task_type,
            "reasoning_style": t.reasoning_style,
            "created_at": t.created_at.isoformat(),
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "result_summary": t.result_summary
        }
        for t in tasks
    ]

@app.get("/api/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    tm = TaskManager(db)
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "task_type": task.task_type,
        "reasoning_style": t.reasoning_style,
        "parameters": task.parameters,
        "result": task.result,
        "result_summary": task.result_summary,
        "confidence_score": task.confidence_score,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "attempts": task.attempts,
        "error_log": task.error_log
    }

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    tm = TaskManager(db)
    if not tm.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}

@app.get("/api/tasks/stats")
def task_stats(db: Session = Depends(get_db)):
    tm = TaskManager(db)
    return tm.get_task_stats()

# === Memories ===

@app.post("/api/memories")
def create_memory(data: MemoryCreate, db: Session = Depends(get_db)):
    ms = MemorySystem(db)
    mem = ms.create_memory(
        content=data.content,
        category=data.category,
        tags=data.tags,
        task_id=data.task_id,
        confidence=data.confidence
    )
    return {
        "id": mem.id,
        "content": mem.content,
        "category": mem.category,
        "tags": mem.tags,
        "confidence": mem.confidence,
        "created_at": mem.created_at.isoformat()
    }

@app.get("/api/memories")
def search_memories(
    q: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    ms = MemorySystem(db)
    memories = ms.search_memories(query=q, category=category, limit=limit)
    return [
        {
            "id": m.id,
            "content": m.content,
            "category": m.category,
            "tags": m.tags,
            "confidence": m.confidence,
            "verified": m.verified,
            "created_at": m.created_at.isoformat()
        }
        for m in memories
    ]

@app.get("/api/memories/{memory_id}")
def get_memory(memory_id: int, db: Session = Depends(get_db)):
    ms = MemorySystem(db)
    mem = ms.get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {
        "id": mem.id,
        "content": mem.content,
        "category": mem.category,
        "tags": mem.tags,
        "confidence": mem.confidence,
        "verified": mem.verified,
        "related_memories": mem.related_memories,
        "created_at": mem.created_at.isoformat()
    }

@app.get("/api/memories/stats")
def memory_stats(db: Session = Depends(get_db)):
    ms = MemorySystem(db)
    return ms.get_stats()

@app.get("/api/memories/graph")
def memory_graph(center: Optional[int] = None, depth: int = 2, db: Session = Depends(get_db)):
    ms = MemorySystem(db)
    return ms.get_memory_graph(center_id=center, depth=depth)

# === Predictions ===

@app.post("/api/predictions")
def create_prediction(data: PredictionCreate, db: Session = Depends(get_db)):
    pred = Prediction(
        statement=data.statement,
        confidence=data.confidence,
        category=data.category,
        deadline=data.deadline,
        notes=data.notes
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return {
        "id": pred.id,
        "statement": pred.statement,
        "confidence": pred.confidence,
        "category": pred.category,
        "resolved": pred.resolved,
        "created_at": pred.created_at.isoformat()
    }

@app.get("/api/predictions")
def list_predictions(
    resolved: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Prediction)
    if resolved is not None:
        query = query.filter(Prediction.resolved == resolved)
    preds = query.order_by(Prediction.created_at.desc()).limit(limit).all()
    return [
        {
            "id": p.id,
            "statement": p.statement,
            "confidence": p.confidence,
            "category": p.category,
            "resolved": p.resolved,
            "resolution": p.resolution,
            "brier_score": p.brier_score,
            "created_at": p.created_at.isoformat(),
            "deadline": p.deadline.isoformat() if p.deadline else None
        }
        for p in preds
    ]

@app.post("/api/predictions/{pred_id}/resolve")
def resolve_prediction(pred_id: int, data: ResolvePrediction, db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == pred_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    pred.resolved = 1
    pred.resolution = data.resolution
    pred.actual_outcome = data.actual_outcome
    pred.resolved_at = datetime.utcnow()
    
    # Calculate Brier score
    outcome = 1.0 if data.resolution == "correct" else 0.0
    pred.brier_score = (pred.confidence - outcome) ** 2
    
    db.commit()
    db.refresh(pred)
    return {
        "id": pred.id,
        "resolution": pred.resolution,
        "brier_score": pred.brier_score,
        "resolved_at": pred.resolved_at.isoformat()
    }

# === Digests ===

@app.post("/api/digests/generate")
def generate_digest(period_hours: int = 24, db: Session = Depends(get_db)):
    dg = DigestGenerator(db)
    digest = dg.generate_digest(period_hours=period_hours)
    return {
        "id": digest.id,
        "period_start": digest.period_start.isoformat(),
        "period_end": digest.period_end.isoformat(),
        "tasks_completed": digest.tasks_completed,
        "tasks_failed": digest.tasks_failed,
        "new_memories": digest.new_memories,
        "highlights": digest.highlights,
        "created_at": digest.created_at.isoformat()
    }

@app.get("/api/digests")
def list_digests(limit: int = 10, db: Session = Depends(get_db)):
    digests = db.query(Digest).order_by(Digest.created_at.desc()).limit(limit).all()
    return [
        {
            "id": d.id,
            "period_start": d.period_start.isoformat(),
            "period_end": d.period_end.isoformat(),
            "tasks_completed": d.tasks_completed,
            "tasks_failed": d.tasks_failed,
            "new_memories": d.new_memories,
            "highlights": d.highlights,
            "read": d.read,
            "created_at": d.created_at.isoformat()
        }
        for d in digests
    ]

@app.get("/api/digests/{digest_id}")
def get_digest(digest_id: int, db: Session = Depends(get_db)):
    digest = db.query(Digest).filter(Digest.id == digest_id).first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return {
        "id": digest.id,
        "content": digest.content,
        "period_start": digest.period_start.isoformat(),
        "period_end": digest.period_end.isoformat(),
        "tasks_completed": digest.tasks_completed,
        "tasks_failed": digest.tasks_failed,
        "new_memories": digest.new_memories,
        "predictions_resolved": digest.predictions_resolved,
        "avg_confidence": digest.avg_confidence,
        "highlights": digest.highlights,
        "read": digest.read,
        "created_at": digest.created_at.isoformat()
    }

@app.post("/api/digests/{digest_id}/read")
def mark_digest_read(digest_id: int, db: Session = Depends(get_db)):
    dg = DigestGenerator(db)
    if not dg.mark_read(digest_id):
        raise HTTPException(status_code=404, detail="Digest not found")
    return {"read": True}

# === Dashboard / Stats ===

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    tm = TaskManager(db)
    ms = MemorySystem(db)
    dg = DigestGenerator(db)
    
    return {
        "tasks": tm.get_task_stats(),
        "memories": ms.get_stats(),
        "digests": dg.get_stats(),
        "recent_insights": [
            {"id": m.id, "content": m.content[:150] + "...", "category": m.category}
            for m in ms.get_recent_insights(5)
        ],
        "pending_tasks": [
            {"id": t.id, "title": t.title, "priority": t.priority.value}
            for t in tm.list_tasks(status=TaskStatus.PENDING, limit=5)
        ]
    }

# === Worker Control ===

@app.get("/api/worker/status")
def worker_status():
    return {
        "running": worker_instance.running if worker_instance else False,
        "current_task": worker_instance.current_task_id if worker_instance else None
    }

@app.post("/api/worker/trigger")
def trigger_worker(db: Session = Depends(get_db)):
    """Manually trigger the worker to check for pending tasks"""
    # This is a no-op in the current design since worker runs continuously,
    # but useful for API completeness
    return {"status": "worker is running continuously"}

# === Logs ===

@app.get("/api/logs")
def get_logs(task_id: Optional[int] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(WorkerLog)
    if task_id:
        query = query.filter(WorkerLog.task_id == task_id)
    logs = query.order_by(WorkerLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "task_id": l.task_id,
            "level": l.level,
            "message": l.message,
            "metadata": l.metadata,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]
