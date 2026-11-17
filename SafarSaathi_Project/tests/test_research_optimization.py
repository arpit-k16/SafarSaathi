from copy import deepcopy
import numpy as np
import pytest
from safarsaathi_ml.optimization import optimize, parse_problem, project, scores


def payload(algorithm='ga'):
    return {'problem': {'demand': 120, 'exposure_tradeoff': .7, 'destinations': [
        {'id': 'A', 'capacity': 80, 'accessibility': 1, 'road_capacity': 70, 'resource_capacity': 60, 'exposure_weight': .1},
        {'id': 'B', 'capacity': 90, 'accessibility': .8, 'road_capacity': 90, 'resource_capacity': 90, 'exposure_weight': .8},
        {'id': 'C', 'capacity': 60, 'accessibility': 1, 'road_capacity': 60, 'resource_capacity': 60, 'exposure_weight': .3},
    ]}, 'algorithm': algorithm, 'seed': 23, 'population': 12, 'iterations': 15}


@pytest.mark.parametrize('algorithm', ['ga', 'pso'])
def test_feasible_reproducible_improves_baseline(algorithm):
    p = payload(algorithm); before = deepcopy(p)
    a, b = optimize(p), optimize(p)
    assert p == before
    assert a['allocations'] == b['allocations'] and a['convergence'] == b['convergence']
    assert a['candidate']['objective'] <= a['baseline']['objective'] + 1e-12
    assert sum(r['candidate'] for r in a['allocations']) == pytest.approx(120)
    assert all(0 <= r['candidate'] <= r['effective_capacity'] + 1e-8 for r in a['allocations'])
    assert all(x >= y - 1e-12 for x, y in zip(a['convergence'], a['convergence'][1:]))
    assert not a['globally_optimal']


def test_objective_independent_arithmetic_and_effective_constraints():
    problem = parse_problem(payload()['problem'])
    assert problem.capacity.tolist() == [60, 72, 60]
    x = np.array([.5, .25, .25])
    expected = .7 * (.5*.1 + .25*.8 + .25*.3) + .3 * (60**2/60 + 30**2/72 + 30**2/60)/120
    assert scores(problem, x)['objective'] == pytest.approx(expected)


@pytest.mark.parametrize('algorithm', ['ga', 'pso'])
def test_zero_demand_zero_capacity_and_closed_destination(algorithm):
    p = payload(algorithm)
    p['problem']['demand'] = 0
    for r in p['problem']['destinations']: r['capacity'] = 0
    result = optimize(p)
    assert result['candidate']['objective'] == 0
    assert all(r['candidate'] == 0 for r in result['allocations'])
    p = payload(algorithm); p['problem']['destinations'][0]['accessibility'] = 0
    assert optimize(p)['allocations'][0]['candidate'] == 0


@pytest.mark.parametrize('kind', ['overflow', 'missing', 'negative', 'nan', 'boolean', 'duplicate', 'tiny', 'extreme', 'unknown'])
def test_rejects_infeasible_and_invalid_inputs(kind):
    p = payload(); row = p['problem']['destinations'][0]
    if kind == 'overflow': p['problem']['demand'] = 1000
    elif kind == 'missing': del row['road_capacity']
    elif kind == 'negative': row['capacity'] = -1
    elif kind == 'nan': row['capacity'] = float('nan')
    elif kind == 'boolean': p['seed'] = True
    elif kind == 'duplicate': p['problem']['destinations'][1]['id'] = 'A'
    elif kind == 'tiny': row['capacity'] = 1e-100
    elif kind == 'extreme': p['population'] = 100000
    elif kind == 'unknown': p['algorithm'] = 'fake'
    with pytest.raises(ValueError): optimize(p)


def test_projection_random_feasibility_and_all_capacity_boundary():
    rng = np.random.default_rng(8)
    for _ in range(50):
        caps = rng.uniform(0, 1, 6); total = rng.uniform(0, caps.sum())
        result = project(rng.normal(size=6), caps, total)
        assert result.sum() == pytest.approx(total, abs=1e-9)
        assert (result >= 0).all() and (result <= caps + 1e-12).all()
    caps = np.array([.1, .5, 0])
    assert project([5, -1, 6], caps, .6).tolist() == pytest.approx(caps.tolist())


@pytest.mark.parametrize('algorithm', ['ga', 'pso'])
def test_single_destination_and_large_numeric_inputs(algorithm):
    p = payload(algorithm)
    p['problem']['destinations'] = [p['problem']['destinations'][0]]
    p['problem']['demand'] = 60
    assert optimize(p)['allocations'][0]['candidate'] == pytest.approx(60)
    p['problem']['demand'] = 1e9
    p['problem']['destinations'][0].update(capacity=1e9, accessibility=1, road_capacity=1e9, resource_capacity=1e9)
    assert optimize(p)['conservation_error'] < 1e-6
