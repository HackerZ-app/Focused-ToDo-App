from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    total_completed_tasks = Column(Integer, default=0)
    daily_streak = Column(Integer, default=0)
    last_completed_date = Column(Date, nullable=True)

    tasks = relationship("Task", back_populates="owner")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    completed = Column(Boolean, default=False)
    due_date = Column(DateTime, nullable=True)
    tag = Column(String, nullable=True)
    priority = Column(String, default="Medium")
    status = Column(String, default="Todo")
    completed_at = Column(Date, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="tasks")
