from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime


# create a SQLite database
DATABASE_URL = "sqlite:///./echo_note.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# define the Task model
class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    def __repr__(self):
        return f"<Task(id={self.id}, name='{self.name}', completed={self.completed})>"

# initialize the database
def init_db():
    Base.metadata.create_all(bind=engine)

# CRUD operations
def create_task(name):
    db = SessionLocal()
    task = Task(name=name)
    db.add(task)
    db.commit()
    db.close()

def get_all_tasks():
    db = SessionLocal()
    tasks = db.query(Task).all()
    db.close()
    return tasks

def update_task(task_id, name=None, completed=None):
    db = SessionLocal()
    task = db.query(Task).get(task_id)
    if not task:
        db.close()
        return None  # or raise an error
    if name is not None:
        task.name = name
    if completed is not None:
        task.completed = completed
    db.commit()
    db.refresh(task)
    db.close()
    return task

def delete_task(task_id):
    db = SessionLocal()
    task = db.query(Task).get(task_id)
    if not task:
        db.close()
        return False
    db.delete(task)
    db.commit()
    db.close()
    return True

