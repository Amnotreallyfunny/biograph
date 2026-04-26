# biograph

**biograph** is a visual workflow platform specifically designed for bioinformatics and AI-driven biological analysis. It allows researchers and engineers to build, execute, and monitor complex pipelines using an intuitive drag-and-drop interface.

## 🚀 Features

- **Visual DAG Builder:** Airflow-style interface for building genomic pipelines.
- **AI Model Registry:** Plugin-based system for integrating AI models (e.g., Sequence Embedding, Variant Prediction).
- **Live Execution Monitoring:** Watch your pipeline execute in real-time with visual node status updates.
- **Node Inspector:** Detailed logs and parameter configuration for every step.
- **Bio-Specific Nodes:** Specialized nodes for Data Ingestion (FASTQ/VCF), Processing (Alignment), and AI Inference.

## 🏗️ Architecture

- **Backend:** FastAPI (Python)
  - `DAGEngine`: Handles dependency resolution and execution.
  - `ModelRegistry`: Manages AI model plugins.
  - `FileManager`: Local storage for genomic data.
- **Frontend:** React + React Flow + Tailwind CSS
  - Drag-and-drop canvas for pipeline design.
  - Real-time polling for execution status.

## 🛠️ Getting Started

### 1. Backend Setup
```bash
cd backend
# Create virtual environment
python3 -m venv venv
source venv/bin/activate
# Install dependencies
pip install fastapi uvicorn pydantic
# Run server
python main.py
```
*The API will be available at http://localhost:8000*

### 2. Frontend Setup
```bash
cd frontend
# Install dependencies
npm install
# Run development server
npm run dev
```
*The UI will be available at http://localhost:3001*

## 🧩 Model Plugin Example

Registering a new AI model is as simple as extending the `ModelPlugin` class:

```python
class MyCustomModel(ModelPlugin):
    async def run(self, input_data):
        # Your inference logic here
        return {"result": "analyzed_data"}

# Register in ModelRegistry
registry.models["my-model"] = MyCustomModel("My Model", "DNA", "JSON")
```

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---
Built with ❤️ for the Bio-Tech Community.
