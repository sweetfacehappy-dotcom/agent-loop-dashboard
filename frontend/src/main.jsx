import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [loops, setLoops] = useState([]);
  const [name, setName] = useState('MR review loop');

  async function loadLoops() {
    const res = await fetch('http://localhost:8000/loops');
    setLoops(await res.json());
  }

  async function createLoop() {
    await fetch('http://localhost:8000/loops', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, description: 'Review GitLab MRs using Jira/GitLab context', mode: 'review'})
    });
    await loadLoops();
  }

  async function fireLoop(id) {
    await fetch(`http://localhost:8000/loops/${id}/fire`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({dry_run: true})
    });
    await loadLoops();
  }

  useEffect(() => { loadLoops(); }, []);

  return <main>
    <section className="hero">
      <p className="eyebrow">Agent Loop Dashboard</p>
      <h1>Monitor and fire bounded Jira/GitLab agent loops</h1>
      <p>Create loop definitions, assemble context from Jira tickets + GitLab MRs, then dispatch controlled review/automation loops.</p>
    </section>
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
