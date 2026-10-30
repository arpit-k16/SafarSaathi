"""Source-backed historical indicators, intentionally outside the trained model registry."""
import json
from .pipeline import sha256

def load_indicators(project):
    root=project/'outputs/indicators/india_environment_tourism'
    checksum=json.loads((root/'integrity.json').read_text())['sha256']
    if sha256(root/'indicators.json')!=checksum:raise ValueError('Indicator checksum validation failed.')
    data=json.loads((root/'indicators.json').read_text(encoding='utf-8'))
    if data.get('status')!='DERIVED_INDICATOR_NOT_A_TRAINED_MODEL' or not data.get('records'):raise ValueError('Invalid indicator snapshot.')
    return data

def indicators(project,payload):
    if not isinstance(payload,dict) or set(payload)!={'geography','year'} or not isinstance(payload.get('geography'),str) or type(payload.get('year')) is not int:raise ValueError('Expected supported geography and integer year only.')
    data=load_indicators(project)
    selected=next((r for r in data['records'] if r['geography']==payload['geography'] and r['year']==payload['year']),None)
    if selected is None:raise ValueError('No observed indicator record for this geography/year. National: 2011–2024; State/UT: 2023–2024.')
    return {'status':data['status'],'observation':selected,'formulae':data['formulae'],'missing_data_rule':data['missing_data_rule'],'limitations':data['limitations'],'prediction':False,'trained_model':False}
