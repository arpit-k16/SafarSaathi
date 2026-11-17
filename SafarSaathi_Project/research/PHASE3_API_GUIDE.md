# Phase 3 API and interface

The architecture and existing routes are retained. Restart the Python server after source changes. Vite uses `VITE_SAFARSAATHI_API_URL`, default `http://127.0.0.1:8000`.

- `GET /research/status`: bounded generated findings from research/research_status.json;503 when evidence is missing. This is stored audit evidence, not a live validation run.
- `GET /optimization/metadata`: actual hypothetical allocation formulation, constraints and limitations.
- `POST /optimization/allocate`: strict JSON with problem, algorithm (`ga`/`pso`), seed, population8..64, iterations1..100. Problem has demand, exposure_tradeoff0..1, and1..12 unique destination objects. See optimization/hypothetical_problem.json and OPTIMIZATION_FORMULATION.md. Invalid/infeasible inputs return422; no demand is silently discarded.
- `POST /reports/generate`: optional `optimization` accepts those request parameters and reruns the optimizer. It never trusts a submitted result object. Existing optional scenario reports remain available.
- Legacy `/optimization/solve` remains501 for operational intervention planning. `/integration/status.pages` retains its legacy operational contract; its research_extensions field points to the new research metadata. The UI reads the new metadata to show hypothetical availability.

Model Center, Risk & Resilience, Satellite Intelligence and Reports show the same evidence notice from the API. Optimizer and Explanation panels expose the existing-form-style research tool, actual baseline/candidate values, trace, constraints, runtime, and recomputed JSON report. Other maps/telemetry remain explicitly static/demo/unavailable. No CSS, fonts, branding, navigation, source map assets or model artifacts were changed.

Core numerical and HTTP tests precede API exposure. Browser evidence is in end_to_end/BROWSER_VERIFICATION.md. Operational flood warning, intervention costs/benefits, verified local closures and live telemetry remain unavailable.
