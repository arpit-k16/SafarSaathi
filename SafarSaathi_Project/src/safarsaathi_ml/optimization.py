"""Seeded GA/PSO for explicit hypothetical, continuous visitor allocation.

This is a mathematical planning experiment, not a learned hazard/exposure model.
No geographic, observed capacity, intervention-effect or operational data is inferred.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
import math
import numpy as np


LIMITATIONS = [
    'All capacities, accessibility and exposure weights are explicit user assumptions, not observed or validated local conditions.',
    'Continuous visitor-equivalent allocation for one common period; fractional allocations are not dispatch instructions.',
    'Exposure is a weighted proxy, not hazard probability, casualties, flood depth or measured tourist exposure.',
    'Congestion is a capacity-utilization proxy, not a road-network traffic simulation.',
    'GA/PSO return feasible candidate plans; no global optimum is claimed.',
]


@dataclass(frozen=True)
class Problem:
    ids: tuple[str, ...]
    capacity: np.ndarray
    weights: np.ndarray
    demand: float
    alpha: float


def numeric(value, field, low, high):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise ValueError(f'{field} must be a finite number in [{low:g}, {high:g}].')
    if 0 < value < 1e-6 and field != 'exposure_tradeoff':
        raise ValueError(f'{field}: nonzero values below 1e-6 are outside the supported numerical scale.')
    return float(value)


def parse_problem(payload):
    if not isinstance(payload, dict) or set(payload) != {'demand', 'destinations', 'exposure_tradeoff'}:
        raise ValueError('problem requires exactly demand, destinations and exposure_tradeoff.')
    demand = numeric(payload['demand'], 'demand', 0, 1e9)
    alpha = numeric(payload['exposure_tradeoff'], 'exposure_tradeoff', 0, 1)
    rows = payload['destinations']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 12:
        raise ValueError('destinations must contain 1..12 explicit hypothetical destination objects.')
    ids, capacities, weights = [], [], []
    fields = {'id', 'capacity', 'accessibility', 'road_capacity', 'resource_capacity', 'exposure_weight'}
    for row in rows:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError('Each destination requires id, capacity, accessibility, road_capacity, resource_capacity and exposure_weight only.')
        if not isinstance(row['id'], str) or not row['id'].strip() or len(row['id']) > 64 or row['id'] in ids:
            raise ValueError('Destination IDs must be unique, nonempty strings of at most 64 characters.')
        cap = numeric(row['capacity'], 'capacity', 0, 1e9)
        access = numeric(row['accessibility'], 'accessibility', 0, 1)
        road = numeric(row['road_capacity'], 'road_capacity', 0, 1e9)
        resource = numeric(row['resource_capacity'], 'resource_capacity', 0, 1e9)
        weight = numeric(row['exposure_weight'], 'exposure_weight', 0, 1)
        effective = min(cap * access, road, resource)
        if 0 < effective < 1e-6:
            raise ValueError('Effective nonzero capacity below 1e-6 is outside the supported numerical scale.')
        ids.append(row['id']); capacities.append(effective); weights.append(weight)
    caps = np.asarray(capacities, dtype=float)
    if demand > float(caps.sum()):
        raise ValueError('Infeasible problem: demand exceeds total accessible road/resource-bounded capacity.')
    return Problem(tuple(ids), caps, np.asarray(weights), demand, alpha)


def project(values, caps, total=1.0):
    """Euclidean projection onto 0<=x<=caps, sum(x)=total by water filling."""
    values, caps = np.asarray(values, float), np.asarray(caps, float)
    if values.ndim != 1 or caps.shape != values.shape or not np.isfinite(values).all() or not np.isfinite(caps).all() or (caps < 0).any():
        raise ValueError('Projection requires aligned finite vectors and nonnegative capacities.')
    if not math.isfinite(total) or total < 0 or total > float(caps.sum()) + 1e-12:
        raise ValueError('Infeasible projection total.')
    if total == 0: return np.zeros_like(values)
    low, high = float(np.min(values - caps)), float(np.max(values))
    for _ in range(55):
        midpoint = (low + high) / 2
        result = np.clip(values - midpoint, 0, caps)
        if result.sum() > total: low = midpoint
        else: high = midpoint
    result = np.clip(values - (low + high) / 2, 0, caps)
    # Repair the last floating-point residual without crossing bounds.
    residual = total - float(result.sum())
    for i in range(len(result)):
        step = min(residual, caps[i] - result[i]) if residual >= 0 else max(residual, -result[i])
        result[i] += step; residual -= step
    if abs(float(result.sum()) - total) > 1e-9 or (result < -1e-12).any() or (result > caps + 1e-12).any():
        raise ArithmeticError('Projection failed numerical feasibility checks.')
    return result


def scores(problem, shares):
    if problem.demand == 0: return {'exposure_proxy': 0., 'utilization_proxy': 0., 'objective': 0.}
    exposure = float(np.dot(shares, problem.weights))
    ratio = np.divide(problem.demand, problem.capacity, out=np.zeros_like(problem.capacity), where=problem.capacity > 0)
    utilization = float(np.dot(shares * shares, ratio))
    return {'exposure_proxy': exposure, 'utilization_proxy': utilization,
            'objective': problem.alpha * exposure + (1 - problem.alpha) * utilization}


def run_algorithm(problem, algorithm, seed, population, iterations):
    started = perf_counter()
    if problem.demand == 0:
        return np.zeros(len(problem.ids)), [0.] * (iterations + 1), perf_counter() - started
    cap_shares = np.minimum(problem.capacity, problem.demand) / problem.demand
    baseline = problem.capacity / problem.capacity.sum()
    rng = np.random.default_rng(seed)
    positions = np.stack([baseline] + [project(rng.random(len(problem.ids)), cap_shares) for _ in range(population - 1)])
    objective = lambda x: scores(problem, x)['objective']
    values = np.asarray([objective(x) for x in positions])
    index = int(np.argmin(values)); best, best_value = positions[index].copy(), float(values[index])
    trace = [best_value]
    if algorithm == 'pso':
        velocities = np.zeros_like(positions); personal = positions.copy(); personal_values = values.copy()
    for _ in range(iterations):
        if algorithm == 'ga':
            children = [best.copy()]
            def parent():
                candidates = rng.integers(0, population, size=3)
                return positions[candidates[np.argmin(values[candidates])]]
            while len(children) < population:
                a, b = parent(), parent(); mix = rng.random(len(problem.ids))
                child = mix * a + (1 - mix) * b
                mutate = rng.random(len(problem.ids)) < .25
                child = child + mutate * rng.normal(0, .10, len(problem.ids))
                children.append(project(child, cap_shares))
            positions = np.stack(children)
        else:
            velocities = (.65 * velocities + 1.4 * rng.random(positions.shape) * (personal - positions)
                          + 1.4 * rng.random(positions.shape) * (best - positions))
            velocities = np.clip(velocities, -.25, .25)
            positions = np.stack([project(x + v, cap_shares) for x, v in zip(positions, velocities)])
        values = np.asarray([objective(x) for x in positions])
        if algorithm == 'pso':
            improved = values < personal_values
            personal[improved] = positions[improved]; personal_values[improved] = values[improved]
        index = int(np.argmin(values))
        if values[index] < best_value: best, best_value = positions[index].copy(), float(values[index])
        trace.append(best_value)
    return best, trace, perf_counter() - started


def optimize(payload):
    if not isinstance(payload, dict) or set(payload) != {'problem', 'algorithm', 'seed', 'population', 'iterations'}:
        raise ValueError('Expected problem, algorithm, seed, population and iterations only.')
    algorithm = payload['algorithm']
    if algorithm not in ('ga', 'pso'):
        raise ValueError('algorithm must be ga or pso.')
    for name, low, high in [('seed', 0, 2**32 - 1), ('population', 8, 64), ('iterations', 1, 100)]:
        if type(payload[name]) is not int or not low <= payload[name] <= high:
            raise ValueError(f'{name} must be an integer in [{low}, {high}].')
    problem = parse_problem(payload['problem'])
    shares, trace, runtime = run_algorithm(problem, algorithm, payload['seed'], payload['population'], payload['iterations'])
    allocation = shares * problem.demand
    baseline_shares = problem.capacity / problem.capacity.sum() if problem.capacity.sum() else np.zeros(len(problem.ids))
    candidate = scores(problem, shares); baseline = scores(problem, baseline_shares)
    violation = max(0., float(np.max(allocation - problem.capacity)), float(-np.min(allocation)))
    conservation_error = abs(float(allocation.sum()) - problem.demand)
    if violation > 1e-6 or conservation_error > max(1e-6, problem.demand * 1e-10) or not np.isfinite(allocation).all():
        raise ArithmeticError('Optimization failed final numerical/feasibility validation.')
    return {'status': 'EXPERIMENTAL_HYPOTHETICAL_ALLOCATION', 'formulation_version': 'capacity-allocation-v1',
            'algorithm': algorithm, 'seed': payload['seed'], 'population': payload['population'], 'iterations': payload['iterations'],
            'problem': payload['problem'], 'units': 'continuous visitor equivalents per common user-selected period',
            'allocations': [{'id': key, 'effective_capacity': float(cap), 'baseline': float(base * problem.demand), 'candidate': float(value)}
                            for key, cap, base, value in zip(problem.ids, problem.capacity, baseline_shares, allocation)],
            'baseline': baseline, 'candidate': candidate, 'objective_improvement': baseline['objective'] - candidate['objective'],
            'max_capacity_violation': violation, 'conservation_error': conservation_error, 'convergence': trace,
            'runtime_seconds': runtime, 'globally_optimal': False, 'limitations': LIMITATIONS}


def metadata():
    return {'status': 'OPTIMIZATION AVAILABLE', 'scope': 'EXPERIMENTAL_HYPOTHETICAL_ALLOCATION',
            'algorithms': ['ga', 'pso'], 'formulation_version': 'capacity-allocation-v1',
            'objective': 'alpha * mean assumed exposure weight + (1-alpha) * visitor-weighted utilization',
            'constraints': '0 <= x_i <= min(capacity_i*accessibility_i, road_capacity_i, resource_capacity_i); sum(x)=demand',
            'limitations': LIMITATIONS}
