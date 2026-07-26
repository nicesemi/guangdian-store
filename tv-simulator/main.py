#!/usr/bin/env python3
"""广电算力TV - 电视端模拟应用
在 macOS 上以全屏 Web UI 模拟电视大屏体验。
"""
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
import flask
import requests
import psutil

app = flask.Flask(__name__)
app.secret_key = "guangdian-tv-2026"

PLATFORM_API = "http://127.0.0.1:8080"
INSTALLED_STORE = os.path.join(os.path.dirname(__file__), "installed_skills.json")

# Remote control command queue
import threading
from collections import deque
remote_queue = deque()
remote_lock = threading.Lock()


def load_installed():
    """加载本地已安装Skill记录"""
    if os.path.exists(INSTALLED_STORE):
        with open(INSTALLED_STORE) as f:
            return json.load(f)
    return []


def save_installed(data):
    """保存本地已安装Skill记录"""
    with open(INSTALLED_STORE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or r.stderr.strip()
    except:
        return ""


# ─── 系统信息 ─────────────────────────────────────────────────────────
def get_cpu_info():
    return {
        "brand": run_cmd("sysctl -n machdep.cpu.brand_string"),
        "cores": os.cpu_count(),
        "usage": psutil.cpu_percent(interval=0.3),
    }


def get_gpu_info():
    """获取 GPU 信息"""
    gpus = []
    # system_profiler 获取 GPU
    out = run_cmd("system_profiler SPDisplaysDataType 2>/dev/null")
    if out:
        current = {}
        for line in out.split("\n"):
            line = line.strip()
            if "Chipset Model:" in line:
                current["model"] = line.split("Chipset Model:", 1)[1].strip()
            elif "VRAM" in line:
                current["vram"] = line.split(":", 1)[1].strip()
            elif "Metal" in line:
                current["metal"] = line.split(":", 1)[1].strip()
            elif "Resolution:" in line and current:
                gpus.append(current)
                current = {}
        if current:
            gpus.append(current)
    # 补一个 Apple Silicon GPU
    if not gpus:
        chip = run_cmd("sysctl -n machdep.cpu.brand_string")
        if "Apple" in chip or "M" in chip:
            gpus.append({"model": "Apple Silicon GPU (Integrated)", "vram": "Shared"})
    if not gpus:
        gpus.append({"model": "未知GPU", "vram": "未知"})
    return gpus


def get_memory_info():
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024**3), 1),
        "used_gb": round(mem.used / (1024**3), 1),
        "available_gb": round(mem.available / (1024**3), 1),
        "percent": mem.percent,
    }


