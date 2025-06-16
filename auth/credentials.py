from datetime import datetime

VALID_USERNAME = "HR_Users"
VALID_PASSWORD = "PTT_hr@2025"

def check_credentials(username: str, password: str) -> bool:
    return username == VALID_USERNAME and password == VALID_PASSWORD

def password_expired(last_change_date: datetime, max_days: int = 30) -> bool:
    return (datetime.now() - last_change_date).days >= max_days

def validate_password_change(old_password: str, new_password: str, confirm_password: str) -> tuple[bool, str]:
    if old_password != VALID_PASSWORD:
        return False, "Incorrect old password"
    if new_password != confirm_password:
        return False, "New passwords do not match"
    if not new_password.strip():
        return False, "Please enter a new password"
    if new_password == old_password:
        return False, "New password must be different from the old password"
    return True, "Password changed successfully"