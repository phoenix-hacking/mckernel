"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure binding controls; no observation, admission clock or execution.
"""
import ast,copy,json,tempfile,time
from pathlib import Path
import execution_contract as c
def reject(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('negative accepted')
def main():
    start=time.monotonic();p=c.pins();o=c.owner();checks=['retained19_and_outer_source_pins_exact']
    for name in c.FILES:
        if name.endswith('.py'):ast.parse((c.HERE/name).read_bytes())
    with tempfile.TemporaryDirectory(prefix='pure-bindings-',dir=c.HERE) as d:
        root=Path(d);nonce='0'*32;consumed=p['required_consumed_nonces'];assert nonce not in consumed
        l=dict(author='/root',complete_within_declared_current_boundary=True,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True,current_thread=p['thread'],consumed_nonces=consumed,reserved_abandoned_unconsumed_nonces=[])
        path=root/'ledger.json'
        def save(v):path.write_bytes(c.canonical(v));return c.ref(path)
        lr=save(l);c.ledger(lr,nonce);checks.append('current27_ledger_accepts_fresh_nonce')
        for label,mutator in [('missing_latest_consumed_nonce',lambda q:q.update(consumed_nonces=q['consumed_nonces'][:-1])),('duplicate_consumed',lambda q:q.update(consumed_nonces=q['consumed_nonces']+[consumed[0]])),('wrong_thread',lambda q:q.update(current_thread='old')),('abandoned_nonce',lambda q:q.update(reserved_abandoned_unconsumed_nonces=[nonce])),('consumed_nonce',lambda q:q.update(consumed_nonces=q['consumed_nonces']+[nonce]))]:
            bad=copy.deepcopy(l);mutator(bad);br=save(bad);reject(lambda:c.ledger(br,nonce));checks.append(label+'_rejected')
        lr=save(l);dummy=root/'reference.json';dummy.write_text('{}');reqref=dict(path=str(root/'request.json'),sha256='0'*64);request=dict(nonce=nonce)
        resources=dict(nonce_ledger=lr,observed_clocks=[1000,2000,3000],boot_id=o.BOOT,no_existing_heavy=True,physical_observer=p['pins']['observer']);rp=root/'resources.json';rp.write_bytes(c.canonical(resources))
        admission=dict(schema='mckernel.mcexec-default-current-admission.v1',status='ROOT_RESERVED_MCEXEC_DEFAULT_SOLE_HEAVY',author='/root',request=c.short(reqref),nonce=nonce,boot_id=o.BOOT,profile=o.LIBRARY_PREPARATION['profile'],one_heavy=True,resource_physical=c.ref(rp),consumed_nonces=consumed,nonce_ledger_complete=True,latest_postjoin_acceptance=c.ref(dummy),source_publication=c.ref(dummy),observed_clocks=resources['observed_clocks'],expires_wall=1120)
        c.validate_admission(admission,request,reqref,[1001,2001,3001]);checks.append('exact_admission_reference_and_clock_pass')
        reject(lambda:c.validate_admission(admission,request,reqref,[1120,2120,3120]));checks.append('expired120s_admission_rejected')
        bad=copy.deepcopy(admission);bad['one_heavy']=False;reject(lambda:c.validate_admission(bad,request,reqref,[1001,2001,3001]));checks.append('missing_oneheavy_rejected')
        bad=copy.deepcopy(admission);bad['profile']['jobs']=2;reject(lambda:c.validate_admission(bad,request,reqref,[1001,2001,3001]));checks.append('changed_profile_rejected')
    result=dict(status='PASS_PURE_OUTER_BINDING_CONTROLS',scope=p['scope'],checks=checks,seconds=time.monotonic()-start,actual_observe_calls=0,actual_process_calls=0,compiler_or_container=False,execution_authority=False)
    (c.HERE/'PURE-TEST-RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
