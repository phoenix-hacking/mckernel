"""Bind actual materialized-source identity only; root admission remains late."""
import pathlib,json,hashlib,stat
R=pathlib.Path(__file__).resolve().parent
receipt=json.loads((R/'materialization-receipt.json').read_text())
assert receipt['status']=='PASS_SOURCE_MATERIALIZATION_ONLY' and receipt['source']==str(R/'materialized-source')
source=R/'materialized-source';s=source.lstat();assert stat.S_ISDIR(s.st_mode) and source.resolve()==source
identity={'path':str(source),'dev':s.st_dev,'inode':s.st_ino,'mode':stat.S_IMODE(s.st_mode),'file_type':stat.S_IFMT(s.st_mode),'uid':s.st_uid,'gid':s.st_gid}
d=json.loads((R.parent/'image-request-UNMATERIALIZED-PROPOSAL.json').read_text());assert d['source_identity'] is None;d['source_identity']=identity;d['disk_identity']=dict(identity);d['source_root']=str(source);d['memory_allocation_roots'][0]=str(source)
# Compact ordinary JSON is the same accepted schema, under the enforced32MiB per-file limit.
payload=(json.dumps(d,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();assert len(payload)<33554432
p=R/'image-request-SOURCE-BOUND-PROPOSAL.json'
with p.open('xb') as stream:stream.write(payload)
report={'status':'ACTUAL_SOURCE_IDENTITY_BOUND_ROOT_ADMISSION_PENDING','source_identity':identity,'materialization_receipt_sha256':hashlib.sha256((R/'materialization-receipt.json').read_bytes()).hexdigest(),'request':{'path':str(p),'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)},'pending':['root fresh UUID/device/backup identities','root aggregate memory/disk/sole-heavy admission','publication/fetched proof and exact execution release'],'compiler_executed':False}
(R/'actual-source-identity-binding.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':report['status'],'request_bytes':len(payload),'compiler_executed':False}))
