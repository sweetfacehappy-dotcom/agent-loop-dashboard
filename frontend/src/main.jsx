import React, { useEffect, useState } from 'react';
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
  const [name, setName] = useState('MR review loop');
  const [error, setError] = useState('');

  async function loadLoops() {
    try {
      setError('');
      setLoops(await apiRequest('/loops'));
    } catch (err) {
      setError(err.message);
    }
  }

  async function createLoop() {
    try {
      setError('');
      const created = await apiRequest('/loops', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, description: 'Review GitLab MRs using Jira/GitLab context', mode: 'review'})
      });
      setLoops(currentLoops => [...currentLoops, created]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function fireLoop(id) {
    try {
      setError('');
      const updated = await apiRequest(`/loops/${id}/fire`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({dry_run: true})
      });
      setLoops(currentLoops => currentLoops.map(loop => loop.id === id ? updated : loop));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { loadLoops(); }, []);

  return <main>
    <section className="hero">
      <p className="eyebrow">Agent Loop Dashboard</p>
      <h1>Monitor and fire bounded Jira/GitLab agent loops</h1>
      <p>Create loop definitions, assemble context from Jira tickets + GitLab MRs, then dispatch controlled review/automation loops.</p>
    </section>
    {error && <section className="panel error">{error}</section>}
    <section className="panel">
      <h2>Create loop</h2>
      <input value={name} onChange={e => setName(e.target.value)} />
      <button onClick={createLoop}>Create</button>
    </section>
    <section className="grid">
      {loops.map(loop => <article className="card" key={loop.id}>
        <h3>{loop.name}</h3>
        <p>{loop.description || 'No description'}</p>
        <small>Status: {loop.status}</small>
        <button onClick={() => fireLoop(loop.id)}>Dry-run fire</button>
      </article>)}
    </section>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
