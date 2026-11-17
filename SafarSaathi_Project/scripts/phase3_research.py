"""Reproduce scenario and hypothetical GA/PSO experiments; never modify raw data."""
from pathlib import Path
import csv
import hashlib
import json
import sys
import time
from copy import deepcopy

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'src'))
import numpy as np
from scipy.optimize import minimize
from safarsaathi_ml.integration_services import capacity_scenario
from safarsaathi_ml.optimization import optimize, parse_problem


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def example_problem():
    return {'demand': 120, 'exposure_tradeoff': .7, 'destinations': [
        {'id': 'Hypothetical A', 'capacity': 80, 'accessibility': 1, 'road_capacity': 70, 'resource_capacity': 60, 'exposure_weight': .1},
        {'id': 'Hypothetical B', 'capacity': 90, 'accessibility': .8, 'road_capacity': 90, 'resource_capacity': 90, 'exposure_weight': .8},
        {'id': 'Hypothetical C', 'capacity': 60, 'accessibility': 1, 'road_capacity': 60, 'resource_capacity': 60, 'exposure_weight': .3},
    ]}


def scenario_experiments():
    out = PROJECT / 'research/scenario_validation'; out.mkdir(parents=True, exist_ok=True)
    base = {'baseline_visitors': 100, 'capacity': 120, 'demand_change_percent': 0, 'available_capacity_percent': 100}
    rows = []
    for field, values in [('demand_change_percent', [-100, 0, 25, 50, 100, 1000]),
                          ('available_capacity_percent', [0, 25, 50, 75, 100]),
                          ('capacity', [1, 60, 90, 120, 240]), ('baseline_visitors', [0, 50, 100, 200, 1e9])]:
        for value in values:
            params = {**base, field: value}; result = capacity_scenario(params)
            expected_demand = params['baseline_visitors'] * (100 + params['demand_change_percent']) / 100
            expected_capacity = params['capacity'] * params['available_capacity_percent'] / 100
            expected_served = min(expected_demand, expected_capacity)
            expected_unserved = expected_demand - expected_served
            actual = result['scenario']
            assert abs(actual['served_visitors'] - expected_served) <= 1e-6
            assert abs(actual['unserved_visitors'] - expected_unserved) <= 1e-6
            assert result == capacity_scenario(params)
            rows.append({'experiment_id': f'scenario_{len(rows):03}', 'changed_parameter': field, 'value': value,
                         'demand': actual['visitors'], 'capacity': actual['available_capacity'],
                         'served': actual['served_visitors'], 'unserved': actual['unserved_visitors'],
                         'utilization': actual['utilization_ratio'], 'independent_formula_pass': True,
                         'scope': 'hypothetical_capacity_accounting_not_historical_accuracy'})
    write_csv(out / 'SCENARIO_SENSITIVITY_RESULTS.csv', rows)
    unsupported = []
    for key in ['rainfall_mm', 'road_accessibility', 'emergency_resources']:
        try: capacity_scenario({**base, key: 50})
        except ValueError as exc: unsupported.append({'input': key, 'status': 'REJECTED_UNSUPPORTED', 'detail': str(exc)})
        else: raise AssertionError('Unsupported physical driver was silently accepted.')
    write_json(out / 'scenario_checks.json', {'controlled_cases': len(rows), 'repeatability_pass': True, 'unsupported_drivers': unsupported})
    (out / 'SCENARIO_ENGINE_AUDIT.md').write_text('''# Scenario engine audit

The existing capacity_scenario function is one-period conservation accounting. It has four explicit inputs: baseline visitor equivalents, visitor-place capacity, demand change percent and available-capacity percent. It has no rainfall, runoff, hydrodynamics, terrain, routing, accommodation observation or emergency-dispatch model. Original UI controls for those concepts are labeled unmodeled context.

Demand = B(1+d/100); available capacity = C a/100; served = min(demand, available capacity); unserved = max(0, demand−capacity). Utilization is demand/capacity, null at zero capacity. Baseline uses B, C with no changes. All inputs are hypothetical, not inferred local conditions. Output has no affected locations.

Rainfall/accessibility/resource fields are explicitly rejected rather than assigned arbitrary causal coefficients. Reduced accommodation can be represented only as an explicitly assumed reduction in visitor-place capacity; reduced road access can be a hypothetical aggregate capacity loss, not a validated road-state calculation. Emergency resource limits are supported separately as explicit bottleneck capacities in the optimizer, not as a learned scenario relation.

Hardening preserves the formula: huge integers now yield input errors instead of overflow; an unrepresentable utilization ratio is rejected rather than emitted as Infinity/invalid JSON. No predictive flood accuracy is claimed.
''', encoding='utf-8')
    (out / 'SCENARIO_VALIDATION_REPORT.md').write_text(f'''# Scenario validation results

{len(rows)} controlled one-at-a-time cases passed direct independent arithmetic and exact repeatability. Inputs cover −100% to +1000% demand change, zero/full availability, one-place/large capacity and zero/large demand. As the formula requires, demand increases cannot reduce unmet demand, and capacity increases cannot increase unmet demand. Zero demand is served without inventing visitors; zero capacity gives no served visitors and null utilization.

Rainfall, road accessibility and emergency-resource fields were tested as unsupported and rejected; they are not silently treated as physical flood drivers. The CSV preserves all results and units. These are deterministic mathematical checks, **not prediction accuracy or a Nepal flood reconstruction**. No aligned observed capacity/visitor history is available for empirical validation. Accommodation/resource constraints are hypothetical where supplied.
''', encoding='utf-8')
    (out / 'SCENARIO_TEST_RESULTS.md').write_text('''# Scenario tests

Run `python scripts/phase3_research.py` for the CSV and independent formula checks. Run `python -m pytest tests/test_integration_adapters.py tests/test_research_hardening.py -q` for bounds, missing keys, conservation, invalid/boolean/nonfinite/extreme inputs and safe model output handling. Final executed test counts are recorded centrally in research/end_to_end/END_TO_END_TEST_REPORT.md; this file does not assert unexecuted tests passed.
''', encoding='utf-8')
    return rows


