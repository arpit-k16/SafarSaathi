"""Fixtures validate contracts only; real-source training evidence is kept in versioned model reports."""
import json,shutil,threading
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import numpy as np,pandas as pd,pytest
from safarsaathi_ml.india_data import cyclone_calendar,worldbank_series,validate_series,verified_source
from safarsaathi_ml.scoped_forecasts import compare,train_scoped,load_scoped,evaluate_scoped,predict_scoped,SPECS
from safarsaathi_ml.pressure_indicators import indicators,load_indicators
from safarsaathi_ml.pipeline import sha256
from safarsaathi_ml.config import settings
from safarsaathi_ml.artifacts import ArtifactUnavailable
from safarsaathi_ml.http_api import Handler,ThreadingHTTPServer
from safarsaathi_ml.capabilities import capabilities

def test_archive_counting_deduplicates_storms_and_does_not_manufacture_binary_labels():
    rows=[['a','1979-12-30','NI','TS','main'],['a','1980-01-01','NI','TS','main'],['b','1980-02-01','WP','TS','main'],['b','1980-03-01','NI','TS','main'],['b','1980-03-02','NI','TS','main'],['c','1980-03-01','NI','TS','PROVISIONAL'],['d','1980-03-01','NI','NR','main']]
    frame=pd.DataFrame(rows,columns=['SID','ISO_TIME','BASIN','NATURE','TRACK_TYPE'])
    calendar,events=cyclone_calendar(frame,'1980-01','1980-04')
    assert calendar.value.tolist()==[0,0,1,0]
    assert events.event_id.tolist()==['b']
    assert set(calendar)=={'date','value'} and 'verified_no_event' not in calendar

@pytest.mark.parametrize('fault',['missing_column','bad_date','missing_sid'])
def test_archive_schema_rejects_incomplete_rows(fault):
    frame=pd.DataFrame([{'SID':'a','ISO_TIME':'2000-01-01','BASIN':'NI','NATURE':'TS','TRACK_TYPE':'main'}])
    if fault=='missing_column':frame=frame.drop(columns='NATURE')
    elif fault=='bad_date':frame.loc[0,'ISO_TIME']='not-a-date'
    else:frame.loc[0,'SID']=None
    with pytest.raises(ValueError):cyclone_calendar(frame)

@pytest.mark.parametrize('kind',['cyclone_count','pm25'])
def test_chronological_selection_and_first_test_prediction_do_not_use_future_targets(kind):
    dates=pd.period_range('1980-01','2024-12',freq='M').astype(str) if kind=='cyclone_count' else [str(y) for y in range(1990,2024)]
    values=np.arange(len(dates))%4 if kind=='cyclone_count' else 40+np.sin(np.arange(len(dates)))
    frame=pd.DataFrame({'date':dates,'value':values});before=compare(frame,kind)
    changed=frame.copy();changed.loc[changed.date>SPECS[kind]['validation_end'],'value']+=100
    after=compare(changed,kind)
    assert before['selected_method']==after['selected_method']
    for method in before['methods']:
        assert before['methods'][method]['validation']==after['methods'][method]['validation']
        assert before['predictions'][method]['test'][0]['prediction']==after['predictions'][method]['test'][0]['prediction']

@pytest.mark.parametrize('dates,values',[(['2000','2002'],[1,2]),(['2000','2000'],[1,2]),(['2000','2001'],[1,np.nan]),(['2000','2001'],[1,-1])])
def test_invalid_target_series_is_rejected(dates,values):
    with pytest.raises(ValueError):validate_series(pd.DataFrame({'date':dates,'value':values}),'annual')

def test_worldbank_rejects_other_geography_and_duplicates():
    row={'countryiso3code':'IND','indicator':{'id':'PM'},'date':'2000','value':1}
    with pytest.raises(ValueError):worldbank_series([{},[row,row]],'PM')
    row['countryiso3code']='USA'
    with pytest.raises(ValueError):worldbank_series([{},[row]],'PM')

def test_source_checksum_detects_changed_input(tmp_path):
    source=tmp_path/'source.json';source.write_text('{}')
    source.with_name(source.name+'.manifest.json').write_text(json.dumps({'sha256':sha256(source),'bytes':2}))
    verified_source(source);source.write_text('[]x')
    with pytest.raises(ValueError):verified_source(source)

