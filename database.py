from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from typing import Optional, List


# create a SQLite database
db = SQLAlchemy()


# define the Task model
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<Task(id={self.id}, name='{self.name}', completed={self.completed}, due_date='{self.due_date}')>"


# CRUD operations


def create_task(name: str, due_date=None) -> Task:
    task = Task(name=name, due_date=due_date)
    db.session.add(task)
    db.session.commit()
    return task



def get_all_tasks() -> List[Task]:
    return Task.query.all()

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