def detect_local_models():
    """检测本机已安装的大模型 (Ollama / LM Studio / HuggingFace / 本地目录)"""
    models = []
    seen = set()

    # 1. Ollama - 尝试多个路径
    for ollama_bin in ["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "ollama"]:
        ollama_models = run_cmd(f"{ollama_bin} list 2>/dev/null")
        if ollama_models and "NAME" in ollama_models:
            for line in ollama_models.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    size = parts[-1] if any(x in parts[-1] for x in ("GB", "MB", "TB")) else ""
                    if not size:
                        size = " ".join(parts[2:4]) if len(parts) >= 3 else "未知"
                    models.append({"name": name, "source": "Ollama", "size": size})
                    seen.add(name)
            break

    # 2. LM Studio
    lm_dir = os.path.expanduser("~/.cache/lm-studio/models")
    if os.path.isdir(lm_dir):
        for root, dirs, files in os.walk(lm_dir):
            for f in files:
                if f.endswith(".gguf"):
                    size_bytes = os.path.getsize(os.path.join(root, f))
                    size_gb = round(size_bytes / (1024**3), 1)
                    models.append({"name": f.replace(".gguf", ""), "source": "LM Studio", "size": f"{size_gb} GB"})
            break

    # 3. HuggingFace cache (~/.cache/huggingface/hub/)
    hf_hub = os.path.expanduser("~/.cache/huggingface/hub")
    if os.path.isdir(hf_hub):
        for entry in os.listdir(hf_hub):
            hub_path = os.path.join(hf_hub, entry)
            if not os.path.isdir(hub_path):
                continue
            # 查找 snapshots 目录下的 safetensors
            snaps = os.path.join(hub_path, "snapshots")
            if os.path.isdir(snaps):
                for snap in os.listdir(snaps):
                    snap_path = os.path.join(snaps, snap)
                    if os.path.isdir(snap_path):
                        for f in os.listdir(snap_path):
                            if f.endswith(".safetensors") and "tokenizer" not in f.lower():
                                name = entry.replace("models--", "").replace("--", "/")
                                size_bytes = os.path.getsize(os.path.join(snap_path, f))
                                size_gb = round(size_bytes / (1024**3), 1)
                                if name not in seen:
                                    models.append({"name": name, "source": "HuggingFace", "size": f"{size_gb} GB"})
                                    seen.add(name)

    # 4. 扫描 safetensors 目录（含项目 checkpoints）
    scan_dirs = [
        os.path.expanduser("~/models"),
        os.path.expanduser("~/llama"),
        os.path.expanduser("~/ACE-Step-1.5/checkpoints"),
    ]
    for scan_root in scan_dirs:
        if not os.path.isdir(scan_root):
            continue
        for root, dirs, files in os.walk(scan_root):
            depth = root.replace(scan_root, "").count(os.sep)
            if depth > 3:
                continue
            for f in files:
                if f.endswith((".safetensors", ".gguf")) and "tokenizer" not in f.lower() and "vae" not in root.lower():
                    dir_name = os.path.basename(root)
                    if dir_name.startswith("."):
                        continue
                    size_bytes = os.path.getsize(os.path.join(root, f))
                    size_gb = round(size_bytes / (1024**3), 1)
                    if dir_name not in seen:
                        models.append({"name": dir_name, "source": "本地Checkpoint", "size": f"{size_gb} GB"})
                        seen.add(dir_name)

    return models


def get_compute_resources():
    """综合本机算力资源评估"""
    cpu = get_cpu_info()
    gpu = get_gpu_info()
    mem = get_memory_info()
    models = detect_local_models()

    # 估算本地 TOPS (粗略)
    cpu_tops = round(cpu["cores"] * 0.05, 1)
    gpu_tops = 0
    for g in gpu:
        model = g.get("model", "")
        if "M3" in model or "M4" in model:
            gpu_tops += 20
        elif "M2" in model:
            gpu_tops += 15
        elif "M1" in model:
            gpu_tops += 10
        elif "Apple" in model:
            gpu_tops += 8
        else:
            gpu_tops += 3
    local_tops = round(cpu_tops + gpu_tops, 1)

    return {
        "cpu": cpu,
        "gpu": gpu,
        "memory": mem,
        "models": models,
        "local_tops": local_tops,
        "os": f"{platform.system()} {platform.release()}",
    }


# ─── 天气模拟 ─────────────────────────────────────────────────────────
def get_weather():
    """模拟获取长沙天气（可用 OpenWeatherMap API 替换）"""
    # 尝试真实 API
    api_key = os.environ.get("OWM_API_KEY", "")
    if api_key:
        try:
            import urllib.request
            url = f"https://api.openweathermap.org/data/2.5/weather?lat=28.23&lon=112.94&appid={api_key}&lang=zh_cn&units=metric"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                d = r.json()
                return {
                    "city": "长沙",
                    "temp": round(d["main"]["temp"]),
                    "desc": d["weather"][0]["description"],
                    "humidity": d["main"]["humidity"],
                    "wind": d["wind"]["speed"],
                    "aqi": "良",
                }
        except:
            pass
    # 兜底模拟
    hour = datetime.now().hour
    if 6 <= hour < 12:
        desc, temp = "晴间多云", 34
    elif 12 <= hour < 18:
        desc, temp = "晴", 37
    elif 18 <= hour < 21:
        desc, temp = "多云", 31
    else:
        desc, temp = "晴", 28
    return {"city": "长沙", "temp": temp, "desc": desc, "humidity": 65, "wind": 3.2, "aqi": "良"}


# ─── LLM 语音意图识别 ────────────────────────────────────────────────
SILICONFLOW_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_MODEL = os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")

VOICE_SYSTEM_PROMPT = """你是一个智能电视语音助手，解析用户的语音指令。
返回严格的JSON格式，不要有任何额外内容。

操作类型：
- 导航: {"action":"navigate","direction":"up|down|left|right"}
- 确认: {"action":"navigate","direction":"ok"}
- 首页: {"action":"navigate","direction":"home"}
- 返回: {"action":"navigate","direction":"back"}
- 打开应用: {"action":"open_app","app":"deepedu|deepcat"}
- 打开面板: {"action":"open_modal","modal":"mall|system|models|weather|status|billing"}
- 卸载应用: {"action":"uninstall","app":"deepedu|deepcat"}
- 无法识别: {"action":"unknown","message":"简短中文提示"}

关键映射：
- deepedu / deepschool / school / 教育 / 学校 → app=deepedu
- deepcat / 动画 / 猫 → app=deepcat
- 商城 / 市场 / 商店 / 应用 → modal=mall
- 系统 / 资源 / 本机 / 硬件 → modal=system
- 模型 / 安装 / 部署 → modal=models
- 天气 / 气温 → modal=weather
- 状态 / 连接 / 网络 → modal=status
- 计费 / 仪表 / token / 费用 → modal=billing"""

def call_llm_intent(text):
    if not SILICONFLOW_KEY:
        print("[voice] 无 SiliconFlow Key，使用关键词兜底")
        return fallback_intent(text)
    try:
        resp = requests.post(
            "https://api.siliconflow.cn/v1/chat/completions",
            headers={"Authorization": f"Bearer {SILICONFLOW_KEY}"},
            json={
                "model": SILICONFLOW_MODEL,
                "messages": [
                    {"role": "system", "content": VOICE_SYSTEM_PROMPT},
                    {"role": "user", "content": f"解析语音指令：{text}"}
                ],
                "temperature": 0.1,
                "max_tokens": 200,
                "response_format": {"type": "json_object"}
            },
            timeout=5
        )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"[voice] LLM 调用失败: {e}")
        return fallback_intent(text)

