import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { X, FlaskConical, Zap } from 'lucide-react';

const API_BASE = "http://localhost:8000";

const Dashboard = () => {
  const [runs, setRuns] = useState([]);
  const fetch = useCallback(() => { axios.get(`${API_BASE}/runs`).then(r => setRuns(r.data)); }, []);
  useEffect(() => { fetch(); const i = setInterval(fetch, 5000); return () => clearInterval(i); }, [fetch]);
  return (
    <div className="p-10 font-sans">
      <div className="flex justify-between mb-10">
        <h1 className="text-2xl font-bold">Research_Vault</h1>
        <Link to="/new" className="bg-blue-600 text-white px-4 py-2 rounded">NEW_RUN</Link>
      </div>
      {runs.map(r => (
        <div key={r.id} className="border p-4 mb-2 flex justify-between">
          <Link to={`/run/${r.id}`}>{r.name}</Link>
          <span>{r.status}</span>
        </div>
      ))}
    </div>
  );
};

const RunView = () => {
  const { runId } = useParams();
  const [run, setRun] = useState(null);
  const [logs, setLogs] = useState([]);
  useEffect(() => {
    axios.get(`${API_BASE}/runs/${runId}`).then(r => setRun(r.data));
    const es = new EventSource(`${API_BASE}/runs/${runId}/events`);
    es.addEventListener('log', e => {
      const d = JSON.parse(e.data);
      setLogs(prev => [...prev, d.line]);
    });
    return () => es.close();
  }, [runId]);
  if (!run) return <div>Loading...</div>;
  return (
    <div className="p-10 font-mono bg-black text-emerald-500 h-screen overflow-y-auto">
      <Link to="/" className="text-white">← Back</Link>
      <h1 className="text-white mb-10">{run.name}</h1>
      {logs.map((l, i) => <div key={i}>{l}</div>)}
    </div>
  );
};

const RunCreator = () => {
  const navigate = useNavigate();
  const [name, setName] = useState("New Experiment");
  const submit = async (e) => {
    e.preventDefault();
    const dag = { name, nodes: [{ id: 'INGEST', type: 'bioTask', data: { command: "echo 'Starting...'; sleep 2; echo 'Done.';" } }], edges: [] };
    const res = await axios.post(`${API_BASE}/runs`, dag);
    navigate(`/run/${res.data.run_id}`);
  };
  return (
    <div className="p-20 font-sans">
      <h1>New Run</h1>
      <form onSubmit={submit}>
        <input className="border p-2" value={name} onChange={e => setName(e.target.value)} />
        <button className="bg-black text-white p-2 ml-2">RUN</button>
      </form>
    </div>
  );
};

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
