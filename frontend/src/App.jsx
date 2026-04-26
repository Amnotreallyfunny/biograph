import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, { 
  addEdge, 
  Background, 
  Controls, 
  Panel,
  useNodesState,
  useEdgesState,
  Handle,
  Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';
import { Database, Cpu, Brain, FileOutput, Play, Save, Plus, Terminal } from 'lucide-react';

const API_BASE = "http://localhost:8000";

// --- Custom Node Components ---

const DataNode = ({ data }) => (
  <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-blue-500 min-w-[150px]">
    <div className="flex items-center border-b pb-2 mb-2">
      <Database size={16} className="mr-2 text-blue-500" />
      <div className="text-xs font-bold uppercase tracking-wider">Data Ingestion</div>
    </div>
    <div className="text-xs text-gray-600">{data.fileName || "Select File..."}</div>
    <Handle type="source" position={Position.Right} className="w-3 h-3 bg-blue-500" />
  </div>
);

const ProcessNode = ({ data }) => (
  <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-emerald-500 min-w-[150px]">
    <Handle type="target" position={Position.Left} className="w-3 h-3 bg-emerald-500" />
    <div className="flex items-center border-b pb-2 mb-2">
      <Cpu size={16} className="mr-2 text-emerald-500" />
      <div className="text-xs font-bold uppercase tracking-wider">Processing</div>
    </div>
    <div className="text-xs text-gray-600">{data.tool || "Alignment"}</div>
    <Handle type="source" position={Position.Right} className="w-3 h-3 bg-emerald-500" />
  </div>
);

const ModelNode = ({ data }) => (
  <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-purple-500 min-w-[150px]">
    <Handle type="target" position={Position.Left} className="w-3 h-3 bg-purple-500" />
    <div className="flex items-center border-b pb-2 mb-2">
      <Brain size={16} className="mr-2 text-purple-500" />
      <div className="text-xs font-bold uppercase tracking-wider">AI Model</div>
    </div>
    <div className="text-xs text-gray-600">{data.modelId || "Variant Predictor"}</div>
    <Handle type="source" position={Position.Right} className="w-3 h-3 bg-purple-500" />
  </div>
);

const OutputNode = ({ data }) => (
  <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-slate-500 min-w-[150px]">
    <Handle type="target" position={Position.Left} className="w-3 h-3 bg-slate-500" />
    <div className="flex items-center border-b pb-2 mb-2">
      <FileOutput size={16} className="mr-2 text-slate-500" />
      <div className="text-xs font-bold uppercase tracking-wider">Output</div>
    </div>
    <div className="text-xs text-gray-600">Final Report</div>
  </div>
);

const nodeTypes = {
  dataNode: DataNode,
  processNode: ProcessNode,
  modelNode: ModelNode,
  outputNode: OutputNode,
};

const initialNodes = [
  { id: '1', type: 'dataNode', position: { x: 50, y: 100 }, data: { fileName: 'sample_dna.fastq' } },
  { id: '2', type: 'processNode', position: { x: 300, y: 100 }, data: { tool: 'BWA-MEM Alignment' } },
  { id: '3', type: 'modelNode', position: { x: 550, y: 100 }, data: { modelId: 'Variant Predictor' } },
  { id: '4', type: 'outputNode', position: { x: 800, y: 100 }, data: {} },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2' },
  { id: 'e2-3', source: '2', target: '3' },
  { id: 'e3-4', source: '3', target: '4' },
];

const App = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [runId, setRunId] = useState(null);
  const [runData, setRunData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  const saveDAG = async () => {
    const dag = { name: "Bio-AI Pipeline", nodes, edges };
    const res = await axios.post(`${API_BASE}/dag`, dag);
    alert(`DAG Saved with ID: ${res.data.id}`);
    return res.data.id;
  };

  const executePipeline = async () => {
    const dagId = await saveDAG();
    const res = await axios.post(`${API_BASE}/execute/${dagId}`);
    setRunId(res.data.run_id);
  };

  useEffect(() => {
    if (runId) {
      const interval = setInterval(async () => {
        const res = await axios.get(`${API_BASE}/runs/${runId}`);
        setRunData(res.data);
        
        // Update node visual status based on backend
        setNodes((nds) => 
          nds.map((node) => {
            const status = res.data.node_states[node.id];
            let border = "#3b82f6"; // default blue
            if (status === 'running') border = "#eab308";
            if (status === 'success') border = "#10b981";
            if (status === 'failed') border = "#ef4444";
            
            return {
              ...node,
              style: { ...node.style, border: `3px solid ${border}` }
            };
          })
        );

        if (res.data.status === 'success' || res.data.status === 'failed') {
          clearInterval(interval);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [runId]);

  const onNodeClick = (event, node) => {
    setSelectedNode(node);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-50 font-sans">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-600 p-1.5 rounded-lg text-white">
            <Brain size={24} />
          </div>
          <h1 className="text-xl font-bold text-slate-800 tracking-tight">biograph</h1>
        </div>
        <div className="flex gap-3">
          <button onClick={saveDAG} className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-50">
            <Save size={16} /> Save Pipeline
          </button>
          <button onClick={executePipeline} className="flex items-center gap-2 px-4 py-2 bg-emerald-600 rounded-lg text-sm font-semibold text-white hover:bg-emerald-700 shadow-md transition-all">
            <Play size={16} /> Execute DAG
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar / Palette */}
        <div className="w-64 bg-white border-r border-slate-200 p-4 flex flex-col gap-4">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Node Palette</h2>
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3 p-3 border-2 border-dashed border-blue-200 rounded-lg cursor-grab hover:bg-blue-50 transition-colors">
              <Database size={18} className="text-blue-500" />
              <span className="text-sm font-medium text-slate-700">Data Source</span>
            </div>
            <div className="flex items-center gap-3 p-3 border-2 border-dashed border-emerald-200 rounded-lg cursor-grab hover:bg-emerald-50 transition-colors">
              <Cpu size={18} className="text-emerald-500" />
              <span className="text-sm font-medium text-slate-700">Processing</span>
            </div>
            <div className="flex items-center gap-3 p-3 border-2 border-dashed border-purple-200 rounded-lg cursor-grab hover:bg-purple-50 transition-colors">
              <Brain size={18} className="text-purple-500" />
              <span className="text-sm font-medium text-slate-700">AI Model</span>
            </div>
          </div>
          
          <div className="mt-auto border-t pt-4">
             <div className="text-[10px] text-slate-400 uppercase font-bold mb-2 tracking-tighter">System Health</div>
             <div className="flex items-center gap-2 text-emerald-500 text-xs font-bold">
               <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
               BACKEND_OPERATIONAL
             </div>
          </div>
        </div>

        {/* DAG Builder Canvas */}
        <div className="flex-1 relative bg-slate-50">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            fitView
          >
            <Background color="#cbd5e1" gap={20} />
            <Controls />
            <Panel position="top-right" className="bg-white/80 p-2 rounded shadow-sm border border-slate-200 text-[10px] font-bold text-slate-500 uppercase">
              Drag_Canvas_v1.0
            </Panel>
          </ReactFlow>
        </div>

        {/* Inspector Panel */}
        <div className="w-80 bg-white border-l border-slate-200 flex flex-col">
          <div className="p-4 border-b border-slate-100 flex items-center gap-2">
             <Terminal size={18} className="text-slate-400" />
             <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Inspector</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            {selectedNode ? (
              <div className="space-y-6">
                <div>
                   <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Node ID</div>
                   <div className="text-sm font-mono bg-slate-50 p-2 rounded border border-slate-100">{selectedNode.id}</div>
                </div>
                <div>
                   <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Status</div>
                   <div className="text-sm font-bold text-emerald-600">
                      {runData?.node_states[selectedNode.id] || "IDLE"}
                   </div>
                </div>
                <div>
                   <div className="text-[10px] font-bold text-slate-400 uppercase mb-2">Live Logs</div>
                   <pre className="text-[10px] bg-slate-900 text-slate-300 p-3 rounded-lg overflow-x-auto h-64 border border-slate-800">
                      {runData?.logs[selectedNode.id] || "No execution data yet."}
                   </pre>
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-300 text-center px-6">
                 <Plus size={48} className="mb-4 opacity-20" />
                 <p className="text-sm">Select a node in the DAG to view parameters and logs</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