def fallback_intent(text):
    """LLM 不可用时的关键词兜底"""
    t = text.lower().replace(" ", "")
    if any(k in t for k in ["卸载", "删除", "去掉"]):
        if any(k in t for k in ["deepedu", "教育", "学校", "deepschool", "school"]):
            return {"action": "uninstall", "app": "deepedu"}
        if any(k in t for k in ["deepcat", "动画", "猫"]):
            return {"action": "uninstall", "app": "deepcat"}
    if any(k in t for k in ["deepedu", "deepschool", "school", "教育", "学校"]):
        return {"action": "open_app", "app": "deepedu"}
    if any(k in t for k in ["deepcat", "动画", "猫"]):
        return {"action": "open_app", "app": "deepcat"}
    if any(k in t for k in ["商城", "市场", "商店"]):
        return {"action": "open_modal", "modal": "mall"}
    if any(k in t for k in ["系统", "资源", "本机", "硬件"]):
        return {"action": "open_modal", "modal": "system"}
    if any(k in t for k in ["模型"]):
        return {"action": "open_modal", "modal": "models"}
    if any(k in t for k in ["天气", "气温"]):
        return {"action": "open_modal", "modal": "weather"}
    if any(k in t for k in ["状态", "连接", "网络"]):
        return {"action": "open_modal", "modal": "status"}
    if any(k in t for k in ["计费", "仪表", "token", "费用"]):
        return {"action": "open_modal", "modal": "billing"}
    if any(k in t for k in ["首页", "主屏", "主页"]):
        return {"action": "navigate", "direction": "home"}
    if any(k in t for k in ["返回", "后退", "退出"]):
        return {"action": "navigate", "direction": "back"}
    if any(k in t for k in ["上", "up"]):
        return {"action": "navigate", "direction": "up"}
    if any(k in t for k in ["下", "down"]):
        return {"action": "navigate", "direction": "down"}
    if any(k in t for k in ["左", "left"]):
        return {"action": "navigate", "direction": "left"}
    if any(k in t for k in ["右", "right"]):
        return {"action": "navigate", "direction": "right"}
    if any(k in t for k in ["确认", "确定", "ok", "打开"]):
        return {"action": "navigate", "direction": "ok"}
    return {"action": "unknown", "message": f"未识别: {text}"}


