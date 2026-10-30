"""Bounded remote ZIP metadata inspection within the approved dataset download."""
import io
import json
from pathlib import Path
from urllib.request import Request,urlopen
import zipfile


class RangeFile(io.RawIOBase):
    def __init__(self,url,size):self.url=url;self.size=size;self.position=0;self.bytes_read=0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        return self.position
    def read(self,size=-1):
        size=min(size if size>=0 else self.size-self.position,self.size-self.position)
        if size==0:return b''
        if size>16*1024*1024:raise ValueError('Metadata range exceeds bounded inspection limit.')
        start=self.position;end=start+size-1
        with urlopen(Request(self.url,headers={'Range':f'bytes={start}-{end}','User-Agent':'SafarSaathi bounded approved dataset inspection'}),timeout=60) as response:
            if response.status!=206:raise ValueError('Range not honored')
            result=response.read(size)
        if len(result)!=size:raise ValueError('Truncated metadata range')
        self.position+=len(result);self.bytes_read+=len(result)
        return result


def main():
    directory=Path('data/external/sturm_flood/12748983')
    metadata=json.loads((directory/'zenodo_record_12748983.json').read_text())
    entry=metadata['files'][0];reader=RangeFile(entry['links']['self'],entry['size'])
    with zipfile.ZipFile(reader) as archive:
        files=[{'path':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size} for i in archive.infolist()]
        output=directory/'archive_inventory.json'
        if not output.exists():output.write_text(json.dumps(files,indent=2),encoding='utf-8')
        for item in archive.infolist():
            if item.filename.endswith('.csv') and item.file_size<15_000_000:
                name=directory/Path(item.filename).name
                if not name.exists():name.write_bytes(archive.read(item))
                print(item.filename,item.file_size,flush=True)
    print('Archive entries',len(files),'remote metadata bytes',reader.bytes_read,flush=True)
    print(files[:8],flush=True)


if __name__=='__main__':main()
