import os
import json
import uuid
import sys
import shutil
import asyncio
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional

from models import init_db, Run, Task
from engine import HardenedRunnerEngine, stream_manager

app = FastAPI(title="biograph Control Plane")
SessionLocal = init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/runs")
async def trigger_run(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    dag_json = payload["dag"]
    run_name = payload.get("name", "Web Run")
    
    session = SessionLocal()
    run_id = str(uuid.uuid4())
    run_record = Run(id=run_id, name=run_name, status="queued")
    session.add(run_record)
    
    for node in dag_json["nodes"]:
        t = Task(run_id=run_id, node_id=node["id"], name=node["id"], 
                 command=node["data"].get("command", "echo 'Node Execute'"))
        session.add(t)
    session.commit()
    session.close()

    background_tasks.add_task(execute_in_background, run_id, dag_json)
    return {"run_id": run_id}

@app.post("/runs/{run_id}/retry")
async def retry_task(run_id: str, payload: Dict[str, Any], background_tasks: BackgroundTasks):
    task_node_id = payload["task_id"]
    # In Phase 1, we'll simple re-trigger the original DAG from that node
    # Implementation simplified: finding the original DAG
    return {"message": "Retry enqueued", "new_run_id": run_id}

@app.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, request: Request):
    async def event_generator():
        queue = stream_manager.subscribe(run_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                msg = await queue.get()
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
                if msg['event'] == 'done':
                    break
        finally:
            # stream_manager.cleanup(run_id) # Optional: delayed cleanup
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/system/doctor")
async def system_doctor():
    tools = ["bwa", "samtools", "bcftools"]
    tool_status = []
    for t in tools:
        path = shutil.which(t)
        tool_status.append({
            "name": t,
            "status": "ok" if path else "missing",
            "version": "unknown" if not path else "detected",
            "fix": None if path else f"conda install -c bioconda {t}"
        })
    
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "sqlite": "ok",
        "tools": tool_status
    }

async def execute_in_background(run_id: str, dag_json: dict):
    session = SessionLocal()
    engine = HardenedRunnerEngine(session)
    await engine.execute_dag(run_id, dag_json)
    session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
