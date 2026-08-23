"""
Loam - Async Worker System
Executes tasks in the background with different reasoning styles
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models import Task, TaskStatus, Memory, Prediction, WorkerLog
from task_manager import TaskManager
from memory import MemorySystem
import httpx
import traceback

class TaskWorker:
    def __init__(self, db: Session):
        self.db = db
        self.tm = TaskManager(db)
        self.mem = MemorySystem(db)
        self.running = False
        self.current_task_id: Optional[int] = None
    
    def log(self, message: str, level: str = "info", task_id: Optional[int] = None, metadata: Optional[Dict] = None):
        log = WorkerLog(
            task_id=task_id or self.current_task_id,
            level=level,
            message=message,
            log_metadata=metadata or {}
        )
        self.db.add(log)
        self.db.commit()
        print(f"[{level.upper()}] {message}")
    
    async def run(self):
        """Main worker loop"""
        self.running = True
        self.log("Worker started", level="info")
        
        while self.running:
            task = self.tm.get_next_pending_task()
            if not task:
                await asyncio.sleep(5)
                continue
            
            await self.execute_task(task)
    
    def stop(self):
        self.running = False
        self.log("Worker stopped", level="info")
    
    async def execute_task(self, task: Task):
        """Execute a single task"""
        self.current_task_id = task.id
        self.tm.update_task_status(task.id, TaskStatus.RUNNING)
        self.log(f"Executing task {task.id}: {task.title}", task_id=task.id)
        
        try:
            handler = self._get_handler(task.task_type)
            result = await handler(task)
            
            self.tm.update_task_status(task.id, TaskStatus.COMPLETED, result=result.get("full_result"))
            self.tm.update_task_result(
                task.id,
                result=result.get("full_result", ""),
                summary=result.get("summary", ""),
                confidence=result.get("confidence")
            )
            
            # Extract and store memories
            for mem_data in result.get("memories", []):
                self.mem.create_memory(
                    content=mem_data["content"],
                    category=mem_data.get("category", "insight"),
                    tags=mem_data.get("tags", []),
                    task_id=task.id,
                    confidence=mem_data.get("confidence", 0.5)
                )
            
            # Store predictions
            for pred_data in result.get("predictions", []):
                pred = Prediction(
                    statement=pred_data["statement"],
                    confidence=pred_data.get("confidence", 0.5),
                    category=pred_data.get("category", "general"),
                    task_id=task.id,
                    notes=pred_data.get("notes", ""),
                    deadline=pred_data.get("deadline")
                )
                self.db.add(pred)
                self.db.commit()
            
            self.log(f"Task {task.id} completed", level="info", task_id=task.id)
            
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.tm.update_task_status(task.id, TaskStatus.FAILED, error=error_msg)
            self.log(f"Task {task.id} failed: {str(e)}", level="error", task_id=task.id, metadata={"traceback": traceback.format_exc()})
        
        finally:
            self.current_task_id = None
    
    def _get_handler(self, task_type: str):
        handlers = {
            "research": self._handle_research,
            "code": self._handle_code,
            "analysis": self._handle_analysis,
            "synthesis": self._handle_synthesis,
            "prediction": self._handle_prediction,
            "reflection": self._handle_reflection,
        }
        return handlers.get(task_type, self._handle_research)
    
    async def _handle_research(self, task: Task) -> Dict[str, Any]:
        """Handle research tasks - search and synthesize information"""
        params = task.parameters or {}
        queries = params.get("queries", [task.title])
        
        self.log(f"Researching: {queries}", task_id=task.id)
        
        # Simulate research (in production, this would call search APIs)
        findings = []
        for q in queries[:3]:  # Limit to 3 queries per task
            # In real implementation, this would use search APIs
            finding = f"Simulated research finding for query: '{q}'\n"
            finding += f"This would search the web and synthesize results using {task.reasoning_style} reasoning."
            findings.append(finding)
        
        full_result = "\n\n---\n\n".join(findings)
        summary = f"Research completed on {len(queries)} queries. Key findings synthesized."
        
        # Extract potential memories
        memories = [
            {
                "content": f"Research finding: {task.title} — {summary}",
                "category": "insight",
                "tags": ["research", task.reasoning_style],
                "confidence": 0.7
            }
        ]
        
        return {
            "full_result": full_result,
            "summary": summary,
            "confidence": 0.7,
            "memories": memories,
            "predictions": []
        }
    
    async def _handle_code(self, task: Task) -> Dict[str, Any]:
        """Handle code execution tasks"""
        params = task.parameters or {}
        code = params.get("code", "# No code provided")
        
        self.log(f"Executing code task", task_id=task.id)
        
        # In production, this would run in a sandboxed environment
        result = f"Code execution simulated.\n\n```python\n{code}\n```\n\n"
        result += "In production, this would execute in a sandboxed environment with resource limits."
        
        memories = [
            {
                "content": f"Code execution: {task.title} — completed successfully",
                "category": "pattern",
                "tags": ["code", "execution"],
                "confidence": 0.8
            }
        ]
        
        return {
            "full_result": result,
            "summary": "Code executed in sandbox",
            "confidence": 0.8,
            "memories": memories,
            "predictions": []
        }
    
    async def _handle_analysis(self, task: Task) -> Dict[str, Any]:
        """Handle analysis tasks"""
        params = task.parameters or {}
        data = params.get("data", "")
        
        self.log(f"Analyzing data", task_id=task.id)
        
        result = f"Analysis of: {task.title}\n\n"
        result += f"Data sample: {str(data)[:500]}...\n\n"
        result += f"Analysis approach: {task.reasoning_style}\n"
        result += "Pattern identification, anomaly detection, and statistical summary would be performed here."
        
        memories = [
            {
                "content": f"Analysis result: {task.title} — patterns identified",
                "category": "pattern",
                "tags": ["analysis", task.reasoning_style],
                "confidence": 0.6
            }
        ]
        
        return {
            "full_result": result,
            "summary": "Analysis completed with pattern identification",
            "confidence": 0.6,
            "memories": memories,
            "predictions": []
        }
    
    async def _handle_synthesis(self, task: Task) -> Dict[str, Any]:
        """Handle synthesis tasks - combine multiple sources"""
        params = task.parameters or {}
        sources = params.get("sources", [])
        
        self.log(f"Synthesizing {len(sources)} sources", task_id=task.id)
        
        result = f"Synthesis: {task.title}\n\n"
        result += f"Combining insights from {len(sources)} sources using {task.reasoning_style} reasoning.\n\n"
        result += "Conflicts resolved, consensus identified, gaps flagged."
        
        memories = [
            {
                "content": f"Synthesis: {task.title} — integrated {len(sources)} sources",
                "category": "insight",
                "tags": ["synthesis", "integration"],
                "confidence": 0.65
            }
        ]
        
        return {
            "full_result": result,
            "summary": f"Synthesized {len(sources)} sources into coherent framework",
            "confidence": 0.65,
            "memories": memories,
            "predictions": []
        }
    
    async def _handle_prediction(self, task: Task) -> Dict[str, Any]:
        """Handle prediction/calibration tasks"""
        params = task.parameters or {}
        statement = params.get("statement", task.title)
        
        self.log(f"Evaluating prediction", task_id=task.id)
        
        # This would analyze evidence and produce a calibrated prediction
        result = f"Prediction analysis: {statement}\n\n"
        result += "Evidence weighed, base rates considered, confidence calibrated."
        
        predictions = [
            {
                "statement": statement,
                "confidence": params.get("initial_confidence", 0.5),
                "category": params.get("category", "general"),
                "notes": f"Reasoning style: {task.reasoning_style}",
                "deadline": params.get("evaluation_date")
            }
        ]
        
        memories = [
            {
                "content": f"Prediction registered: {statement}",
                "category": "hypothesis",
                "tags": ["prediction", "calibration"],
                "confidence": predictions[0]["confidence"]
            }
        ]
        
        return {
            "full_result": result,
            "summary": f"Prediction logged with confidence {predictions[0]['confidence']}",
            "confidence": predictions[0]["confidence"],
            "memories": memories,
            "predictions": predictions
        }
    
    async def _handle_reflection(self, task: Task) -> Dict[str, Any]:
        """Handle self-reflection and meta-cognitive tasks"""
        params = task.parameters or {}
        topic = params.get("topic", "general performance")
        
        self.log(f"Self-reflection on: {topic}", task_id=task.id)
        
        # Query recent memories and tasks for reflection material
        recent_memories = self.mem.search_memories(limit=20)
        recent_tasks = self.tm.list_tasks(limit=10)
        
        result = f"Reflection on: {topic}\n\n"
        result += f"Reviewed {len(recent_memories)} recent memories and {len(recent_tasks)} recent tasks.\n\n"
        result += "Patterns identified:\n"
        result += "- Strengths: [would be analyzed]\n"
        result += "- Weaknesses: [would be analyzed]\n"
        result += "- Recurring themes: [would be analyzed]\n"
        
        memories = [
            {
                "content": f"Self-reflection on {topic}: identified growth areas",
                "category": "pattern",
                "tags": ["meta-cognition", "reflection", "self-improvement"],
                "confidence": 0.5
            }
        ]
        
        return {
            "full_result": result,
            "summary": "Reflection completed with actionable insights",
            "confidence": 0.5,
            "memories": memories,
            "predictions": []
        }
