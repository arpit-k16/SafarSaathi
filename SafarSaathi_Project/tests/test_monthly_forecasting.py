"""Clearly synthetic unit fixtures; real training evidence lives in the versioned artifact."""
import json
import numpy as np
import pandas as pd
import pytest

from safarsaathi_ml.monthly_forecasting import METHODS, MonthlyForecaster, evaluate_monthly, forecast_monthly, monthly_features, train_monthly, validate_series
from safarsaathi_ml.pipeline import sha256


def test_monthly_schema_and_past_only_features():
    dates=pd.period_range('2019-01',periods=72,freq='M').astype(str)
    frame=pd.DataFrame({'destination':'IND','date':dates,'arrivals':np.arange(72)+100})
    observed,values=validate_series(frame)
    assert len(observed)==72
    for invalid in (frame.iloc[::-1],pd.concat([frame,frame.iloc[:1]]),frame.assign(arrivals=-1),frame.assign(destination='XX')):
        with pytest.raises(ValueError):validate_series(invalid)
    changed=values.copy();changed[36:]+=100000
    assert np.array_equal(monthly_features(values[:36]),monthly_features(changed[:36]))
    for method in METHODS:
        a=MonthlyForecaster(method).fit(values[:36]);b=MonthlyForecaster(method).fit(changed[:36])
        assert a.forecast(values[:36],6)==b.forecast(changed[:36],6)


@pytest.mark.parametrize('horizon',[None,True,0,7,'1',1.5])
def test_monthly_invalid_horizons(horizon):
    with pytest.raises(ValueError):MonthlyForecaster('persistence').fit(np.arange(36)+10).forecast(np.arange(36)+10,horizon)


def test_monthly_training_serialization_and_replay_on_fixture(tmp_path):
    derived=tmp_path/'fixture';derived.mkdir();(tmp_path/'models').mkdir()
    frame=pd.DataFrame({'destination':'IND','date':pd.period_range('2019-01',periods=72,freq='M').astype(str),'arrivals':np.arange(72)*10+1000})
    frame.to_csv(derived/'monthly_fta.csv',index=False)
    (derived/'provenance.json').write_text(json.dumps({'target':'SYNTHETIC UNIT TEST FIXTURE ONLY','derived_csv_sha256':sha256(derived/'monthly_fta.csv')}))
    entry=train_monthly(tmp_path,derived)
    assert entry['training_completed']
    assert evaluate_monthly(tmp_path)['evaluation_reproduced']
    result=forecast_monthly(tmp_path,'IND',3)
    assert result['latest_observed_date']=='2024-12'
    assert [r['date'] for r in result['forecasts']]==['2025-01','2025-02','2025-03']
    with pytest.raises(ValueError,match='already'):train_monthly(tmp_path,derived)


def test_real_monthly_inference_readonly():
    from safarsaathi_ml.config import settings
    from safarsaathi_ml.http_api import Handler,ThreadingHTTPServer
    import threading
    from urllib.request import Request,urlopen
    from urllib.error import HTTPError,URLError
    project=settings().project_root
    assert evaluate_monthly(project)['evaluation_reproduced']
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        request=Request(f'http://127.0.0.1:{server.server_port}/tourism/monthly-forecast',data=b'{"destination":"IND","horizon":3}',headers={'Content-Type':'application/json'})
        try:
            with urlopen(request) as response:
                result=json.loads(response.read());assert len(result['forecasts'])==3
        except URLError as exc:
            if getattr(exc.reason,'winerror',None)==10013:pytest.skip('Sandbox blocks HTTP; run outside sandbox.')
            raise
        with pytest.raises(HTTPError) as exc:
            urlopen(Request(request.full_url,data=b'{"destination":"IND","horizon":true}',headers={'Content-Type':'application/json'}))
        assert exc.value.code==422
    finally:server.shutdown();thread.join();server.server_close()
