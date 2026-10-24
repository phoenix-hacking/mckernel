"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Freeze one production recipe/driver only. No compiler/test/CPU reservation.
"""
from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent;SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 rf=P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json';cf=P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json';driver=P/'run_production_batch_once.py'
 r=json.loads(rf.read_text());c=json.loads(cf.read_text());ast.parse(driver.read_text())
 assert len(r['source_inputs'])==78 and len(c['headers'])==73 and len(c['commands'])==14
 assert len(r['argv'])==48 and r['argv']==c['commands'][0]['argv']
 unionargv=json.loads(Path(r['accepted_prior_Rust_recipe']['path']).read_text())['argv'];assert r['argv'][:46]==unionargv[:46]
 assert r['argv'][-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage'] and r['argv'][-4:-2]==['-C','codegen-units=1']
 for row in r['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before']
 for row in [c['private_source'],c['canonical_preimage'],c['ABI_witness'],*c['headers'].values(),*c['canonical_headers'].values(),*r['accepted_union_refs']]:assert pin(Path(row['path']))==row
 extra=[pin(P/'SOURCE-BATCH-AND-ACCEPTED-SYNC-QUALIFICATION.json'),pin(P/'SOURCE-PREPARATION-FAILURE-1.json'),pin(P/'DRIVER-SOURCE-TOOL-INPUT-FAILURE-1.json'),r['accepted_sync795'],pin(Path(r['accepted_prior_object_not_rehashed']['receipt']['path']))]
 ready=dict(scope=SCOPE,status='ONE_COHERENT_PROCESS_BATCH_PRODUCTION_EXECUTABLE_READY_NO_GRANT_OR_JOB',Rust_recipe=pin(rf),C_recipe=pin(cf),driver=pin(driver),preparer=pin(P/'prepare_production_batch.py'),sealer=pin(Path(__file__)),evidence_bindings=extra,source_count=78,headers=73,source_identity=r['source_identity'],profile=dict(r['profile'],STACK=2<<20),compiler=pin(Path(r['argv'][6])),argv_count=48,cfg_count=4,CGU=1,prepared_commands=14,current_canonical_process=c['canonical_preimage'],current_canonical_process_Rust=r['source_inputs']['kernel/rust/process_helpers.rs']['canonical_before'],private_C=c['private_source'],private_Rust=r['source_inputs']['kernel/rust/process_helpers.rs']['private'],only_private_current78_override='kernel/rust/process_helpers.rs',expected_T_delta=r['expected_T_delta'],expected_U_delta=r['expected_U_delta'],accepted_sync795_reused=r['accepted_sync795'],sync_fixture_replayed=False,new_remap_range_log_functional_comparisons='NOT RUN; prior404-case extension remains source-only and is not one of these14 commands.',known_remap_source_correction='Only three analogous unsupported addr_of trailing commas removed; accepted corrected sync body/signature unchanged. Original sources/failures retained.',allocated_relocation_scope='Retired three C definitions and allocated C references absent; seven metadata imports resolved by typed C data; full caller bytes/relocation lists unchanged through partial, named-target counts separate from GOT/other machinery; no raw two-U oracle.',provider_debt='Existing phys_to_page C forwarding provider and existing backend/lock/log callbacks; static C metadata; other process.c bodies. These14 commands cannot prove native/runtime provider behavior.',failure_history=r['failure_history'],compiler_jobs=0,CPU_reservations=0,canonical_mutations=0,full_default_image_native_credit=False,requires='Root creates ROOT-GRANT.json with exact scope, CPU6, ordinary_jobs1 and this ready SHA before one ordinary job; fresh19GiB/floors/fullgap/CPU6 admission, O_EXCL outputs, h990dict/AST handlers, first unexpected STOPexpert/no auto retry. No compiler job/slot was started by preparation.')
 write(P/'EXECUTABLE-READY.NOT-GRANTED.json',ready)
 rootready=pin(P/'EXECUTABLE-READY.NOT-GRANTED.json')
 write(P/'ROOT-GRANT.EXAMPLE-NOT-AUTHORITY.json',dict(scope=SCOPE,CPU=6,ordinary_jobs=1,ready_sha256=rootready['sha256']))
 print(json.dumps(dict(scope=SCOPE,ready=rootready,Rust_recipe=ready['Rust_recipe'],C_recipe=ready['C_recipe'],driver=ready['driver'],source_identity=r['source_identity'],private_C=ready['private_C'],private_Rust=ready['private_Rust'],exact_command=['/home/holden/anaconda3/bin/python3',str(driver)],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
