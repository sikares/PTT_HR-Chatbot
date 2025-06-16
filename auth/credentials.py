from datetime import datetime, timedelta
from typing import Optional

VALID_USERNAME = "HR_Users"
VALID_PASSWORD = "PTT_hr@2025"
PASSWORD_EXPIRY_DAYS = 30

def check_credentials(username: str, password: str) -> bool:
    return username == VALID_USERNAME and password == VALID_PASSWORD

def password_expired(last_change_date: Optional[datetime]) -> bool:
    if last_change_date is None:
        return True
    return (datetime.now() - last_change_date) >= timedelta(days=PASSWORD_EXPIRY_DAYS)

def validate_password_change(old_password: str, new_password: str, confirm_password: str) -> tuple[bool, str]:
    if old_password != VALID_PASSWORD:
        return False, "Incorrect old password"
    if new_password != confirm_password:
        return False, "New passwords do not match"
    if not new_password.strip():
        return False, "New password cannot be empty"
    if new_password == old_password:
        return False, "New password must be different from old password"
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters"
    return True, "Password changed successfully"