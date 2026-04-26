import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useParams, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import ReactFlow, { Background, Controls } from 'reactflow';
import { 
  Play, RotateCcw, Activity, Terminal, AlertCircle, 
  CheckCircle, Plus, Copy, BarChart2, Zap, Settings, 
  FileUp, Database, ArrowLeftRight, X
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const API_BASE = "http://localhost:8000";

// --- SSE Hook ---
const useRunStream = (runId) => {
  const [logs, setLogs] = useState([]);
  const [nodeStatus, setNodeStatus] = useState({});
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    if (!runId) return;
    const eventSource = new EventSource(`${API_BASE}/runs/${runId}/stream`);
    
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

// --- Components ---

const SystemBanner = () => {
  const [doctor, setDoctor] = useState(null);
  useEffect(() => {
    axios.get(`${API_BASE}/system/doctor`).then(res => setDoctor(res.data));
  }, []);

  if (!doctor || doctor.tools.every(t => t.status === 'ok')) return null;

  return (
    <div className="bg-rose-600 text-white px-6 py-2 flex items-center justify-between text-xs font-bold uppercase tracking-wider sticky top-0 z-[200]">
      <div className="flex items-center gap-4">
        <AlertCircle size={14} />
        <span>System Alert: Missing Critical Bio-Tools</span>
        <div className="flex gap-2 ml-4">
          {doctor.tools.filter(t => t.status !== 'ok').map(t => (
            <span key={t.name} className="bg-white/20 px-2 py-0.5 rounded">{t.name}</span>
          ))}
        </div>
      </div>
      <div className="opacity-70">Check console or logs for fix commands</div>
    </div>
  );
};

const QCChart = ({ data, name }) => (
  <div className="h-32 w-full mt-2">
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <Bar dataKey="value" fill="#10b981">
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.status === 'suspicious' ? '#f59e0b' : '#10b981'} />
          ))}
        </Bar>
        <Tooltip cursor={{fill: 'transparent'}} contentStyle={{fontSize: '10px', background: '#000', border: 'none'}} />
      </BarChart>
    </ResponsiveContainer>
    <div className="text-[10px] text-slate-500 text-center uppercase mt-1">{name}</div>
  </div>
);

const RunCreator = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const cloneId = searchParams.get('clone');
  
  const [formData, setFormData] = useState({
    name: "New Research Run",
    template: "germline_v1",
    params: { threads: 4, memory: "8G" }
  });

  useEffect(() => {
    if (cloneId) {
      axios.get(`${API_BASE}/runs/${cloneId}`).then(res => {
        setFormData(prev => ({ ...prev, name: `${res.data.name} (Clone)` }));
      });
    }
  }, [cloneId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Simplified DAG generation for demo
    const mockDag = {
      name: formData.name,
      nodes: [
        { id: 'ingest', type: 'dataNode', data: { command: "echo 'Ingesting data...'; sleep 1" } },
        { id: 'align', type: 'processNode', data: { command: "echo 'Aligning sequences...'; sleep 2" } }
      ],
      edges: [{ id: 'e1', source: 'ingest', target: 'align' }],
      node_map: { 'ingest': {}, 'align': {} }
    };
    const res = await axios.post(`${API_BASE}/runs`, { dag: mockDag, name: formData.name });
    navigate(`/run/${res.data.run_id}`);
  };

  return (
    <div className="p-12 max-w-2xl mx-auto">
      <Link to="/" className="text-slate-500 hover:text-slate-800 text-sm mb-8 inline-block">← Back to Dashboard</Link>
      <h1 className="text-3xl font-bold mb-8">Initialize_New_Run</h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Run Identity</label>
          <input 
            className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3 outline-none focus:border-blue-500"
            value={formData.name}
            onChange={e => setFormData({...formData, name: e.target.value})}
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Pipeline Template</label>
          <select className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3">
            <option>Germline Variant Calling v1.0</option>
            <option>RNA-Seq Expression Analysis</option>
            <option>Metagenomic Profiling</option>
          </select>
        </div>
        <div className="grid grid-cols-2 gap-4">
           <div>
            <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Compute Threads</label>
            <input type="number" className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3" defaultValue={4} />
           </div>
           <div>
            <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Memory Allocation</label>
            <input className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3" defaultValue="8G" />
           </div>
        </div>
        <button type="submit" className="w-full bg-blue-600 text-white py-4 rounded-xl font-bold hover:bg-blue-700 shadow-lg transition-all flex items-center justify-center gap-2">
           <Zap size={20}/> Deploy_Workflow
        </button>
      </form>
    </div>
  );
};

