"""REST API路由"""

from fastapi import APIRouter, Request, Depends, HTTPException
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/nodes")
async def get_nodes():
    """获取所有节点状态（含模型名）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.*, m.name as model_name, m.type as model_type
        FROM nodes n
        LEFT JOIN models m ON n.model_id = m.id
        ORDER BY n.id
    """)
    nodes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"nodes": nodes, "count": len(nodes)}


@router.get("/stats")
async def get_stats():
    """获取平台统计数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(tops_capacity) as total_tops, COUNT(*) as total, SUM(CASE WHEN status='online' THEN 1 ELSE 0 END) as online FROM nodes")
    nodes = dict(cursor.fetchone())
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='running'")
    active = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM skills WHERE status='active'")
    skills = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    conn.close()
    return {
        "total_tops": nodes["total_tops"] or 0,
        "total_nodes": nodes["total"] or 0,
        "online_nodes": nodes["online"] or 0,
        "active_tasks": active,
        "total_skills": skills,
        "total_users": users
    }


@router.get("/skills")
async def get_skills():
    """获取全部Skill列表（含本地部署/算力/Token信息）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, m.name as model_name, m.required_tops as model_tops
        FROM skills s
        LEFT JOIN models m ON s.model_id = m.id
        WHERE s.status='active'
        ORDER BY s.installs DESC
    """)
    skills = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return skills


@router.get("/user/installed-skills")
async def get_installed_skills(request: Request):
    """获取当前用户已安装的Skill列表"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="需要登录")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.name, s.category, s.description, s.price,
               s.local_deploy, s.tops_required, s.token_cost_per_call,
               s.skill_url, s.rating, us.installed_at,
               m.name as model_name, m.required_tops as model_tops
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        LEFT JOIN models m ON s.model_id = m.id
        WHERE us.user_id = ?
        ORDER BY us.installed_at DESC
    """, (user["user_id"],))
    skills = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"installed": skills, "count": len(skills)}


@router.post("/skills/{skill_id}/install")
async def install_skill(request: Request, skill_id: int):
    """安装Skill"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="需要登录")

    conn = get_db()
    cursor = conn.cursor()

    # 检查Skill是否存在
    cursor.execute("SELECT * FROM skills WHERE id=?", (skill_id,))
    skill = cursor.fetchone()
    if not skill:
        conn.close()
        raise HTTPException(status_code=404, detail="Skill不存在")

    # 检查是否已安装
    cursor.execute("SELECT 1 FROM user_skills WHERE user_id=? AND skill_id=?", (user["user_id"], skill_id))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="已安装该Skill")

    skill = dict(skill)

    # 如果收费，检查余额
    if skill["price"] > 0:
        cursor.execute("SELECT balance FROM users WHERE id=?", (user["user_id"],))
        balance = cursor.fetchone()[0]
        if balance < skill["price"]:
            conn.close()
            raise HTTPException(status_code(402), detail=f"余额不足，需要 ¥{skill['price']}")

        # 扣款
        cursor.execute("UPDATE users SET balance = balance - ? WHERE id=?", (skill["price"], user["user_id"]))
        # 创建订单
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO orders (user_id, skill_id, amount, payment_method, status, created_at) VALUES (?,?,?,?,?,?)",
            (user["user_id"], skill_id, skill["price"], "balance", "completed", now)
        )
        # 创建账单
        cursor.execute("INSERT INTO bills (user_id, amount, type, created_at) VALUES (?,?,?,?)",
                       (user["user_id"], -skill["price"], "消费", now))

    # 安装
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO user_skills (user_id, skill_id, installed_at) VALUES (?,?,?)",
                   (user["user_id"], skill_id, now))
    cursor.execute("UPDATE skills SET installs = installs + 1 WHERE id=?", (skill_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"已成功安装 {skill['name']}"}


@router.post("/skills/{skill_id}/uninstall")
async def uninstall_skill(request: Request, skill_id: int):
    """卸载Skill"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="需要登录")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_skills WHERE user_id=? AND skill_id=?", (user["user_id"], skill_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="未安装该Skill")
    conn.commit()
    conn.close()
    return {"success": True, "message": "已成功卸载"}


@router.post("/ai/chat")
async def ai_chat(request: Request):
    """AI对话接口（模拟）"""
    import json
    body = await request.json()
    message = body.get("message", "")
    replies = [
        "这是一个很好的问题！让我为您详细解答。基于广电算力平台的分布式计算能力，我可以实时处理这类复杂查询。",
        "根据您的需求，我推荐使用我们的AI推理节点来处理这个任务。目前全网有多个可用节点，预计响应时间约500ms。",
        "广电算力平台支持多种AI模型，包括LLM推理、图像生成、语音识别等。您可以根据需求选择最合适的模型。",
        "感谢您的提问！我们的AI家教系统可以为您提供个性化的学习辅导，覆盖数学、物理、英语等多个学科。",
        "在电视端使用AI助手非常方便，支持语音输入，您可以直接通过遥控器语音键进行交互。"
    ]
    import hashlib
    idx = int(hashlib.md5(message.encode()).hexdigest(), 16) % len(replies)
    return {"reply": replies[idx]}
