"""广电商城路由"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/mall", tags=["mall"])


@router.get("/", response_class=HTMLResponse)
async def mall_index(request: Request, category: str = ""):
    """广电商城首页"""
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()

    if category:
        cursor.execute("SELECT * FROM skills WHERE category=? AND status='active' ORDER BY installs DESC", (category,))
    else:
        cursor.execute("SELECT * FROM skills WHERE status='active' ORDER BY installs DESC")

    skills = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # 获取用户已安装的skill ids
    installed_ids = set()
    if user:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT skill_id FROM user_skills WHERE user_id=?", (user["user_id"],))
        installed_ids = {row[0] for row in cursor.fetchall()}
        conn.close()

    return request.app.state.templates.TemplateResponse("mall/index.html", {
        "request": request, "user": user, "skills": skills,
        "category": category, "installed_ids": installed_ids
    })


@router.get("/detail/{skill_id}", response_class=HTMLResponse)
async def skill_detail(request: Request, skill_id: int):
    """Skill详情"""
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM skills WHERE id=?", (skill_id,))
    skill = cursor.fetchone()
    if not skill:
        conn.close()
        return RedirectResponse(url="/mall", status_code=302)
    skill = dict(skill)
    conn.close()

    installed = False
    if user:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=?", (user["user_id"], skill_id))
        installed = cursor.fetchone() is not None
        conn.close()

    return request.app.state.templates.TemplateResponse("mall/detail.html", {
        "request": request, "user": user, "skill": skill, "installed": installed
    })


@router.get("/my", response_class=HTMLResponse)
async def my_skills(request: Request):
    """我的Skill"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, us.installed_at FROM skills s
        JOIN user_skills us ON s.id = us.skill_id
        WHERE us.user_id=? ORDER BY us.installed_at DESC
    """, (user["user_id"],))
    skills = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return request.app.state.templates.TemplateResponse("mall/my.html", {
        "request": request, "user": user, "skills": skills
    })
