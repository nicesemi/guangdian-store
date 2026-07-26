"""SQLite数据库初始化与种子数据"""

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

# Vercel 使用 /tmp 作为可写目录，本地使用项目目录
_is_vercel = os.environ.get("VERCEL") == "1" or os.path.exists("/tmp") and os.environ.get("HOME", "").startswith("/tmp")
DB_PATH = os.path.join("/tmp" if _is_vercel else os.path.dirname(__file__), "guangdian.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            tv_account TEXT,
            role TEXT DEFAULT 'user',
            balance REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 节点表（含地图坐标、IP、可用算力、模型绑定）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            ip_address TEXT DEFAULT '',
            tops_capacity REAL NOT NULL,
            available_tops REAL DEFAULT 0.0,
            status TEXT DEFAULT 'online',
            load REAL DEFAULT 0.0,
            temperature REAL DEFAULT 40.0,
            uptime INTEGER DEFAULT 0,
            model_id INTEGER,
            latitude REAL DEFAULT 28.2282,
            longitude REAL DEFAULT 112.9388,
            last_heartbeat TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (model_id) REFERENCES models(id)
        )
    """)
    # 迁移：为旧表补列
    for col, col_def in [
        ("ip_address", "TEXT DEFAULT ''"),
        ("available_tops", "REAL DEFAULT 0.0"),
        ("model_id", "INTEGER"),
        ("latitude", "REAL DEFAULT 28.2282"),
        ("longitude", "REAL DEFAULT 112.9388"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE nodes ADD COLUMN {col} {col_def}")
        except:
            pass  # 列已存在

    # 模型表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            type TEXT NOT NULL,
            required_tops REAL NOT NULL,
            status TEXT DEFAULT 'active',
            deployed_nodes INTEGER DEFAULT 0
        )
    """)

    # Skill表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            developer_id INTEGER,
            model_id INTEGER,
            description TEXT,
            price REAL DEFAULT 0.0,
            local_deploy INTEGER DEFAULT 0,
            tops_required REAL DEFAULT 0.0,
            token_cost_per_call REAL DEFAULT 0.0,
            rating REAL DEFAULT 0.0,
            installs INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (developer_id) REFERENCES users(id),
            FOREIGN KEY (model_id) REFERENCES models(id)
        )
    """)
    # 迁移：为旧 skill 表补列
    for col, col_def in [
        ("local_deploy", "INTEGER DEFAULT 0"),
        ("tops_required", "REAL DEFAULT 0.0"),
        ("token_cost_per_call", "REAL DEFAULT 0.0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE skills ADD COLUMN {col} {col_def}")
        except:
            pass

    # 用户Skill关联表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            installed_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (skill_id) REFERENCES skills(id)
        )
    """)

    # 任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            node_id INTEGER,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            tops_used REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (node_id) REFERENCES nodes(id)
        )
    """)

    # 订单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT DEFAULT 'balance',
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (skill_id) REFERENCES skills(id)
        )
    """)

    # 账单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 工单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 课程表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS edu_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            grade TEXT NOT NULL,
            description TEXT,
            video_url TEXT
        )
    """)

    # 题库表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS edu_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            answer TEXT NOT NULL,
            explanation TEXT,
            FOREIGN KEY (course_id) REFERENCES edu_courses(id)
        )
    """)

    conn.commit()

    # 检查是否已有数据
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_data(conn)

    conn.close()


