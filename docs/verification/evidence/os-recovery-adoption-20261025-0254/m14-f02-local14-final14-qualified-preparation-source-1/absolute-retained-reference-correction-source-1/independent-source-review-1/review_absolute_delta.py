"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Absolute retained reference-only source delta; no qualifier main/guard/workload.
"""
from pathlib import Path
import ast,copy,datetime,hashlib,json
D=Path(__file__).resolve().parent;Q=D.parent;P=Q.parent;E=P.parent;OLD=P/'fallback-storage-class-readback-correction-source-1';REPO=Path('/home/holden/mckernel')
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
r=read(Q/'SOURCE-READY.json');p=read(Q/'PROFILE.NOT-GRANTED.json');op=read(OLD/'PROFILE.NOT-GRANTED.json')
assert ref(Q/'SOURCE-READY.json')['sha256']=='c70b5cd45e79188a800b3bdbbb40742767ea79ee594e75f690ce7be445f43d9b'
for key in ['profile','one_command','diagnosis','storage_manifest','retained_prefix_identity']:assert ref(r[key]['path'])==r[key]
prior=OLD/'independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json';assert ref(prior)['sha256']=='b8c6aa085f744207bdf28f7816987c1714497d0c809a828926bb2522bfa96101'
a=read(OLD/'RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json');b=read(Q/'RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json');assert len(a['records'])==len(b['records'])==41
changes=[]
for x,y in zip(a['records'],b['records']):
 expected=copy.deepcopy(x);path=Path(x['reference']['path'])
 if not path.is_absolute():expected['reference']['path']=str(REPO/path);changes.append(dict(before=x['reference']['path'],after=expected['reference']['path'],bytes=x['reference']['bytes'],sha256=x['reference']['sha256'],device=x['device'],inode=x['inode']))
 assert y==expected and Path(y['reference']['path']).is_absolute() and Path(y['reference']['path']).exists()
assert len(changes)==1
newfile=Path(changes[0]['after']);s=newfile.lstat();assert s.st_dev==changes[0]['device'] and s.st_ino==changes[0]['inode'] and ref(newfile)['sha256']==changes[0]['sha256']
x=read(OLD/'EXACT17-ORIGINAL-HOST-C-STORAGE.json');y=read(Q/'EXACT17-ORIGINAL-HOST-C-STORAGE.json');x['original_HOST_C']['reference']['path']=changes[0]['after']
rawold=read(x['raw_readback']['path']);rawnew=read(y['raw_readback']['path']);raw_path_changes=[]
def normalize_raw_paths(a,b,path=''):
 if isinstance(a,dict):
  assert a.keys()==b.keys()
  for k in a:normalize_raw_paths(a[k],b[k],path+'/'+k)
 elif isinstance(a,list):
  assert len(a)==len(b)
  for i,(u,v) in enumerate(zip(a,b)):normalize_raw_paths(u,v,path+'/'+str(i))
 elif a!=b:
  assert isinstance(a,str) and a.startswith('docs/') and b==str(REPO/a);raw_path_changes.append(path)
normalize_raw_paths(rawold,rawnew);assert len(raw_path_changes)==5
assert ref(y['raw_readback']['path'])==y['raw_readback'];x['raw_readback']=y['raw_readback'];assert x==y
oldtree=ast.parse((OLD/'qualify_changed_objects.py').read_text());newtree=ast.parse((Q/'qualify_changed_objects.py').read_text());of={n.name:n for n in oldtree.body if isinstance(n,ast.FunctionDef)};nf={n.name:n for n in newtree.body if isinstance(n,ast.FunctionDef)};assert set(of)==set(nf)
for name,n in of.items():
 if name!='verify_retained_identities':assert ast.dump(n,include_attributes=False)==ast.dump(nf[name],include_attributes=False),name
n=copy.deepcopy(nf['verify_retained_identities']);assert_count=[v for v in ast.walk(n) if isinstance(v,ast.Assert) and isinstance(v.test,ast.Call) and isinstance(v.test.func,ast.Attribute) and v.test.func.attr=='is_absolute'];assert len(assert_count)==1
class RemoveAddedAbsoluteAssert(ast.NodeTransformer):
 def visit_Assert(self,node):
  if isinstance(node.test,ast.Call) and isinstance(node.test.func,ast.Attribute) and node.test.func.attr=='is_absolute':return None
  return node
n=RemoveAddedAbsoluteAssert().visit(n);assert ast.dump(n,include_attributes=False)==ast.dump(of['verify_retained_identities'],include_attributes=False)
assignments={n.targets[0].id:ast.literal_eval(n.value) for n in newtree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'STORAGE_MANIFEST_REF','RETAINED_IDENTITIES_REF'}}
assert assignments['STORAGE_MANIFEST_REF']==r['storage_manifest'] and assignments['RETAINED_IDENTITIES_REF']==r['retained_prefix_identity']
assert len(p['commands'])==1 and p['commands'][0]['argv'][:2]==['/usr/bin/python3','-B'] and p['commands'][0]['argv'][2]==str(Q/'qualify_changed_objects.py') and p['commands'][0]['argv'][3]==op['commands'][0]['argv'][3] and p['commands'][0]['argv'][4]==p['leaves'][0]['output']
assert not Path(p['capture_root']).exists() and not Path(p['leaves'][0]['output']).exists()
assert all(Path(i['path']).is_absolute() and Path(i['path']).exists() for i in p['inputs'])
for key in ['goal','fixed_deadline_UTC','fixed_cutoffs','resources','host_growth_reserve_bytes','scope_limit']:assert p[key]==op[key]
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';t=ast.parse(runner.read_text());ns=dict(Path=Path,hashlib=hashlib,json=json,THREAD='01a17e6f-112f-7660-8771-85d15e07a26c',CUTOFFS=[1793165769.0,947874.5689514667,963213.6960030915]);exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'need','validate_profile'}],type_ignores=[]),'existing pure ordinary profile validator','exec'),ns);ns['validate_profile'](p)
report=dict(scope=__doc__.splitlines()[0],decision='PASS_SOURCE_EXACT17_C_FALLBACK_READBACK_ABSOLUTE_REFERENCE_CORRECTION',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ready=ref(Q/'SOURCE-READY.json'),profile=ref(Q/'PROFILE.NOT-GRANTED.json'),reader=ref(Q/'qualify_changed_objects.py'),prior_blocked_review=ref(prior),same41_retained_bytes_and_inode_metadata=True,one_absolute_reference_change=changes,exact17_storage_class_manifest=ref(Q/'EXACT17-ORIGINAL-HOST-C-STORAGE.json'),retained_identity_manifest=ref(Q/'RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json'),raw_diagnostic_absolute_path_fields=raw_path_changes,
findings=['Exactly one of41 identity reference paths changes from repository-relative to its exact absolute path. All bytes/digests/device/inode/uid/gid/mode/nlink/mtime/ctime entries remain equal to b8c6 independently verified values; changed selected0 file retains actual digest/device/inode.','Storage manifest has no class/type/bind/size/alignment/semantic change: original HOST reference path becomes absolute and raw diagnostic is rebound after five artifact path strings are absolutized, with all other raw leaves identical. Every original helper function is AST-identical except verify_retained_identities adds exactly one explicit path.is_absolute assertion. New manifest hashes/paths bind exact corrected files.','Exact17 per-name original HOST C .data.rel.ro[.local]/WA or .rodata/A classes remain finite. Strict selectedRust/production readonly, actual ABI/scalar/padding/callback/LOCAL pointer/registry46+102/148 checks and folded-consumer OPEN/exit2 remain unchanged; no generic writable or physical C-RELRO acceptance.','All profile input paths are absolute/existing, and unchanged6e98 pure validate_profile passes. One Python qualifier only consumes the six successful compiled/CPP/link outputs and writes a fresh report/capture; no producer/CPP/link command or failed/passed-prefix replay is authorized. Original4099/e82e/b8c6 and both actual failed attempts remain preserved.','All original CPU6/resource/account/fixedclock/defaultON nondefault limitations remain in force. Fresh Root CPU6 exclusion/account/resources/nonce/grant is still required; source PASS supplies no execution authority.'],
reused_positive_prefix=read(prior)['positive_findings'],retained_open=['Actual qualifier result and any current folded instruction/dataflow supplement are pending.','DefaultON rejects RUSAGE_DEBUG/TIMER_CPU_ID/ARCH_MEMCLEAR without optionOFF; Fugaku excluded; all-profile object/link/native and whole-file credit remain OPEN.'],blocking_findings=[],runtime_authority=None,qualifier_main_actions=0,compiler_CPP_link_replays=0,guard_or_resource_queries=0,workloads=0,canonical_mutations=0)
out=D/'INDEPENDENT-SOURCE-REVIEW.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),changed_retained_paths=1,qualifier_commands=1,blocking_findings=0)))
