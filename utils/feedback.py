import csv
from datetime import datetime
from pathlib import Path
from typing import Literal

FEEDBACK_FILE = Path("data/feedback_log.csv")

def log_feedback(question: str, answer: str, feedback_type: Literal["like", "dislike"]):
    FEEDBACK_FILE.parent.mkdir(exist_ok=True)
    
    if not FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "question", "answer", "feedback_type"])
    
    with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), question, answer, feedback_type])

def get_feedback_stats() -> dict:
    if not FEEDBACK_FILE.exists():
        return {"like": 0, "dislike": 0, "total": 0}
    
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        feedbacks = list(reader)
    
    stats = {
        "like": sum(1 for f in feedbacks if f["feedback_type"] == "like"),
        "dislike": sum(1 for f in feedbacks if f["feedback_type"] == "dislike"),
        "total": len(feedbacks)
    }
    stats["satisfaction"] = stats["like"] / stats["total"] if stats["total"] > 0 else 0
    return stats