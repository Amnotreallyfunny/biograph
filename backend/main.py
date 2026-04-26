import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from models import init_db, Run, Task
from engine import HardenedRunnerEngine
from events import event_bus
from schemas import DAGPayload, RunResponse, export_api_schema

# Active engine registry for termination control
active_engines: Dict[str, HardenedRunnerEngine] = {}

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

@app.post("/runs/{run_id}/heartbeat")
async def run_heartbeat(run_id: str):
    """CLI/Engine check-in to confirm the process is still alive."""
    session = SessionLocal()
    run = session.query(Run).filter_by(id=run_id).first()
    if run:
        run.last_heartbeat = datetime.utcnow()
        session.commit()
    session.close()
    return {"status": "ok"}

async def monitor_zombie_runs():
    """Background loop to detect and mark stalled/crashed runs."""
    while True:
        await asyncio.sleep(15) # Check every 15 seconds
        session = SessionLocal()
        threshold = datetime.utcnow() - timedelta(seconds=45)
        
        # Find runs that are 'running' but haven't checked in recently
        stalled_runs = session.query(Run).filter(
            Run.status == "running",
            Run.last_heartbeat < threshold
        ).all()
        
        for run in stalled_runs:
            run.status = "stalled"
            run.error_type = "HEARTBEAT_LOST"
            run.suggested_fix = "The execution process may have crashed or was killed externally. Check system logs."
            await event_bus.publish(run.id, "done", {"status": "stalled"})
            
        if stalled_runs:
            session.commit()
        session.close()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_zombie_runs())

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

@app.get("/runs/{run_id}/logs/chunked")
async def get_logs_chunked(run_id: str, offset: int = 0, limit: int = 100):
    """Retrieve logs in slices to support frontend virtualization and prevent OOM."""
    session = SessionLocal()
    run = session.query(Run).filter_by(id=run_id).first()
    if not run:
        session.close()
        raise HTTPException(status_code=404)
    
    # Merge all task logs into a single lines array for this demo
    all_lines = []
    for t in run.tasks:
        text = (t.stdout or "") + (t.stderr or "")
        for line in text.split('\n'):
            if line.strip():
                all_lines.append(f"[{t.node_id}] {line.strip()}")
    
    chunk = all_lines[offset : offset + limit]
    session.close()
    return {
        "lines": chunk,
        "total": len(all_lines),
        "offset": offset,
        "limit": limit
    }

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

@app.post("/runs/{run_id}/terminate")
async def terminate_run(run_id: str):
    """Abort an active run by killing its process group."""
    if run_id in active_engines:
        engine = active_engines[run_id]
        engine.cleanup_processes()
        
        session = SessionLocal()
        run = session.query(Run).filter_by(id=run_id).first()
        if run:
            run.status = "aborted"
            session.commit()
        session.close()
        
        await event_bus.publish(run_id, "done", {"status": "aborted"})
        return {"status": "terminated"}
    raise HTTPException(status_code=404, detail="Active run not found or already finished")

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
    active_engines[run_id] = engine
    
    try:
        await engine.execute_dag(run_id, dag_json)
    finally:
        if run_id in active_engines:
            del active_engines[run_id]
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
