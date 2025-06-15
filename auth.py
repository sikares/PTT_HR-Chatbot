from datetime import datetime

VALID_USERNAME = "HR_Users"
VALID_PASSWORD = "PTT_hr@2025"

def check_credentials(username: str, password: str) -> bool:
    return username == VALID_USERNAME and password == VALID_PASSWORD

def password_expired(last_change_date: datetime, max_days: int = 30) -> bool:

    days_since_change = (datetime.now() - last_change_date).days
    return days_since_change >= max_days

def validate_password_change(old_password: str, new_password: str, confirm_password: str) -> tuple[bool, str]:

    if old_password != VALID_PASSWORD:
        return False, "รหัสผ่านเก่าไม่ถูกต้อง"
    if new_password != confirm_password:
        return False, "รหัสผ่านใหม่ไม่ตรงกัน"
    if new_password == "":
        return False, "กรุณากรอกรหัสผ่านใหม่"
    if new_password == old_password:
        return False, "รหัสผ่านใหม่ต้องไม่เหมือนรหัสผ่านเก่า"
    
    return True, "เปลี่ยนรหัสผ่านสำเร็จ"