def convex_reference(problem):
    p = parse_problem(problem); ratios = p.demand / p.capacity
    objective = lambda q: p.alpha * np.dot(q, p.weights) + (1-p.alpha) * np.dot(q*q, ratios)
    gradient = lambda q: p.alpha*p.weights + 2*(1-p.alpha)*q*ratios
    solution = minimize(objective, p.capacity/p.capacity.sum(), jac=gradient, method='SLSQP',
                        bounds=[(0, min(c/p.demand, 1)) for c in p.capacity],
                        constraints=[{'type': 'eq', 'fun': lambda q: q.sum()-1, 'jac': lambda q: np.ones(len(q))}],
                        options={'ftol': 1e-12, 'maxiter': 500})
    if not solution.success or abs(solution.x.sum()-1) > 1e-8: raise RuntimeError('Numerical reference solver failed.')
    return float(solution.fun)


def optimization_experiments():
    out = PROJECT / 'research/optimization'; out.mkdir(parents=True, exist_ok=True)
    fixture = example_problem(); write_json(out / 'hypothetical_problem.json', fixture)
    version = hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest()
    rows, traces, examples = [], [], []
    for alpha in [0., .5, 1.]:
        problem = {**deepcopy(fixture), 'exposure_tradeoff': alpha}
        reference = convex_reference(problem)
        for seed in [5, 23, 79]:
            for algorithm in ['ga', 'pso']:
                request = {'problem': problem, 'algorithm': algorithm, 'seed': seed, 'population': 16, 'iterations': 30}
                result = optimize(request); replay = optimize(request)
                assert result['allocations'] == replay['allocations']
                assert result['convergence'] == replay['convergence']
                exp_id = f'{algorithm}_a{alpha:g}_seed{seed}'
                rows.append({'experiment_id': exp_id, 'dataset_version': version, 'algorithm': algorithm,
                             'alpha': alpha, 'seed': seed, 'population': 16, 'iterations': 30,
                             'baseline_objective': result['baseline']['objective'],
                             'objective': result['candidate']['objective'], 'reference_objective': reference,
                             'gap_to_numerical_reference': result['candidate']['objective']-reference,
                             'exposure_proxy': result['candidate']['exposure_proxy'],
                             'utilization_proxy': result['candidate']['utilization_proxy'],
                             'capacity_violation': result['max_capacity_violation'], 'conservation_error': result['conservation_error'],
                             'runtime_seconds': result['runtime_seconds'], 'same_seed_repeatable': True,
                             'scope': 'synthetic_hypothetical_fixture_not_operational_evidence'})
                traces.extend({'experiment_id': exp_id, 'iteration': i, 'best_objective': value} for i, value in enumerate(result['convergence']))
                examples.append(result)
    # Algorithm-parameter sensitivity on a fixed, non-test-selected hypothetical problem.
    sensitivity = []
    for algorithm in ['ga', 'pso']:
        for population, iterations in [(8, 10), (16, 30), (32, 60)]:
            result = optimize({'problem': fixture, 'algorithm': algorithm, 'seed': 23, 'population': population, 'iterations': iterations})
            sensitivity.append({'algorithm': algorithm, 'seed': 23, 'population': population, 'iterations': iterations,
                                'objective': result['candidate']['objective'], 'runtime_seconds': result['runtime_seconds']})
    write_csv(out / 'OPTIMIZATION_COMPARISON.csv', rows); write_csv(out / 'convergence.csv', traces)
    write_csv(out / 'parameter_sensitivity.csv', sensitivity); write_json(out / 'candidate_plans.json', examples)
    (out / 'OPTIMIZATION_FORMULATION.md').write_text('''# Explicit hypothetical allocation formulation

Decision x_i is continuous visitor equivalents allocated to destination i during a common user-selected period. All capacities are visitor places for that same period, not PCU/hour or beds without conversion. Effective bound c_i = min(destination capacity × accessibility fraction, road-throughput capacity, emergency-resource-supported capacity). These are explicit hypothetical bottlenecks, not learned operational relations. Bounds: 0≤x_i≤c_i; sum x_i=D. Infeasible demand is rejected; it is not silently dropped or rerouted.

Exposure proxy E=sum(x_i w_i)/D, with user-assumed weights 0≤w_i≤1. Utilization proxy U=sum(x_i²/c_i)/D (zero-capacity destinations receive zero). Scalar objective alpha E+(1−alpha)U; alpha∈[0,1]. Zero demand gives all-zero allocations/proxies. Proportional-effective-capacity allocation is the feasible baseline. Capacity-share variables normalize the numerical scale; capped-simplex water-filling projection repairs each candidate. Final bounds/conservation/finiteness are checked.

This is convex as a mathematical proxy problem; a separate SLSQP numerical reference checks experiment results. GA/PSO are deliberately compared with a simple baseline/reference, not claimed necessary or globally optimal. No hazard depth, casualties, actual ecological stress, route graph, integer dispatch, costs or validated intervention benefits are inferred. User-supplied capacities/weights are not empirical evidence.

Weighted-sum experiments at alpha=0,0.5,1 explore trade-offs and multiple seeds. They are not an exhaustive Pareto frontier or NSGA-II implementation. The fixture is synthetic/hypothetical and stored with a hash. No Nepal/Uttarakhand operational calibration is claimed. Independent seeds assess stochastic robustness, not uncertainty in the real world.
''', encoding='utf-8')
    (out / 'GA_IMPLEMENTATION_REPORT.md').write_text('''# Genetic algorithm implementation

src/safarsaathi_ml/optimization.py implements a real-valued GA: seeded population containing the proportional baseline, tournament selection of three candidates, per-gene blend crossover, 25% Gaussian mutation (standard deviation 0.10 in share space), capped-simplex repair and elite preservation. Evaluations call the declared objective, not random score updates. Best-so-far convergence is recorded every generation.

Experiments use three seeds and three exposure/utilization weightings; parameter sensitivity changes population/iteration budgets. Runtime is measured wall-clock and not deterministic. Candidate vectors and objective traces are reproducible for fixed software/input/seed. Objective improvements are numerical proxy improvements on the labeled hypothetical fixture, not empirical intervention effectiveness.
''', encoding='utf-8')
    (out / 'PSO_IMPLEMENTATION_REPORT.md').write_text('''# Particle swarm implementation

The same module implements bounded PSO: inertia 0.65, cognitive/social coefficients 1.4, velocity clamp ±0.25 in share space, seeded random coefficients, personal/global best updates and capped-simplex repair. Every position is evaluated using the same declared objective and capacities as GA. Best-so-far objective traces and candidate plans are retained.

Three seeds/three objective weights and parameter-budget sensitivity are compared with the identical baseline and an independent numerical convex reference. No globally optimal or operational recommendation is asserted. Stochastic convergence is not predictive calibration, hazard skill or a confidence percentage.
''', encoding='utf-8')
    max_gap = max(r['gap_to_numerical_reference'] for r in rows)
    max_violation = max(r['capacity_violation'] for r in rows)
    (out / 'OPTIMIZATION_VALIDATION_REPORT.md').write_text(f'''# Optimization validation

{len(rows)} seeded GA/PSO/weight experiments and {len(sensitivity)} algorithm-budget sensitivity cases executed. Each primary experiment repeated exactly for allocations/objective traces at the same seed. Maximum recorded capacity violation: {max_violation:.3g} visitor equivalents. Largest gap to the numerical convex reference: {max_gap:.8g} objective units; positive gaps are heuristic suboptimality, not suppressed. Constraint conservation errors and all runtimes are retained in OPTIMIZATION_COMPARISON.csv.

Zero exposure weight (alpha=0) tests whether heuristics can improve an already suitable proportional-capacity baseline; no improvement is fabricated. Seed variation and proxy trade-offs must be interpreted on these explicit assumptions only. The CSV includes reference gaps, objective components, baseline scores and parameters. The fixture is synthetic, not empirical validation of tourism pressure or Nepal flood interventions.

Core tests cover feasible/infeasible/missing/negative/nonfinite/extreme inputs, zero demand/capacity, inaccessible destinations, numerical projection, conservation, baseline comparison, one destination, large inputs and same-seed repeatability. API exposure is permitted only after core tests pass. Final counts/HTTP evidence are recorded in the central end-to-end report. Legacy /optimization/solve remains an explicit unavailable operational boundary; the new /optimization/allocate route supports this narrow research formulation.
''', encoding='utf-8')
    return rows


if __name__ == '__main__':
    started = time.perf_counter()
    scenario = scenario_experiments(); optimization = optimization_experiments()
    print(json.dumps({'scenario_cases': len(scenario), 'optimizer_experiments': len(optimization), 'runtime_seconds': time.perf_counter()-started}))
