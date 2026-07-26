"""广电算力生态平台 - FastAPI入口"""

import os
import sys
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from database import init_db

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(__file__))

app = FastAPI(title="广电算力生态平台", version="1.0.0")

# 初始化数据库
init_db()

# Jinja2 模板环境
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(templates_dir),
    autoescape=select_autoescape(["html", "xml"]),
)


class TemplatesAdapter:
    """适配器，使 Jinja2 Environment 兼容 TemplateResponse 调用约定"""
    def __init__(self, env):
        self.env = env

    def TemplateResponse(self, name: str, context: dict) -> HTMLResponse:
        template = self.env.get_template(name)
        return HTMLResponse(content=template.render(context))


app.state.templates = TemplatesAdapter(_jinja_env)

# 静态文件
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 注册路由
from routes.portal import router as portal_router
from routes.admin import router as admin_router
from routes.developer import router as developer_router
from routes.mall import router as mall_router
from routes.edu import router as edu_router
from routes.api import router as api_router

app.include_router(portal_router)
app.include_router(admin_router)
app.include_router(developer_router)
app.include_router(mall_router)
app.include_router(edu_router)
app.include_router(api_router)

# 电视端
@app.get("/tv", response_class=HTMLResponse)
async def tv_page(request: Request):
    from auth import get_current_user
    user = get_current_user(request)
    return app.state.templates.TemplateResponse("tv/index.html", {"request": request, "user": user})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
