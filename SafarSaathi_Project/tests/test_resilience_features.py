"""Digital twin, stress index, anomalies, hotspots, routing, explanations and release gate."""
import math
from http import HTTPStatus

import pytest

from safarsaathi_ml import resilience, routing
from safarsaathi_ml.config import settings
from safarsaathi_ml.resilience_api import get as rget, post as rpost

P = settings().project_root


def test_utdb_visits_are_complete_and_self_consistent():
    from safarsaathi_ml.utdb import DESTINATIONS, load_visits
    rows = load_visits(P)
    assert len(rows) == 28 * 25
    assert {r['year'] for r in rows} == set(range(2000, 2025))
    assert {r['id'] for r in rows} == {d for _, d in DESTINATIONS}
    assert all(r['indian'] + r['foreign'] == r['total'] for r in rows)
    ked = {r['year']: r['total'] for r in rows if r['id'] == 'kedarnath'}
    assert ked[2014] < 0.2 * ked[2012]  # the post-2013 collapse is in the data


def test_twin_state_labels_and_scenario():
    st = resilience.twin_state(P, {'year': 2024, 'scenario': {'demand_change_pct': 30}})
    base = st['baseline']
    assert len(base) == 28 and [r['rank'] for r in base] == list(range(1, 29))
    for r in base:
        assert 0 <= r['stress_index'] <= 1
        assert math.isclose(sum(c['contribution'] for c in r['contributions']), r['stress_index'], abs_tol=1e-3)
        assert r['index_status'] == 'derived' and r['field_status']['visitors'] == 'observed'
        lo, hi = r['rank_interval_90']; assert lo <= r['rank'] <= hi
    scen = {r['id']: r for r in st['scenario']['rows']}
    assert all(scen[r['id']]['stress_index'] >= r['stress_index'] - 1e-9 for r in base)  # more visitors never lowers stress
    assert all(r['index_status'] == 'simulated' for r in scen.values())
    assert st['sensitivity']['median_rho'] > 0.9


@pytest.mark.parametrize('payload', [{'year': 1990}, {'weights': {'nope': 1}}, {'weights': {'visitor_load': -1}},
                                     {'scenario': {'demand_change_pct': 900}}, {'extra': 1}, []])
def test_twin_rejects_bad_input(payload):
    with pytest.raises(ValueError):
        resilience.twin_state(P, payload)


def test_anomalies_find_known_events_and_beat_baseline_on_precision():
    a = resilience.anomalies(P)
    flagged = {(f['id'], f['year']) for f in a['visitor_anomalies']}
    assert ('kedarnath', 2014) in flagged
    e = a['evaluation']
    assert e['robust_z']['precision'] > e['baseline_50pct_change']['precision']
    assert len(a['series']['kedarnath']) == 25


def test_hotspots_beat_random_labels():
    for q in ({'method': 'dbscan'}, {'method': 'kmeans', 'k': '4'}):
        h = resilience.hotspots(P, q)
        assert h['evaluation']['silhouette'] > h['evaluation']['random_label_baseline']
        assert sum(len(c['members']) for c in h['clusters']) == 28
    with pytest.raises(ValueError):
        resilience.hotspots(P, {'method': 'magic'})


def test_routing_compares_routes_and_handles_closures():
    r = routing.route(P, {'from': 'rishikesh', 'to': 'kedarnath'})
    sp, ra = r['shortest_time'], r['risk_aware']
    assert 150 < sp['distance_km'] < 300 and sp['time_min'] > 0
    assert len(sp['geometry']) > 10
    closed = routing.route(P, {'from': 'rishikesh', 'to': 'kedarnath', 'closures': [{'near': 'rudraprayag', 'radius_km': 4}]})
    assert closed['closed_segments'] > 0 and closed['shortest_time']['distance_km'] > sp['distance_km']
    # risk-aware cost is never worse on exposure than the time-only route under the same closures
    assert closed['risk_aware']['exposure_km'] <= closed['shortest_time']['exposure_km'] + 1e-6
    cut = routing.route(P, {'from': 'haridwar', 'to': 'badrinath', 'closures': [{'near': 'joshimath', 'radius_km': 3}]})
    assert cut['status'] == 'NO_ROUTE'
    for bad in ({'from': 'x', 'to': 'kedarnath'}, {'from': 'rishikesh', 'to': 'rishikesh'},
                {'from': 'rishikesh', 'to': 'kedarnath', 'weights': {'alpha': 0}}):
        with pytest.raises(ValueError):
            routing.route(P, bad)


def test_http_adapter_routes():
    for path in ('/twin/metadata', '/anomalies', '/hotspots?year=2024', '/routing/metadata', '/release'):
        status, body = rget(P, path)
        assert status == HTTPStatus.OK and body
    status, body = rpost(P, '/twin/state', {'year': 2023})
    assert status == HTTPStatus.OK and body['year'] == 2023


def test_forecasts_carry_explanations():
    from safarsaathi_ml.forecasting import forecast
    from safarsaathi_ml.monthly_forecasting import forecast_monthly
    for res in (forecast(P, 'IND', 2), forecast_monthly(P, 'IND', 2)):
        ex = res['explanation']
        assert ex and ex['kind'] in {'rule', 'linear_contributions'} and ex['uncertainty']['held_out_MAE'] > 0


def test_release_gate_is_evidence_based():
    from safarsaathi_ml.release_gate import release
    r = release(P)
    assert r and r['passed'] == r['total'] == 6
    for m in r['models']:
        g = m['gates']
        assert g['G1_artifact_integrity'] and g['G3_limitations_documented']
        assert g['G2_beats_or_matches_naive_baseline']['passed']


def test_intervention_planner_finds_optimum_and_beats_doing_nothing():
    for alg in ('ga', 'pso'):
        o = resilience.interventions(P, {'budget': 100, 'algorithm': alg})
        plan, base = o['plan'], o['baselines']
        assert plan['feasible'] and plan['cost'] <= 100
        assert plan['objective'] <= base['do_nothing']['objective']
        assert plan['objective'] <= base['greedy_benefit_per_cost']['objective'] + 1e-9
        assert o['optimality_gap'] is not None and o['optimality_gap'] <= 1e-6
    zero = resilience.interventions(P, {'budget': 0})
    assert zero['plan']['cost'] == 0
    for bad in ({'budget': -1}, {'interventions': [{'type': 'shift', 'from': 'kedarnath', 'to': 'kedarnath', 'pct': 10, 'cost': 1}]},
                {'algorithm': 'magic'}, {'interventions': [{'type': 'cap', 'from': 'nowhere', 'pct': 10, 'cost': 1}]}):
        with pytest.raises(ValueError):
            resilience.interventions(P, bad)


def test_scoped_forecast_status_follows_release():
    from safarsaathi_ml.scoped_forecasts import predict_scoped, SPECS
    kind = next(iter(SPECS))
    spec = SPECS[kind]
    res = predict_scoped(P, kind, {'geography': spec['geography'], 'horizon': 1})
    assert res['quality_status'] == 'FINAL_V1'


def test_map_config_from_environment(monkeypatch):
    from fastapi.testclient import TestClient
    from safarsaathi_ml.asgi import app
    monkeypatch.setenv('SAFARSAATHI_CARTO_KEY', 'test-key')
    body = TestClient(app).get('/map-config.json').json()
    assert body == {'carto_key': 'test-key', 'carto_style': 'dark_all'}
