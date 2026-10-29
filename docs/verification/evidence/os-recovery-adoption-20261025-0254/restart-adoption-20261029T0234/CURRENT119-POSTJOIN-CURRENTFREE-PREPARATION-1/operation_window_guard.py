"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private actual-bound weekly operation consumer. Separate exact operation review required.
The exact new guardian owns fresh weekly allowance/controller/receipt validation.
"""
import hashlib,importlib.util,json,math,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
THREAD='01a18582-1fc6-77b1-bfb6-15c86483f579'
WINDOW_SHA256='c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'
WEEKLY_IDENTITY=dict(limit_id='codex',window_duration_mins=10080,resets_at=1793774133)
# Root binds these only after the exact weekly guardian/API/receipt review exists.
# None is deliberate: even configure/current_cutoffs refuse until data is sealed.
RUNTIME_BINDINGS={'weekly_limit_identity': {'limit_id': 'codex', 'window_duration_mins': 10080, 'resets_at': 1793774133}, 'window_sha256': 'c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596', 'billing_mode': 'included_only', 'allow_prepaid_fallback': False, 'armed_receipt': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/ACTUAL-CONTROLS-ARMED.json', 'bytes': 2021, 'sha256': '42c8b2a0045a7720f15ef591436a0158c2e08f219e30982d22f961c19be4c039'}, 'guardian': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/recovery-quota-confirmation-binding-1/actual-control-binding-2/guardian_guard.py', 'bytes': 18114, 'sha256': '5d991e2a0b43d624035d77d7b46f00d3600e351e4b0f5b1461a0c8371d4e2276'}, 'operation_cutoffs': [1793774133, 1556235.568922472, 1571573.6959699572]}

def need(ok,why):
 if not ok:raise ValueError(why)
def no_duplicates(pairs):
 result={}
 for key,value in pairs:
  need(key not in result,'duplicate JSON key');result[key]=value
 return result
def decode(raw):
 def constant(value):raise ValueError('nonfinite JSON constant: '+value)
 return json.loads(raw,object_pairs_hook=no_duplicates,parse_constant=constant)
def reference(path):
 path=Path(path);need(path.is_absolute()and not path.is_symlink()and path.is_file(),'absolute regular byte subject');raw=path.read_bytes()
 return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def authenticated(ref,declared_json=False):
 need(type(ref)is dict and set(ref)=={'path','bytes','sha256'}and reference(ref['path'])==ref,'authenticated exact BYTE reference');raw=Path(ref['path']).read_bytes()
 return decode(raw)if declared_json else raw
def triplet(values):
 need(type(values)in(list,tuple)and len(values)==3 and all(type(v)in(int,float)and math.isfinite(v)and v>=0 for v in values),'three finite epoch/MONOTONIC/BOOTTIME clocks')
 return tuple(values)
def bound():
 need(RUNTIME_BINDINGS is not None,'UNBOUND: actual reviewed weekly guardian/arm/schema/caps required')
 # This dictionary will be fixed in a separately reviewed source materialization.
 # Its receipt validator and guard must authenticate the actual weekly arm, fresh
 # included-only account/reset and complete controller identities on every call.
 need(RUNTIME_BINDINGS['weekly_limit_identity']==WEEKLY_IDENTITY and RUNTIME_BINDINGS['window_sha256']==WINDOW_SHA256,'exact weekly allowance/window')
 need(RUNTIME_BINDINGS['billing_mode']=='included_only'and RUNTIME_BINDINGS['allow_prepaid_fallback']is False,'no prepaid continuation')
 authenticated(RUNTIME_BINDINGS['armed_receipt'])
 authenticated(RUNTIME_BINDINGS['guardian'])
 return RUNTIME_BINDINGS

def validate_operation(successor,review,operation,subjects,clocks,boot_id=BOOT):
 """Existing adapter signature retained. This pure result is not execution authority."""
 clocks=triplet(clocks);binding=bound()
 need(operation in ('current118-postjoin-current64','bfd-postjoin-current62','current119-postjoin-current67')and boot_id==BOOT,'same exact readonly operation and boot')
 need(successor['schema']=='mckernel.explicit-new-window-operation-successor.v1'and successor['author']=='/root'and successor['operation']==operation and successor['decision']=='EXPLICIT_OPERATION_WINDOW_SUCCESSOR','explicit Root operation successor')
 need(successor['window_sha256']==WINDOW_SHA256 and successor['first_prepared_window_sha256']==WINDOW_SHA256 and successor['predecessor_cutoffs']is None,'new weekly operation, no historical release replay')
 need(not any(k in successor for k in ['credit_run_id','credit_ceiling','minimum_cumulative_spent']),'historical credit ledger is not operation spending authority')
 need(successor['weekly_limit_identity']==WEEKLY_IDENTITY and successor['billing_mode']=='included_only'and successor['allow_prepaid_fallback']is False,'exact current included-only weekly binding')
 limits=triplet(successor['operation_cutoffs']);maximum=triplet(binding['operation_cutoffs'])
 need(all(0<limit<=cap for limit,cap in zip(limits,maximum))and all(now<limit for now,limit in zip(clocks,limits)),'strict earliest actual weekly operation cutoffs')
 need(successor['subjects']==subjects and type(subjects)is dict and bool(subjects),'exact consumer source closure')
 need(review['schema']=='mckernel.independent-operation-window-review.v1'and review['decision']=='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR'and review['independent']is True and review['reviewer'].startswith('/root/')and review['reviewer']not in successor['source_owners']and review['operation']==operation and review['successor']==successor,'independent exact operation successor review')
 need(successor['source_owners']and '/root'in successor['source_owners'],'explicit source ownership')
 need(successor['guardian']==dict(source=binding['guardian'],entrypoint='guard'),'exact reviewed new weekly guardian')
 return limits

def guard(operation,successor_ref,review_ref,expected_subjects):
 """Future interface only; never called during this source preparation."""
 clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
 binding=bound();successor=authenticated(successor_ref,True);review=authenticated(review_ref,True)
 limits=validate_operation(successor,review,operation,expected_subjects,clocks,Path('/proc/sys/kernel/random/boot_id').read_text().strip())
 for subject in expected_subjects.values():authenticated(subject)
 source=binding['guardian'];authenticated(source)
 spec=importlib.util.spec_from_file_location('reviewed_weekly_only_guardian',source['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 result=triplet(module.guard())
 need(all(a<=b<limit for a,b,limit in zip(clocks,result,limits)),'fresh weekly guardian inside earliest strict cutoffs')
 return list(result)
