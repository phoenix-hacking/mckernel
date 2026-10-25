"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation only: bind one genuine fetched-overlay object and repin unchanged transport.
"""
from pathlib import Path
import ast,hashlib,json,sys
s=Path(__file__).resolve().parent
# The only arguments are the actual root-produced fetched-overlay record and its exact hash.
assert len(sys.argv)==3
p=Path(sys.argv[1]);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==sys.argv[2]
v=json.loads(raw)
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def assign(t,k,value):
 ns=[n for n in ast.parse(t).body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id==k for x in n.targets)];assert len(ns)==1
 n=ns[0];ls=t.splitlines(True);ls[n.lineno-1:n.end_lineno]=[k+' = '+repr(value)+'\n'];o=''.join(ls);ast.parse(o);return o

def units(t):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(t).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def emit(n,t,old):
 ast.parse(t);assert units(t)==units(old)
 out=s/n
 with out.open('x') as f:f.write(t)
 return ref(out)
old=(s/'fill_BFD_C_C_current_review_payload.SOURCE25-FETCH-BOUND.OVERLAY-PENDING.py').read_text()
n=next(n for n in ast.parse(old).body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='COHORT_AUTHORITY' for x in n.targets));c=ast.literal_eval(n.value)
spec=json.loads((s/'EXACT-SEVENTEEN-C_C-SOURCE25-CURRENT-TRANSPORT-OVERLAY.json').read_bytes())
assert v['status']=='PASS_FETCHED_BFD_C_C_CURRENT_TRANSPORT_OVERLAY' and v['source_proof']==c['fetched_source_proof']
for k in ('current_independent_acceptance','query_source','query_inputs','member_count','retirement_members'):assert v[k]==spec[k]
assert v['commit']==v['fetched_commit'] and len(v['published_members'])==17
assert isinstance(v['published_members'],dict) and set(v['published_members'])==set(spec['files'])
for name,row in v['published_members'].items():
 assert set(row)=={'path','bytes','sha256'} and row['path']==str(Path(spec['destination'])/name)
 assert row['bytes']==spec['files'][name]['bytes'] and row['sha256']==spec['files'][name]['sha256']
 assert ref(Path(row['path']))==row
c['overlay_fetched_proof']=ref(p);c['overlay_fetched_expected']=v
fr=emit('fill_BFD_C_C_current_review_payload.OVERLAY-FETCH-BOUND.NOT-RELEASED.py',assign(old,'COHORT_AUTHORITY',c),old)
old=(s/'direct_query_postjoin_prepare.C_C_SOURCE25-FETCH-BOUND.OVERLAY-PENDING.py').read_text();t=old
for k,val in dict(FILL_REF=fr,FETCH_SHA=c['fetched_source_proof']['sha256'],APPROVAL_SHA=c['source_approval']['sha256']).items():t=assign(t,k,val)
chain=emit('direct_query_postjoin_prepare.C_C_SOURCE25-OVERLAY-FETCH-BOUND.NOT-RELEASED.py',t,old)
old=(s/'publish_reviewed_release_then_exec_owner.C_C_PENDING-SOURCE.py').read_text();same=emit('publish_reviewed_release_then_exec_owner.C_C_SOURCE25-OVERLAY-FETCH-BOUND.NOT-RELEASED.py',assign(old,'FILL_REF',fr),old)
outer=['/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--']
ready=dict(scope=__doc__,status='SOURCE_READY_NO_EXECUTION_GRANT',fill=fr,chain=chain,samePID=same,overlay_proof=ref(p),source_approval=c['source_approval'],source_proof=c['fetched_source_proof'],query=spec['query_source'],query_inputs=spec['query_inputs'],function_class_AST_unchanged=True,whole_sources_AST_parse=True,query_argv=outer+['/home/holden/anaconda3/bin/python3','-I','-B',chain['path'],chain['sha256']],samePID_argv_template=outer+['/home/holden/anaconda3/bin/python3','-I','-B',same['path'],'--actual-review','FUTURE_GENUINE_EXECUTION_REVIEW_PATH','FUTURE_GENUINE_EXECUTION_REVIEW_SHA256',same['sha256']])
out=s/'READY.C_C-FROZEN-PRECLOCK-TRANSPORT.SOURCE-ONLY.json'
with out.open('x') as f:json.dump(ready,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(dict(ready=ref(out),**ready),sort_keys=True))
