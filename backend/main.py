import os
import json
import uuid
import time
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="biograph API")

# Storage paths
BASE_DIR = Path(os.path.expanduser("~/biograph/backend/storage"))
UPLOAD_DIR = BASE_DIR / "uploads"
DAG_DIR = BASE_DIR / "dags"
RUN_DIR = BASE_DIR / "runs"

for d in [UPLOAD_DIR, DAG_DIR, RUN_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---

class Node(BaseModel):
    id: str
    type: str
    data: Dict[str, Any]
    position: Dict[str, float]

class Edge(BaseModel):
    id: str
    source: str
    target: str

class DAG(BaseModel):
    id: Optional[str] = None
    name: str
    nodes: List[Node]
    edges: List[Edge]

class RunStatus(BaseModel):
    run_id: str
    status: str
    node_states: Dict[str, str] # node_id -> status
    logs: Dict[str, str]

# --- Model Registry / Plugin System ---

class ModelPlugin:
    def __init__(self, name: str, input_type: str, output_type: str):
        self.name = name
        self.input_type = input_type
        self.output_type = output_type

    async def run(self, input_data: Any) -> Any:
        # Mocking inference
        await asyncio.sleep(2)
        return f"Result from {self.name} using {input_data}"

class SeqEmbeddingModel(ModelPlugin):
    async def run(self, sequence: str):
        await asyncio.sleep(1.5)
        return [0.1, 0.5, -0.3] # Mock vector

class ModelRegistry:
    def __init__(self):
        self.models = {
            "seq-embed": SeqEmbeddingModel("Sequence Embedding", "DNA", "Vector"),
            "variant-predictor": ModelPlugin("Variant Effect Predictor", "VCF", "JSON"),
            "protein-struct": ModelPlugin("Protein Structure Stub", "PDB", "3D-Mesh")
        }
    
    def get_model(self, model_id: str):
        return self.models.get(model_id)

model_registry = ModelRegistry()

# --- DAG Engine ---

class DAGEngine:
    def __init__(self):
        self.active_runs = {}

    async def execute_node(self, node: Node, inputs: Dict[str, Any], run_id: str):
        self.active_runs[run_id]["node_states"][node.id] = "running"
        self.active_runs[run_id]["logs"][node.id] = f"Starting {node.type} execution...\n"
        
        try:
            if node.type == "dataNode":
                res = f"Loaded file: {node.data.get('fileName')}"
            elif node.type == "processNode":
                await asyncio.sleep(2) # Simulate tool execution
                res = f"Processed with {node.data.get('tool')}"
            elif node.type == "modelNode":
                model = model_registry.get_model(node.data.get('modelId'))
                if model:
                    res = await model.run(inputs)
                else:
                    res = "Model not found"
            else:
                res = "Success"
            
            self.active_runs[run_id]["node_states"][node.id] = "success"
            self.active_runs[run_id]["logs"][node.id] += f"Output: {res}\nNode Complete."
            return res
        except Exception as e:
            self.active_runs[run_id]["node_states"][node.id] = "failed"
            self.active_runs[run_id]["logs"][node.id] += f"ERROR: {str(e)}"
            raise e

    async def run_dag(self, dag: DAG, run_id: str):
        self.active_runs[run_id] = {
            "status": "running",
            "node_states": {n.id: "pending" for n in dag.nodes},
            "logs": {n.id: "" for n in dag.nodes}
        }

        # Simple topological execution (demo level)
        # In a real system, we'd use a dependency resolver
        for node in dag.nodes:
            await self.execute_node(node, {}, run_id)
        
        self.active_runs[run_id]["status"] = "success"
        
        # Persist run
        with open(RUN_DIR / f"{run_id}.json", "w") as f:
            json.dump(self.active_runs[run_id], f)

dag_engine = DAGEngine()

# --- Endpoints ---

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename, "size": file_path.stat().st_size}

@app.get("/files")
async def list_files():
    return [{"name": f.name, "size": f.stat().st_size} for f in UPLOAD_DIR.iterdir()]

@app.post("/dag")
async def save_dag(dag: DAG):
    dag_id = dag.id or str(uuid.uuid4())
    dag.id = dag_id
    with open(DAG_DIR / f"{dag_id}.json", "w") as f:
        f.write(dag.json())
    return {"id": dag_id}

@app.get("/dag/{id}")
async def get_dag(id: str):
    path = DAG_DIR / f"{id}.json"
    if not path.exists():
        raise HTTPException(status_code=404)
    return json.loads(path.read_text())

@app.post("/execute/{dag_id}")
async def execute_dag(dag_id: str):
    path = DAG_DIR / f"{dag_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404)
    dag = DAG.parse_raw(path.read_text())
    run_id = str(uuid.uuid4())
    asyncio.create_task(dag_engine.run_dag(dag, run_id))
    return {"run_id": run_id}

@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    if run_id in dag_engine.active_runs:
        return dag_engine.active_runs[run_id]
    
    path = RUN_DIR / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404)
    return json.loads(path.read_text())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
