# biograph: Visual Bioinformatics & AI Workflow Platform

**biograph** is a production-grade, execution-driven platform designed for building, monitoring, and scaling complex bioinformatics pipelines. It combines an intuitive **Visual DAG Builder** with a **Hardened Execution Engine** and a **Scientific Data Layer** to ensure research is fast, reproducible, and operationally robust.

---

## 🚀 Key Features

### 🛠️ Visual Workflow Builder
- **Airflow-style UI:** Drag-and-drop nodes to design complex genomic workflows.
- **Specialized Bio-Nodes:** Pre-built modules for data ingestion (FASTQ/BAM/VCF), alignment, and AI inference.
- **Real-time Monitoring:** Watch your pipeline execute with live visual status updates (Success, Running, Suspicious, Failed).

### ⚡ Hardened Execution Engine (`bioctl`)
- **Process Supervision:** Full group supervision to prevent orphan/zombie bioinformatics processes.
- **Step-Level Caching:** Automatically skips redundant computations by hashing inputs, parameters, and tool versions.
- **Deterministic Replay:** Snapshot-based reproducibility—replay any historical run exactly as it happened.

### 🏛️ Scientific Data & Persistence
- **Relational Integrity:** Backed by SQLAlchemy with a biologically-aware schema (Projects, Samples, Reference Genomes).
- **Data Provenance:** Every file is tracked via unique SHA-256 hashes and linked to its producing task.
- **Automated QC:** Middleware validation for FASTQ and BAM files, detecting low read counts or malformed headers.

---

## 🏗️ Architecture

- **Frontend:** React + React Flow + Tailwind CSS
- **Backend:** FastAPI (Python)
- **Database:** SQLAlchemy (SQLite by default, PostgreSQL supported)
- **Control Layer:** `bioctl.py` CLI for terminal-based execution and management.

---

## 🛠️ Getting Started

### 1. Requirements
- Python 3.9+
- Node.js & npm
- (Optional) Conda for bioinformatics tool management

### 2. Backend & CLI Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate

# Install production dependencies
pip install fastapi uvicorn sqlalchemy psutil python-multipart pydantic

# Run the API server
python3 main.py
```
*Backend runs on `http://localhost:8000`*

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
*Frontend runs on `http://localhost:3001`*

### 4. Running via CLI
```bash
# Execute a pipeline configuration
python3 bioctl.py run path/to/dag.json

# Check environment health
python3 bioctl.py doctor
```

---

## 🧩 Plugin System

Extend **biograph** by adding custom biological tools or AI models in `backend/bio_plugins.py`:

```python
class VariantModelPlugin(NodePlugin):
    @property
    def name(self): return "variant-model"
    
    def run(self, input_data, params):
        # Your inference/tool logic here
        return {"result": "analyzed_data"}
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---
Built by engineers, for scientists. 🧬💻
