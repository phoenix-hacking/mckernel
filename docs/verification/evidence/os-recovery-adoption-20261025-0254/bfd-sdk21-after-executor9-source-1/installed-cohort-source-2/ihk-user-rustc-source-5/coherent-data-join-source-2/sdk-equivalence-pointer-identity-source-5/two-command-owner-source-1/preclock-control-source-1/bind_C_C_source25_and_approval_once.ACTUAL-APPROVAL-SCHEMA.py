"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite two-command C/C source25 data binding; no query/root/Docker/SDK. Existing AST-only method.
"""
from pathlib import Path
import ast,json,hashlib,sys,re
s=Path(__file__).resolve().parent
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
assert len(sys.argv)==5
p=Path(sys.argv[1]);a=Path(sys.argv[3]);assert ref(p)['sha256']==sys.argv[2] and ref(a)['sha256']==sys.argv[4]
proof=json.loads(p.read_bytes());approval=json.loads(a.read_bytes());ready=json.loads((s/'READY.C_C_FULL_STATIC_TRANSPORT.CURRENT-HASH-CORRECTED.PENDING-SOURCE25.json').read_bytes())
c=s.parent;specpath=c/'EXACT-TWO-COMMAND-C-C-CONTROL-SOURCE25-SPEC.json';spec=json.loads(specpath.read_bytes());pub=json.loads((c/'source25-publication-1/ACTUAL-OVERLAY-PUBLICATION.json').read_bytes());maps=json.loads(Path(ready['runtime_source_map']['path']).read_bytes())
assert proof['status']=='PASS_ACTUAL_FETCHED_SOURCE' and proof['source_member_count']==25 and proof['source_spec']==ref(specpath) and proof['source_members']==spec['files'] and proof['published_members']==pub['published']
assert proof['commit']==proof['fetched_commit'] and re.fullmatch('[0-9a-f]{40}',proof['commit'])
assert proof['current_owner']==ready['owner'] and proof['current_request']==ready['request'] and proof['current_source_map']==ready['runtime_source_map']
assert approval['schema']=='mckernel.bfd.original-c-twice.owner-consumable-source-review.v1' and approval['decision']=='PASS_SOURCE' and approval['implementation_ownership'] is False and approval['reviewer']!='/root'
assert approval['source_sha256']==maps and approval['source_map_sha256']==ready['runtime_source_map']['sha256'] and approval['request_sha256']==ready['request']['sha256']
assert approval['ready_sha256']=='bdd9bc59cbe58fcd678845a8a21d02fb248c93a57c7d06dea4c20426b05885a7' and approval['original_oracle_unchanged'] is True
assert all(approval[k] is False for k in ['execution_authority','Rust_ABI_acceptance','SDK21_acceptance','native_acceptance','default_acceptance'])
for row in spec['files'].values():assert ref(Path(row['path']))==row
for key in ['query','fill','entry','chain','samePID','genuine_current_BFD_acceptance']:assert ref(Path(ready[key]['path']))==ready[key]
out=s/'admission-preparation-source25-bound-1';assert not out.exists();out.mkdir(mode=0o700)
qold=Path(ready['query']['path']).read_text();qt=assign(assign(qold,'STATIC_SOURCE_PROOF',ref(p)),'STATIC_SOURCE_APPROVAL',ref(a));assert units(qt)==units(qold)
qp=out/'run_root_sdk_readonly_admission.py';qp.write_text(qt);qr=ref(qp);ip=out/'QUERY-INPUTS.ROOT.json';ip.write_bytes(Path(ready['query_inputs']['path']).read_bytes());ir=ref(ip)
cohort=dict(author='/root',source_approval=ref(a),source_approval_expected=approval,fetched_source_proof=ref(p),fetched_source_expected=proof,overlay_fetched_proof=None,overlay_fetched_expected=None)
fold=Path(ready['fill']['path']).read_text();ft=assign(fold,'COHORT_AUTHORITY',cohort)
repls={ready['query']['path']:qr['path'],ready['query']['sha256']:qr['sha256'],ready['query_inputs']['path']:ir['path']}
ls=ft.splitlines(True);edits=[]
for n in ast.walk(ast.parse(ft)):
 if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value in repls:edits.append((n.lineno,n.col_offset,n.end_lineno,n.end_col_offset,repr(repls[n.value])))
for x,col,z,end,val in sorted(edits,reverse=True):assert x==z;line=ls[x-1];ls[x-1]=line[:col]+val+line[end:]
ft=''.join(ls).replace("A=D/'admission-preparation-1'","A=D/'admission-preparation-source25-bound-1'")
# Repin complete exact descriptors including bytecounts for both query and inputs.
ls=ft.splitlines(True);edits=[]
for n in ast.walk(ast.parse(ft)):
 if isinstance(n,ast.Dict):
  try:v=ast.literal_eval(n)
  except (ValueError,TypeError):continue
  if isinstance(v,dict) and set(v)=={'path','sha256','bytes'} and v.get('path') in (qr['path'],ir['path']):edits.append((n.lineno,n.col_offset,n.end_lineno,n.end_col_offset,repr(qr if v['path']==qr['path'] else ir)))
for x,col,z,end,val in sorted(edits,reverse=True):assert x==z;line=ls[x-1];ls[x-1]=line[:col]+val+line[end:]
ft=''.join(ls);fr=emit('fill_BFD_C_C_current_review_payload.SOURCE25-FETCH-BOUND.OVERLAY-PENDING.py',ft,fold)
etold=Path(ready['entry']['path']).read_text();et=etold.replace("'admission-preparation-1'","'admission-preparation-source25-bound-1'");et=assign(et,'pins',{'run_root_sdk_readonly_admission.py':qr['sha256'],'QUERY-INPUTS.ROOT.json':ir['sha256']});er=emit('direct_query_entry.C_C_SOURCE25-FETCH-BOUND.py',et,etold)
chainold=Path(ready['chain']['path']).read_text();ct=chainold.replace("'admission-preparation-1'","'admission-preparation-source25-bound-1'")
for name,value in dict(ENTRY_REF=er,QUERY_REF=qr,INPUTS_REF=ir).items():ct=assign(ct,name,value)
cr=emit('direct_query_postjoin_prepare.C_C_SOURCE25-FETCH-BOUND.OVERLAY-PENDING.py',ct,chainold)
ar=ready['genuine_current_BFD_acceptance'];accept=json.loads(Path(ar['path']).read_bytes())
files={'transport/query.py':qr,'transport/query-inputs.json':ir,'transport/fill.py':fr,'transport/directentry.py':er,'transport/chain.py':cr,'transport/samePID.py':ready['samePID'],'data/owner-entry.json':ready['owner_entry'],'data/pending-release.json':ready['pending_release'],'authority/source-approval.json':ref(a),'authority/source-proof.json':ref(p),'authority/current-BFD.json':ar}
for rel,sha in accept['evidence_sha256_by_relative_path'].items():
 row=ref(Path(accept['evidence_root'])/rel);assert row['sha256']==sha;files['authority/current-BFD/'+rel]=row
assert len(files)==17
output=dict(scope=ready['scope'],status='C_C_SOURCE25_CURRENT_BFD_TRANSPORT17_SOURCE_ONLY',member_count=17,retirement_members=7,files=files,destination=str(s/'current-C-C-source25-transport17-overlay-1'),base_source_proof=ref(p),source_proof=ref(p),current_independent_acceptance=ar,query_source=qr,query_inputs=ir,fill_source=fr,current_owner=ready['owner'],current_request=ready['request'],execution_release=False)
sp=s/'EXACT-SEVENTEEN-C_C-SOURCE25-CURRENT-TRANSPORT-OVERLAY.json'
with sp.open('x') as f:json.dump(output,f,sort_keys=True,indent=2);f.write('\n')
result=dict(scope=ready['scope'],status='C_C_SOURCE25_BOUND_TRANSPORT17_READY_NOT_PUBLISHED',spec=ref(sp),query=qr,query_inputs=ir,fill=fr,entry=er,chain=cr,samePID=ready['samePID'],source_proof=ref(p),source_approval=ref(a),query_grant=False,execution_release=False)
rp=s/'READY.C_C-SOURCE25-BOUND-TRANSPORT17.PENDING.json'
with rp.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(result))
