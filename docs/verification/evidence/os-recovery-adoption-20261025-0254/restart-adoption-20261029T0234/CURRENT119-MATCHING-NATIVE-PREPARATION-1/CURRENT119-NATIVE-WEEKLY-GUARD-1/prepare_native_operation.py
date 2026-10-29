"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only source/data formatter. No guard call, resource observation, staging or grant.
"""
from pathlib import Path
import argparse,json
import native_operation_guard as g
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);p.add_argument('--root-intent',type=Path,required=True);p.add_argument('--root-intent-sha256',required=True);a=p.parse_args();assert g.ref(a.root_intent)['sha256']==a.root_intent_sha256
q=g.decode(a.root_intent.read_bytes());assert set(q)=={'author','decision','runtime_authority','context','cutoffs'} and q['author']=='/root' and q['decision']=='PREPARE_CURRENT119_MATCHING235_NATIVE_OPERATION_SOURCE_DATA_ONLY' and q['runtime_authority'] is None
c=q['context'];subjects=g.context_subjects(c);binder=g.load(subjects['accepted_helper'],'pure_weekly_native_cap_binding');limits=binder.weekly_limits(g.read(c['armed_controls']),g.read(c['bootstrap_caps']));assert list(q['cutoffs'])==list(limits) and all(0<x<=maximum for x,maximum in zip(g.triplet(limits),g.MAXIMUM))
op=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation=g.OPERATION,window_sha256=g.WINDOW_SHA,first_prepared_window_sha256=g.WINDOW_SHA,weekly_limit_identity=g.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(limits),subjects=subjects,context=c,guardian=dict(source=subjects['guardian'],entrypoint='guard'),source_owners=['/root','/root/m14_integration_terra'])
out=D/'CURRENT119-NATIVE-OPERATION.PENDING-REVIEW.json'
with out.open('x')as f:json.dump(op,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(status='SOURCE_DATA_ONLY_NATIVE_OPERATION_PENDING_INDEPENDENT_REVIEW',operation=g.ref(out),source=g.ref(D/'native_operation_guard.py'),subject_count=len(subjects),runtime_authority=None),indent=2))
