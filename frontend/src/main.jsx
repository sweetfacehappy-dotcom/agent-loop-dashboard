import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function apiRequest(path, options) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) {
    throw new Error(`API request failed: ${res.status}`);
  }
  if (res.status === 204) {
    return null;
  }
  return res.json();
}

function App() {
  const [loops, setLoops] = useState([]);
  const [runtime, setRuntime] = useState({model_labels: {}});
  const [name, setName] = useState('MR review loop');
  const [modelLabel, setModelLabel] = useState('');
  const [lastRun, setLastRun] = useState(null);
  const [error, setError] = useState('');

  const modelOptions = useMemo(() => Object.entries(runtime.model_labels ?? {}), [runtime]);

  async function loadInitialState() {
    try {
      setError('');
      const [loadedLoops, runtimeStatus] = await Promise.all([
        apiRequest('/loops'),
        apiRequest('/runtime/status')
      ]);
      setLoops(loadedLoops);
      setRuntime(runtimeStatus);
      const defaultLabel = Object.keys(runtimeStatus.model_labels ?? {})[0] ?? '';
      setModelLabel(current => current || defaultLabel);
    } catch (err) {
      setError(err.message);
    }
  }

  async function createLoop() {
    try {
      setError('');
      const payload = {
        name,
        description: 'Review GitLab MRs using Jira/GitLab context',
        mode: 'review',
        ...(modelLabel ? {model_label: modelLabel} : {})
      };
      const created = await apiRequest('/loops', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      setLoops(currentLoops => [...currentLoops, created]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function fireLoop(id) {
    try {
      setError('');
      const result = await apiRequest(`/loops/${id}/fire`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({dry_run: true})
      });
      setLoops(currentLoops => currentLoops.map(loop => loop.id === id ? result.loop : loop));
      setLastRun(result.run);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { loadInitialState(); }, []);

  return <main>
    <section className="hero">
      <p className="eyebrow">Agent Loop Dashboard</p>
      <h1>Monitor and fire bounded Jira/GitLab agent loops</h1>
      <p>Create loop definitions, assemble context from Jira tickets + GitLab MRs, then dispatch controlled review/automation loops.</p>
    </section>
    {error && <section className="panel error">{error}</section>}
    <section className="panel runtime">
      <h2>Anthropic runtime</h2>
      <p>Status: <strong>{runtime.configured ? 'configured' : 'missing config'}</strong></p>
      <p>Endpoint: {runtime.base_url || 'not configured'}</p>
      <p>Model labels: {modelOptions.length ? modelOptions.map(([label, model]) => `${label} → ${model}`).join(', ') : 'none configured'}</p>
    </section>
    <section className="panel">
      <h2>Create loop</h2>
      <input value={name} onChange={e => setName(e.target.value)} />
      <select value={modelLabel} onChange={e => setModelLabel(e.target.value)}>
        {modelOptions.length === 0 && <option value="">default</option>}
        {modelOptions.map(([label, model]) => <option value={label} key={label}>{label} — {model}</option>)}
      </select>
      <button onClick={createLoop}>Create</button>
    </section>
    {lastRun && <section className="panel">
      <h2>Last dry run</h2>
      <p>{lastRun.summary}</p>
      <p>Model: {lastRun.model_label} / {lastRun.model || 'unresolved'}</p>
    </section>}
    <section className="grid">
      {loops.map(loop => <article className="card" key={loop.id}>
        <h3>{loop.name}</h3>
        <p>{loop.description || 'No description'}</p>
        <small>Status: {loop.status}</small>
        <small>Model: {loop.model_label}</small>
        <button onClick={() => fireLoop(loop.id)}>Dry-run fire</button>
      </article>)}
    </section>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
