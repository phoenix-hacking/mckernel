import importlib.util,json
from pathlib import Path
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r',P/'readback_observer.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
ob=dict(selected_files=[dict(path='captured',sha256='0'*64)],inventories={'output':[dict(path='one')]},mount={},root_lock={},target={},client_ledger=[],request_lease_absent=True)
draft=dict(status='NOT_RELEASED',observation=ob)
data={n:None for n in r.NAMES}
for name,value in [('observation.json',ob),('cleanup-release-draft.json',draft),('new-object-metadata.json',{}),('ownership.json',dict(nonce=r.NONCE))]:data[name]=(r.canonical(value),value)
result=dict(status='PASS_READ_ONLY_OBSERVATION_ONLY',nonce=r.NONCE,cleanup_executed=False,observation_sha256=r.digest(data['observation.json'][0]),cleanup_release_draft_sha256=r.digest(data['cleanup-release-draft.json'][0]))
data['observer-result.json']=(r.canonical(result),result)
out=r.summarize(data);assert out['observation']['inventories']['output']['entries']==1 and 'observation' not in out['cleanup_draft'];assert len(r.canonical(out))<1<<20
cases=0
for key,value in [('nonce','wrong'),('cleanup_executed',True),('observation_sha256','bad'),('cleanup_release_draft_sha256','bad')]:
 old=result[key];result[key]=value
 try:r.summarize(data)
 except AssertionError:cases+=1
 else:raise AssertionError('bad result accepted '+key)
 result[key]=old
draft['status']='PASS_EXECUTION_RELEASE'
try:r.summarize(data)
except AssertionError:cases+=1
else:raise AssertionError('released cleanup accepted')
print(json.dumps(dict(status='PASS_FINITE_READBACK_FIXTURES',positive=1,refusals=cases,root_execution=False)))
