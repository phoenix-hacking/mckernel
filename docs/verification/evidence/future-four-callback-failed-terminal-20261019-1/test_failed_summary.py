from pathlib import Path
import hashlib,json,types
F=Path(__file__).resolve().parent;p=F/'readback_observer.py';m=types.ModuleType('summary');m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__)
pairs=json.loads((F/'retained-production-objects/retained-objects.json').read_bytes());rows=[pair[key] for pair in pairs for key in ('original','retained')]
observation=dict(selected_files=[],inventories={},mount={},root_lock={},target={},client_ledger=[],request_lease_absent=True)
raw=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')).encode()+b'\n'
draft=dict(status='NOT_RELEASED',observation=observation);result=dict(status='PASS_READ_ONLY_OBSERVATION_ONLY',nonce=m.NONCE,cleanup_executed=False,observation_sha256=hashlib.sha256(raw(observation)).hexdigest(),cleanup_release_draft_sha256=hashlib.sha256(raw(draft)).hexdigest())
values={'observer-result.json':result,'observation.json':observation,'cleanup-release-draft.json':draft,'new-object-metadata.json':dict(objects=rows),'ownership.json':dict(nonce=m.NONCE)}
s=m.summarize({k:(raw(v),v) for k,v in values.items()});assert s['cleanup_draft']['observation_canonical_sha256']==hashlib.sha256(raw(observation)[:-1]).hexdigest();assert s['new_object_metadata']['objects']==rows and len(rows)==2*len(pairs)==22
print(json.dumps(dict(status='PASS_AFFECTED_SUMMARY_CONSUMER_ONLY',checks=2,metadata_rows=len(rows),cleanup_executed=False)))
