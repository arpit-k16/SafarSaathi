"""Read-only baseline and official PDF discovery for the India completion work."""
import hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone
from pypdf import PdfReader

project=Path(__file__).resolve().parents[1]
release=project/'release/india_scope_20261025_03'
release.mkdir(exist_ok=True)
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
snapshot=release/'initial_state.json'
if not snapshot.exists():
    protected={}
    for root in [project/'models',*[p for p in (project/'release').iterdir() if p!=release]]:
        for p in ([root] if root.is_file() else root.rglob('*')):
            if p.is_file():protected[p.relative_to(project).as_posix()]=digest(p)
    raw=project.parent/'SafarSaathi_Datasets/raw'
    raw_stats={p.relative_to(raw).as_posix():{'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in raw.rglob('*') if p.is_file()}
    old=json.loads((project/'release/final_working_20261025_02/initial_state.json').read_text())
    with snapshot.open('x',encoding='utf-8') as f:json.dump({'created_at':datetime.now(timezone.utc).isoformat(),'protected_sha256':protected,'raw_stats':raw_stats,'registry':json.loads((project/'models/registry.json').read_text()),'legacy_protected_sha256':{k:v for k,v in old['protected_sha256'].items() if 'trash' in k.split('/')}},f,indent=2)
    print('Protected files',len(protected),'raw files',len(raw_stats),flush=True)
cache=project/'data/interim/india_pdf_audit_20261025'
cache.mkdir(exist_ok=True)
for name in ['India Tourism Data Compendium 2025_1.pdf','India Tourism Data Compendium 2024.pdf','India Tourism Statistics 2023-English (1).pdf','INDIA TOURISM STATISTICS 2022 (master-tourism.digifootprint.gov.in).pdf']:
    output=cache/(Path(name).stem+'.json')
    if output.exists():continue
    path=project.parent/'SafarSaathi_Datasets/raw/tourism_india'/name
    reader=PdfReader(path);pages=[]
    for i,page in enumerate(reader.pages):
        text=page.extract_text() or ''
        if re.search(r'state.{0,25}(?:wise|UT)|occupancy|pollution|carrying capacity|water consumption',text,re.I):pages.append({'pdf_page':i+1,'text':text})
    with output.open('x',encoding='utf-8') as f:json.dump({'source':str(path),'sha256':digest(path),'pages':pages},f,indent=2)
    print(name,[(p['pdf_page'],p['text'][:70].replace('\n',' ')) for p in pages],flush=True)
