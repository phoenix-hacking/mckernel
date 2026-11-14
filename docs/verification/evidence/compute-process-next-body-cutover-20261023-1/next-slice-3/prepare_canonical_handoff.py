# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import ast,json,hashlib,shutil,os
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-3'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def load(p):return json.loads(p.read_text())
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
bind=load(P/'SOURCE-BINDINGS.json');changes=bind['changes'];assert set(changes)=={'kernel/process.c','kernel/rust/sched_helpers.rs'}
for rel,row in changes.items():assert pin(R/rel)==row['before'] and pin(Path(row['after']['path']))==row['after']
RT=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk6-successor-1');owner=RT/'source/native_diagnostic_container_owner.py';assert pin(owner)['sha256']=='fbedb881439d6db6b0aa13ecea2d7dfa31737607cc1fc1f150a2e65ac4d89ce3'
tree=ast.parse(owner.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_HASHES' for t in n.targets)];assert len(nodes)==1;pins=ast.literal_eval(nodes[0].value);assert isinstance(pins,dict) and len(pins)==167
canonical={str(R/rel) for rel in changes};identities={(Path(p).stat().st_dev,Path(p).stat().st_ino) for p in canonical};direct=[p for p in pins if p in canonical];resolved=[p for p in pins if str(Path(p).resolve()) in canonical];aliases=[p for p in pins if (Path(p).stat().st_dev,Path(p).stat().st_ino) in identities];assert not direct and not resolved and not aliases
cohortpath=RT/'COHORT-BINDINGS.json';cohort=load(cohortpath);cohortchecked=[]
for name,row in cohort.items():assert pin(Path(row['path']))==row;cohortchecked.append(row)
jsonchecked=[];exacthits=[];mismatches=[]
# Finite selected167 map only. Read its JSON metadata for exact canonical refs;
# never execute/import authority code or hash large images/modules/objects.
for path,expected in pins.items():
 if path.endswith('.json'):
  q=Path(path);raw=q.read_bytes();actual=hashlib.sha256(raw).hexdigest();jsonchecked.append(dict(path=path,sha256=actual,bytes=len(raw)))
  if actual!=expected:mismatches.append(dict(path=path,expected=expected,actual=actual))
  if any(x.encode() in raw for x in canonical):exacthits.append(path)
assert not exacthits and not mismatches,(exacthits,mismatches)
links=RT/'source/CURRENT68-SDK6-AUTHORITY-LINKS.json';authority=load(links);authoritychecked={}
for name,row in authority['proofs'].items():assert pin(Path(row['path']))==row;authoritychecked[name]=row
thin=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/thin-inputs.json');oldthin=load(thin);frozen=[]
for rel in changes:
 row=oldthin['lineage']['overlays'][rel];q=Path(row['frozen_path']);qp=pin(q);assert qp['sha256']==row['after_sha256'];st=q.stat();assert str(q.resolve()) not in canonical and (st.st_dev,st.st_ino) not in identities
 frozen.append(dict(relative=rel,frozen_input=qp,canonical_target_distinct=True,source='Selected LONG map image thin-inputs lineage/overlays, not live canonical'))
imageproof=load(Path(authority['proofs']['image_build_acceptance']['path']));imagereceipt=Path(imageproof['producer_receipt']['path']);assert pin(imagereceipt)==imageproof['producer_receipt'];image=load(imagereceipt)
sdkproof=load(Path(authority['proofs']['SDK6_source_preparation']['path']));sdkreq=Path(sdkproof['request']['path']);assert pin(sdkreq)==sdkproof['request'];sdkrequest=load(sdkreq);assert not any(x in sdkreq.read_text() for x in canonical)
rootaccept=E/'production-fullcrate-1/INDEPENDENT-ACTUAL-RUST-ACCEPTANCE.ROOT-RECORD.json';accept=load(rootaccept);assert accept['verdict']=='PASS_PRIVATE_MIGRATION_LOG_ACTUAL_PRODUCTION_RUST_OBJECT_ONLY' and accept['actual_receipt_sha256']=='739accc925947afc864f785b14dc69af3a6618cde861efadbc0fd992c7223607'
exclusion=dict(scope=SCOPE,status='PASS_FINITE_ACTIVE167_AND_SELECTED_TRANSITIVE_AUTHORITY_EXCLUSION_ONLY',owner=pin(owner),extraction='AST literal_eval SOURCE_HASHES assignment only; no imports/module execution',map_count=167,direct_canonical_paths=direct,resolved_path_aliases=resolved,inode_aliases=aliases,cohort=pin(cohortpath),cohort_rows_checked=cohortchecked,pinned_JSON_rows_checked=jsonchecked,exact_canonical_strings_in_selected_JSON=exacthits,pinned_JSON_hash_mismatches=mismatches,authority_links=pin(links),selected_authority_refs_verified=authoritychecked,transitive_frozen_image_rows=frozen,current_image_source_derivative=image['source_derivative_sha256'],current_image_materialization=image['materialization_sha256'],current_image_source_manifest=image['source_manifest_sha256'],image_producer_receipt=pin(imagereceipt),SDK6_module_request=pin(sdkreq),SDK6_candidate_root=sdkrequest['candidate_root'],SDK6_input_root=sdkrequest['input_root'],interpretation='Active167 runtime pins and selected SDK6/image authority derivatives consume their frozen/materialized sources and retained artifacts, not either canonical edit target. Exclusion is not physical runtime retirement or a new guest/build release.',source_or_runtime_mutations=0)
(P/'ACTIVE-SDK6-LONG167-PIN-EXCLUSION.json').write_text(json.dumps(exclusion,indent=2)+'\n')
# Executable argv is handoff DATA ONLY. Root executes after its own decision.
code='''from pathlib import Path
import hashlib,json
root=Path('/home/holden/mckernel')
rows=ROWS
payloads={}
for rel,row in rows.items():
 target=root/rel;source=Path(row['after']['path']);data=source.read_bytes()
 assert hashlib.sha256(target.read_bytes()).hexdigest()==row['before']['sha256'],('preimage',rel)
 assert hashlib.sha256(data).hexdigest()==row['after']['sha256'],('private postimage',rel)
 payloads[rel]=data
for rel,data in payloads.items():
 (root/rel).write_bytes(data)
for rel,row in rows.items():
 assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==row['after']['sha256'],('canonical postimage',rel)
print(json.dumps({'status':'PASS_EXACT_TWO_CANONICAL_POSTIMAGES','paths':list(rows)}))
'''.replace('ROWS',repr(changes),1)
ready=dict(scope=SCOPE,status='READY_FOR_ROOT_EXACT_TWO_FILE_INTEGRATION_NOT_EXECUTED',changes=changes,current_canonical_preimages_match=True,patch=pin(P/'PRIVATE-PRODUCTION.patch'),pin_exclusion=pin(P/'ACTIVE-SDK6-LONG167-PIN-EXCLUSION.json'),original_actual_leaf=pin(P/'ACTUAL-LEAF-RECEIPT.json'),original_leaf_export=pin(P/'LEAF-EXPORT-RECEIPT.json'),original_actual78_Rust=pin(P/'production-fullcrate-1/ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json'),independent_source_leaf_acceptance='Root parent explicit PASS_PRIVATE_MIGRATION_LOG_SOURCE_ABI_AND_ACTUAL_LEAF_ONLY from m14_build_release_review; reused by root actualRust acceptance record',independent_actual_Rust_acceptance=pin(rootaccept),root_only_apply_argv=['/home/holden/anaconda3/bin/python3','-I','-B','-c',code],apply_contract='Verify both exact canonical preimages and both private postimages BEFORE any writes; write only these2existing paths; verify both exactpostimages. Root owns actual canonical integration receipt/decision. No worker execution.',remaining=dict(C_declarative_data='Existing C __verbose descriptor data retained to preserve original Cfile/function/line selectors. Selected C runtime helper body replaced by Rust; fallback C body preserved.',exact_GCC14whole_process_TU='OPEN',defaultkernel_defaultlink='OPEN',native_logging='OPEN',wholefile_or_zeroC_credit=False),canonical_mutation_executed=False,compiler_build_guest_root_jobs=0,CPU_held=False)
(P/'CANONICAL-INTEGRATION-READY.json').write_text(json.dumps(ready,indent=2)+'\n')
# Candidate12 data successor only; frozen11 source/request/controller untouched.
B=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-11/default-image-preparation-1');handoff=load(B/'next-build-preparation-1/WHOLE-CANDIDATE11-HANDOFF.json');review=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-11/default-image-preparation-1/next-build-preparation-1/INDEPENDENT-ACTUAL-PREPARATION.ROOT-RECORD.json';assert review.is_file()
matroot=Path(handoff['source_identity']['path']);source_rows=[]
for rel,row in changes.items():
 before=pin(matroot/rel);assert before['sha256']==row['before']['sha256'];source_rows.append(dict(relative=rel,candidate11_exact_before=before,accepted_candidate12_postimage=row['after']))
consumer_delta=[dict(boundary='selected PUBLIC process.c',before='T process_sched_migrate_log_bridge, no declarative imported descriptor',after='No C function body/Tlog; one32byte __verbose D process_sched_migrate_debug with originalfile/function/line422/default0/fmtNULL'),dict(boundary='actual production Rust object',before='U process_sched_migrate_log_bridge',after='oneTlog, noUlog, oneUprocess_sched_migrate_debug; undefined560->560 exactswap; preservemigration/timer/spin/memoryexports'),dict(boundary='GCC14 full process ABI appendix',before='M14_MIGRATION_HEADER_ABI_ASSERTIONS takes &process_sched_migrate_log_bridge from current C function',after='Retain actual process.h getter assertion. Replace old Cfunction-body assertion with actual descriptor declaration/type/size/alignment/pointerfield assertions; no fake C prototype or bitfield offsetof. ActualGCC14bitfield/wholeTU proof remainsOPEN.'),dict(boundary='final kernel defaultlink',before='unique Clog T and RustUlog, uniqueRustgetter/body',after='uniqueRustlog T and Cdescriptor D; no unresolved log/descriptor; unchanged all-existing defaultlink/wholeundefinedempty gates')]
prep=dict(scope=SCOPE,status='CANDIDATE12_COHERENT_SUCCESSOR_DATA_ONLY_NOT_MATERIALIZED_NOT_RELEASED',base_candidate11_handoff=pin(B/'next-build-preparation-1/WHOLE-CANDIDATE11-HANDOFF.json'),base_candidate11_independent_acceptance=pin(review),base_source_identity=handoff['source_identity'],base_source_manifest_sha256=handoff['source_manifest_sha256'],base_source_derivative_sha256=handoff['source_derivative_sha256'],base_materialization_sha256=handoff['materialization_sha256'],base_request=handoff['request'],base_driver=pin(B/'native_rust_exact_mckernel_image_offline.py'),exact_source_delta=source_rows,all_other_candidate11_source_entries_and_modes='Preserve unchanged; no source materialization/copy performed by this data preparation',accepted_product_patch=pin(P/'PRIVATE-PRODUCTION.patch'),integration_handoff=pin(P/'CANONICAL-INTEGRATION-READY.json'),actual_Rust_object_acceptance=pin(rootaccept),required_consumer_contract_delta=consumer_delta,next_operation='After root canonicalintegration, existing productionstage owner derive fresh candidate12 source/controller/materializer/request pins coherently from accepted11 plus these2postimages and exact changed consumer/data contract. Separate ordinary preparation grant/actualpurevalidation/independent sourceprofile/heavy release required. Do not reuse old11 logging provider assertion.',actual_candidate12_source_manifest=None,actual_candidate12_materialization=None,actual_candidate12_request=None,actual_candidate12_pure_consumer=None,heavy_or_root_release=None,reservation=None,canonical_or_candidate11_mutations=0,compiler_build_guest_jobs=0,wholeTU_defaultlink_native='OPEN')
(P/'CANDIDATE12-SOURCE-SUCCESSOR-DATA.PREPARED.json').write_text(json.dumps(prep,indent=2)+'\n')
for name in ['prepare_canonical_handoff.py','ACTIVE-SDK6-LONG167-PIN-EXCLUSION.json','CANONICAL-INTEGRATION-READY.json','CANDIDATE12-SOURCE-SUCCESSOR-DATA.PREPARED.json']:shutil.copyfile(P/name,E/name)
print(json.dumps(dict(integration=pin(P/'CANONICAL-INTEGRATION-READY.json'),exclusion=pin(P/'ACTIVE-SDK6-LONG167-PIN-EXCLUSION.json'),candidate12=pin(P/'CANDIDATE12-SOURCE-SUCCESSOR-DATA.PREPARED.json'),changes={rel:dict(before=x['before']['sha256'],after=x['after']['sha256']) for rel,x in changes.items()},canonical_writes=False,CPU_held=False)))
