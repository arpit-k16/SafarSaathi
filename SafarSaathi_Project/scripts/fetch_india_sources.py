"""Bounded public-source acquisition; immutable files with provenance, never original raw data."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen

def fetch(url,directory,name,terms,max_bytes):
    directory.mkdir(parents=True,exist_ok=True);target=directory/name
    if target.exists():raise ValueError('Refusing to overwrite source snapshot.')
    with urlopen(Request(url,headers={'User-Agent':'SafarSaathi research source validation'}),timeout=60) as response:
        size=int(response.headers.get('Content-Length','0'))
        if size>max_bytes:raise ValueError('Unexpectedly large response; approval required.')
        digest=hashlib.sha256();count=0
        with target.with_suffix(target.suffix+'.part').open('xb') as output:
            while block:=response.read(1024*1024):
                count+=len(block)
                if count>max_bytes:raise ValueError('Size bound exceeded; download stopped.')
                output.write(block);digest.update(block)
        if size and count!=size:raise ValueError('Truncated source.')
        target.with_suffix(target.suffix+'.part').rename(target)
        manifest={'source':url,'downloaded_at':datetime.now(timezone.utc).isoformat(),'original_filename':name,'bytes':count,'sha256':digest.hexdigest(),'license_access_terms':terms,'http_last_modified':response.headers.get('Last-Modified'),'transformation_history':['Unmodified public download; stored separately from original raw collection.']}
    with (directory/(name+'.manifest.json')).open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',choices=['ibtracs','ndem','environment']);a=p.parse_args()
    root=Path(__file__).resolve().parents[1]/'data/external/india_scope_20261025'
    if a.source=='ibtracs':fetch('https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv',root/'disaster_risk','ibtracs.NI.list.v04r01.csv','NOAA IBTrACS metadata: redistribution/use without restriction; cite Gahtan et al. 2024, DOI 10.25921/82ty-9e16 and Knapp et al. 2010. NOAA ERDDAP official license metadata verified.',35_000_000)
    elif a.source=='environment':
        for code in ['EN.ATM.PM25.MC.M3','ER.H2O.FWST.ZS','AG.SRF.TOTL.K2']:
            fetch(f'https://api.worldbank.org/v2/country/IND/indicator/{code}?format=json&date=2011:2024&per_page=100',root/'destination_stress',code+'.json','World Bank WDI: CC BY 4.0; retain underlying-source attribution and indicator metadata. Historical environmental context, not a tourism-attribution label.',100_000)
            fetch(f'https://api.worldbank.org/v2/indicator/{code}?format=json',root/'destination_stress',code+'.metadata.json','World Bank WDI indicator metadata and original-source definitions.',100_000)
    else:fetch('https://ndem.nrsc.gov.in/',root/'disaster_risk','ndem_public_index.html','Public landing-page inspection only; no protected layers or registration bypass.',100_000)
