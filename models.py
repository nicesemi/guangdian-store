"""Pydantic数据模型"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str
    tv_account: Optional[str] = None
    role: str = "user"  # admin, developer, user
    balance: float = 0.0


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    id: int
    created_at: str

    class Config:
        from_attributes = True


class Node(BaseModel):
    id: int
    name: str
    location: str
    tops_capacity: float
    status: str  # online, offline, maintenance
    load: float
    temperature: float
    uptime: int  # 秒
    last_heartbeat: str

    class Config:
        from_attributes = True


class ModelInfo(BaseModel):
    id: int
    name: str
    version: str
    type: str
    required_tops: float
    status: str  # active, inactive, updating
    deployed_nodes: int = 0

    class Config:
        from_attributes = True


class Skill(BaseModel):
    id: int
    name: str
    category: str
    developer_id: int
    model_id: Optional[int] = None
    description: str
    price: float
    rating: float
    installs: int
    status: str  # pending, approved, rejected, active

    class Config:
        from_attributes = True


class SkillCreate(BaseModel):
    name: str
    category: str
    description: str
    price: float = 0.0
    model_id: Optional[int] = None


class UserSkill(BaseModel):
    id: int
    user_id: int
    skill_id: int
    installed_at: str

    class Config:
        from_attributes = True


class Task(BaseModel):
    id: int
    user_id: int
    node_id: Optional[int] = None
    type: str
    status: str
    tops_used: float
    created_at: str

    class Config:
        from_attributes = True


class Order(BaseModel):
    id: int
    user_id: int
    skill_id: int
    amount: float
    payment_method: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class Bill(BaseModel):
    id: int
    user_id: int
    amount: float
    type: str
    created_at: str

    class Config:
        from_attributes = True


class Ticket(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    status: str  # open, processing, resolved, closed
    created_at: str

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    title: str
    description: str


class EduCourse(BaseModel):
    id: int
    title: str
    subject: str
    grade: str
    description: str
    video_url: Optional[str] = None

    class Config:
        from_attributes = True


class EduExercise(BaseModel):
    id: int
    course_id: int
    question: str
    options: str  # JSON string
    answer: str
    explanation: str

    class Config:
        from_attributes = True


class PortalStats(BaseModel):
    total_tops: float
    online_nodes: int
    active_tasks: int
    total_nodes: int
