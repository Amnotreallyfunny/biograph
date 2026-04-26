import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useParams, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import ReactFlow, { Background, Controls, Handle, Position } from 'reactflow';
import 'reactflow/dist/style.css';
import { 
  Play, RotateCcw, Activity, Terminal, AlertCircle, 
  CheckCircle, Plus, Copy, BarChart2, Zap, Settings, 
  FileUp, Database, ArrowLeftRight, X, FlaskConical,
  Microscope, Dna, Info, ChevronRight, Layout
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const API_BASE = "http://localhost:8000";

// --- Custom Node ---
const BioTaskNode = ({ data }) => {
  const statusColors = {
    success: "bg-emerald-500",
    running: "bg-blue-500 animate-pulse",
    failed: "bg-rose-500",
    suspicious: "bg-amber-500",
    pending: "bg-slate-300"
  };
  return (
    <div className={`px-4 py-3 shadow-xl rounded-xl bg-white border-2 flex items-center gap-3 min-w-[180px] ${data.status === 'running' ? 'border-blue-400' : 'border-slate-100'}`}>
      <Handle type="target" position={Position.Left} />
      <div className={`w-3 h-3 rounded-full ${statusColors[data.status] || statusColors.pending}`} />
      <div className="flex flex-col">
        <span className="text-[10px] font-black uppercase text-slate-400 tracking-tighter">{data.type || 'TASK'}</span>
        <span className="text-xs font-bold text-slate-800">{data.label}</span>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
};

const nodeTypes = { bioTask: BioTaskNode };

// --- SSE Hook ---
const useRunStream = (runId) => {
  const [logs, setLogs] = useState([]);
  const [nodeStatus, setNodeStatus] = useState({});
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    if (!runId) return;
    const eventSource = new EventSource(`${API_BASE}/runs/${runId}/events`);
    eventSource.addEventListener('log', (e) => {
      const data = JSON.parse(e.data);
      setLogs(prev => [...prev, `[${data.task_id}] ${data.line}`]);
    });
    eventSource.addEventListener('status', (e) => {
      const data = JSON.parse(e.data);
      setNodeStatus(prev => ({ ...prev, [data.task_id]: data.status }));
    });
    eventSource.addEventListener('done', (e) => {
      setIsDone(true);
      eventSource.close();
    });
    return () => eventSource.close();
  }, [runId]);
  return { logs, nodeStatus, isDone };
};

// --- Dashboard ---
const Dashboard = () => {
  const [runs, setRuns] = useState([]);
  const fetchRuns = useCallback(() => {
    axios.get(`${API_BASE}/runs`).then(res => setRuns(res.data));
  }, []);
  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  return (
    <div className="min-h-screen bg-slate-50 p-12">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-end mb-12">
          <h1 className="text-4xl font-black uppercase">Analysis_Vault</h1>
          <Link to="/new" className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2">
            <Plus size={18}/> NEW_RUN
          </Link>
        </div>
        <div className="grid gap-4">
          {runs.map(run => (
            <Link to={`/run/${run.id}`} key={run.id} className="bg-white p-6 rounded-2xl border border-slate-200 flex justify-between items-center hover:shadow-lg transition-all">
              <div className="flex items-center gap-6">
                <FlaskConical className="text-blue-500" />
                <h2 className="font-bold text-slate-800">{run.name}</h2>
              </div>
              <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${run.status === 'success' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}`}>
                {run.status}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

// --- Run Creator ---
const RunCreator = () => {
  const navigate = useNavigate();
  const [name, setName] = useState("New Sequence Run");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const mockDag = {
      name,
      nodes: [{ id: 'ingest-01', type: 'bioTask', data: { label: 'Ingest' } }],
      edges: []
    };
    const res = await axios.post(`${API_BASE}/runs`, mockDag);
    navigate(`/run/${res.data.run_id}`);
  };

  return (
    <div className="p-12 max-w-xl mx-auto">
      <h1 className="text-2xl font-black mb-8 uppercase">Initialize_Run</h1>
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-2xl border border-slate-200 space-y-6">
        <div>
          <label className="text-xs font-bold text-slate-400 block mb-2">RUN_NAME</label>
          <input className="w-full border p-3 rounded-lg" value={name} onChange={e => setName(e.target.value)} />
        </div>
        <button className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold">DEPLOY_WORKFLOW</button>
      </form>
    </div>
  );
};

// --- Run View ---
const RunView = () => {
  const { runId } = useParams();
  const { logs, nodeStatus, isDone } = useRunStream(runId);
  const [run, setRun] = useState(null);
  const logEndRef = useRef(null);

  useEffect(() => {
    axios.get(`${API_BASE}/runs/${runId}`).then(res => setRun(res.data));
  }, [runId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!run) return <div className="p-20 text-center font-black animate-pulse uppercase">Syncing_Data...</div>;

  return (
    <div className="h-screen bg-slate-900 text-slate-200 flex flex-col overflow-hidden">
      <div className="p-6 bg-slate-800 flex justify-between items-center">
        <Link to="/" className="text-slate-500 hover:text-white uppercase font-bold text-xs">← Dashboard</Link>
        <h1 className="text-xl font-black uppercase">{run.name}</h1>
        <div className="text-[10px] bg-blue-600 px-3 py-1 rounded-full font-black uppercase">{isDone ? 'DONE' : 'EXECUTING'}</div>
      </div>
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 p-8 overflow-y-auto font-mono text-[11px] bg-black">
          {logs.map((l, i) => <div key={i} className="text-emerald-500 mb-1">{l}</div>)}
          <div ref={logEndRef} />
        </div>
        <div className="w-80 bg-slate-800 border-l border-slate-700 p-6">
           <h2 className="text-xs font-black uppercase text-slate-500 mb-6">Task_Status</h2>
           {Object.entries(nodeStatus).map(([id, status]) => (
             <div key={id} className="bg-slate-900 p-4 rounded-xl mb-3 flex justify-between items-center border border-slate-700">
               <span className="text-xs font-bold">{id}</span>
               <span className={`text-[10px] font-black uppercase ${status === 'success' ? 'text-emerald-500' : 'text-blue-500'}`}>{status}</span>
             </div>
           ))}
        </div>
      </div>
    </div>
  );
};

// --- App Entry ---
const App = () => (
  <Router>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/new" element={<RunCreator />} />
      <Route path="/run/:runId" element={<RunView />} />
    </Routes>
  </Router>
);

export default App;
