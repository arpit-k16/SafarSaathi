"""Resume the explicitly approved archive with eight bounded HTTP range readers."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from urllib.request import Request, urlopen


def main():
    directory=Path('data/external/sturm_flood/12748983').resolve()
    record=json.loads((directory/'zenodo_record_12748983.json').read_text(encoding='utf-8'))
    entry=next(f for f in record['files'] if f['key']=='Dataset.zip');size=entry['size']
    partial=directory/'Dataset.zip.part';state_path=directory/'range_resume_state.json';archive=directory/'Dataset.zip'
    if archive.exists():print('Completed archive preserved.');return
    if state_path.exists():state=json.loads(state_path.read_text())
    else:
        prefix=partial.stat().st_size if partial.exists() else 0
        state={'prefix_bytes':prefix,'size':size,'chunk_bytes':64*1024*1024,'completed':[]}
        state_path.write_text(json.dumps(state),encoding='utf-8')
        with partial.open('r+b' if partial.exists() else 'xb') as handle:handle.truncate(size)
    lock=threading.Lock();chunk=state['chunk_bytes'];prefix=state['prefix_bytes']
    ranges=[(i,start,min(start+chunk,size)-1) for i,start in enumerate(range(prefix,size,chunk)) if i not in state['completed']]
    def fetch(item):
        index,start,end=item
        for attempt in range(3):
            try:
                request=Request(entry['links']['self'],headers={'Range':f'bytes={start}-{end}','User-Agent':'SafarSaathi approved research download'})
                with urlopen(request,timeout=90) as response:
                    if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':raise ValueError('Range mismatch')
                    count=0
                    with partial.open('r+b') as output:
                        output.seek(start)
                        while block:=response.read(min(1024*1024,end-start+1-count)):
                            output.write(block);count+=len(block)
                            if count==end-start+1:break
                    if count!=end-start+1:raise ValueError('Truncated range')
                with lock:
                    state['completed'].append(index)
                    temporary=state_path.with_suffix('.tmp');temporary.write_text(json.dumps(state),encoding='utf-8');os.replace(temporary,state_path)
                    print(f'Completed range {index}: {start}-{end}; {len(state["completed"])} chunks complete',flush=True)
                return
            except Exception:
                if attempt==2:raise
                time.sleep(2*(attempt+1))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for result in as_completed([pool.submit(fetch,item) for item in ranges]):result.result()
    md5,strong=hashlib.md5(),hashlib.sha256()
    with partial.open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):md5.update(block);strong.update(block)
    if f'md5:{md5.hexdigest()}'!=entry['checksum']:raise ValueError('Final publisher checksum mismatch; untrusted archive retained.')
    partial.rename(archive)
    (directory/'download_verification.json').write_text(json.dumps({'source':'https://zenodo.org/records/12748983','bytes':size,'md5':md5.hexdigest(),
        'sha256':strong.hexdigest(),'publisher_checksum_matched':True,'license':record['metadata']['license'],
        'approval':'User explicitly approved this approximately 4 GB archive; no weights downloaded.','storage':'Archive streamed in place; full extraction disabled.'},indent=2),encoding='utf-8')
    print('Full publisher checksum PASS',flush=True)


if __name__=='__main__':main()
