# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parent;B=P.parent;R=Path('/home/holden/mckernel')
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
prior=B/'NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json';assert pin(prior)['sha256']=='295d258e7c22789993770d6b155c21dfc16863179d992d92405aa6792b4790d3';old=json.loads(prior.read_text())
profile=B/'ACTUAL-FULLCRATE-PROFILE.json';assert pin(profile)['sha256']=='68fd3eb7f826f5eccadb1a95909affb6bed0323ebbc88a57321419aee8bfae17'
receipt=B/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json';assert pin(receipt)['sha256']=='7f2e8d83fe83067e64cdd6628cfb6dcc704d3ff99ef2c5d763faef9afe5969d3'
bind=json.loads((P/'SOURCE-BINDINGS.json').read_text());source=P/'fullcrate-preparation-1/source';source.mkdir(parents=True,exist_ok=False);inputs={}
for rel,row in old['source_inputs'].items():
 baseline=Path(row['private']['path']);assert pin(baseline)==row['private']
 replacement=Path(bind['outputs'][rel]['path']) if rel in bind['outputs'] else baseline
 if rel in bind['outputs']:assert row['private']['sha256']==bind['source_inputs'][rel]['sha256']
 dst=source/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(replacement,dst)
 inputs[rel]=dict(baseline=row['private'],private=pin(dst),modified_target=replacement!=baseline)
assert len(inputs)==78 and [k for k,v in inputs.items() if v['modified_target']]==['kernel/rust/sched_helpers.rs']
argv=old['argv'][:]
for i,a in enumerate(argv):
 if a.startswith('--emit=obj='):argv[i]='--emit=obj='+str(P/'fullcrate-preparation-1/mckernel_rust.o')
 if a.endswith('/source/kernel/rust/lib.rs'):argv[i]=str(source/'kernel/rust/lib.rs')
review=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/INDEPENDENT-PRIVATE-SPIN-SLEEP-SOURCE-LEAF-ACCEPTANCE.ROOT-RECORD.json'
recipe=dict(scope=old['scope'],status='EXACT_GRANTED_RECIPE_SOURCE_STAGED_NOT_YET_EXECUTED',root_authority='Parent ordinary grant after independent687b/af8d acceptance: same78-input productionRust profile with onlyacceptednextslice postimage; CPU6onejob AS2GiB CPU60 wall120+6 FSIZE32MiB NOFILE256 core0 CGU1stack2MiB',argv=argv,compiler_sha256=old['compiler_sha256'],prior_exact_recipe=pin(prior),prior_actual_profile=pin(profile),prior_actual_receipt=pin(receipt),source_leaf_review=pin(review),source_bindings=pin(P/'SOURCE-BINDINGS.json'),source_count=78,source_inputs=inputs,only_actual_Rust_file_delta='kernel/rust/sched_helpers.rs',C_and_harness_postimages=bind['outputs'],wall_seconds=120,retirement_seconds=6,profile='Exactacceptednightly1.95/CGU1/4cfg/2externmodule; no bootstrap/stubs/equivalence/cfg change',observations='Tspin_sleep/existingbody/currentCPU; noUspin or Cdescriptor; exactpriorproductionU560->559 onlyremovedspin; preservememory/set_timerexports',whole_C_TU_default_link_native='OPEN')
(P/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json').write_text(json.dumps(recipe,indent=2)+'\n');print(json.dumps(dict(recipe=pin(P/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json'),source_count=78)))