const Dashboard = () => {
  const [runs, setRuns] = useState([]);
  const [selectedForCompare, setSelectedForCompare] = useState([]);

  useEffect(() => {
    axios.get(`${API_BASE}/runs`).then(res => setRuns(res.data));
  }, []);

  const toggleSelect = (id) => {
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare(prev => prev.filter(i => i !== id));
    } else if (selectedForCompare.length < 2) {
      setSelectedForCompare(prev => [...prev, id]);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <SystemBanner />
      <div className="p-12 max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-12">
          <div>
            <h1 className="text-4xl font-black tracking-tighter text-slate-900 mb-2 uppercase">Biograph_Dashboard</h1>
            <p className="text-slate-500 font-mono text-sm">Active Monitoring & Workflow Control</p>
          </div>
          <div className="flex gap-4">
            {selectedForCompare.length === 2 && (
              <Link to={`/compare?a=${selectedForCompare[0]}&b=${selectedForCompare[1]}`} className="flex items-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-indigo-700 transition-all">
                <ArrowLeftRight size={18}/> Compare_Selected
              </Link>
            )}
            <Link to="/new" className="flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-slate-800 transition-all">
              <Plus size={18}/> Initiate_Run
            </Link>
          </div>
        </div>

        <div className="grid gap-4">
          {runs.map(run => (
            <div key={run.id} className={`group bg-white p-6 rounded-2xl border transition-all flex justify-between items-center ${selectedForCompare.includes(run.id) ? 'border-indigo-500 ring-2 ring-indigo-100 shadow-md' : 'border-slate-200 hover:border-slate-300'}`}>
              <div className="flex items-center gap-6">
                <input 
                  type="checkbox" 
                  className="w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                  checked={selectedForCompare.includes(run.id)}
                  onChange={() => toggleSelect(run.id)}
                />
                <div>
                  <div className="font-mono text-[10px] text-slate-400 mb-1">{run.id}</div>
                  <Link to={`/run/${run.id}`} className="font-bold text-slate-800 text-lg hover:text-blue-600">{run.name}</Link>
                </div>
              </div>
              <div className="flex items-center gap-8">
                <div className="text-right">
                  <div className="text-[10px] font-bold text-slate-400 uppercase mb-1">Status</div>
                  <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter ${run.status === 'success' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}`}>
                    {run.status}
                  </span>
                </div>
                <Link to={`/new?clone=${run.id}`} title="Clone Run" className="p-2 text-slate-400 hover:text-blue-600 transition-colors">
                  <Copy size={20}/>
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

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

  // Mock data for QC visualization
  const qcData = [
    { name: 'R1', value: 95 },
    { name: 'R2', value: 88, status: 'suspicious' },
    { name: 'R3', value: 99 },
    { name: 'R4', value: 92 },
  ];

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <div className="flex-1 flex flex-col p-8 overflow-hidden">
        <div className="flex justify-between items-center mb-8">
           <div className="flex items-center gap-4">
              <Link to="/" className="bg-white p-2 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800">
                <ArrowLeftRight size={20} className="rotate-180"/>
              </Link>
              <div>
                <h2 className="text-2xl font-black text-slate-900 uppercase tracking-tight">Active_Session</h2>
                <div className="font-mono text-xs text-slate-400">{runId}</div>
              </div>
           </div>
           <div className={`px-4 py-2 rounded-xl text-xs font-black uppercase flex items-center gap-2 ${isDone ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-600 text-white shadow-lg animate-pulse'}`}>
              <Zap size={14}/> {isDone ? 'Session_Finalized' : 'In_Transit_Execution'}
           </div>
        </div>

        <div className="flex-1 grid grid-cols-3 gap-8 overflow-hidden">
          {/* Main Visual: DAG & Terminal */}
          <div className="col-span-2 flex flex-col gap-8 overflow-hidden">
            <div className="h-1/2 bg-white rounded-3xl border border-slate-200 shadow-sm relative overflow-hidden">
               <div className="absolute top-4 left-6 z-10 font-bold text-[10px] text-slate-400 uppercase tracking-widest bg-white/80 p-2 rounded-lg border border-slate-100">Workflow_Topology_v1.2</div>
               <ReactFlow nodes={[]} edges={[]}>
                  <Background color="#f1f5f9" gap={20} />
               </ReactFlow>
            </div>
            
            <div className="h-1/2 bg-slate-900 rounded-3xl overflow-hidden flex flex-col font-mono shadow-2xl border border-slate-800">
              <div className="bg-slate-800 px-6 py-3 text-[10px] text-slate-400 font-bold uppercase flex justify-between items-center border-b border-slate-700">
                <span>Kernel_Standard_Out</span>
                <Terminal size={12}/>
              </div>
              <div className="flex-1 p-6 overflow-y-auto text-[11px] leading-relaxed">
                {logs.map((line, i) => (
                  <div key={i} className="flex gap-4 group">
                    <span className="text-slate-700 select-none">{i+1}</span>
                    <span className="text-emerald-400/90 whitespace-pre-wrap">{line}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          </div>

          {/* Sidebar: Diagnostics */}
          <div className="flex flex-col gap-6 overflow-y-auto pr-2">
             <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
                <h3 className="text-xs font-black text-slate-400 uppercase mb-6 tracking-widest flex items-center gap-2">
                   <BarChart2 size={16} className="text-blue-500"/> Scientific_QC_Report
                </h3>
                <QCChart data={qcData} name="Mapping Quality (Phred)" />
                <div className="mt-8 space-y-4">
                  <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
                    <span className="text-xs font-bold text-slate-500">Read Count</span>
                    <span className="text-sm font-mono font-bold text-slate-900">42,501,102</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-amber-50 border border-amber-100 rounded-xl">
                    <span className="text-xs font-bold text-amber-700">Warning</span>
                    <span className="text-[10px] font-bold text-amber-700 uppercase">Low Diversity</span>
                  </div>
                </div>
             </div>

             <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
                <h3 className="text-xs font-black text-slate-400 uppercase mb-4 tracking-widest">Live_Status_Board</h3>
                <div className="space-y-3">
                  {Object.entries(nodeStatus).map(([id, status]) => (
                    <div key={id} className="flex justify-between items-center p-3 border border-slate-100 rounded-xl">
                      <span className="text-xs font-bold text-slate-700">{id}</span>
                      <span className={`text-[9px] px-2 py-0.5 rounded-full font-black uppercase ${status === 'success' ? 'bg-emerald-100 text-emerald-600' : 'bg-blue-100 text-blue-600'}`}>
                        {status}
                      </span>
                    </div>
                  ))}
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const CompareView = () => {
  const [searchParams] = useSearchParams();
  const runAId = searchParams.get('a');
  const runBId = searchParams.get('b');
  const [runA, setRunA] = useState(null);
  const [runB, setRunB] = useState(null);

  useEffect(() => {
    axios.get(`${API_BASE}/runs/${runAId}`).then(res => setRunA(res.data));
    axios.get(`${API_BASE}/runs/${runBId}`).then(res => setRunB(res.data));
  }, [runAId, runBId]);

  if (!runA || !runB) return <div className="p-12 text-center font-mono">Loading Comparison Data...</div>;

  return (
    <div className="p-12 max-w-6xl mx-auto">
      <Link to="/" className="text-slate-500 hover:text-slate-800 text-sm mb-8 inline-block">← Return to Dashboard</Link>
      <div className="flex justify-between items-center mb-12">
        <h1 className="text-4xl font-black uppercase tracking-tighter">Run_Differential</h1>
        <div className="bg-indigo-100 text-indigo-700 px-4 py-2 rounded-xl text-xs font-bold">DELTA_ANALYSIS_v1</div>
      </div>

      <div className="grid grid-cols-2 gap-12">
        <div className="space-y-8">
           <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-slate-400"></div>
              <div className="text-[10px] font-bold text-slate-400 uppercase mb-2">Subject A</div>
              <h2 className="text-xl font-bold mb-4">{runA.name || 'Web Run'}</h2>
              <div className="font-mono text-xs text-slate-500">{runAId}</div>
           </div>
           {/* Parameters and Metrics list would go here */}
           <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 font-mono text-xs space-y-2">
              <div className="flex justify-between"><span>CPU_THREADS</span><span>4</span></div>
              <div className="flex justify-between"><span>MEMORY_CAP</span><span>8G</span></div>
              <div className="flex justify-between border-t pt-2 mt-4 text-emerald-600 font-bold"><span>MAPPING_RATE</span><span>98.2%</span></div>
           </div>
        </div>

        <div className="space-y-8">
           <div className="bg-white p-8 rounded-3xl border-2 border-indigo-500 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
              <div className="text-[10px] font-bold text-indigo-400 uppercase mb-2">Subject B</div>
              <h2 className="text-xl font-bold mb-4">{runB.name || 'Web Run'}</h2>
              <div className="font-mono text-xs text-slate-500">{runBId}</div>
           </div>
           <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 font-mono text-xs space-y-2">
              <div className="flex justify-between"><span>CPU_THREADS</span><span>8 <span className="text-indigo-600 font-bold">(+4)</span></span></div>
              <div className="flex justify-between"><span>MEMORY_CAP</span><span>16G <span className="text-indigo-600 font-bold">(2x)</span></span></div>
              <div className="flex justify-between border-t pt-2 mt-4 text-emerald-600 font-bold"><span>MAPPING_RATE</span><span>99.1% <span className="text-indigo-600">(+0.9%)</span></span></div>
           </div>
        </div>
      </div>
    </div>
  );
};

const App = () => {
  return (
    <Router>
      <div className="font-sans antialiased text-slate-900">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new" element={<RunCreator />} />
          <Route path="/run/:runId" element={<RunView />} />
          <Route path="/compare" element={<CompareView />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;
