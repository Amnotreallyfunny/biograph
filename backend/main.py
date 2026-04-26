import os
import json
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import the hardened core components
from models import init_db, Run, Task
from engine import HardenedRunnerEngine

app = FastAPI(title="biograph Professional API")

# Initialize DB
SessionLocal = init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/runs")
async def list_runs():
    session = SessionLocal()
    runs = session.query(Run).all()
    res = [{"id": r.id, "name": r.name, "status": r.status, "start_time": r.start_time} for r in runs]
    session.close()
    return res

@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    session = SessionLocal()
    run = session.query(Run).filter_by(id=run_id).first()
    if not run:
        session.close()
        raise HTTPException(status_code=404)
    
    # Map task statuses for the UI
    node_states = {t.node_id: t.status for t in run.tasks}
    logs = {t.node_id: t.stdout + t.stderr for t in run.tasks}
    
    res = {
        "status": run.status,
        "node_states": node_states,
        "logs": logs
    }
    session.close()
    return res

@app.post("/dag")
async def save_dag(dag_json: Dict[str, Any]):
    # In a full system, we'd save this to a 'Pipelines' table
    # For now, we'll keep the logic simple for the UI integration
    dag_id = str(uuid.uuid4())
    os.makedirs("storage/dags", exist_ok=True)
    with open(f"storage/dags/{dag_id}.json", "w") as f:
        json.dump(dag_json, f)
    return {"id": dag_id}

@app.post("/execute/{dag_id}")
async def execute_dag(dag_id: str):
    # Load DAG
    dag_path = f"storage/dags/{dag_id}.json"
    if not os.path.exists(dag_path):
        raise HTTPException(status_code=404)
    
    with open(dag_path, "r") as f:
        dag_json = json.load(f)

    session = SessionLocal()
    engine = HardenedRunnerEngine(session)
    
    # Create the DB Run record
    run_record = Run(id=str(uuid.uuid4()), name=dag_json.get("name", "Web Triggered Run"))
    session.add(run_record)
    
    # Map UI nodes to DB tasks
    for node in dag_json["nodes"]:
        t = Task(run_id=run_record.id, node_id=node["id"], name=node["id"], 
                 command=node["data"].get("command", "echo 'Processed Node'"))
        session.add(t)
    session.commit()

    # Trigger async execution (in background)
    import asyncio
    asyncio.create_task(async_execute(engine, run_record.id, dag_json))
    
    run_id = run_record.id
    session.close()
    return {"run_id": run_id}

async def async_execute(engine, run_id, dag_json):
    # This matches the core CLI execution logic
    engine.execute_dag(run_id, dag_json)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
