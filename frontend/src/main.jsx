import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function apiRequest(path, options) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = body.detail ? `: ${typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)}` : '';
    } catch (_err) {
      detail = '';
    }
    throw new Error(`API request failed: ${res.status}${detail}`);
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
  const [loopSetup, setLoopSetup] = useState({
    description: 'Review GitLab MRs using Jira/GitLab context',
    objective: 'Find risks, missing context, and required fixes before code is merged.',
    trigger: 'Run when a GitLab merge request is opened, updated, or ready for review.',
    input_sources: 'Jira ticket, GitLab merge request diff, discussions, CI status, and existing review feedback.',
    instructions: 'Be specific, cite evidence from the available context, and prioritize actionable feedback.',
    constraints: 'Do not approve, merge, deploy, or expose secrets. Do not invent context that was not provided.',
    allowed_actions: 'Summarize findings, propose review comments, and request human approval for risky actions.',
    output_format: 'Markdown with sections: Summary, Blocking risks, Suggested comments, Open questions, Confidence.',
    success_criteria: 'All blocking risks are identified and each recommendation has a clear next action.',
    stop_conditions: 'Stop after one complete review or when required context is missing.',
    escalation_policy: 'Escalate to a human for low confidence, production impact, security concerns, or missing requirements.'
  });
  const [newLabel, setNewLabel] = useState('');
  const [newModel, setNewModel] = useState('');
  const [lastRun, setLastRun] = useState(null);
  const [error, setError] = useState('');

  const modelOptions = useMemo(() => Object.entries(runtime.model_labels ?? {}), [runtime]);

  function syncRuntime(runtimeStatus) {
    setRuntime(runtimeStatus);
    const defaultLabel = Object.keys(runtimeStatus.model_labels ?? {})[0] ?? '';
    setModelLabel(current => current && runtimeStatus.model_labels?.[current] ? current : defaultLabel);
  }

  async function loadRuntimeStatus() {
    const runtimeStatus = await apiRequest('/runtime/status');
    syncRuntime(runtimeStatus);
    return runtimeStatus;
  }

  async function loadInitialState() {
    try {
      setError('');
      const [loadedLoops, runtimeStatus] = await Promise.all([
        apiRequest('/loops'),
        apiRequest('/runtime/status')
      ]);
      setLoops(loadedLoops);
      syncRuntime(runtimeStatus);
    } catch (err) {
      setError(err.message);
    }
  }

  async function createLoop() {
    try {
      setError('');
      const payload = {
        name,
        ...loopSetup,
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

  async function createModelLabel() {
    try {
      setError('');
      await apiRequest('/runtime/model-labels', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({label: newLabel.trim(), model: newModel.trim()})
      });
      setNewLabel('');
      setNewModel('');
      await loadRuntimeStatus();
    } catch (err) {
      setError(err.message);
    }
  }

  async function updateModelLabel(label, model) {
    try {
      setError('');
      await apiRequest(`/runtime/model-labels/${encodeURIComponent(label)}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({model: model.trim()})
      });
      await loadRuntimeStatus();
    } catch (err) {
      setError(err.message);
    }
  }

  async function deleteModelLabel(label) {
    try {
      setError('');
      await apiRequest(`/runtime/model-labels/${encodeURIComponent(label)}`, {method: 'DELETE'});
      await loadRuntimeStatus();
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
      <p className="eyebrow">Config</p>
      <h2>Anthropic runtime</h2>
      <p>Status: <strong>{runtime.configured ? 'configured' : 'missing config'}</strong></p>
      <p>Endpoint: {runtime.base_url || 'not configured'}</p>
      <p>Model labels are managed here and available immediately when creating loops.</p>
      <div className="model-label-list">
        {modelOptions.length === 0 && <p>None configured yet.</p>}
        {modelOptions.map(([label, model]) => <ModelLabelRow
          key={label}
          label={label}
          model={model}
          onSave={updateModelLabel}
          onDelete={deleteModelLabel}
        />)}
      </div>
      <div className="form-row">
        <input aria-label="New label" placeholder="label, e.g. smart" value={newLabel} onChange={e => setNewLabel(e.target.value)} />
        <input aria-label="New model" placeholder="model id, e.g. claude-sonnet" value={newModel} onChange={e => setNewModel(e.target.value)} />
        <button onClick={createModelLabel} disabled={!newLabel.trim() || !newModel.trim()}>Add model label</button>
      </div>
    </section>
    <section className="panel">
      <h2>Create loop</h2>
      <div className="form-row">
        <input aria-label="Loop name" value={name} onChange={e => setName(e.target.value)} />
        <select aria-label="Loop model label" value={modelLabel} onChange={e => setModelLabel(e.target.value)}>
          {modelOptions.length === 0 && <option value="">default</option>}
          {modelOptions.map(([label, model]) => <option value={label} key={label}>{label} — {model}</option>)}
        </select>
        <button onClick={createLoop}>Create</button>
      </div>
      <div className="loop-setup-grid">
        <LoopSetupField label="Description" field="description" value={loopSetup.description} onChange={setLoopSetup} />
        <LoopSetupField label="Objective" field="objective" value={loopSetup.objective} onChange={setLoopSetup} />
        <LoopSetupField label="Trigger" field="trigger" value={loopSetup.trigger} onChange={setLoopSetup} />
        <LoopSetupField label="Input sources" field="input_sources" value={loopSetup.input_sources} onChange={setLoopSetup} />
        <LoopSetupField label="Instructions" field="instructions" value={loopSetup.instructions} onChange={setLoopSetup} />
        <LoopSetupField label="Constraints / guardrails" field="constraints" value={loopSetup.constraints} onChange={setLoopSetup} />
        <LoopSetupField label="Allowed actions" field="allowed_actions" value={loopSetup.allowed_actions} onChange={setLoopSetup} />
        <LoopSetupField label="Output format" field="output_format" value={loopSetup.output_format} onChange={setLoopSetup} />
        <LoopSetupField label="Success criteria" field="success_criteria" value={loopSetup.success_criteria} onChange={setLoopSetup} />
        <LoopSetupField label="Stop conditions" field="stop_conditions" value={loopSetup.stop_conditions} onChange={setLoopSetup} />
        <LoopSetupField label="Escalation policy" field="escalation_policy" value={loopSetup.escalation_policy} onChange={setLoopSetup} />
      </div>
    </section>
    {lastRun && <section className="panel">
      <h2>Last dry run</h2>
        <p>{lastRun.summary}</p>
      <p>Model: {lastRun.model_label} / {lastRun.model || 'unresolved'}</p>
      {lastRun.prompt_snapshot && <details>
        <summary>Prompt snapshot</summary>
        <pre>{lastRun.prompt_snapshot}</pre>
      </details>}
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

function LoopSetupField({label, field, value, onChange}) {
  return <label className="loop-setup-field">
    <span>{label}</span>
    <textarea
      aria-label={label}
      value={value}
      onChange={e => onChange(current => ({...current, [field]: e.target.value}))}
    />
  </label>;
}

function ModelLabelRow({label, model, onSave, onDelete}) {
  const [draftModel, setDraftModel] = useState(model);

  useEffect(() => { setDraftModel(model); }, [model]);

  return <div className="model-label-row">
    <strong>{label}</strong>
    <input aria-label={`Model for ${label}`} value={draftModel} onChange={e => setDraftModel(e.target.value)} />
    <button onClick={() => onSave(label, draftModel)} disabled={!draftModel.trim() || draftModel === model}>Save</button>
    <button className="secondary danger" onClick={() => onDelete(label)}>Delete</button>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
