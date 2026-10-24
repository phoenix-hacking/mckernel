"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Generate only an exact scalar-algorithm data successor. Never execute integration.
"""
from pathlib import Path
import ast,hashlib,json,os,stat,shutil
R=Path('/home/holden/mckernel');B=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next');Q=B/'bounded-product-correction-1';P=Path(__file__).resolve().parent
T=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1');A=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-mem-next/production-consumer-preparation-1/current-L4-refresh-1/canonical-integration-preparation-1/ROOT-ATOMIC-INTEGRATE.py')
def pin(f):
 data=f.read_bytes();return dict(path=str(f),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
def wr(f,x):f.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
ready=T/'SNAPSHOT-EQUALITY-RUNTIME-SOURCE-AND-ACTUAL-FIXTURE-READY.json';assert pin(ready)['sha256'].startswith('214d772c');rr=json.loads(ready.read_text());owner=Path(rr['owner']['path']);assert pin(owner)==rr['owner'] and rr['owner']['sha256'].startswith('57600f1c');cohort=Path(rr['cohort']['path']);assert pin(cohort)==rr['cohort'];actual=Path(rr['actual_fixture']['path']);assert pin(actual)==rr['actual_fixture'];fix=json.loads(actual.read_text());foot=Path(fix['mount_open_footprint']['path']);assert pin(foot)==fix['mount_open_footprint']
wr(P/'PREPARATION-MODE-ASSERTION.OBSERVATION.json',dict(scope=__doc__,status='INITIAL_PREPARATION_ONLY_EXPECTED_INPUT0644_FOUND0600_NO_CANONICAL_OPERATION',actual_preimage_modes='0600 bothUID1000/nlink1',preserved_bytes='C2b285/Rust2994',explicit_root_requested_published_mode='0644',correction='Record actual original mode; acceptedalgorithm controls staged/post/rollback mode0644. No source/chmod/canonical execution.',initial_stdin_generator_not_separately_saved=True))
rows=[]
for key,pre,post in [('arch/x86_64/kernel/memory.c','2b285359ee00dac9e6281d112743e4f39247b9d661d0b5d00993e74d17a0739e','28a435d862d1a52263c3bf7b08bd401b4a28be914c2f7f9bdd6fedc68283ec46'),('kernel/rust/x86_memory_helpers.rs','2994b6fe46feb6d0f6dd1390cd4a4efc550f8dfee66c067e506eba16b00029d7','245faf1198d9b7715714d236238172330257f4291776aced4e7cee6c3c518ce2')]:
 target=R/key;s=target.lstat();assert stat.S_ISREG(s.st_mode) and stat.S_IMODE(s.st_mode)==0o600 and s.st_uid==s.st_gid==1000 and s.st_nlink==1;before=pin(target);assert before['sha256']==pre;source=Q/'candidate'/key;after=pin(source);assert after['sha256']==post
 stage=P/'staged'/key;back=P/'preimages'/key
 for dest,src in [(stage,source),(back,target)]:
  dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copyfile(src,dest);os.chmod(dest,0o644)
 rows.append(dict(target=str(target),preimage=before,staged_postimage=pin(stage),accepted_private_postimage=after,rollback_preimage=pin(back),mode=0o644,uid=1000,gid=1000,observed_old_mode=oct(stat.S_IMODE(s.st_mode)),observed_old_inode=dict(device=s.st_dev,inode=s.st_ino,nlink=s.st_nlink)))
tree=ast.parse(owner.read_text());n=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='SOURCE_HASHES' for x in n.targets)];assert len(n)==1;pins=ast.literal_eval(n[0].value);assert len(pins)==287
literal={x['target'] for x in rows};resolved={str(Path(x['target']).resolve(strict=True)) for x in rows};inodes={(Path(x['target']).stat().st_dev,Path(x['target']).stat().st_ino) for x in rows};checks=[];matches=[]
for path,h in sorted(pins.items()):
 q=Path(path);rs=q.resolve(strict=True);s=q.stat();hit=dict(literal=path in literal,resolved=str(rs) in resolved,inode=(s.st_dev,s.st_ino) in inodes);row=dict(path=path,pinned_sha256=h,resolved=str(rs),device=s.st_dev,inode=s.st_ino,match=hit);checks.append(row)
 if any(hit.values()):matches.append(row)
assert not matches
f=json.loads(foot.read_text());assert f['source_hash_rows']==287;required=f['all_required_paths'];assert isinstance(required,list);pathmatches=[x for x in required if isinstance(x,str) and (x in literal or str(Path(x).resolve()) in resolved)];assert not pathmatches
exclude=dict(scope=__doc__,status='PASS_CURRENT_ROOT_SELECTED287_EXACT_RESOLVED_INODE_EXCLUSION',current_source_ready=pin(ready),current_owner=pin(owner),current_cohort=pin(cohort),current_actual_fixture=pin(actual),current_actual_footprint=pin(foot),source_pin_count=287,targets=rows,checks=checks,matches=matches,retained_footprint_required_count=len(required),retained_footprint_target_matches=pathmatches,authority_selection='Rootselected currentterminal snapshot-equality owner57600f1c/source214d772c/fixtureff2ea7cf; historical256notused.',qualification='Finite sourceguard/open-footprint exclusion only; broadRO repository mount exposes canonicalpaths. Immutable10972capsule uses fixedartifacts; no physical/native/newprocess wholecrate claim.',canonical_changes=0)
ex=P/'ACTIVE-CURRENT287-PIN-EXCLUSION.json';wr(ex,exclude);authorities=[pin(f) for f in [ready,owner,cohort,actual,foot,ex]]
old=A.read_text();lines=old.splitlines(True);repl=[]
for n in ast.parse(old).body:
 if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in ['ROWS','AUTHORITIES'] for x in n.targets):
  name=n.targets[0].id;repl.append((n.lineno-1,n.end_lineno,name+'='+repr(rows if name=='ROWS' else authorities)+'\n'))
for a,b,text in sorted(repl,reverse=True):lines[a:b]=[text]
s=''.join(lines).replace('.m14-scalar-root-stage-','.m14-l3-root-stage-').replace('.m14-scalar-root-rollback-','.m14-l3-root-rollback-').replace('ROOT_EXACT2_SCALAR_SOURCE_INTEGRATION_PASS','ROOT_EXACT2_L3_SOURCE_INTEGRATION_PASS').replace("'remaining_C_callbacks':13","'remaining_C_callbacks':'L2/L1/effect/log and CwalkL3 dispatcher remain debt'")
script=P/'ROOT-ATOMIC-INTEGRATE.py';script.write_text(s)
def funcs(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
assert funcs(old)==funcs(s)
receipt=B/'production-consumer-preparation-1/ACTUAL-PRODUCTION-CONSUMER-RECEIPT.json';assert pin(receipt)['sha256'].startswith('9c3665a2')
packet=dict(scope=__doc__,status='EXACT2_ROOT_ONLY_CANONICAL_INTEGRATION_READY_NOT_EXECUTED',rows=rows,script=pin(script),accepted_scalar_algorithm=pin(A),algorithm_functions_AST_identical=True,current287_exclusion=pin(ex),root_selected_authorities=authorities,accepted_actual_production=pin(receipt),accepted_actual_fixture=pin(Q/'retained-receipt-correction-1/FINAL-RETAINED-ACTUAL-FIXTURE-HANDOFF.json'),exact_command=['/home/holden/anaconda3/bin/python3','-I','-B',str(script)],required_actor_UID=1000,canonical_execution_count=0,observed_input_mode='0600 bothtargets; no originalchmod',explicit_output_and_conditional_rollback_mode='0644 perrootrequest/acceptedalgorithm',mode_preparation_observation=pin(P/'PREPARATION-MODE-ASSERTION.OBSERVATION.json'),scope_limits='Coordinated per-file atomic replacements, not singlefilesystemtransaction; bothprechecks, owninode/exactpost conditionalrollback, fsync. Frozen15/capsule10972 unchanged; newprocess wholecrate union/native notclaimed.',current_authority_rule='If rootselection changes beforeintegration, hold/rebind exactsmall authority pins. Historicalscope nevercurrentproof.')
wr(P/'CANONICAL-INTEGRATION-READY.json',packet)
print(json.dumps(dict(ready=pin(P/'CANONICAL-INTEGRATION-READY.json'),script=pin(script),exclusion=pin(ex),command=packet['exact_command'])))
