"""广电门户路由"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from database import get_db
from auth import get_current_user, authenticate, create_session

router = APIRouter(prefix="", tags=["portal"])


@router.get("/", response_class=HTMLResponse)
async def portal_home(request: Request):
    """广电门户首页"""
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()

    # 统计算力数据
    cursor.execute("SELECT COUNT(*) as total, SUM(tops_capacity) as tops, SUM(CASE WHEN status='online' THEN 1 ELSE 0 END) as online FROM nodes")
    node_stats = dict(cursor.fetchone())
    cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE status='running'")
    task_count = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 5")
    recent_tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    stats = {
        "total_tops": node_stats["tops"] or 0,
        "total_nodes": node_stats["total"] or 0,
        "online_nodes": node_stats["online"] or 0,
        "active_tasks": task_count
    }
    return request.app.state.templates.TemplateResponse("portal.html", {
        "request": request, "user": user, "stats": stats, "recent_tasks": recent_tasks
    })


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return request.app.state.templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """处理登录"""
    user = authenticate(username, password)
    if not user:
        return request.app.state.templates.TemplateResponse("login.html", {
            "request": request, "error": "账号或密码错误"
        })
    session_id = create_session(user)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie("session_id", session_id, httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    """登出"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_id")
    return response
