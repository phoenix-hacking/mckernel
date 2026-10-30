#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import copy,importlib.util,json,pathlib
O=pathlib.Path(__file__).resolve().parent;A=O.parent
def load(n,p):sp=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v=load('v',O/'validator.py');d=load('d',O/'driver.py');p=A/'m14-root-and-nonheld-composite-1/MOUNT-MANIFEST.json';base=json.loads(p.read_text())['on_source_mount_proposal'];rows=[('/tmp/work','/work',False)]+sorted([(h,t,True) for t,h in base.items()],key=lambda x:(len(pathlib.PurePosixPath(x[1]).parts),x[1]))+[('/tmp/out','/out',True)];i=next(i for i,x in enumerate(rows) if x[1]==v.RUST_TARGET);rows.insert(i+1,(v.PERF_OVERLAY_SOURCE,v.PERF_CHILD,True));out=[]
v._mount_graph(rows);ref=v._check_composite_proposal(p,rows);assert ref['sha256']==v.COMPOSITE_PROPOSAL_SHA;out.append({'case':'exact_graph_and_source_proposal','outcome':'pass_source_only'})
def reject(case,rr,reason):
 try:v._mount_graph(rr)
 except ValueError as e:assert reason in str(e),(case,str(e),reason);out.append({'case':case,'outcome':'rejected','error':str(e)})
 else:raise AssertionError(case)
a=list(rows);a[i+1]=('/tmp/wrong',v.PERF_CHILD,True);reject('wrong_host',a,'perf child binding/order')
a=list(rows);a[i+1]=(v.PERF_OVERLAY_SOURCE,v.PERF_CHILD,False);reject('writable_child',a,'perf child binding/order')
a=list(rows);a[i],a[i+1]=a[i+1],a[i];reject('child_before_parent',a,'perf child binding/order')
a=list(rows);a.insert(i+2,('/tmp/other',v.RUST_TARGET+'/other.rs',True));reject('other_child',a,'unsupported overlap')
a=list(rows);a.insert(i+2,('/tmp/other',v.PERF_CHILD+'/sub',True));reject('child_submount',a,'unsupported overlap')
a=list(rows);a.insert(i+2,(v.PERF_OVERLAY_SOURCE,v.PERF_CHILD,True));reject('duplicate_child',a,'duplicate mount')
# Actual source-proposal verification must reject content or identity drift;
# inject synthetic _file observations only for these negative tests.
old=v._file
for case,change,reason in [('wrong_parent_hash','parent_hash','perf source hash mismatch'),('wrong_child_hash','child_hash','perf source hash mismatch'),('same_inode','alias','perf source inode alias')]:
 def fake(path,change=change):
  r=copy.deepcopy(old(path));is_child=str(path)==v.PERF_OVERLAY_SOURCE;is_parent=str(path)==str(pathlib.Path(base[v.RUST_TARGET])/v.PERF_NAME)
  if change=='parent_hash' and is_parent:r['sha256']='0'*64
  if change=='child_hash' and is_child:r['sha256']='0'*64
  if change=='alias' and (is_parent or is_child):r['identity']=(1,1)+tuple(r['identity'][2:])
  return r
 v._file=fake
 try:v._check_composite_proposal(p,rows)
 except ValueError as e:assert reason in str(e),(case,str(e));out.append({'case':case,'outcome':'rejected','error':str(e)})
 else:raise AssertionError(case)
 finally:v._file=old
# Synthetic mountinfo strings exercise actual parser, without observing mounts.
def line(n,t,mode):return f'{n} 0 0:1 / {t} {mode} - tmpfs tmpfs rw\n'
expected={'/src':True,v.RUST_TARGET:True,v.PERF_CHILD:True};raw=''.join(line(i+1,t,'ro') for i,t in enumerate(expected)).encode();assert d.validate_mountinfo(raw,expected)==3;out.append({'case':'synthetic_exact_mountinfo','outcome':'parser_pass_only'})
for case,raw0,ex,reason in [('unapproved_expected',raw,{**expected,v.RUST_TARGET+'/other.rs':True},'unapproved or writable Rust nested mount'),('writable_expected',raw,{**expected,v.PERF_CHILD:False},'unapproved or writable Rust nested mount'),('unexpected_actual',raw+line(4,v.RUST_TARGET+'/other.rs','ro').encode(),expected,'unexpected nested mount'),('wrong_effective_mode',raw.replace((v.PERF_CHILD+' ro').encode(),(v.PERF_CHILD+' rw').encode()),expected,'missing or wrong effective mount')]:
 try:d.validate_mountinfo(raw0,ex)
 except ValueError as e:assert reason in str(e),(case,str(e));out.append({'case':case,'outcome':'rejected','error':str(e)})
 else:raise AssertionError(case)
try:d.validate_tree(v.RUST_TARGET,{},[v.PERF_CHILD],{})
except ValueError as e:assert 'pre-shadow Rust parent inventory is unbound' in str(e);out.append({'case':'parent_snapshot_gate','outcome':'rejected','error':str(e)})
else:raise AssertionError('parent snapshot gate opened')
try:d.validate_effective_view(None,None,None,None,None)
except ValueError as e:assert 'pre-shadow parent and effective mount identities are unbound' in str(e);out.append({'case':'effective_view_gate','outcome':'rejected','error':str(e)})
else:raise AssertionError('effective view gate opened')
try:v._collect({},None,None,None)
except ValueError as e:assert 'SOURCE_ONLY' in str(e);out.append({'case':'collector_gate','outcome':'rejected','error':str(e)})
else:raise AssertionError('collector gate opened')
(O/'GRAPH-RESULTS.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS',len(out),'graph/parser/gate source-only cases; no mounts or live collector')
