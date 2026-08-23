"""
Loam - Task Management System
Handles CRUD operations for tasks and task lifecycle
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models import Task, TaskStatus, TaskPriority, get_db

class TaskManager:
    def __init__(self, db: Session):
        self.db = db
    
    def create_task(
        self,
        title: str,
        description: str = "",
        task_type: str = "research",
        priority: TaskPriority = TaskPriority.MEDIUM,
        reasoning_style: str = "analytical",
        deadline: Optional[datetime] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            reasoning_style=reasoning_style,
            deadline=deadline,
            parameters=parameters or {}
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def get_task(self, task_id: int) -> Optional[Task]:
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        query = self.db.query(Task)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if task_type:
            query = query.filter(Task.task_type == task_type)
        return query.order_by(Task.priority.desc(), Task.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_next_pending_task(self) -> Optional[Task]:
        """Get the highest priority pending task"""
        return self.db.query(Task).filter(
            Task.status == TaskStatus.PENDING
        ).order_by(
            Task.priority.desc(),
            Task.created_at.asc()
        ).first()
    
    def update_task_status(self, task_id: int, status: TaskStatus, result: Optional[str] = None, error: Optional[str] = None) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None
        
        task.status = status
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.utcnow()
            task.attempts += 1
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task.completed_at = datetime.utcnow()
            if result:
                task.result = result
            if error:
                task.error_log = error
        
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def update_task_result(self, task_id: int, result: str, summary: str = "", confidence: Optional[float] = None) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None
        task.result = result
        task.result_summary = summary
        if confidence is not None:
            task.confidence_score = confidence
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def delete_task(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        self.db.delete(task)
        self.db.commit()
        return True
    
    def get_task_stats(self) -> Dict[str, Any]:
        total = self.db.query(Task).count()
        pending = self.db.query(Task).filter(Task.status == TaskStatus.PENDING).count()
        running = self.db.query(Task).filter(Task.status == TaskStatus.RUNNING).count()
        completed = self.db.query(Task).filter(Task.status == TaskStatus.COMPLETED).count()
        failed = self.db.query(Task).filter(Task.status == TaskStatus.FAILED).count()
        
        return {
            "total": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / (completed + failed) if (completed + failed) > 0 else 0
        }
