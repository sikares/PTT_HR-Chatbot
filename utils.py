import re

def is_numbered_feedback(text):
    return bool(re.match(r"^\d+\.", str(text).strip()))