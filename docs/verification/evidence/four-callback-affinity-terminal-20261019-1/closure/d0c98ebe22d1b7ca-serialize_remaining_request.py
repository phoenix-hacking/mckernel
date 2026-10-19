"""Case-specific ordinary preparation only; does not seed or launch anything."""
from pathlib import Path
import hashlib,json,os,sys
P=Path(__file__).resolve().parent
assert len(sys.argv)==3,'exact reviewed delta path and SHA required'
delta_path=Path(sys.argv[1]);raw=delta_path.read_bytes();assert hashlib.sha256(raw).hexdigest()==sys.argv[2]
d=json.loads(raw);base=Path(d['base_request']['path']);base_bytes=base.read_bytes();assert hashlib.sha256(base_bytes).hexdigest()==d['base_request']['sha256']
q=json.loads(base_bytes);assert d['status']=='DRAFT_REQUEST_DELTA_NOT_SERIALIZED_OR_EXECUTABLE'
for row in [d['owner_source'],*d['overrides']['remaining_image_seed'].values()]:
 p=Path(row['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'] and p.stat().st_size==row['bytes']
for key,value in d['overrides'].items():q[key]=value
work=Path(q['work_root']);evidence=Path(q['owner_evidence_root']);root=work.parent
assert root==P/'remaining-attempt-1' and evidence.parent==root and not os.path.lexists(root)
for path,floor in [('/home/holden',18524371627),('/home/holden/mckernel-work/scratch',13421772800)]:
 st=os.statvfs(path);assert st.f_bavail*st.f_frsize>=floor
root.mkdir(mode=0o700);work.mkdir(mode=0o700);evidence.mkdir(mode=0o700)
request=root/'image-request.json';temp=root/'image-request.json.tmp'
with temp.open('x') as out:json.dump(q,out,sort_keys=True,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
os.rename(temp,request);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
receipt={'status':'SERIALIZED_FRESH_REMAINING_REQUEST_ONLY','base_request':d['base_request'],'delta_sha256':sys.argv[2],'request':{'path':str(request),'sha256':hashlib.sha256(request.read_bytes()).hexdigest(),'bytes':request.stat().st_size},'work_root':str(work),'owner_evidence_root':str(evidence),'actual_seed':False,'compiler':False,'container':False}
with (root/'serialization-receipt.json').open('x') as out:json.dump(receipt,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps({'status':receipt['status'],'request':receipt['request'],'actual_seed':False}))
