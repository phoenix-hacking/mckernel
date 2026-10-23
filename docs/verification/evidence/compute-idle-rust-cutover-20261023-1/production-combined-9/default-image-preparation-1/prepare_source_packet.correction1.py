"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Candidate9 metadata/controller preparation; no compiler or heavy operation.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');B=H/'production-combined-8/default-image-preparation-1';N=H/'production-combined-9/default-image-preparation-1';S=N/'source-materialization-attempt-1'
AUTH=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/CANONICAL-INTEGRATION.json'
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(name,raw):
 if not isinstance(raw,bytes):raw=(json.dumps(raw,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  if (d/name).exists():assert (d/name).read_bytes()==raw
  else:
   with (d/name).open('xb') as f:f.write(raw)
 return ref(N/name)
def controller(name,old,new):
 ast.parse(new);o=save(name,new.encode());save(name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen8/'+name,tofile='future9/'+name)).encode());return o
N.mkdir(parents=True,mode=0o700,exist_ok=True)
a=json.loads(AUTH.read_text());assert a['status']=='CANONICAL_BOUNDED_SET_TIMER_SOURCE_INTEGRATED';POST={p:row['sha256'] for p,row in a['outputs'].items()};pre={p:row['sha256'] for p,row in a['inputs'].items()};assert len(POST)==3
base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h and base['repository_files'][rel]==pre[rel]
 delta.append(dict(path=rel,before_sha256=pre[rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='550284bc2beba2db2221b16a61294034ec4cf1ada0d449b8b2f8fd70add74eb5'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay'])
doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(B/'materialize_source.py').read_text();lines=old.splitlines(True);values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for n in reversed(ast.parse(old).body):
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:
  name=n.targets[0].id;lines[n.lineno-1:n.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("authority['status'] == 'CANONICAL_SOURCE_INTEGRATED_BOUNDED_SLICE' and {row['path']:row['sha256'] for row in authority['after']}","authority['status'] == 'CANONICAL_BOUNDED_SET_TIMER_SOURCE_INTEGRATED' and {p:row['sha256'] for p,row in authority['outputs'].items()}")
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1;prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
old=(B/'native_rust_exact_mckernel_image_offline.py').read_text();new=old.replace(ref(B/'native_rust_exact_build_offline.py')['sha256'],prov['sha256'])
expected_pin_counts={'kernel/process.c':2,'kernel/rust/sched_helpers.rs':3,'kernel/rust/tests/run_equivalence.sh':1}
for row in delta:
 assert new.count(row['before_sha256'])==expected_pin_counts[row['path']]
 new=new.replace(row['before_sha256'],row['after_sha256'])
new=new.replace("M14_RUST_EXPORTS = M14_IDLE_IMPORTS", "M14_TIMER_CALLBACKS = ('process_timer_spin_lock_bridge', 'process_timer_spin_unlock_bridge',\n                       'process_timer_lapic_enable_bridge', 'process_timer_lapic_disable_bridge')\nM14_RUST_EXPORTS = ('set_timer', 'get_this_cpu_local_var', 'timer_set_timer_body_result',\n                    'process_sched_set_timer_bridge') + M14_IDLE_IMPORTS",1)
extension=(E/'set_timer_checks.inc.py').read_text();new=new.replace('def _validate_m14_source_pins(source_root):',extension+'\n\ndef _validate_m14_source_pins(source_root):',1)
anchor="    proof = dict(status='PASS_PINNED_FULLCRATE_DEFAULT_C_CONSUMERS_AND_FINAL_LINK_ONLY',";new=new.replace(anchor,"    set_timer_proof = _validate_m14_set_timer_contract(source_root, build, tools, env, timeout, command_rows, objects)\n"+anchor,1)
new=new.replace('textmap_contract=textmap_proof, idle_imports=M14_IDLE_IMPORTS,','textmap_contract=textmap_proof, set_timer_contract=set_timer_proof, idle_imports=M14_IDLE_IMPORTS,',1)
driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
save('SOURCE-CONSUMER-JOIN.PREPARED.json',dict(scope=__doc__,status='SOURCE_ONLY_PREPARED_NOT_MATERIALIZED',canonical_integration=ref(AUTH),source_ABI_review=ref(AUTH.parent/'INDEPENDENT-SOURCE-ABI-ACCEPTANCE.ROOT-RECORD.json'),accepted_Rust_receipt=ref(AUTH.parent/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json'),accepted_consumer_proposal=ref(AUTH.parent/'NEXT-CANDIDATE8-SET-TIMER-CONSUMER-PREPARATION.NOT-EXECUTED.json'),changed_source_files=delta,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),source_derivative_sha256=doc['source_derivative_sha256'],materialization_sha256=doc['materialization_sha256'],producer=producer,provenance=prov,driver=driver,original19GiB_guard_required=True,preserved_source_entries=6959,preserved_symlinks=49,prior_memory_bridges_preserved=True,set_timer_C_import_required=False,actual_whole_C_TU=None,actual_defaultlink=None,actual_native=None))
print(json.dumps(dict(manifest=mh,producer=producer,driver=driver,provenance=prov),sort_keys=True))
