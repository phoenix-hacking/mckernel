"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only metadata formatter, not a receipt/review/grant or an execution operation.
"""
from pathlib import Path
import argparse,json,re
import runtime_guard as g
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);p.add_argument('--root-intent',type=Path,required=True);p.add_argument('--root-intent-sha256',required=True);a=p.parse_args()
assert g.ref(a.root_intent)['sha256']==a.root_intent_sha256
q=g.decode(a.root_intent.read_bytes());assert set(q)=={'author','decision','runtime_authority','context','cutoffs'} and q['author']=='/root' and q['decision']=='PREPARE_CONVERSION_FIRST_PRODUCER_OPERATION_SOURCE_DATA_ONLY' and q['runtime_authority'] is None
c=q['context'];assert set(c)=={'request','nonce','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps','candidate_snapshot_manifest','reuse_descriptor'} and c['armed_controls']==g.ARM
for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps','candidate_snapshot_manifest','reuse_descriptor'):g.auth(c[k])
assert type(c['nonce']) is str and re.fullmatch('[0-9a-f]{32}',c['nonce']) and c['nonce']!='e984210ca59641b299cf42d392eb953b'
f=g.read(g.FIXED);assert c['request']==f['request'] and c['candidate_snapshot_manifest']==f['snapshot_manifest'] and c['reuse_descriptor']==f['reuse_descriptor'] and c['bootstrap_caps']==f['bootstrap_caps']
ledger=g.validate_frontier(c)
subjects=g.fixed_subjects();subjects.update({'root:'+k:c[k]for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps','candidate_snapshot_manifest','reuse_descriptor')})
accepted=g.load(subjects['accepted_helper'],'pure_root65_operation_preparation');[g.auth(row) for row in subjects.values()]
limits=accepted.weekly_limits(g.read(c['armed_controls']),g.read(c['bootstrap_caps']));assert list(q['cutoffs'])==list(limits) and all(0<x<=maximum for x,maximum in zip(g.triplet(limits),g.MAXIMUM))
operation=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation='conversion-first-three-command-build',window_sha256=g.WINDOW_SHA,first_prepared_window_sha256=g.WINDOW_SHA,weekly_limit_identity=g.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(limits),subjects=subjects,context=c,guardian=dict(source=subjects['guardian'],entrypoint='guard'),source_owners=['/root','/root/m14_integration_terra'])
out=D/'CONVERSION-FIRST-OPERATION.PENDING-REVIEW.json'
with out.open('x') as stream:json.dump(operation,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(dict(status='SOURCE_DATA_ONLY_OPERATION_PENDING_INDEPENDENT_REVIEW',operation=g.ref(out),source=g.ref(D/'runtime_guard.py'),subject_count=len(subjects),runtime_authority=None),indent=2))