def test_small_valid_fixture_training_reload_overwrite_refusal_and_corrupt_artifact(tmp_path):
    derived=tmp_path/'data/processed/india_scope_20261025';derived.mkdir(parents=True)
    models=tmp_path/'models';models.mkdir();(models/'registry.json').write_text('[]')
    frame=pd.DataFrame({'date':list(range(1990,2024)),'value':40+np.sin(np.arange(34))})
    path=derived/'pm25_annual.csv';frame.to_csv(path,index=False)
    (derived/'model_data_provenance.json').write_text(json.dumps({'files':{'pm25_annual.csv':sha256(path)},'pm25':{'fixture_only':True}}))
    entry=train_scoped(tmp_path,'pm25');assert evaluate_scoped(tmp_path,'pm25')['evaluation_reproduced']
    assert predict_scoped(tmp_path,'pm25',{'geography':'IND','horizon':1})['forecasts'][0]['date']=='2024'
    with pytest.raises(ValueError,match='no overwrite'):train_scoped(tmp_path,'pm25')
    (tmp_path/entry['artifact']).write_bytes(b'corrupt fixture')
    with pytest.raises(ArtifactUnavailable):load_scoped(tmp_path,'pm25')

def test_real_indicator_snapshot_preserves_missingness_estimates_and_registry_separation():
    project=settings().project_root;before=sha256(project/'models/registry.json')
    india=indicators(project,{'geography':'IND','year':2024})
    assert india['trained_model'] is False and india['prediction'] is False
    assert india['observation']['pm25_exposure_ug_m3'] is None
    assert india['observation']['water_stress_percent'] is None
    assert india['observation']['domestic_visits_per_surface_km2']>0
    assert indicators(project,{'geography':'Delhi','year':2024})['observation']['source_quality']=='publisher_estimated_using_national_growth'
    assert indicators(project,{'geography':'Uttarakhand','year':2023})['observation']['source_quality']=='publisher_revised'
    assert sha256(project/'models/registry.json')==before
    for payload in [{'geography':'Uttarakhand','year':2019},{'geography':'unknown','year':2024},{'geography':'IND','year':True},{'geography':'IND','year':2026},{'geography':'IND','year':2024,'path':'secret'}]:
        with pytest.raises(ValueError):indicators(project,payload)

def test_indicator_integrity_failure_is_rejected(tmp_path):
    folder=tmp_path/'outputs/indicators/india_environment_tourism';folder.mkdir(parents=True)
    (folder/'integrity.json').write_text(json.dumps({'sha256':'0'*64}));(folder/'indicators.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'):load_indicators(tmp_path)

def test_actual_scoped_http_and_unavailable_broad_models():
    status_map={item['model_id']:item['status'] for item in capabilities(settings().project_root)}
    assert status_map['flood_segmentation_model']=='EXPERIMENTAL'
    assert status_map['tourism_demand_forecaster']=='EXPERIMENTAL'
    assert status_map['disaster_risk_predictor']=='DATA_INSUFFICIENT'
    assert status_map['destination_stress_predictor']=='DATA_INSUFFICIENT'
    broad={item['model_id']:item for item in capabilities(settings().project_root)}
    assert broad['disaster_risk_predictor']['scoped_forecast']['status']=='EXPERIMENTAL'
    assert broad['destination_stress_predictor']['historical_indicators']['status']=='INDICATOR_ONLY'
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def call(path,payload):
        request=Request(f'http://127.0.0.1:{server.server_port}'+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try:response=urlopen(request,timeout=10)
        except HTTPError as exc:response=exc
        with response:return response.status,json.loads(response.read())
    try:
        for path,region in [('/disaster/cyclone-count','NI'),('/environment/pm25-forecast','IND')]:
            status,body=call(path,{'geography':region,'horizon':1});assert status==200 and np.isfinite(body['forecasts'][0]['prediction'])
            for payload in [{},{'geography':'district','horizon':1},{'geography':region,'horizon':True},{'geography':region,'horizon':99},{'geography':region,'horizon':1,'path':'private'}]:
                status,body=call(path,payload);assert status==422 and 'C:\\' not in str(body)
        assert call('/stress/indicators',{'geography':'IND','year':2024})[0]==200
        assert call('/stress/indicators',{'geography':'IND','year':2026})[0]==422
        assert call('/disaster/predict',{})[0]==503 and call('/stress/predict',{})[0]==503
    finally:server.shutdown();thread.join();server.server_close()