# ─── API 路由 ─────────────────────────────────────────────────────────
@app.route("/api/voice/intent", methods=["POST"])
def api_voice_intent():
    data = flask.request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return flask.jsonify({"error": "empty text"}), 400
    intent = call_llm_intent(text)
    return flask.jsonify(intent)


@app.route("/")
def home():
    return flask.render_template("tv.html")

@app.route("/remote")
def remote():
    return flask.render_template("remote.html")

@app.route("/api/tv/remote-command", methods=["GET", "POST"])
def api_remote_command():
    if flask.request.method == "POST":
        data = flask.request.get_json() or {}
        cmd = data.get("command", "")
        with remote_lock:
            remote_queue.append(cmd)
        return flask.jsonify({"success": True, "command": cmd})
    else:
        # Long polling for TV to receive commands
        timeout = 30
        start = time.time()
        while time.time() - start < timeout:
            with remote_lock:
                if remote_queue:
                    cmd = remote_queue.popleft()
                    return flask.jsonify({"command": cmd})
            time.sleep(0.2)
        return flask.jsonify({"command": None})


@app.route("/api/system")
def api_system():
    return flask.jsonify(get_compute_resources())


@app.route("/api/weather")
def api_weather():
    return flask.jsonify(get_weather())


@app.route("/api/time")
def api_time():
    now = datetime.now()
    return flask.jsonify({
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y年%m月%d日"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "timestamp": now.isoformat(),
    })


@app.route("/api/platform/skills")
def api_platform_skills():
    """代理到主平台 API"""
    try:
        r = requests.get(f"{PLATFORM_API}/api/skills", timeout=5)
        return flask.jsonify(r.json())
    except:
        return flask.jsonify({"error": "平台未启动"})


@app.route("/api/platform/nodes")
def api_platform_nodes():
    try:
        r = requests.get(f"{PLATFORM_API}/api/nodes", timeout=5)
        return flask.jsonify(r.json())
    except:
        return flask.jsonify({"error": "平台未启动"})


@app.route("/api/platform/stats")
def api_platform_stats():
    try:
        r = requests.get(f"{PLATFORM_API}/api/stats", timeout=5)
        return flask.jsonify(r.json())
    except:
        return flask.jsonify({"error": "平台未启动"})


@app.route("/api/tv/installed")
def api_tv_installed():
    """返回本地已安装的Skill列表 + 从平台同步"""
    local = load_installed()
    # Try to sync from platform
    platform_skills = []
    try:
        r = requests.get(f"{PLATFORM_API}/api/user/installed-skills", timeout=5)
        if r.status_code == 200:
            platform_skills = r.json().get("installed", [])
    except:
        pass

    # Merge: platform skills that aren't already local get added
    local_names = {s["name"] for s in local}
    new_added = []
    for ps in platform_skills:
        if ps["name"] not in local_names:
            ps["calls_today"] = 0
            local.append(ps)
            new_added.append(ps["name"])

    if new_added:
        save_installed(local)

    return flask.jsonify({"installed": local, "count": len(local)})


