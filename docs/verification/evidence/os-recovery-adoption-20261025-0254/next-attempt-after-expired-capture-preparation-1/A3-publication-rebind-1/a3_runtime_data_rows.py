"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical A3 direct-loader edges over the unchanged reviewed role collector.
No runtime consumer, frontier validator, guard or observation is invoked.
"""
from pathlib import Path
import hashlib,importlib.util,json
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
S=E/'next-attempt-after-expired-capture-preparation-1/A3-source-successor-1'
Q=E/'m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/publication-runtime-closure-correction-source-1/publication_runtime_closure.py'
Q_REF=dict(path=str(Q),bytes=15921,sha256='2b4c4be8e7dd2c1a0ff0c3b5853d09d5b21b5564d9a6d0ffb2fabf1feae58a1c')
raw=Q.read_bytes();assert len(raw)==Q_REF['bytes']and hashlib.sha256(raw).hexdigest()==Q_REF['sha256']
spec=importlib.util.spec_from_file_location('reviewed_publication_role_collector_4891',Q)
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
FRONTIER_INPUTS_REF=dict(path=str(S/'FRONTIER-INPUTS.SOURCE-ONLY.json'),bytes=5918,
 sha256='a46f6b41ea220d1297e92f1747b33311f4a11a61355714d94c6a971f1936910c')


def runtime_data_rows(binding_ref,selection_ref,operation_ref,read_bytes=None):
    rows=q.runtime_data_rows(binding_ref,selection_ref,operation_ref,read_bytes)
    c=q.Closure(read_bytes)
    binding=c.document(binding_ref,'A3_typed_binding')
    pins=c.control(FRONTIER_INPUTS_REF,'A3_FRONTIER_INPUTS_explicit_source_loader')
    frontier=c.control(binding['closed_unlaunched_frontier'],'A3_closed_unlaunched_frontier')
    packet=c.document(pins['evidence_packet'],'A2_original_failure_packet')
    q.need(frontier['evidence_packet']==pins['evidence_packet']and packet['evidence']==pins['evidence'],
           'exact declared A2 packet/receipt bindings; no payload provenance traversal')
    for key,row in pins['evidence'].items():c.selected_evidence(row,'A2_actual_receipt:'+key)
    c.selected_evidence(pins['physical_wrapper_join'],'A2_sixth_actor_actual_physical_wrapper')
    c.control(pins['reservation'],'A3_actual_nonce_reservation')
    c.add(Q_REF,'unchanged_reviewed_role_collector_source')
    by_path={r['actual']['path']:r for r in rows}
    for row in c.result():
        path=row['actual']['path']
        if path in by_path:
            q.need(by_path[path]['actual']==row['actual'],'conflicting A3 direct-loader BYTE ref')
            by_path[path]['declared_by']=sorted(set(by_path[path]['declared_by']+row['declared_by']))
        else:by_path[path]=row
    return [by_path[path]for path in sorted(by_path)]
