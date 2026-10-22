"""One granted pure current constant successor check; no runtime backend.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import ast,hashlib,json,os,types
S=Path(__file__).resolve().parent
B=S.parent
D=B.parent.parent
LG=D/'generated-source-1'
def ref(p):
 b=Path(p).read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def bodies(raw):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def load(p):
 m=types.ModuleType('pure_constant_'+p.stem);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def save(p,v):
 with p.open('x')as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
def main():
 binding=json.loads((S/'SOURCE-DATA-SUCCESSOR.json').read_bytes());matches={}
 for name,row in binding['current_nine_sources'].items():
  old=(LG/name).read_bytes();new=Path(row['path']).read_bytes();compile(new,row['path'],'exec')
  assert bodies(old)==bodies(new),name
  if name in binding['allowed_constant_delta']:
   def normalize(raw):
    tree=ast.parse(raw)
    for n in tree.body:
     if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in binding['allowed_constant_delta'][name]:n.value=ast.Constant(value='DECLARED_MODULE_DATA')
    return ast.dump(tree,include_attributes=False)
   assert normalize(old)==normalize(new),name
  else:assert old==new,name
  matches[name]=dict(function_class_AST_unchanged=True,only_declared_module_DATA_changed=True,source=row)
 old=load(LG/'cleanup_launcher.py');new=load(S/'cleanup_launcher.py')
 fresh=new.transaction_paths();occupied=old.transaction_paths()
 assert len(fresh)==len(occupied)==7 and fresh!=occupied
 fresh_rows=[dict(path=p,lexists=os.path.lexists(p))for p in fresh]
 old_rows=[dict(path=p,lexists=os.path.lexists(p))for p in occupied]
 assert all(not r['lexists']for r in fresh_rows),'new transaction namespace occupied'
 assert any(r['lexists']for r in old_rows),'original occupied negative did not refuse'
 actualdraft=json.loads((B/'actual-exported-original-five-1/cleanup-release-draft.json').read_bytes())
 observation=actualdraft['observation']
 original=old.prepare_release(observation,actualdraft['git_commit'],actualdraft['git_tree']);assert original==actualdraft
 changed=new.prepare_release(observation,actualdraft['git_commit'],actualdraft['git_tree'])
 assert changed['observation']==observation
 assert {k:v for k,v in changed.items()if k not in ('script_sha256','transaction_paths')}=={k:v for k,v in actualdraft.items()if k not in ('script_sha256','transaction_paths')}
 assert changed['transaction_paths']==fresh and changed['script_sha256']==ref(S/'cleanup_launcher.py')['sha256']
 original_engine_row=next(r for r in observation['selected_files']if r['path']==str(LG/'cleanup_launcher.py'))
 assert original_engine_row['sha256']==binding['selected_original_engine_sha256']
 pre=load(S/'check_launcher_fresh_preflight.py');post=load(S/'postjoin_launcher.py');observer=load(LG/'observe_current_launcher_retirement.py')
 assert pre.SOURCE==post.ENGINE==S/'cleanup_launcher.py'and pre.SOURCE_SHA==post.ENGINE_SHA==changed['script_sha256']
 assert post.OBSERVER==LG/'observe_current_launcher_retirement.py'and post.OBSERVER_SHA==ref(post.OBSERVER)['sha256']
 assert observer.SOURCE==LG/'cleanup_launcher.py'and observer.SOURCE_SHA==binding['selected_original_engine_sha256']
 # Prepare all three operation operands together; final release hash remains NULL.
 ops={}
 for role,filename in [('readonly-preflight','check_launcher_fresh_preflight.py'),('cleanup','cleanup_launcher.py'),('postjoin','postjoin_launcher.py')]:
  op=json.loads((B/('OPERATION-'+role+'.PENDING.json')).read_bytes());argv=op['argv']
  argv[argv.index(str(LG/filename))]=str(S/filename)
  for i,v in enumerate(argv):
   if v==str(B/'cleanup-execution-release.json'):argv[i]=str(S/'cleanup-execution-release.json')
   if v==str(B/'actual-cleanup-result-1.json'):argv[i]=str(S/'actual-cleanup-result-1.json')
  op['same_final_release_path']=str(S/'cleanup-execution-release.json');op['source']=ref(S/filename);op['capture_directory']=str(S/('actual-'+role+'-capture-1'))
  assert argv[op['release_sha256_argument_index']]is None
  assert '--cpu=unlimited:unlimited'in argv and op['profile']['required_inherited_cpu_limits']==[-1,-1]
  assert op['profile']['outer_wall_kill']is None and op['profile']['outer_grace_kill']is None
  save(S/('OPERATION-'+role+'.PENDING.json'),op);ops[role]=ref(S/('OPERATION-'+role+'.PENDING.json'))
 route=json.loads((B/'EXACT-PREFLIGHT-CAPTURE-ROUTE.CURRENT-DATA.json').read_bytes());route['current_inline_DATA_binding'].update(C=str(S),p=str(S/'OPERATION-readonly-preflight.ACTUAL.json'));save(S/'EXACT-PREFLIGHT-CAPTURE-ROUTE.CURRENT-DATA.json',route)
 G=Path('/home/holden/mckernel-work/host-preparation/current-focused-progress-recording-20261021-1/current-normalization-review-recording-1')
 pending=dict(changed,status='PASS_EXECUTION_RELEASE',author='/root',fetched_source_verified=None,git_commit=None,git_tree=None,source_review=None,
  actual_original_five_provenance=ref(B/'ACTUAL-EXACT-FIVE-MEMBER-BYTECOPY-PROVENANCE.json'),actual_raw5_acceptance=ref(G/'LAUNCHER-C9-CURRENT-ACTUAL-RAW5-AND-5FD-ACCEPTANCE.json'),actual_publication_proof=None)
 pending.pop('execution_review')
 save(S/'CLEANUP-FULL-ACTUAL-SUCCESSOR-DATA.PENDING.json',pending)
 result=dict(status='PASS_FRESH_MODULE_DATA_SUCCESSOR_NINE_BODIES_AND_PURE_PRODUCER_ONLY',body_count=9,body_matches=matches,
  fresh_namespace_positive=fresh_rows,original_occupied_negative=old_rows,full_observation_unchanged=True,original_selected_engine_descriptor_retained=original_engine_row,
  actual_prepare_release_delta_only=['script_sha256','transaction_paths'],all_three_operations=ops,preflight_capture_route=ref(S/'EXACT-PREFLIGHT-CAPTURE-ROUTE.CURRENT-DATA.json'),
  pending_release=ref(S/'CLEANUP-FULL-ACTUAL-SUCCESSOR-DATA.PENDING.json'),source_review=None,execution_review=None,publication=None,root_grant=None,
  configure_executed=False,preflight_executed=False,observer_replayed=False,root_backend_executed=False,cleanup_authorized=False,physical_release=None)
 save(S/'ACTUAL-CONSTANT-SUCCESSOR-CHECK.json',result)
 print(json.dumps(dict(status=result['status'],body_count=9,fresh_paths=7,original_negative_refused=True,result=ref(S/'ACTUAL-CONSTANT-SUCCESSOR-CHECK.json')),sort_keys=True))
if __name__=='__main__':main()