def seed_data(conn):
    cursor = conn.cursor()

    # 种子用户
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    users = [
        ("admin", hash_password("admin123"), "GD-0001-ADMIN", "admin", 10000.0, now),
        ("developer01", hash_password("dev123"), "GD-0002-DEV", "developer", 5000.0, now),
        ("user01", hash_password("user123"), "GD-0003-USER", "user", 500.0, now),
    ]
    cursor.executemany(
        "INSERT INTO users (username, password, tv_account, role, balance, created_at) VALUES (?,?,?,?,?,?)",
        users
    )

    # 种子模型（8个）—— 必须在节点之前，因为节点有外键引用
    models = [
        ("Llama-3-70B", "v3.1", "LLM推理", 70.0, "active", 8),
        ("Qwen-2-72B", "v2.0", "LLM推理", 72.0, "active", 6),
        ("Stable-Diffusion-XL", "v1.0", "图像生成", 40.0, "active", 5),
        ("Whisper-Large-v3", "v3.0", "语音识别", 10.0, "active", 10),
        ("YOLO-v8", "v8.2", "视频分析", 20.0, "active", 12),
        ("Gemma-2-27B", "v2.0", "LLM推理", 27.0, "active", 4),
        ("DeepSeek-R1", "v1.0", "LLM推理", 60.0, "updating", 3),
        ("GPT-SoVITS", "v2.0", "语音合成", 15.0, "active", 7),
    ]
    cursor.executemany(
        "INSERT INTO models (name, version, type, required_tops, status, deployed_nodes) VALUES (?,?,?,?,?,?)",
        models
    )

    # 种子节点：100台长沙一体机，50TOPS/台，含IP/坐标/可用算力/模型绑定
    import random as _r
    _r.seed(42)
    # 长沙市中心散射 ~2km
    base_lat, base_lng = 28.2282, 112.9388
    model_ids = [1,2,3,4,5,6,7,8]
    status_pool = ["online"]*92 + ["maintenance"]*5 + ["offline"]*3
    _r.shuffle(status_pool)
    nodes = []
    for i in range(1, 101):
        ip = f"10.43.{_r.randint(0,3)}.{i}"
        tops = 50.0
        load = round(_r.uniform(3, 30), 1)
        avail = max(0, round(tops - load - _r.uniform(0, 5), 1))
        model_id = _r.choice(model_ids) if _r.random() < 0.8 else None
        lat = round(base_lat + _r.uniform(-0.018, 0.018), 6)
        lng = round(base_lng + _r.uniform(-0.018, 0.018), 6)
        temp = round(_r.uniform(38, 52), 1)
        uptime = _r.randint(24, 720)
        nodes.append((
            f"长沙一体机-{i:03d}", "长沙", ip, tops, avail,
            status_pool[i-1], load, temp, uptime, model_id, lat, lng, now
        ))
    cursor.executemany(
        "INSERT INTO nodes (name, location, ip_address, tops_capacity, available_tops, status, load, temperature, uptime, model_id, latitude, longitude, last_heartbeat) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        nodes
    )

    # 种子Skill（15个，5个分类各3个）
    skills = [
        # 教育类 (model_id, local_deploy, tops_required, token_cost)
        ("AI数学家教", "教育", 1, 1, "一对一数学辅导，覆盖小学到高中全学段", 0.0, 0, 70.0, 0.05, 4.8, 5632, "active"),
        ("英语口语陪练", "教育", 1, 4, "AI英语口语对话练习，实时发音纠正", 9.9, 1, 10.0, 0.0, 4.6, 3210, "active"),
        ("编程启蒙老师", "教育", 1, 6, "面向青少年的Python编程入门课程", 0.0, 1, 27.0, 0.0, 4.7, 1890, "active"),
        # 办公类
        ("智能PPT生成", "办公", 1, 2, "一句话生成精美PPT，支持多种模板", 29.9, 0, 72.0, 0.05, 4.5, 8900, "active"),
        ("AI会议纪要", "办公", 1, 4, "自动录音转文字+智能摘要生成", 19.9, 1, 10.0, 0.0, 4.4, 6540, "active"),
        ("合同智能审查", "办公", 1, 1, "AI驱动的合同条款风险审查", 99.0, 0, 70.0, 0.05, 4.9, 1230, "active"),
        # 创意类
        ("AI艺术画廊", "创意", 1, 3, "文本生成艺术作品，支持多种风格", 15.0, 1, 40.0, 0.0, 4.3, 4500, "active"),
        ("短视频AI剪辑", "创意", 1, 5, "AI自动剪辑短视频，智能配乐", 49.9, 1, 20.0, 0.0, 4.2, 2340, "active"),
        ("AI作曲助手", "创意", 1, 8, "AI辅助作曲，支持多种音乐风格", 39.9, 1, 15.0, 0.0, 4.1, 890, "active"),
        # 生活类
        ("家庭健康顾问", "生活", 1, 1, "AI健康咨询与生活建议", 0.0, 0, 70.0, 0.05, 4.0, 7800, "active"),
        ("智能菜谱推荐", "生活", 1, 2, "根据食材智能推荐菜谱和烹饪方法", 0.0, 0, 72.0, 0.05, 4.5, 4320, "active"),
        ("旅行规划师", "生活", 1, 1, "AI一键生成个性化旅行计划", 6.9, 0, 70.0, 0.05, 4.3, 2100, "active"),
        # 广电特色类
        ("电视AI助手", "广电特色", 1, 1, "电视端AI语音助手，支持节目推荐和智能问答", 0.0, 0, 70.0, 0.05, 4.6, 15600, "active"),
        ("智能节目单", "广电特色", 1, 2, "基于用户兴趣的个性化节目推荐", 0.0, 0, 72.0, 0.05, 4.4, 8900, "active"),
        ("家庭KTV评分", "广电特色", 1, 4, "AI实时评分+演唱指导，居家KTV升级", 19.9, 1, 10.0, 0.0, 4.2, 3450, "active"),
    ]
    cursor.executemany(
        "INSERT INTO skills (name, category, developer_id, model_id, description, price, local_deploy, tops_required, token_cost_per_call, rating, installs, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        skills
    )

    # 种子Skill — 真实部署（deepedu.school & DeepCat）
    try:
        cursor.execute("ALTER TABLE skills ADD COLUMN skill_url TEXT DEFAULT ''")
    except:
        pass
    real_skills = [
        ("deepedu.school", "教育", 1, 1, "AI智能教育平台，一站式学习伴侣：AI家教、课程广场、题库练习、学习报告。真实部署在Vercel云端。", 0.0, 0, 70.0, 0.05, 4.9, 0, "active", "https://deepedu.school"),
        ("DeepCat", "创意", 1, 3, "本地部署AI动画生成工具，基于Stable Diffusion，支持文本转动画、风格迁移。已优化适配50TOPS一体机。", 0.0, 1, 40.0, 0.0, 4.8, 0, "active", ""),
    ]
    cursor.executemany(
        "INSERT INTO skills (name, category, developer_id, model_id, description, price, local_deploy, tops_required, token_cost_per_call, rating, installs, status, skill_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        real_skills
    )

    # 种子课程（3个）
    courses = [
        ("小学数学思维训练", "数学", "小学", "通过AI互动培养数学思维能力", ""),
        ("初中物理实验探究", "物理", "初中", "虚拟物理实验，AI指导探究式学习", ""),
        ("Python编程入门", "编程", "通用", "从零开始学Python，AI辅助编程练习", ""),
    ]
    cursor.executemany(
        "INSERT INTO edu_courses (title, subject, grade, description, video_url) VALUES (?,?,?,?,?)",
        courses
    )

    # 种子习题
    exercises = [
        (1, "小明有12个苹果，给了小红3个，又买了5个，现在一共有多少个苹果？",
         '["A. 9个","B. 14个","C. 17个","D. 20个"]', "B", "12-3+5=14"),
        (1, "一个长方形的长是8厘米，宽是5厘米，周长是多少厘米？",
         '["A. 13厘米","B. 26厘米","C. 40厘米","D. 20厘米"]', "B", "(8+5)×2=26"),
        (2, "下列哪个是力的单位？",
         '["A. 米","B. 千克","C. 牛顿","D. 秒"]', "C", "牛顿是力的国际单位"),
        (2, "光在真空中的传播速度约为多少？",
         '["A. 3×10^6 m/s","B. 3×10^8 m/s","C. 3×10^4 m/s","D. 3×10^10 m/s"]', "B", "光速约为3×10^8 m/s"),
        (3, "Python中用于输出的函数是？",
         '["A. input()","B. print()","C. output()","D. echo()"]', "B", "print()是Python内置的输出函数"),
        (3, "下列哪个是合法的Python变量名？",
         '["A. 1var","B. my-var","C. my_var","D. class"]', "C", "变量名不能以数字开头，不能含连字符，不能用关键字"),
    ]
    cursor.executemany(
        "INSERT INTO edu_exercises (course_id, question, options, answer, explanation) VALUES (?,?,?,?,?)",
        exercises
    )

    # 种子任务
    tasks = [
        (3, 1, "AI推理", "completed", 35.0, now),
        (3, 3, "视频处理", "running", 18.5, now),
        (3, 5, "AI推理", "completed", 12.0, now),
        (2, 2, "图像生成", "running", 28.0, now),
        (3, 1, "语音识别", "pending", 5.0, now),
    ]
    cursor.executemany(
        "INSERT INTO tasks (user_id, node_id, type, status, tops_used, created_at) VALUES (?,?,?,?,?,?)",
        tasks
    )

    # 种子订单
    orders = [
        (3, 2, 9.9, "balance", "completed", now),
        (3, 5, 99.0, "wechat", "completed", now),
        (2, 8, 49.9, "balance", "completed", now),
    ]
    cursor.executemany(
        "INSERT INTO orders (user_id, skill_id, amount, payment_method, status, created_at) VALUES (?,?,?,?,?,?)",
        orders
    )

    # 种子账单
    bills = [
        (3, 500.0, "充值", now),
        (3, -9.9, "消费", now),
        (3, -99.0, "消费", now),
        (2, 2000.0, "收益", now),
    ]
    cursor.executemany(
        "INSERT INTO bills (user_id, amount, type, created_at) VALUES (?,?,?,?)",
        bills
    )

    # 种子工单
    tickets = [
        (3, "节点连接超时", "深圳节点近期频繁出现连接超时问题，影响推理任务", "open", now),
        (2, "模型部署失败", "Stable-Diffusion模型在南京节点部署时出现OOM错误", "processing", now),
    ]
    cursor.executemany(
        "INSERT INTO tickets (user_id, title, description, status, created_at) VALUES (?,?,?,?,?)",
        tickets
    )

    # 种子用户Skill安装记录
    user_skills = [
        (3, 1, now),
        (3, 4, now),
        (3, 13, now),
        (3, 14, now),
        (2, 7, now),
        (2, 8, now),
    ]
    cursor.executemany(
        "INSERT INTO user_skills (user_id, skill_id, installed_at) VALUES (?,?,?)",
        user_skills
    )

    conn.commit()
    print("Database initialized with seed data.")


if __name__ == "__main__":
    init_db()
    print("Database setup complete.")
