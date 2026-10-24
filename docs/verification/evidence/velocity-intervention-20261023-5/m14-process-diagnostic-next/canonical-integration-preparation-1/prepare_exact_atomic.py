"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare only exact accepted scalar-algorithm data successor. Never execute it.
"""
from pathlib import Path
import ast,hashlib,json,os,shutil,stat
R=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;B=P.parent
Q=B/'production-consumer-preparation-1/bounded-correction-1'
T=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1')
A=R/'docs/verification/evidence/velocity-intervention-20261023-4/m14-mem-next/production-consumer-preparation-1/current-L4-refresh-1/canonical-integration-preparation-1/ROOT-ATOMIC-INTEGRATE.py'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def main():
 assert pin(A)['sha256']=='27c048688e65a2ed7aefb549ad6440c734826e7da25536a45f3396d341b16864'
 ready=T/'SNAPSHOT-EQUALITY-RUNTIME-SOURCE-AND-ACTUAL-FIXTURE-READY.json'
 assert pin(ready)['sha256']=='214d772c14dfc54bd5066a8d7b5c1c501ebc5bec46605dbfc94b867905127bc5'
 selected=json.loads(ready.read_text());owner=Path(selected['owner']['path']);cohort=Path(selected['cohort']['path']);actual=Path(selected['actual_fixture']['path'])
 for path,row in [(owner,selected['owner']),(cohort,selected['cohort']),(actual,selected['actual_fixture'])]:assert pin(path)==row
 assert pin(owner)['sha256']=='57600f1c92d2075ee85d6a52949f11ae69c99dbd122087c227bab28178caedb6'
 assert pin(cohort)['sha256']=='b5aa82c50bdd34f15d88275d1d12540a5ee194291bedba4e670b06169f284ea8'
 fixture=json.loads(actual.read_text());foot=Path(fixture['mount_open_footprint']['path']);assert pin(foot)==fixture['mount_open_footprint']
 assert pin(foot)['sha256']=='16cf0d2f59ef6633e669d533d5a8c673c9389fa42e99eb0b535a588cc09ab802'
 footprint=json.loads(foot.read_text());assert footprint['source_hash_rows']==287 and footprint['all_required_paths']==332
 rows=[]
 for key,pre,source,post in [('kernel/process.c','64af918855ea361bd850d6ad7480d304634c28814e04127fe3dec8c013f21044',B/'candidate/process.c','08c238a08066a6eda5f346bbd6e6f87333bd505d8d598276dc9c52cd43568a45'),('kernel/rust/process_helpers.rs','3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e',Q/'candidate/process_helpers.rs','d04b48c887c834edd6380e3ae06fccdef7dfafaf67196fd28af7f9571993bd6d')]:
  target=R/key;s=target.lstat();before=pin(target);after=pin(source)
  assert stat.S_ISREG(s.st_mode) and s.st_uid==s.st_gid==1000 and s.st_nlink==1
  assert stat.S_IMODE(s.st_mode)==0o600 and before['sha256']==pre and after['sha256']==post
  stage=P/'staged'/key;back=P/'preimages'/key
  for dst,src in [(stage,source),(back,target)]:
   dst.parent.mkdir(parents=True,exist_ok=True)
   with dst.open('xb') as stream:stream.write(src.read_bytes())
   os.chmod(dst,0o644)
  rows.append(dict(target=str(target),preimage=before,staged_postimage=pin(stage),accepted_private_postimage=after,rollback_preimage=pin(back),mode=0o644,uid=1000,gid=1000,observed_old_mode=oct(stat.S_IMODE(s.st_mode)),observed_old_inode=dict(device=s.st_dev,inode=s.st_ino,nlink=s.st_nlink)))
 nodes=[node for node in ast.parse(owner.read_text()).body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_HASHES' for t in node.targets)]
 assert len(nodes)==1;pins=ast.literal_eval(nodes[0].value);assert len(pins)==287
 literal={row['target'] for row in rows};resolved={str(Path(path).resolve(strict=True)) for path in literal};inodes={(Path(path).stat().st_dev,Path(path).stat().st_ino) for path in literal};checks=[]
 for path,sha in sorted(pins.items()):
  q=Path(path);s=q.stat();r=str(q.resolve(strict=True));hits=dict(literal=path in literal,resolved=r in resolved,inode=(s.st_dev,s.st_ino) in inodes)
  assert not any(hits.values()),(path,hits)
  checks.append(dict(path=path,pinned_sha256=sha,resolved=r,device=s.st_dev,inode=s.st_ino,match=hits))
 exclusion=P/'ACTIVE-CURRENT287-PIN-EXCLUSION.json'
 write(exclusion,dict(scope=SCOPE,status='PASS_CURRENT_ROOT_SELECTED287_LITERAL_RESOLVED_INODE_EXCLUSION',current_source_ready=pin(ready),current_owner=pin(owner),current_cohort=pin(cohort),current_actual_fixture=pin(actual),current_actual_footprint=pin(foot),source_pin_count=287,targets=rows,checks=checks,matches=[],retained_footprint_required_count=332,footprint_scope='332 is a retained integer metadata count, no additional332-path/live-open audit or claim. Exactly requested287 source pin paths checked.',authority_scope='Current root-selected terminal ready214d/owner5760/cohortb5aa/fixtureff2e/foot16cf only. Historical256 not used.',qualification='Finite owner sourceguard literal/resolved/inode exclusion only. Broad readonly repository mounts expose canonical files, but fixed artifact sourcepins consume neither target. No physical/native/full-current-union proof.',canonical_changes=0))
 production=Q/'ACTUAL-PRODUCTION-WHOLE-JOIN.json';metadata=Q/'ACTUAL-DEBUG-METADATA-ABI.json';leaf=B/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json';failure=B/'production-consumer-preparation-1/PRODUCTION-FIRST-FAILURE-1.json';error=B/'production-consumer-preparation-1/actual-production-capture-1/00-current78-production-Rust-compile/stderr';qualification=Q/'SOLE-DECLARATION-CORRECTION-AND-LEAF-SCOPE.json'
 assert pin(production)['sha256']=='7a0191a235c29356ab48f25fd28e6e33b698ae1bd9a539ab84c795c52fc9993f'
 assert pin(leaf)['sha256']=='bebe72021c410cddfd8c67dfc086c365d51641e074aca04f87f5450405509316'
 assert pin(failure)['sha256']=='2fb3a2294e4347bc7eced2aee91ef259778c079779bcbfa5e8f61eda3fb17698'
 assert pin(error)['sha256']=='e9a1a83c79078bfecf6bfd2e63cca2705fa1dbfbe16ad7afff3e830d093e0425'
 authorities=[pin(path) for path in (ready,owner,cohort,actual,foot,exclusion,production,metadata,leaf,failure,error,qualification)]
 old=A.read_text();lines=old.splitlines(True);replacements=[]
 for node in ast.parse(old).body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'ROWS','AUTHORITIES'} for t in node.targets):
   name=node.targets[0].id;replacements.append((node.lineno-1,node.end_lineno,name+'='+repr(rows if name=='ROWS' else authorities)+'\n'))
 for start,end,text in sorted(replacements,reverse=True):lines[start:end]=[text]
 proposed=''.join(lines).replace('.m14-scalar-root-stage-','.m14-process-log-root-stage-').replace('.m14-scalar-root-rollback-','.m14-process-log-root-rollback-').replace('ROOT_EXACT2_SCALAR_SOURCE_INTEGRATION_PASS','ROOT_EXACT2_PROCESS_LOG_SOURCE_INTEGRATION_PASS').replace("'remaining_C_callbacks':13","'remaining_C_callbacks':'vm_range_insert_dump_bridge/dump_tree/optional dtree and other process.c compute remain debt'")
 def normalized(source):
  tree=ast.parse(source)
  for node in tree.body:
   if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'ROWS','AUTHORITIES'} for t in node.targets):node.value=ast.Constant(value='DATA_ONLY')
  for node in ast.walk(tree):
   if isinstance(node,ast.Constant) and isinstance(node.value,str):
    node.value=node.value.replace('.m14-process-log-root-stage-','.m14-scalar-root-stage-').replace('.m14-process-log-root-rollback-','.m14-scalar-root-rollback-').replace('ROOT_EXACT2_PROCESS_LOG_SOURCE_INTEGRATION_PASS','ROOT_EXACT2_SCALAR_SOURCE_INTEGRATION_PASS').replace('vm_range_insert_dump_bridge/dump_tree/optional dtree and other process.c compute remain debt','DATA_DEBT')
   if isinstance(node,ast.Dict):
    for i,key in enumerate(node.keys):
     if isinstance(key,ast.Constant) and key.value=='remaining_C_callbacks':node.values[i]=ast.Constant(value='DATA_DEBT')
  return ast.dump(tree,include_attributes=False)
 assert normalized(old)==normalized(proposed)
 script=P/'ROOT-ATOMIC-INTEGRATE.py'
 with script.open('x') as stream:stream.write(proposed)
 packet=dict(scope=SCOPE,status='EXACT2_ROOT_ONLY_INTEGRATION_PROPOSAL_READY_NOT_EXECUTED',rows=rows,script=pin(script),accepted_scalar_algorithm=pin(A),full_control_flow_AST_identical_after_only_data_tag_report_normalization=True,current287_exclusion=pin(exclusion),authorities=authorities,accepted_actual_production=pin(production),accepted_actual_leaf=pin(leaf),first_E0428_failure_preserved=pin(failure),corrected_d04b_used_not_failed17c=True,exact_command=['/home/holden/anaconda3/bin/python3','-I','-B',str(script)],required_actor_UID=1000,execution_count=0,observed_input_modes='0600 bothUID/GID1000/nlink1, no canonicalchmod',published_and_conditional_rollback_modes='0644 as explicitly requested and unchanged accepted scalar algorithm',transaction_scope='Two coordinated per-file atomic replacements, not a single filesystem atomic transaction; both prechecks, exact staged/backup bytes, fsync, own published inode+exactpost conditionalrollback. Intervening edits retained.',retained_runtime_scope='Current287 ownerpins only, not historical256 and not new broad mounted-path/physical audit.',production_proof_scope='Actual corrected cohort986f includes x86_memory2994. Root now integrated L3C28a/Rust245faf outside this 2file set; no retrospective whole-union/default-image/native credit.',remaining_C_debt='Declarative debugselector data, Cdump bridge/dump_tree/optional dtree, other process.c compute',no_frozen15_changes=True,current_authority_rule='If root changes selected runtime authority, hold and rebind exact current authority rows before command; source proposal grants no runtime/root/guest operation.')
 write(P/'CANONICAL-INTEGRATION-READY.json',packet)
 mirror=R/'docs/verification/evidence/velocity-intervention-20261023-5/m14-process-diagnostic-next/canonical-integration-preparation-1';shutil.copytree(P,mirror,dirs_exist_ok=True)
 print(json.dumps(dict(scope=SCOPE,ready=pin(P/'CANONICAL-INTEGRATION-READY.json'),script=pin(script),exclusion=pin(exclusion),exact_command=packet['exact_command'],canonical_execution_count=0),indent=2))
if __name__=='__main__':main()
