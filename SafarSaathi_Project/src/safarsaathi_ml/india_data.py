"""Strict source-derived contracts; archive zeros are not verified no-disaster labels."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .pipeline import sha256

EXTERNAL='data/external/india_scope_20261025'
DERIVED='data/processed/india_scope_20261025'

def verified_source(path):
    manifest=json.loads(path.with_name(path.name+'.manifest.json').read_text(encoding='utf-8'))
    if sha256(path)!=manifest['sha256'] or path.stat().st_size!=manifest['bytes']:raise ValueError('Source checksum mismatch.')
    return manifest

def cyclone_calendar(frame,start='1980-01',end='2024-12'):
    required={'SID','ISO_TIME','BASIN','NATURE','TRACK_TYPE'}
    if not required.issubset(frame):raise ValueError('Missing IBTrACS identity/time/type fields.')
    data=frame[list(required)].copy()
    for c in required:data[c]=data[c].astype('string').str.strip()
    if data.SID.isna().any() or data.ISO_TIME.isna().any():raise ValueError('Missing storm identity/time.')
    data['time']=pd.to_datetime(data.ISO_TIME,utc=True,errors='raise')
    # Basin files also contain out-of-basin points. Do not count them or provisional/spur tracks.
    eligible=data[(data.BASIN=='NI')&(data.NATURE=='TS')&(data.TRACK_TYPE=='main')]
    first=eligible.sort_values(['time','SID']).drop_duplicates('SID').copy()
    first['month']=first.time.dt.strftime('%Y-%m')
    first=first[first.month.between(start,end)].sort_values(['month','SID'])
    months=pd.period_range(start,end,freq='M').astype(str)
    # This is the number of eligible records in the declared archive calendar, not latent true disaster incidence.
    counts=first.groupby('month').size().reindex(months,fill_value=0)
    calendar=pd.DataFrame({'date':months,'value':counts.to_numpy(dtype=int)})
    if calendar.value.sum()!=len(first) or first.SID.duplicated().any():raise ValueError('Storm counting mismatch.')
    return calendar,first[['SID','month']].rename(columns={'SID':'event_id','month':'date'}).reset_index(drop=True)

def worldbank_series(payload,code):
    if not isinstance(payload,list) or len(payload)!=2 or not isinstance(payload[1],list):raise ValueError('Invalid World Bank response.')
    rows=[]
    for r in payload[1]:
        if r.get('countryiso3code')!='IND' or r.get('indicator',{}).get('id')!=code:raise ValueError('Wrong country or indicator.')
        if not str(r.get('date','')).isdigit() or len(str(r['date']))!=4:raise ValueError('Invalid annual date.')
        v=r.get('value')
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) or v<0):raise ValueError('Invalid observed indicator value.')
        rows.append({'date':str(r['date']),'value':v})
    result=pd.DataFrame(rows).sort_values('date').reset_index(drop=True)
    if result.empty or result.date.duplicated().any():raise ValueError('Empty/duplicate country-year records.')
    return result

def validate_series(frame,frequency):
    if set(frame)!={'date','value'} or frame.empty or frame.isna().any().any():raise ValueError('Complete date/value series required; no target imputation.')
    dates=frame.date.astype(str)
    freq='M' if frequency=='monthly' else 'Y'
    parsed=pd.PeriodIndex(dates,freq=freq)
    if len(parsed.unique())!=len(parsed) or list(parsed)!=list(pd.period_range(parsed[0],parsed[-1],freq=freq)):raise ValueError('Dates must be unique, chronological and contiguous.')
    values=pd.to_numeric(frame.value,errors='raise').to_numpy(float)
    if not np.isfinite(values).all() or np.any(values<0):raise ValueError('Finite nonnegative targets required.')
    if frequency=='monthly' and np.any(values%1):raise ValueError('Recorded event counts must be integers.')
    return values

def prepare_model_data(project):
    output=project/DERIVED;output.mkdir(parents=True,exist_ok=True)
    external=project/EXTERNAL
    cyclone=external/'disaster_risk/ibtracs.NI.list.v04r01.csv'
    provenance=verified_source(cyclone)
    raw=pd.read_csv(cyclone,skiprows=[1],usecols=['SID','ISO_TIME','BASIN','NATURE','TRACK_TYPE'],low_memory=False)
    calendar,events=cyclone_calendar(raw)
    pm=external/'destination_stress/PM25_India_1990_2023.json'
    pm_provenance=verified_source(pm)
    exposure=worldbank_series(json.loads(pm.read_text()),'EN.ATM.PM25.MC.M3')
    validate_series(calendar,'monthly');validate_series(exposure,'annual')
    for name,frame in [('cyclone_monthly.csv',calendar),('cyclone_events.csv',events),('pm25_annual.csv',exposure)]:
        with (output/name).open('x',encoding='utf-8',newline='') as f:frame.to_csv(f,index=False)
    report={'cyclone':{'source':provenance,'raw_rows':len(raw),'eligible_events':len(events),'calendar_rows':len(calendar),'zero_count_months':int(calendar.value.eq(0).sum()),'count_distribution':{str(k):int(v) for k,v in calendar.value.value_counts().sort_index().items()},'coverage':[calendar.date.iloc[0],calendar.date.iloc[-1]],'target':'Count of distinct MAIN SIDs with a North Indian basin tropical (NATURE=TS) record, assigned to their first such month. Includes tropical depressions; no wind threshold or landfall definition.','zeros':'Explicit zero eligible archived storm IDs in an included calendar month. Not verified absence of all cyclones/disasters.','excluded':'Pre-1980, 2025/2026 incomplete/provisional years, non-main tracks, non-NI positions, non-TS positions. First qualifying month determined before date filtering to avoid counting cross-year storms twice.','geography':'NI basin, not Indian political territory or district landfalls.'},
            'pm25':{'source':pm_provenance,'rows':len(exposure),'coverage':[exposure.date.iloc[0],exposure.date.iloc[-1]],'missing_targets':int(exposure.value.isna().sum()),'target':'National population-weighted modeled annual PM2.5 exposure','units':'micrograms/m³','measurement':'GBD/IHME modeled exposure republished by World Bank; not a raw sensor measurement or tourism-attribution label.'},
            'files':{n:sha256(output/n) for n in ['cyclone_monthly.csv','cyclone_events.csv','pm25_annual.csv']}}
    with (output/'model_data_provenance.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
    return report
