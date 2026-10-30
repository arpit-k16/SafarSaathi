"""Extract published visit indicators and align national environmental context, with no invented stress labels."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from safarsaathi_ml.india_data import worldbank_series,verified_source,EXTERNAL
from safarsaathi_ml.pipeline import sha256,utc_now

project=Path(__file__).resolve().parents[1]
cache=project/'data/interim/india_pdf_audit_20261025/India Tourism Data Compendium 2025_1.json'
source=json.loads(cache.read_text());pages={p['pdf_page']:p['text'] for p in source['pages']}
names=['Chandigarh','Delhi','Haryana','Himachal Pradesh','Jammu and Kashmir','Ladakh','Punjab','Rajasthan','Uttar Pradesh','Uttarakhand','Andaman and Nicobar Islands','Bihar','Jharkhand','Odisha','West Bengal','Arunachal Pradesh','Assam','Manipur','Meghalaya','Mizoram','Nagaland','Sikkim','Tripura','Chhattisgarh','Goa','Gujarat','Madhya Pradesh','Maharashtra','Dadra and Nagar Haveli and Daman and Diu','Andhra Pradesh','Karnataka','Kerala','Lakshadweep','Puducherry','Tamil Nadu','Telangana']
revised={6,10,16,20,29};estimated={2,28}
state=[]
pattern=r'^\s*(\d{1,2})\s+([^\d\n]+?)\s+'+r'\s+'.join([r'(-?\d+\.\d+)']*8)+r'\s*$'
seen=set()
for page in [213,214]:
    for match in re.finditer(pattern,pages[page],re.M):
        index=int(match[1]);seen.add(index);values=[float(match[i]) for i in range(3,11)]
        if not 1<=index<=36 or min(values[:4])<0:raise ValueError('Invalid source-table row.')
        for year,domestic,foreign in [(2023,values[0],values[1]),(2024,values[2],values[3])]:
            state.append({'geography':names[index-1],'year':year,'domestic_visits_million':domestic,'foreign_visits_million':foreign,'source_quality':'publisher_estimated_using_national_growth' if year==2024 and index in estimated else 'publisher_revised' if year==2023 and index in revised else 'reported_rounded_state_return','source_pdf_page':page,'source_table':'4.1.2','source_row':index,'environment_context':None})
if seen!=set(range(1,37)) or len(state)!=72:raise ValueError('Did not extract exactly 36 State/UT rows per year.')
# Rounded state values reconcile within a conservative sum-of-rounding tolerance, not to false exact counts.
for year,domestic,foreign in [(2023,2508.818,19.241),(2024,2948.191,20.942)]:
    selected=[r for r in state if r['year']==year]
    if abs(sum(r['domestic_visits_million'] for r in selected)-domestic)>.02 or abs(sum(r['foreign_visits_million'] for r in selected)-foreign)>.02:raise ValueError('State-table rounded totals do not reconcile.')
annual=[]
for match in re.finditer(r'^(20(?:1\d|2[0-4]))\s+[^\d\n]*?(\d{8,10})\s+(\d{6,9})\s+',pages[211],re.M):
    annual.append({'geography':'IND','year':int(match[1]),'domestic_visits':int(match[2]),'foreign_visits':int(match[3]),'source_quality':'published_national_compilation_including_estimates','source_pdf_page':211,'source_table':'4.1.1'})
if sorted(r['year'] for r in annual)!=list(range(2011,2025)):raise ValueError('National annual visit coverage is incomplete.')
environment={};manifests=[]
for code in ['EN.ATM.PM25.MC.M3','ER.H2O.FWST.ZS','AG.SRF.TOTL.K2']:
    path=project/EXTERNAL/'destination_stress'/(code+'.json');manifests.append(verified_source(path))
    series=worldbank_series(json.loads(path.read_text()),code)
    environment[code]={int(row.date):None if row.value!=row.value else float(row.value) for row in series.itertuples()}
for row in annual:
    year=row['year'];area=environment['AG.SRF.TOTL.K2'].get(year)
    if area is not None and area<=0:raise ValueError('Area denominator must be positive.')
    row['surface_area_km2']=area
    row['domestic_visits_per_surface_km2']=row['domestic_visits']/area if area is not None else None
    row['pm25_exposure_ug_m3']=environment['EN.ATM.PM25.MC.M3'].get(year)
    row['water_stress_percent']=environment['ER.H2O.FWST.ZS'].get(year)
records=annual+state
for row in records:
    previous=next((r for r in records if r['geography']==row['geography'] and r['year']==row['year']-1),None)
    field='domestic_visits' if row['geography']=='IND' else 'domestic_visits_million'
    row['domestic_visit_growth_percent']=100*(row[field]/previous[field]-1) if previous and previous[field]>0 else None
report={'schema_version':1,'generated_at':utc_now(),'status':'DERIVED_INDICATOR_NOT_A_TRAINED_MODEL','geographies':['IND']+names,'years':list(range(2011,2025)),'records':records,
 'formulae':{'national_visit_intensity':'Domestic tourist visits / same-year reported national surface area (km²). Repeated visits are counted; not simultaneous visitor density or carrying capacity.','growth':'100*(current reported domestic visits / previous reported domestic visits - 1); missing or zero denominator => null.'},
 'missing_data_rule':'No interpolation or carry-forward. State environmental indicators and capacity denominators are unavailable and remain null. Source-estimated tourism returns stay flagged, not treated as direct measurements.',
 'source_manifests':manifests+[{'source':source['source'],'sha256':source['sha256'],'publisher':'Ministry of Tourism / State-UT Tourism Departments; national compilation includes estimation.','pages':[211,213,214],'access_terms':'Existing official local publication; source PDF not redistributed in release. No new license assigned.','transformations':['Extracted numeric tables with printed million units retained.','Jammu & Pradesh printed typo canonicalized to Jammu and Kashmir by row identity; no numeric change.','Validated 36 rows/year and rounded national totals.','Explicitly retained 2024 Delhi/Maharashtra estimation flags and 2023 revision flags.']}],
 'limitations':['Historical indicators, not predictions and not a trained destination-stress model.','No occupancy, occupied/available accommodation capacity, crowd density or ecological carrying-capacity labels exist in this panel.','PM2.5 is modeled national population-weighted exposure; water stress is FAO national freshwater withdrawal/resource context. Neither isolates tourism impacts.','Environmental indicators are national only: no allocation to individual states or destinations, and no causal tourism-pollution claim.','Visits may repeat persons, source totals include estimates and revisions, and rounded state units differ from exact printed national totals.','Only two state-year observations per state/UT here; insufficient temporal coverage for a supervised destination-pressure model.']}
out=project/'outputs/indicators/india_environment_tourism';out.mkdir(parents=True,exist_ok=True)
with (out/'indicators.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2,allow_nan=False)
with (out/'integrity.json').open('x',encoding='utf-8') as f:json.dump({'sha256':sha256(out/'indicators.json')},f)
print(json.dumps({'national_rows':len(annual),'state_rows':len(state),'state_count':36,'environment_nonmissing':{code:sum(v is not None for v in values.values()) for code,values in environment.items()}},indent=2))
