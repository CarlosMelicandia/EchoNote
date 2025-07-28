from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from typing import Optional, List
from flask_login import UserMixin
from sqlalchemy import Text
import json

# create a SQLite database
db = SQLAlchemy()

#define the events model
class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    recurrence = db.Column(db.String(50), nullable=True)  # e.g., 'daily', 'weekly', 'monthly'

    def __repr__(self):
        return (f"<Event(id={self.id}, user_id={self.user_id}, "
                f"title='{self.title}', start_time='{self.start_time}', end_time='{self.end_time}')>")

#define the user model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pw_hash = db.Column(db.String(128), nullable=False)
    tasks = db.relationship('Task', backref='owner', lazy=True)
    theme = db.Column(db.Text, nullable=True)

    def get_theme(self):
        if self.theme:
            return json.loads(self.theme)
        return None

# define the Task model
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.String(100), nullable=True)
    raw_text = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return (f"<Task(id={self.id}, user_id={self.user_id}, "
                f"name='{self.name}', completed={self.completed}, due_date='{self.due_date}')>")

# CRUD operations

def create_task(user_id: int, name: str, due_date: Optional[str] = None, raw_text: Optional[str] = None) -> Task:
    task = Task(user_id=user_id, name=name, due_date=due_date, raw_text=raw_text)
    db.session.add(task)
    db.session.commit()
    return task

def get_all_tasks(user_id: int) -> List[Task]:
    return Task.query.filter_by(user_id=user_id) \
                     .order_by(Task.created_at.desc()) \
                     .all()

def get_task(task_id: int) ->Optional[Task]:
    return Task.query.get(task_id)


def update_task(task_id: int,
    name: Optional[str] = None,
    completed: Optional[bool] = None,
    due_date: Optional[str] = None
) -> Optional[Task]:
    task = Task.query.get(task_id)
    if not task:
        return None

    if name is not None:
        task.name = name
    if completed is not None:
        task.completed = completed
    if due_date is not None:
        task.due_date = due_date

    db.session.commit()
    return task

def delete_task(task_id: int) -> bool:
    task = Task.query.get(task_id)
    if not task:
        return False
    db.session.delete(task)
    db.session.commit()
    return True

def get_user_by_username(username: str) -> Optional[User]:
    return User.query.filter_by(username=username).first()
