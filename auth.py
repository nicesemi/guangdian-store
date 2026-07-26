"""简易Session-based认证"""

import hashlib
import time
from typing import Optional, Dict
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from database import get_db, hash_password

# 简单的内存Session存储
sessions: Dict[str, dict] = {}


def create_session(user: dict) -> str:
    """创建Session并返回session_id"""
    session_id = hashlib.sha256(f"{user['id']}_{time.time()}".encode()).hexdigest()
    sessions[session_id] = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "tv_account": user.get("tv_account"),
        "balance": user.get("balance", 0.0),
        "created_at": time.time()
    }
    return session_id


def get_current_user(request: Request) -> Optional[dict]:
    """从Cookie中获取当前用户"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        session = sessions[session_id]
        # Session有效期24小时
        if time.time() - session["created_at"] < 86400:
            return session
        else:
            del sessions[session_id]
    return None


def login_required(request: Request):
    """要求登录的依赖"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


def admin_required(request: Request):
    """要求管理员权限的依赖"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def authenticate(username: str, password: str) -> Optional[dict]:
    """验证用户凭据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, role, tv_account, balance FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
