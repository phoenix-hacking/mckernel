"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only data binding; no compiler, Docker, resource observation or entry.
Fresh nonce comes from Root; this does not reserve or consume the campaign ledger.
"""
import argparse,json,os
from pathlib import Path
import execution_contract as c
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['check','inputs','propose','publish'])
    for n in ('nonce','ledger','source-review','admission','execution-review'):p.add_argument('--'+n)
    for n in ('ledger','source-review','admission','execution-review'):p.add_argument('--'+n+'-sha256')
    a=p.parse_args();o=c.owner();here=c.HERE;reqpath=here/'ADOPT-REQUEST.json'
    def supplied(name):
        path=getattr(a,name.replace('-','_'));sha=getattr(a,name.replace('-','_')+'_sha256');c.need(path and sha,'exact supplied '+name);r=dict(path=str(Path(path).resolve()),sha256=sha);return r,c.bound(r)
    if a.mode=='check':
        print(json.dumps(dict(status='PASS_RETAINED19_AND_OUTER_SOURCE_PINS_ONLY',source_sha256=c.pins()['source_sha256'],outer_source_sha256=c.source_map(),execution_authority=False)));return
    if a.mode=='inputs':
        lr,_=supplied('ledger');c.need(a.nonce,'Root fresh nonce');c.ledger(lr,a.nonce)
        c.need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary Root coordinator identity')
        for path in [reqpath,here/'STATIC-INPUTS-PREPARED.NOT-RELEASED.json']:c.need(not os.path.lexists(path),'fresh metadata namespace')
        parent=o.OUTPUT_PARENT
        if not parent.exists():parent.mkdir(mode=0o700)
        c.need(o.node(parent)['mode']==0o700 and not parent.is_symlink(),'private exact output parent')
        candidate=parent/('native-running-modules-candidate-'+a.nonce);evidence=parent/('native-running-modules-owner-'+a.nonce);admission=parent/('native-running-modules-admission-'+a.nonce)
        c.need(not any(os.path.lexists(x) for x in (candidate,evidence,admission)),'fresh candidate/evidence/admission')
        candidate.mkdir(mode=0o700);back=o.BACKING.stat()
        r=dict(schema='mckernel.daemon-soleheavy-sdk-request.v1',candidate_sha=o.CANDIDATE,image_id=o.IMAGE,nonce=a.nonce,request_path=str(reqpath),preparation=dict(path=str(o.PREPARATION),sha256=o.PREPARATION_SHA),driver=dict(path=str(o.DRIVER),sha256=o.BFD_DRIVER_SHA),input_root=str(o.PREPARATION.parent),candidate_root=str(candidate),owner_evidence_root=str(evidence),lease_path=str(o.LEASE),common_exclusion_path=str(o.COMMON),basis_identity=o.node(o.BASIS),candidate_identity=o.node(candidate),input_identity=o.node(o.PREPARATION.parent),boot_id=o.BOOT,timeout=o.LIBRARY_PREPARATION['timeout'],disk_budget_bytes=o.LIBRARY_PREPARATION['output_budget_bytes'],capture_budget_bytes=o.LIBRARY_PREPARATION['capture_budget_bytes'],terminal_policy='remove-owned-terminal',output_parent_identity=o.node(parent),backing_identity=dict(o.node(o.BACKING),size=back.st_size,nlink=back.st_nlink))
        c.write(reqpath,r);c.write(here/'STATIC-INPUTS-PREPARED.NOT-RELEASED.json',dict(status='ROOT_STATIC_EXECUTOR_INPUTS_ONLY',request=c.ref(reqpath),nonce_ledger=lr,runtime_authority=False));print(json.dumps(dict(request=c.ref(reqpath),entry=False)));return
    rr=c.ref(reqpath);request=json.loads(reqpath.read_bytes());proposal=here/'RELEASE-PAYLOAD.PROPOSAL.json'
    if a.mode=='propose':
        sr,review=supplied('source-review');ar,admission=supplied('admission');outer=c.source_map()
        c.need(review.get('decision')=='PASS_SOURCE' and review.get('implementation_ownership') is False and review.get('reviewer') not in (None,'','/root') and review.get('source_sha256')==c.pins()['source_sha256'] and review.get('outer_source_sha256')==outer,'exact independent retained19 plus outer source review')
        c.validate_admission(admission,request,rr,c.campaign())
        payload=dict(schema='mckernel.daemon-soleheavy-sdk-release.v1',status='PASS_EXECUTION_RELEASE',execution_count=1,request=c.short(rr),nonce=request['nonce'],boot_id=o.BOOT,fetched_source_verified=True,terminal_policy='remove-owned-terminal',historical_observer=dict(path=str(o.HISTORICAL_OBSERVER),sha256=o.HISTORICAL_OBSERVER_SHA,prefix=list(o.HISTORICAL_PREFIX),timeout_seconds=30),source_sha256=c.pins()['source_sha256'],outer_execution=dict(wrapper=c.short(c.ref(here/'run_mcexec_current.py')),source_sha256=outer),source_review=sr,current_admission=ar,author='/root')
        c.write(proposal,payload);print(json.dumps(dict(proposal=c.ref(proposal),reviewed_release_payload_sha256=__import__('hashlib').sha256(c.canonical(payload)).hexdigest(),entry=False)));return
    er,review=supplied('execution-review');payload=json.loads(proposal.read_bytes())
    c.need(review.get('decision')=='PASS_EXECUTION' and review.get('implementation_ownership') is False and review.get('reviewer') not in (None,'','/root') and review.get('reviewed_release_payload_sha256')==__import__('hashlib').sha256(c.canonical(payload)).hexdigest(),'exact independent execution review')
    c.need(payload['request']==c.short(rr) and payload['nonce']==request['nonce'],'actual request unchanged')
    release=here/'ACTUAL-REVIEWED-RELEASE.json';c.write(release,dict(payload,execution_review=er));print(json.dumps(dict(release=c.ref(release),entry=False)))
if __name__=='__main__':main()
