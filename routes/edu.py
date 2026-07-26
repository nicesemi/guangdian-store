"""教育板块路由"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/edu", tags=["edu"])


@router.get("/", response_class=HTMLResponse)
async def edu_index(request: Request):
    """deependu.school首页"""
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM edu_courses ORDER BY id DESC")
    courses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return request.app.state.templates.TemplateResponse("edu/index.html", {
        "request": request, "user": user, "courses": courses
    })


@router.get("/tutor", response_class=HTMLResponse)
async def tutor_page(request: Request):
    """AI家教"""
    user = get_current_user(request)
    return request.app.state.templates.TemplateResponse("edu/tutor.html", {
        "request": request, "user": user
    })


@router.get("/courses", response_class=HTMLResponse)
async def courses_page(request: Request):
    """课程广场"""
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM edu_courses ORDER BY id")
    courses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return request.app.state.templates.TemplateResponse("edu/courses.html", {
        "request": request, "user": user, "courses": courses
    })


@router.get("/practice", response_class=HTMLResponse)
async def practice_page(request: Request, course_id: int = 0):
    """题库练习"""
    user = get_current_user(request)
    conn = get_db()
    cursor = conn.cursor()

    if course_id:
        cursor.execute("SELECT * FROM edu_exercises WHERE course_id=?", (course_id,))
    else:
        cursor.execute("SELECT * FROM edu_exercises ORDER BY id")

    exercises = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM edu_courses")
    courses = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return request.app.state.templates.TemplateResponse("edu/practice.html", {
        "request": request, "user": user, "exercises": exercises,
        "courses": courses, "selected_course": course_id
    })


@router.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    """学习报告"""
    user = get_current_user(request)
    return request.app.state.templates.TemplateResponse("edu/report.html", {
        "request": request, "user": user
    })


@router.get("/teacher", response_class=HTMLResponse)
async def teacher_page(request: Request):
    """教师端"""
    user = get_current_user(request)
    return request.app.state.templates.TemplateResponse("edu/teacher.html", {
        "request": request, "user": user
    })
