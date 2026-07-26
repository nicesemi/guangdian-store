"""开放平台路由"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/developer", tags=["developer"])


@router.get("/", response_class=HTMLResponse)
async def developer_index(request: Request):
    """开放平台首页"""
    user = get_current_user(request)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM skills WHERE developer_id=?", (user["user_id"],))
    skill_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(installs) FROM skills WHERE developer_id=?", (user["user_id"],))
    total_installs = cursor.fetchone()[0] or 0
    cursor.execute("SELECT AVG(rating) FROM skills WHERE developer_id=?", (user["user_id"],))
    avg_rating = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM orders JOIN skills ON orders.skill_id = skills.id WHERE skills.developer_id=?", (user["user_id"],))
    total_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT * FROM skills WHERE developer_id=? ORDER BY installs DESC", (user["user_id"],))
    my_skills = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return request.app.state.templates.TemplateResponse("developer/index.html", {
        "request": request, "user": user, "skill_count": skill_count,
        "total_installs": total_installs, "avg_rating": round(avg_rating, 1),
        "total_revenue": total_revenue, "my_skills": my_skills
    })


@router.get("/sdk", response_class=HTMLResponse)
async def sdk_page(request: Request):
    """SDK与API文档"""
    user = get_current_user(request)
    return request.app.state.templates.TemplateResponse("developer/sdk.html", {
        "request": request, "user": user
    })


@router.get("/console", response_class=HTMLResponse)
async def console_page(request: Request):
    """API调试控制台"""
    user = get_current_user(request)
    return request.app.state.templates.TemplateResponse("developer/console.html", {
        "request": request, "user": user
    })


@router.get("/submit", response_class=HTMLResponse)
async def submit_page(request: Request):
    """提交Skill"""
    user = get_current_user(request)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM models WHERE status='active'")
    models = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return request.app.state.templates.TemplateResponse("developer/submit.html", {
        "request": request, "user": user, "models": models
    })
