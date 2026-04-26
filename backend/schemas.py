from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

# --- Pydantic API Models ---

class TaskResponse(BaseModel):
    id: str
    node_id: str
    status: str
    validation_status: Optional[str]
    duration: Optional[float]

class RunResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime
    tasks: List[TaskResponse]

class DAGNode(BaseModel):
    id: str
    type: str
    data: Dict[str, Any]

class DAGEdge(BaseModel):
    id: str
    source: str
    target: str

class DAGPayload(BaseModel):
    name: str
    nodes: List[DAGNode]
    edges: List[DAGEdge]

# Utility to export schema for Frontend
def export_api_schema(output_path: str):
    import json
    schema = {
        "Run": RunResponse.schema(),
        "Task": TaskResponse.schema(),
        "DAG": DAGPayload.schema()
    }
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)

# Preserve SQLAlchemy models below...
# (Already defined in models.py, adding Pydantic atop them)
