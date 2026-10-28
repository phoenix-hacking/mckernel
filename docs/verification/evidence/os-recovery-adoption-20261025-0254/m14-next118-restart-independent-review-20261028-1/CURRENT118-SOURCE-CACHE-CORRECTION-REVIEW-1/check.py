"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow retained publication DATA comparison. Hash nine affected source files only.
"""
from pathlib import Path
import hashlib,json
R=Path('/home/holden/mckernel');E=R/'docs/verification/evidence/os-recovery-adoption-20261025-0254';A=E/'ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-2';D=E/'restart-adoption-20261028T1911/CURRENT118-TYPED-INTEGRATION-1';S=E/'m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1';HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
oldp=A/'PUBLICATION-ROWS.PREPARED.json';newp=A/'PUBLICATION-ROWS.PREPARED.SOURCE-REFS-CORRECTED.json';sealp=S/'IMPLEMENTATION-SEAL.json';failurep=D/'STALE-CACHED-SOURCE-REFS.FAILURE.json';opp=D/'CURRENT118-OPERATION.ACTUAL.json'
assert ref(newp)['sha256']=='9a73ced9692a198b584458194a1f2298ff3f2eac58c4311249b30a0d21664c61'and ref(newp)['bytes']==438774
assert ref(oldp)['sha256']=='88681e4ab5d3ed0ea7c82cd96b0ebbcccdac8e81e3b65783098143524c489177'
assert ref(sealp)['sha256']=='b7dd561500a6f74747c53448951fa3c12c8f615f9f6ceeb4d6d4a1649b7f2f22'
assert ref(opp)['sha256']=='16eb1f31b82a2b13b38bbc3bd97bc64ea75cbcafb9e87b3ce9f2723c52837c2e'
old,new,seal,failure,op=[read(p)for p in [oldp,newp,sealp,failurep,opp]]
assert len(old['rows'])==len(new['rows'])==732 and len(seal['candidate_files'])==55 and len(op['subjects'])==34
assert len(failure['mismatches'])==9 and failure['source_seal_sha256']==ref(sealp)['sha256']
sealed={x['path']:x for x in seal['candidate_files']};subjects={v['path']:v for v in op['subjects'].values()}
assert len(sealed)==55
mismatches={x['path']:x for x in failure['mismatches']};assert len(mismatches)==9
correction=new['source_cache_ref_correction'];assert correction['previous_product']==ref(oldp) and correction['source_seal_sha256']==ref(sealp)['sha256']
assert set(correction['changed_paths'])==set(mismatches) and len(correction['changed_paths'])==9
assert {k:v for k,v in new.items()if k!='source_cache_ref_correction'and k!='rows'}=={k:v for k,v in old.items()if k!='rows'}
assert new['runtime_authority']is None and new['actual_fetched_commit']is None and not new['source_export_traversal_replayed']
transitions=[];unchanged=0;overlap=[]
for index,(before,after)in enumerate(zip(old['rows'],new['rows'])):
 if before==after:unchanged+=1;continue
 path=before['actual']['path'];assert path==after['actual']['path']and path in mismatches
 assert {k:v for k,v in before.items()if k!='actual'}=={k:v for k,v in after.items()if k!='actual'}
 row=mismatches[path];assert before['actual']==row['cached']and after['actual']==row['accepted_frozen_source']==sealed[path]
 actual=ref(Path(path));assert actual==sealed[path]
 if path in subjects:assert subjects[path]==actual;overlap.append(path)
 transitions.append(dict(index=index,old_cached_reference=before['actual'],accepted_sealed_actual_reference=actual,fetched_equivalent_path_unchanged=after['fetched_equivalent_path'],operation34_overlap=path in subjects))
assert unchanged==723 and len(transitions)==9 and {x['accepted_sealed_actual_reference']['path']for x in transitions}==set(mismatches)
assert len(overlap)==5
assert failure['compilers_or_native_runs']==0 and failure['nonce_status']=='RESERVED_UNUSED'
result=dict(scope=__doc__.splitlines()[0],decision='PASS_SOURCE_CACHE_CORRECTION_EXACT_NINE_SEALED_REFS_ONLY',inputs={k:ref(v)for k,v in [('preserved_original_publication_rows',oldp),('corrected_publication_rows',newp),('accepted_implementation_seal',sealp),('preserved_failure',failurep),('unchanged_operation34',opp)]},total_rows=732,corrected_rows=9,unchanged_rows=723,aliases_and_row_order_unchanged=True,source_files_hashed=9,other732_corpus_source_files_hashed=0,seal_records_compared_without_rehash=55,operation_subjects_compared_without_rehash=34,operation_overlap_matches=5,transitions=transitions,original_failure_and_RESERVED_UNUSED_nonce_retained=True,full_fetched_verification_or_admission_run=False,runtime_authority=None)
(HERE/'CHECKS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['transitions','inputs']}))
