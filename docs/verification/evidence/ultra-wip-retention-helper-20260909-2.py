from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,os,shutil,tarfile,sys
assert os.getuid()==1000 and os.sched_getaffinity(0)=={2,3,4,5}
work=Path('/work');out=work/('ultra-wip-retained-20260909-'+sys.argv[1]);out.mkdir()
record=dict(status='RUNNING',started_utc=datetime.now(timezone.utc).isoformat(),application_handoff_ready=False,scope='WIP prerequisite review/source checkpoint; native module build, controlled protocols and container references passed; no current guest image/runtime acceptance',artifacts=[],captures=[])
def identity(p):
 data=p.read_bytes();return dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())
try:
 for n,expected in [('native-ultra-module-20260909-1','PASS'),('native-signal-abi-protocol-20260909-1','FAIL'),('native-signal-abi-protocol-20260909-2','FAIL'),('native-signal-abi-protocol-20260909-3','PASS'),('ultra-futex-clone-protocol-20260909-native-1','FAIL'),('ultra-futex-clone-protocol-20260909-native-2','PASS'),('ultra-futex-clone-protocol-20260909-compat-1','PASS'),('native-fault-protocol-20260909-1','PASS'),('ultra-test-plan-protocol-20260909-1','PASS')]:
  src=work/n;state=json.loads((src/'record.json').read_text());assert state['status']==expected
  dest=out/(n+'.tar.gz')
  with dest.open('xb') as raw:
   with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as gz:
    with tarfile.open(fileobj=gz,mode='w') as tar:tar.add(src,arcname=n)
  seen=set()
  with tarfile.open(dest,'r:gz') as tar:
   for member in tar.getmembers():
    relative=Path(member.name).relative_to(n);current=src/relative;seen.add(str(relative))
    if member.isdir(): assert current.is_dir()
    elif member.issym(): assert current.is_symlink() and os.readlink(current)==member.linkname
    else:
     assert (member.isfile() or member.islnk()) and current.is_file(),member.name
     assert tar.extractfile(member).read()==current.read_bytes(),member.name
  expected_paths={'.'}|{str(p.relative_to(src)) for p in src.rglob('*')};assert seen==expected_paths
  record['captures'].append(dict(path=str(src),status=expected,record=identity(src/'record.json')))
  record['artifacts'].append(dict(path='docs/verification/evidence/'+dest.name,**identity(dest)))
 helper=out/'ultra-wip-retention-helper-20260909-2.py';shutil.copyfile(__file__,helper)
 record['artifacts'].append(dict(path='docs/verification/evidence/'+helper.name,**identity(helper)))
 record['status']='PASS'
except BaseException as e:record.update(status='FAIL',error=str(e));raise
finally:
 record['finished_utc']=datetime.now(timezone.utc).isoformat();(out/'ultra-wip-checkpoint-20260909-2.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');print(record['status'],out,flush=True)
