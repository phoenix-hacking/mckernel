"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only metadata formatter, not a receipt/review/grant or an execution operation.
"""
from pathlib import Path
import argparse,json,re
import runtime_guard as g
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);p.add_argument('--root-intent',type=Path,required=True);p.add_argument('--root-intent-sha256',required=True);a=p.parse_args()
assert g.ref(a.root_intent)['sha256']==a.root_intent_sha256
q=g.decode(a.root_intent.read_bytes());assert set(q)=={'author','decision','runtime_authority','context','cutoffs'} and q['author']=='/root' and q['decision']=='PREPARE_CURRENT119_PRODUCER_OPERATION_SOURCE_DATA_ONLY' and q['runtime_authority'] is None
c=q['context'];assert set(c)=={'request','nonce','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps'} and c['current_free']==g.read(g.FIXED)['current_free'] and c['armed_controls']==g.ARM
for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps'):g.auth(c[k])
assert type(c['nonce']) is str and re.fullmatch('[0-9a-f]{32}',c['nonce']) and c['nonce']!='e984210ca59641b299cf42d392eb953b'
ledger=g.read(c['current_ledger']);assert c['nonce']not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']
subjects=g.fixed_subjects();subjects.update({'root:'+k:c[k]for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps')})
accepted=g.load(subjects['accepted_helper'],'pure_root65_operation_preparation');accepted.accepted_metadata(c,g.read(c['current_free']),ledger);accepted.accepted_chain(c)
limits=accepted.weekly_limits(g.read(c['armed_controls']),g.read(c['bootstrap_caps']));assert list(q['cutoffs'])==list(limits) and all(0<x<=maximum for x,maximum in zip(g.triplet(limits),g.MAXIMUM))
operation=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation='current119-build',window_sha256=g.WINDOW_SHA,first_prepared_window_sha256=g.WINDOW_SHA,weekly_limit_identity=g.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(limits),subjects=subjects,context=c,guardian=dict(source=subjects['guardian'],entrypoint='guard'),source_owners=['/root','/root/m14_integration_terra'])
out=D/'CURRENT119-OPERATION.PENDING-REVIEW.json'
with out.open('x') as stream:json.dump(operation,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(dict(status='SOURCE_DATA_ONLY_OPERATION_PENDING_INDEPENDENT_REVIEW',operation=g.ref(out),source=g.ref(D/'runtime_guard.py'),subject_count=len(subjects),runtime_authority=None),indent=2))
