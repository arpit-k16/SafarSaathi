import React, { useState } from 'react';
import { useApiAction, useApiQuery } from '../hooks/useApi.js';
import { api } from '../services/api/resources.js';
import ApiState from './ApiState.jsx';

export function ResearchNotice() {
  const query = useApiQuery('phase3-research', api.research);
  return <div className="text-xs text-slate-400 my-3" data-testid="research-status">
    <ApiState {...query} />
    {query.data && <><p className="text-primary">{query.data.status}</p>
      <ul className="list-disc pl-5">{query.data.findings.map(item => <li key={item}>{item}</li>)}</ul></>}
  </div>;
}

const fixture = {
  demand: 180, exposure_tradeoff: 0.5,
  destinations: [
    { id: 'Hypothetical A', capacity: 120, accessibility: 1, road_capacity: 100, resource_capacity: 110, exposure_weight: 0.8 },
    { id: 'Hypothetical B', capacity: 100, accessibility: 0.9, road_capacity: 95, resource_capacity: 90, exposure_weight: 0.2 },
    { id: 'Hypothetical C', capacity: 80, accessibility: 1, road_capacity: 75, resource_capacity: 70, exposure_weight: 0.4 },
  ],
};

export function OptimizationTool() {
  const [problem, setProblem] = useState(JSON.stringify(fixture, null, 2));
  const [algorithm, setAlgorithm] = useState('ga');
  const [seed, setSeed] = useState(23);
  const action = useApiAction();
  const report = useApiAction();
  const input = 'bg-black/30 border border-white/20 rounded p-2 text-sm';
  const button = 'border border-primary/40 text-primary rounded px-4 py-2 text-xs disabled:opacity-40';
  return <div data-testid="research-optimizer">
    <p className="text-amber-400 mb-3">Experimental GA / PSO · hypothetical continuous visitor allocation. Assumed exposure weights are user inputs. No verified intervention costs or operational road conditions.</p>
    <p className="text-xs text-slate-400 mb-3">Minimize α × assumed exposure + (1−α) × visitor-weighted utilization. Total demand is conserved; each allocation is bounded by capacity × accessibility, road capacity and resource capacity in the same period. The reference plan allocates in proportion to effective capacity.</p>
    <form onSubmit={e => { e.preventDefault(); report.run(() => Promise.resolve(null)); action.run(() => api.optimize({ problem: JSON.parse(problem), algorithm, seed: Number(seed), population: 16, iterations: 30 })); }}>
      <label className="block">Hypothetical problem JSON<textarea aria-label="Hypothetical optimization problem" rows={13} className={`${input} w-full mt-2 font-mono`} value={problem} onChange={e => setProblem(e.target.value)} /></label>
      <label>Algorithm <select className={input} value={algorithm} onChange={e => setAlgorithm(e.target.value)}><option value="ga">GA</option><option value="pso">PSO</option></select></label>
      <label className="ml-3">Seed <input className={input} type="number" min="0" max="4294967295" required value={seed} onChange={e => setSeed(e.target.value)} /></label>
      <button className={`${button} ml-3`} disabled={action.loading}>Run hypothetical allocation</button>
    </form>
    <ApiState {...action} />
    {action.data && <div className="text-xs mt-3" data-testid="optimization-result">
      <p className="text-primary">{action.data.status} · {action.data.algorithm.toUpperCase()} · seed {action.data.seed}</p>
      <p>Baseline objective {action.data.baseline.objective.toFixed(6)} → candidate {action.data.candidate.objective.toFixed(6)}. No global optimum claim.</p>
      <table className="w-full my-3"><thead><tr>{['Destination', 'Effective capacity', 'Baseline', 'Candidate'].map(x => <th key={x} className="text-left">{x}</th>)}</tr></thead><tbody>{action.data.allocations.map(r => <tr key={r.id}><td>{r.id}</td><td>{r.effective_capacity.toFixed(3)}</td><td>{r.baseline.toFixed(3)}</td><td>{r.candidate.toFixed(3)}</td></tr>)}</tbody></table>
      <p>Conservation error {action.data.conservation_error} · capacity violation {action.data.max_capacity_violation} · runtime {action.data.runtime_seconds.toFixed(3)} s</p>
      <details><summary className="text-primary cursor-pointer">Executed convergence and constraints</summary><pre className="whitespace-pre-wrap">{JSON.stringify({ convergence: action.data.convergence, limitations: action.data.limitations }, null, 2)}</pre></details>
      <button className={`${button} mt-3`} disabled={report.loading} onClick={() => report.run(() => api.optimizationReport(action.data))}>Generate recomputed optimization report</button>
      <ApiState {...report} />
      {report.data && <a className="text-primary underline block mt-2" download="safarsaathi-optimization.json" href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(report.data, null, 2))}`}>Download optimization JSON report</a>}
    </div>}
  </div>;
}
