from pathlib import Path
import hashlib,json,os
P=Path(__file__).resolve().parent
v=json.loads((P/'materialization-inputs.json').read_text())
def copy(src,dst,expected):
 src=Path(src);assert not src.is_symlink() and src.is_file();raw=src.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
 dst=Path(dst);dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 fd=os.open(dst,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert os.getuid()==os.geteuid()==1000
for d in [v['candidate'],v['inputs']]:assert not Path(d).exists()
for d in [v['candidate'],v['inputs']]:Path(d).mkdir(mode=0o700)
for d in ['modules','home','tmp']:Path(v['candidate'],d).mkdir(mode=0o700)
for row in v['module_sources']:copy(row['source'],str(Path(v['candidate'],'modules',row['relative'])),row['sha256'])
for row in v['input_files']:copy(row['source'],str(Path(v['inputs'],row['relative'])),row['sha256'])
print(json.dumps({'status':'MATERIALIZED_IHK_INPUTS_ONLY','module_sources':len(v['module_sources']),'input_files':len(v['input_files']),'build':False}))
