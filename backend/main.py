import os
import json
import uuid
import asyncio
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from models import init_db, Run, Task
from engine import HardenedRunnerEngine
from events import event_bus
from schemas import DAGPayload, RunResponse, export_api_schema

app = FastAPI(title="biograph Reactive Backend")
SessionLocal = init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Export schema on startup
os.makedirs("../frontend/types", exist_ok=True)
export_api_schema("../frontend/types/generated.json")

# --- Endpoints ---

@app.get("/runs")
async def list_runs():
    """List all runs for the dashboard."""
    session = SessionLocal()
    runs = session.query(Run).order_by(Run.start_time.desc()).all()
    res = [{"id": r.id, "name": r.name, "status": r.status, "start_time": r.start_time} for r in runs]
    session.close()
    return res

@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get full details of a specific run."""
    session = SessionLocal()
    run = session.query(Run).filter_by(id=run_id).first()
    if not run:
        session.close()
        raise HTTPException(status_code=404, detail="Run not found")
    
    tasks_data = []
    for t in run.tasks:
        tasks_data.append({
            "node_id": t.node_id,
            "status": t.status,
            "exit_code": t.exit_code,
            "validation": {
                "status": t.validation_status,
                "messages": t.validation_messages
            },
            "duration": t.duration,
            "start_time": t.start_time
        })

    res = {
        "id": run.id,
        "name": run.name,
        "status": run.status,
        "tasks": tasks_data,
        "logs": {t.node_id: (t.stdout or "") + (t.stderr or "") for t in run.tasks},
        "edges": [{"id": f"e{i}", "source": run.tasks[i-1].node_id, "target": run.tasks[i].node_id} for i in range(1, len(run.tasks))]
    }
    session.close()
    return res

@app.patch("/runs/{run_id}")
async def update_run(run_id: str, updates: Dict[str, Any]):
    session = SessionLocal()
    run = session.query(Run).filter_by(id=run_id).first()
    if not run:
        session.close()
        raise HTTPException(status_code=404)
    for key, value in updates.items():
        if hasattr(run, key): setattr(run, key, value)
    session.commit()
    session.close()
    return {"status": "updated"}

@app.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    session = SessionLocal()
    run = session.query(Run).filter_by(id=run_id).first()
    if not run:
        session.close()
        raise HTTPException(status_code=404)
    session.query(Task).filter_by(run_id=run_id).delete()
    session.delete(run)
    session.commit()
    session.close()
    return {"status": "deleted"}

@app.post("/runs", status_code=202)
async def create_run(dag: DAGPayload, background_tasks: BackgroundTasks):
    """Initiate a non-blocking pipeline run."""
    session = SessionLocal()
    run_id = str(uuid.uuid4())
    run_record = Run(id=run_id, name=dag.name, status="queued")
    session.add(run_record)
    
    # Pre-populate tasks in DB
    for node in dag.nodes:
        task = Task(
            run_id=run_id, 
            node_id=node.id, 
            name=node.id,
            command=node.data.get("command", "echo 'Simulated Node'")
        )
        session.add(task)
    
    session.commit()
    session.close()

    # Enqueue background execution
    background_tasks.add_task(run_executor, run_id, dag.dict())
    
    return {"run_id": run_id}

@app.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str, request: Request):
    """SSE Endpoint for real-time state and log streaming."""
    async def event_generator():
        queue = event_bus.subscribe(run_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                # Wait for next event from the bus
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"event: {message['event']}\ndata: {json.dumps(message['data'])}\n\n"
                    
                    if message['event'] == 'done':
                        break
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield ": keep-alive\n\n"
        finally:
            event_bus.unsubscribe(run_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/data/{run_id}/{filename}")
async def serve_data(run_id: str, filename: str):
    """Securely serve biological output files."""
    # Basic path traversal protection
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # In production, we'd lookup the actual path in FileRecord table
    file_path = os.path.join(os.getcwd(), filename) # Simplified for demo
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

# --- Background Worker Logic ---

async def run_executor(run_id: str, dag_json: dict):
    """Background task that runs the engine and publishes to the bus."""
    session = SessionLocal()
    engine = HardenedRunnerEngine(session)
    
    # Execute and emit events
    # The RunnerEngine now calls event_bus.publish internally
    await engine.execute_dag(run_id, dag_json)
    
    session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
