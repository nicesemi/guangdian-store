"""管理后台路由"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


def admin_required(request: Request):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)
    return user


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_redirect(request: Request):
    """管理后台 - 监控大屏（/dashboard路径）"""
    return await _render_dashboard(request)

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """管理后台首页 - 监控大屏"""
    return await _render_dashboard(request)

async def _render_dashboard(request: Request):
    user = admin_required(request)
    if hasattr(user, "status_code"):
        return user

    conn = get_db()
    cursor = conn.cursor()

    # 节点统计
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status='online' THEN 1 ELSE 0 END) as online,
            SUM(CASE WHEN status='offline' THEN 1 ELSE 0 END) as offline,
            SUM(CASE WHEN status='maintenance' THEN 1 ELSE 0 END) as maintenance,
            SUM(CASE WHEN load > 80 AND status='online' THEN 1 ELSE 0 END) as alerts
        FROM nodes
    """)
    node_stats = dict(cursor.fetchone())

    # 节点列表
    cursor.execute("SELECT * FROM nodes ORDER BY tops_capacity DESC")
    nodes = [dict(row) for row in cursor.fetchall()]

    # 最近告警（负载>80或离线）
    cursor.execute("SELECT * FROM nodes WHERE load > 80 OR status='offline' ORDER BY last_heartbeat DESC LIMIT 5")
    alerts = [dict(row) for row in cursor.fetchall()]

    # 任务统计
    cursor.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status")
    task_stats = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return request.app.state.templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "user": user, "node_stats": node_stats,
        "nodes": nodes, "alerts": alerts, "task_stats": task_stats
    })


@router.get("/models", response_class=HTMLResponse)
async def models_page(request: Request):
    """模型管理"""
    user = admin_required(request)
    if hasattr(user, "status_code"):
        return user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM models ORDER BY required_tops DESC")
    models = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return request.app.state.templates.TemplateResponse("admin/models.html", {
        "request": request, "user": user, "models": models
    })


@router.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    """计费管理"""
    user = admin_required(request)
    if hasattr(user, "status_code"):
        return user
    conn = get_db()
    cursor = conn.cursor()

    # 收入统计
    cursor.execute("SELECT SUM(amount) FROM bills WHERE type='收入'")
    total_income = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM orders WHERE status='completed'")
    total_orders = cursor.fetchone()[0] or 0

    cursor.execute("SELECT * FROM bills ORDER BY created_at DESC LIMIT 20")
    bills = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 20")
    orders = [dict(row) for row in cursor.fetchall()]

    # 节点收益
    cursor.execute("SELECT * FROM nodes ORDER BY tops_capacity DESC")
    nodes = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return request.app.state.templates.TemplateResponse("admin/billing.html", {
        "request": request, "user": user, "bills": bills, "orders": orders,
        "nodes": nodes, "total_income": total_income, "total_orders": total_orders
    })


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """用户管理"""
    user = admin_required(request)
    if hasattr(user, "status_code"):
        return user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return request.app.state.templates.TemplateResponse("admin/users.html", {
        "request": request, "user": user, "users": users
    })


@router.get("/tickets", response_class=HTMLResponse)
async def tickets_page(request: Request):
    """工单系统"""
    user = admin_required(request)
    if hasattr(user, "status_code"):
        return user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    tickets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return request.app.state.templates.TemplateResponse("admin/tickets.html", {
        "request": request, "user": user, "tickets": tickets
    })
