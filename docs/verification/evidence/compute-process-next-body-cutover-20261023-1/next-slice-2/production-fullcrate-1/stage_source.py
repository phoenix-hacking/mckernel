# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,shutil
D=Path(__file__).resolve().parent;P=D.parent;B=P.parent/'next-slice-1';R=Path('/home/holden/mckernel')
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
prior=B/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json';assert pin(prior)['sha256']=='d34cfadf3107672c46687ca8db898ca7f806beea69bcc3507e5bc9d230324373';old=json.loads(prior.read_text())
receipt=B/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json';assert pin(receipt)['sha256']=='a19c4303bdbe94285a41fc0822b7528afc3468ff9f83ebccafc7e73c540f28df';oldreceipt=json.loads(receipt.read_text())
assert oldreceipt['object']['sha256']=='85701f312f0a973bb47fa6aa3a370c572166de14d2ec2fadd0ce8ad828be3047'
profile=B/'ACTUAL-FULLCRATE-PROFILE.json';assert pin(profile)['sha256']==oldreceipt['actual_profile']['sha256']
bind=json.loads((P/'SOURCE-BINDINGS.json').read_text());leaf=P/'ACTUAL-LEAF-RECEIPT.json';assert pin(leaf)['sha256']=='5aac2393faf4b2d56af021787f369eb0c6a8a5bbec712a4c8074f56912fc400a'
source=D/'source';source.mkdir(exist_ok=False);inputs={}
for rel,row in old['source_inputs'].items():
 canonical=R/rel;assert pin(canonical)['sha256']==row['private']['sha256'],('current canonical differs from accepted spin78input',rel)
 replacement=P/'source'/rel if rel=='kernel/rust/sched_helpers.rs' else canonical
 if rel=='kernel/rust/sched_helpers.rs':assert pin(canonical)==bind['changes'][rel]['before'] and pin(replacement)==bind['changes'][rel]['after']
 dst=source/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(replacement,dst)
 inputs[rel]=dict(baseline=row['private'],canonical_before=pin(canonical),private=pin(dst),modified_target=replacement!=canonical)
assert len(inputs)==78 and [k for k,v in inputs.items() if v['modified_target']]==['kernel/rust/sched_helpers.rs']
argv=old['argv'][:];argv[-2]='--emit=obj='+str(D/'mckernel_rust.o');argv[-1]=str(source/'kernel/rust/lib.rs')
recipe=dict(scope=old['scope'],status='GRANTED_EXACT78INPUT_PRODUCTION_SOURCE_STAGED_NOT_YET_COMPILED',root_authority='Parent followup grants CPU6onejob AS2GiB CPU60 wall120+6 FSIZE32MiB NOFILE256 core0 samepinnednightly1.95 CGU1/4cfg/2externalmodules/2MiBstack; independent private migrate source ABI and37500leaf accepted. No canonical/image/native.',argv=argv,compiler_sha256=old['compiler_sha256'],prior_exact_recipe=pin(prior),prior_actual_profile=pin(profile),prior_actual_receipt=pin(receipt),prior_actual_object=oldreceipt['object'],prior_nm_capture=oldreceipt['nm_join']['captures']['stdout'],source_leaf=pin(leaf),source_bindings=pin(P/'SOURCE-BINDINGS.json'),source_count=78,source_inputs=inputs,only_actual_Rust_file_delta='kernel/rust/sched_helpers.rs',C_postimage=bind['changes']['kernel/process.c']['after'],wall_seconds=120,retirement_seconds=6,profile='Sameacceptednightly1.95/CGU1/4cfg/2externmodule; no bootstrap/stubs/equivalence/cfg change',expected_U_delta=dict(before=559,after=560,removed=[],added=['process_sched_migrate_log_bridge']),whole_C_TU_default_link_native='OPEN',prior_leaf_qualification='37500 mocked callback/schedule lifetime pairs, actual types/header fixture; no production migration execution')
(D/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json').write_text(json.dumps(recipe,indent=2)+'\n');print(json.dumps(dict(recipe=pin(D/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json'),source_count=78,canonical_77_inputs_match_accepted_spin=True)))
