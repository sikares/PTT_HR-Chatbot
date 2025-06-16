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