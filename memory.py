"""
Loam - Memory & Knowledge Graph System
Stores and connects insights, facts, patterns, and failures
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models import Memory, Task
import networkx as nx
import json

class MemorySystem:
    def __init__(self, db: Session):
        self.db = db
    
    def create_memory(
        self,
        content: str,
        category: str = "insight",
        tags: Optional[List[str]] = None,
        task_id: Optional[int] = None,
        source_type: str = "task",
        source_url: Optional[str] = None,
        confidence: float = 0.5,
        related_memories: Optional[List[int]] = None
    ) -> Memory:
        memory = Memory(
            content=content,
            category=category,
            tags=tags or [],
            task_id=task_id,
            source_type=source_type,
            source_url=source_url,
            confidence=confidence,
            related_memories=related_memories or []
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory
    
    def get_memory(self, memory_id: int) -> Optional[Memory]:
        return self.db.query(Memory).filter(Memory.id == memory_id).first()
    
    def search_memories(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        verified: Optional[int] = None,
        limit: int = 50
    ) -> List[Memory]:
        q = self.db.query(Memory)
        if query:
            q = q.filter(Memory.content.contains(query))
        if category:
            q = q.filter(Memory.category == category)
        if tags:
            for tag in tags:
                q = q.filter(Memory.tags.contains(json.dumps(tag)))
        if verified is not None:
            q = q.filter(Memory.verified == verified)
        return q.order_by(Memory.created_at.desc()).limit(limit).all()
    
    def get_memories_by_task(self, task_id: int) -> List[Memory]:
        return self.db.query(Memory).filter(Memory.task_id == task_id).all()
    
    def update_memory(self, memory_id: int, **kwargs) -> Optional[Memory]:
        memory = self.get_memory(memory_id)
        if not memory:
            return None
        for key, value in kwargs.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
        memory.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(memory)
        return memory
    
    def verify_memory(self, memory_id: int, verified: int, notes: str = "") -> Optional[Memory]:
        """verified: 1=confirmed, -1=disproven, 0=unverified"""
        memory = self.get_memory(memory_id)
        if not memory:
            return None
        memory.verified = verified
        if notes:
            memory.content += f"\n[Verification note: {notes}]"
        self.db.commit()
        self.db.refresh(memory)
        return memory
    
    def link_memories(self, memory_id: int, related_ids: List[int]) -> Optional[Memory]:
        memory = self.get_memory(memory_id)
        if not memory:
            return None
        current = set(memory.related_memories or [])
        current.update(related_ids)
        memory.related_memories = list(current)
        self.db.commit()
        self.db.refresh(memory)
        return memory
    
    def get_memory_graph(self, center_id: Optional[int] = None, depth: int = 2) -> Dict:
        """Export memory connections as a graph structure"""
        G = nx.Graph()
        
        memories = self.db.query(Memory).all()
        for m in memories:
            G.add_node(m.id, content=m.content[:100], category=m.category, confidence=m.confidence)
        
        for m in memories:
            for related in (m.related_memories or []):
                if G.has_node(related):
                    G.add_edge(m.id, related)
        
        if center_id and G.has_node(center_id):
            nodes = nx.single_source_shortest_path_length(G, center_id, cutoff=depth).keys()
            G = G.subgraph(nodes)
        
        return {
            "nodes": [{"id": n, **G.nodes[n]} for n in G.nodes()],
            "edges": [{"source": u, "target": v} for u, v in G.edges()]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        total = self.db.query(Memory).count()
        categories = {}
        for cat in ["insight", "fact", "pattern", "failure", "hypothesis"]:
            categories[cat] = self.db.query(Memory).filter(Memory.category == cat).count()
        
        verified = self.db.query(Memory).filter(Memory.verified == 1).count()
        disproven = self.db.query(Memory).filter(Memory.verified == -1).count()
        unverified = total - verified - disproven
        
        return {
            "total": total,
            "by_category": categories,
            "verified": verified,
            "disproven": disproven,
            "unverified": unverified
        }
    
    def get_recent_insights(self, n: int = 10) -> List[Memory]:
        return self.db.query(Memory).filter(
            Memory.category.in_(["insight", "pattern"])
        ).order_by(Memory.created_at.desc()).limit(n).all()
