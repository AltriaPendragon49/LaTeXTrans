from datetime import datetime, timezone, timedelta

def get_cst_now() -> datetime:
    """获取当前的中国标准时间 (UTC+8)"""
    return datetime.now(timezone(timedelta(hours=8)))

def get_cst_now_iso() -> str:
    """获取当前中国标准时间的 ISO 格式字符串"""
    return get_cst_now().isoformat()