@app.route("/api/tv/install", methods=["POST"])
def api_tv_install():
    """从平台安装Skill到TV本地"""
    data = flask.request.get_json()
    skill_id = data.get("skill_id")
    if not skill_id:
        return flask.jsonify({"error": "缺少skill_id"}), 400

    # Fetch skill detail from platform
    try:
        r = requests.get(f"{PLATFORM_API}/api/skills", timeout=5)
        if r.status_code == 200:
            all_skills = r.json()
            skill = next((s for s in all_skills if s["id"] == skill_id), None)
            if not skill:
                return flask.jsonify({"error": "Skill不存在"}), 404
        else:
            return flask.jsonify({"error": "平台未响应"}), 503
    except:
        return flask.jsonify({"error": "无法连接平台"}), 503

    # Save locally
    local = load_installed()
    local_names = {s["name"] for s in local}
    if skill["name"] in local_names:
        return flask.jsonify({"success": True, "message": f"已安装 {skill['name']}", "action": "existing"})

    skill["calls_today"] = 0
    local.append(skill)
    save_installed(local)

    # If this is a model-type skill (DeepCat), trigger local model discovery
    if skill.get("local_deploy") and "DeepCat" in skill["name"]:
        detect_local_models()

    return flask.jsonify({"success": True, "message": f"已安装 {skill['name']}", "action": "installed", "skill": skill})


@app.route("/api/tv/uninstall", methods=["POST"])
def api_tv_uninstall():
    """从TV本地卸载Skill"""
    data = flask.request.get_json()
    skill_name = data.get("skill_name")
    if not skill_name:
        return flask.jsonify({"error": "缺少skill_name"}), 400

    local = load_installed()
    new_local = [s for s in local if s["name"] != skill_name]
    if len(new_local) == len(local):
        return flask.jsonify({"error": "未找到该Skill"}), 404

    save_installed(new_local)
    return flask.jsonify({"success": True, "message": f"已卸载 {skill_name}"})


@app.route("/api/tv/record-call", methods=["POST"])
def api_tv_record_call():
    """记录一次Skill调用，用于真实计费"""
    data = flask.request.get_json()
    skill_name = data.get("skill_name", "")
    if not skill_name:
        return flask.jsonify({"error": "缺少skill_name"}), 400

    local = load_installed()
    for s in local:
        if s["name"] == skill_name:
            s["calls_today"] = s.get("calls_today", 0) + 1
            save_installed(local)
            return flask.jsonify({"success": True, "skill": skill_name, "calls_today": s["calls_today"]})
    return flask.jsonify({"error": "未找到该Skill"}), 404


@app.route("/api/billing/summary")
def api_billing_summary():
    """计费汇总：本地算力 vs 分布式算力（基于实际安装的Skill）"""
    system = get_compute_resources()
    local_tops = system["local_tops"]
    local_installed = load_installed()

    skill_billing = []
    for s in local_installed:
        is_local = s.get("local_deploy", False)
        token_per = s.get("token_cost_per_call", 0)
        calls = s.get("calls_today", 0)
        tokens_used = round(calls * token_per, 2)
        skill_billing.append({
            "name": s["name"],
            "deploy": "本地" if is_local else "分布式",
            "tops": s.get("tops_required", 0),
            "token_per_call": token_per,
            "calls_today": calls,
            "tokens_used": tokens_used,
        })

    total_tokens = sum(s["tokens_used"] for s in skill_billing)
    local_tokens = sum(s["tokens_used"] for s in skill_billing if s["deploy"] == "本地")
    dist_tokens = sum(s["tokens_used"] for s in skill_billing if s["deploy"] == "分布式")
    return flask.jsonify({
        "local_tops": local_tops,
        "skills": skill_billing,
        "total_tokens": total_tokens,
        "local_tokens": local_tokens,
        "distributed_tokens": dist_tokens,
        "cpt_price": 0.01,
        "total_cost_yuan": round(total_tokens * 0.01, 2),
    })


# ─── 启动入口 ─────────────────────────────────────────────────────────
def open_browser():
    """用全屏模式打开 Chrome"""
    import webbrowser
    url = "http://127.0.0.1:5151"
    time.sleep(1)
    # 尝试用 Chrome 全屏模式
    try:
        subprocess.Popen([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            f"--app={url}",
            "--start-fullscreen",
            "--kiosk",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        try:
            subprocess.Popen(["open", "-a", "Safari", url])
        except:
            webbrowser.open(url)


if __name__ == "__main__":
    import threading
    threading.Thread(target=open_browser, daemon=True).start()
    print("\n  广电算力TV 启动中...")
    print("  http://127.0.0.1:5151\n")
    app.run(host="0.0.0.0", port=5151, debug=False, threaded=True)
