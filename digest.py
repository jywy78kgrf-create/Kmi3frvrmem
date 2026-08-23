"""
Loam - Digest Generator
Creates periodic summaries of what happened "while you were away"
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models import Digest, Task, TaskStatus, Memory, Prediction
from task_manager import TaskManager
from memory import MemorySystem

class DigestGenerator:
    def __init__(self, db: Session):
        self.db = db
        self.tm = TaskManager(db)
        self.mem = MemorySystem(db)
    
    def generate_digest(self, period_hours: int = 24) -> Digest:
        """Generate a digest for the last N hours"""
        now = datetime.utcnow()
        start = now - timedelta(hours=period_hours)
        
        # Collect stats
        completed_tasks = self.db.query(Task).filter(
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at >= start
        ).all()
        
        failed_tasks = self.db.query(Task).filter(
            Task.status == TaskStatus.FAILED,
            Task.completed_at >= start
        ).all()
        
        new_memories = self.db.query(Memory).filter(
            Memory.created_at >= start
        ).all()
        
        resolved_predictions = self.db.query(Prediction).filter(
            Prediction.resolved == 1,
            Prediction.resolved_at >= start
        ).all()
        
        # Build confidence metrics
        confidences = [t.confidence_score for t in completed_tasks if t.confidence_score is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None
        
        # Build highlights
        highlights = []
        
        if completed_tasks:
            highlights.append(f"Completed {len(completed_tasks)} tasks")
            top_task = max(completed_tasks, key=lambda t: t.priority.value if t.priority else 0)
            highlights.append(f"Highest priority completed: {top_task.title}")
        
        if new_memories:
            insights = [m for m in new_memories if m.category in ("insight", "pattern")]
            if insights:
                highlights.append(f"Discovered {len(insights)} new insights")
        
        if resolved_predictions:
            correct = sum(1 for p in resolved_predictions if p.resolution == "correct")
            highlights.append(f"Resolved {len(resolved_predictions)} predictions ({correct} correct)")
        
        # Build narrative content
        content = self._build_narrative(
            start, now,
            completed_tasks, failed_tasks,
            new_memories, resolved_predictions,
            avg_confidence
        )
        
        digest = Digest(
            period_start=start,
            period_end=now,
            content=content,
            tasks_completed=len(completed_tasks),
            tasks_failed=len(failed_tasks),
            new_memories=len(new_memories),
            predictions_resolved=len(resolved_predictions),
            avg_confidence=avg_confidence,
            highlights=highlights
        )
        
        self.db.add(digest)
        self.db.commit()
        self.db.refresh(digest)
        return digest
    
    def _build_narrative(
        self,
        start: datetime,
        end: datetime,
        completed: List[Task],
        failed: List[Task],
        memories: List[Memory],
        predictions: List[Prediction],
        avg_confidence: float
    ) -> str:
        """Build human-readable digest narrative"""
        lines = []
        lines.append(f"# Digest: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        # Executive summary
        lines.append("## Summary")
        total = len(completed) + len(failed)
        lines.append(f"- Tasks processed: {total} ({len(completed)} succeeded, {len(failed)} failed)")
        lines.append(f"- New memories formed: {len(memories)}")
        lines.append(f"- Predictions resolved: {len(predictions)}")
        if avg_confidence:
            lines.append(f"- Average confidence: {avg_confidence:.2f}")
        lines.append("")
        
        # Completed tasks
        if completed:
            lines.append("## Completed Work")
            for task in completed[:5]:  # Top 5
                lines.append(f"### {task.title}")
                lines.append(f"- Type: {task.task_type} | Priority: {task.priority.name} | Confidence: {task.confidence_score or 'N/A'}")
                if task.result_summary:
                    lines.append(f"- Result: {task.result_summary}")
                lines.append("")
        
        # Key insights
        insights = [m for m in memories if m.category in ("insight", "pattern")][:5]
        if insights:
            lines.append("## Key Insights")
            for mem in insights:
                lines.append(f"- **{mem.category.upper()}**: {mem.content[:200]}...")
            lines.append("")
        
        # Failures and lessons
        if failed:
            lines.append("## Failures & Lessons")
            lines.append(f"{len(failed)} tasks failed. Key learnings:")
            for task in failed[:3]:
                error_preview = (task.error_log or "Unknown error")[:150]
                lines.append(f"- '{task.title}': {error_preview}...")
            lines.append("")
        
        # Prediction updates
        if predictions:
            lines.append("## Prediction Updates")
            for pred in predictions:
                status = "✓" if pred.resolution == "correct" else "✗"
                lines.append(f"- {status} '{pred.statement[:80]}...' (confidence was {pred.confidence:.2f})")
            lines.append("")
        
        # Forward looking
        lines.append("## What's Next")
        pending = self.db.query(Task).filter(Task.status == TaskStatus.PENDING).count()
        lines.append(f"- {pending} tasks waiting in queue")
        
        # Upcoming deadlines
        upcoming = self.db.query(Task).filter(
            Task.deadline is not None,
            Task.deadline <= end + timedelta(days=3),
            Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
        ).all()
        if upcoming:
            lines.append("- Upcoming deadlines:")
            for task in upcoming[:3]:
                lines.append(f"  - '{task.title}' due {task.deadline.strftime('%Y-%m-%d')}")
        
        lines.append("")
        lines.append("---")
        lines.append("*This digest was auto-generated. Mark as read when reviewed.*")
        
        return "\n".join(lines)
    
    def get_latest_digest(self) -> Digest:
        """Get the most recent digest, or generate one if none exists"""
        latest = self.db.query(Digest).order_by(Digest.created_at.desc()).first()
        if not latest:
            return self.generate_digest()
        return latest
    
    def get_unread_digests(self) -> List[Digest]:
        return self.db.query(Digest).filter(Digest.read == 0).order_by(Digest.created_at.desc()).all()
    
    def mark_read(self, digest_id: int) -> bool:
        digest = self.db.query(Digest).filter(Digest.id == digest_id).first()
        if not digest:
            return False
        digest.read = 1
        self.db.commit()
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        total_digests = self.db.query(Digest).count()
        unread = self.db.query(Digest).filter(Digest.read == 0).count()
        
        return {
            "total": total_digests,
            "unread": unread,
            "latest": self.get_latest_digest().created_at.isoformat() if self.get_latest_digest() else None
        }
