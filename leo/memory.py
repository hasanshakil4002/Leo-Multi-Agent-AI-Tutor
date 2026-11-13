import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

DEFAULT_MEMORY_DIR = os.environ.get("LEO_MEMORY_DIR", "memory_store")


def _safe_filename(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())
    return slug or "student"


class StudentMemory:
    def __init__(self, student_name: str, memory_dir: str = DEFAULT_MEMORY_DIR):
        self.student_name = student_name
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        self.path = os.path.join(self.memory_dir, f"{_safe_filename(student_name)}.json")
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "student_name": self.student_name,
            "created_at": datetime.utcnow().isoformat(),
            "topics": {},  # topic -> {"sessions": [...], "weak_areas": [...]}
        }

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    # ---- read helpers -----------------------------------------------------

    def get_topic_history(self, topic: str) -> Dict[str, Any]:
        return self.data["topics"].get(topic, {"sessions": [], "weak_areas": []})

    def get_weak_areas(self, topic: str) -> List[str]:
        return self.get_topic_history(topic).get("weak_areas", [])

    def context_snippet(self, topic: str) -> str:
        """A short natural-language memory summary injected into agent prompts."""
        hist = self.get_topic_history(topic)
        if not hist["sessions"]:
            return f"This is {self.student_name}'s first session on '{topic}'. No prior history."
        last = hist["sessions"][-1]
        weak = ", ".join(hist["weak_areas"]) or "none recorded"
        return (
            f"{self.student_name} has studied '{topic}' before "
            f"({len(hist['sessions'])} previous session(s)). "
            f"Last quiz score: {last.get('score_percent', 'N/A')}%. "
            f"Known weak areas to reinforce: {weak}."
        )

    # ---- write helpers ------------------------------------------------

    def record_session(self, topic: str, score_percent: float, weak_areas: List[str]) -> None:
        topics = self.data.setdefault("topics", {})
        entry = topics.setdefault(topic, {"sessions": [], "weak_areas": []})
        entry["sessions"].append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "score_percent": score_percent,
                "weak_areas": weak_areas,
            }
        )
        # keep a de-duplicated rolling list of weak areas across sessions
        merged = list(dict.fromkeys(entry["weak_areas"] + weak_areas))
        entry["weak_areas"] = merged
        self.save()

    def clear_weak_areas(self, topic: str, resolved: Optional[List[str]] = None) -> None:
        """Call after a successful re-teach + re-quiz to drop resolved weak areas."""
        entry = self.data["topics"].get(topic)
        if not entry:
            return
        if resolved is None:
            entry["weak_areas"] = []
        else:
            entry["weak_areas"] = [w for w in entry["weak_areas"] if w not in resolved]
        self.save()
