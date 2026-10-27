"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only candidate for one combined independent metadata/execution review.
A conditional metadata document is never published as actual until its real PASS.
"""
from pathlib import Path
import json,hashlib,time,sys,importlib.util
A=Path(__file__).resolve().parent;D=A.parent/'sdk7-postgrowth-final-static-1';sys.path.insert(0,str(D))
spec=importlib.util.spec_from_file_location('reviewed_sdk_adapter',D/'sdk-reference-shape-correction-1/sdk7_authority_adapter.OWNER-REFERENCE-SHAPE.SOURCE-ONLY.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,v):
 with p.open('xb') as f:f.write(m.canonical(v))
b=json.loads((A/'PREQUERY-BUNDLE.json').read_bytes());origin=json.loads(m.ORIGIN.read_bytes());window=m.load_window();q=json.loads((A/'QUERY-CAPTURE/stdout').read_bytes());live=json.loads((A/'LIVE-CURRENT.json').read_bytes());req=json.loads(Path(b['request']['path']).read_bytes());j=json.loads((A/'QUERY-WHOLE-JOIN.json').read_bytes());m.joined(j)
assert j['captures']['stdout']['sha256']==ref(A/'QUERY-CAPTURE/stdout')['sha256']
b.update(query=ref(A/'QUERY-CAPTURE/stdout'),query_join=ref(A/'QUERY-WHOLE-JOIN.json'))
reservation=dict(status='ROOT_RESERVED_DAEMON7_SOLE_HEAVY',author='/root',nonce=req['nonce'],request=b['request'],window=b['parent_window'],operation_head=b['operation_head'],profile=origin['profile'],one_heavy=True,jobs_total=4,host_reserve_bytes=4*2**30,expires_wall=min(live['clock']['wall']+120,window['deadline_epoch']),query_capture=b['query_join'],capture_helper=origin['capture_helper'],actual_aggregate_memory_bytes=18*2**30,owned_holder=q['owned_holder'],clock=q['clock'],aggregate_planning_memory_GiB='21.7531',HEAD_frozen='a9550f6629b1fe378607a561666d67951c758e3a')
write(A/'ACTUAL-ROOT-RESERVATION.json',reservation);b['reservation']=ref(A/'ACTUAL-ROOT-RESERVATION.json')
review=dict(decision='PASS_DAEMON7_CURRENT_ADMISSION',reviewer='/root/custody_release_review',implementation_ownership=False,independent=True,execution_release=False,bindings={k:b[k] for k in ('request','parent_window','operation_head','latest_operation','live_observation','query','query_join','reservation','accepted_growth_stage')},historical_source_approval=origin['source_approval'],current_source_map=b['current_source_map'],current_source_review=b['current_source_review'],current_source_publication=b['current_source_publication'],growth_closure=b['growth_closure'],seven_commands=origin['seven_commands'],profile=origin['profile'])
raw=m.canonical(review);future=dict(path=str(A/'ACTUAL-METADATA-ADMISSION-REVIEW.json'),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());b['root_admission_review']=future
write(A/'METADATA-REVIEW.PROPOSAL.json',dict(status='PENDING_ACTUAL_INDEPENDENT_PASS_NOT_AN_ACCEPTANCE',proposed_document=review,proposed_reference=future))
def conditional_load(r,document=True):
 if r==future:return review if document else raw
 return m.bound(r,document)
draft=m.adapt(b,origin,window,m.actual_clock(),load=conditional_load);payload=m.release_payload(draft)
write(A/'FINAL-BUNDLE.PENDING-REVIEW.json',b);write(A/'EXECUTION-REVIEW-PAYLOAD.PENDING.json',payload)
info=dict(status='PENDING_BOTH_ACTUAL_INDEPENDENT_DECISIONS_NO_RELEASE',metadata_proposed_reference=future,reviewed_release_payload_sha256=hashlib.sha256(m.canonical(payload)).hexdigest(),payload=ref(A/'EXECUTION-REVIEW-PAYLOAD.PENDING.json'),live_clock=live['clock'],query_clock=q['clock'],expires_wall=reservation['expires_wall'],nonce=req['nonce'],query_holder=q['owned_holder'],age_seconds=time.time()-live['clock']['wall']);write(A/'REVIEW-NEEDED.json',info);print(json.dumps(info))
