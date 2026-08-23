import logging
import time

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine, get_db, Base
import models
import schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tasks-api")

app = FastAPI(title="Tasks API", version="0.1.0")


@app.on_event("startup")
def on_startup():
    # Retry table creation briefly in case Postgres isn't ready yet
    # (matters in docker-compose where app can start before the db).
    for attempt in range(1, 6):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables ready.")
            return
        except Exception as exc:
            logger.warning("DB not ready (attempt %s/5): %s", attempt, exc)
            time.sleep(2)
    logger.error("Could not connect to database after retries.")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """
    Liveness + readiness check in one. Returns 200 only if the app
    can actually talk to the database — this is the endpoint
    the load balancer / CloudWatch will poll later.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.error("Health check DB failure: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable")

    return {"status": "ok", "database": db_status}


@app.post("/tasks", response_model=schemas.TaskOut, status_code=201)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = models.Task(title=task.title, done=task.done)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    logger.info("Created task id=%s", db_task.id)
    return db_task


@app.get("/tasks", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(models.Task).order_by(models.Task.id).all()


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="task not found")
    return db_task
