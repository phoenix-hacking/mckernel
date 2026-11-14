"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent current118 source/data/publication check, no guard or observer calls.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT=Path('/home/holden/mckernel')
E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
A=E/'ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-2'
H=A/'FINITE-REVIEW-HANDOFF'
C=E/'m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/prepared118-current63-1/cohort'

def ref(path):
    p=Path(path);assert p.is_absolute() and p.is_file() and not p.is_symlink()
    first=p.stat();raw=p.read_bytes();last=p.stat()
    assert (first.st_dev,first.st_ino,first.st_size,first.st_mtime_ns,first.st_ctime_ns)==(last.st_dev,last.st_ino,last.st_size,last.st_mtime_ns,last.st_ctime_ns)
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def auth(row):
    assert set(row)=={'path','bytes','sha256'} and ref(row['path'])==row
    return Path(row['path'])

def checked(row):return json.loads(auth(row).read_bytes())
def read(path):return json.loads(Path(path).read_bytes())

def main():
    binding=C/'REVIEWER-ACTUAL-BINDINGS.json'
    assert ref(binding)['sha256']=='70dd0e0b2deec01b6666b9eda3717f167a4cb07a189a178adfdb62644ef6ce33'
    b=read(binding);refs=b['static_refs'];assert len(refs)==26
    for row in refs.values():auth(row)
    assert b['reviewer']=='/root/observerreview' and b['Root_must_not_execute_approver'] is True
    assert b['admission']==str(A) and b['nonce']=='1d3f2239b2884cedbd9e7dbe248ae1aa' and b['actual_execution_authority'] is None
    assert b['authorized_cutoffs']==[1793253600.0,1035704.5689393478,1051042.6959879305]
    p=checked(refs['profile']);x=checked(refs['input_export']);q=checked(refs['request_payload']);adoption=checked(refs['request_adoption']);ledger=checked(refs['nonce_ledger']);boundary=checked(refs['current_boundary'])
    assert p['runtime_authority'] is None and len(p['exact_commands'])==4
    assert p['CPU']==[2,3,4,5] and p['memory_bytes']==12<<30 and p['pids']==512
    assert p['actual_nonce']==q['nonce']==adoption['nonce']==b['nonce']
    assert p['request_sha256']==refs['request_payload']['sha256']==x['request_sha256']==adoption['request_sha256']
    assert adoption['profile']==refs['profile'] and adoption['input_export']==refs['input_export'] and adoption['request']==refs['request_payload']
    assert p['actual_root_adoption']==q['source_adoption']==adoption['source_adoption']==refs['source_adoption']
    assert p['native_custody_clearance']==boundary['native_custody_clearance']==refs['native_custody_clearance']
    assert boundary['nonce_ledger']==refs['nonce_ledger']
    assert b['nonce'] not in ledger['consumed_nonces'] and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
    schema=checked(refs['observer_schema']);schema_review=checked(refs['observer_schema_review'])
    assert schema['observer']==refs['observer_source'] and schema_review['reviewed_observer_schema']==refs['observer_schema']
    assert schema_review['independent'] is True and schema_review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING'
    for key in ['source_review','mechanical_review','current_boundary_review']:
        review=checked(refs[key]);assert review['independent'] is True and review['implementation_ownership'] is False and review['decision'].startswith('PASS')
    assert p['inputs']['retained_count']==8 and p['inputs']['replaced_count']==3
    export=p['inputs']['source_directory_exports'][0];manifest=checked(export['manifest']);assert len(manifest['files'])==123
    rust=[row['snapshot'] for row in manifest['files']]
    expected=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in p['inputs']['postimages']]+rust+[r['source'] for r in p['inputs']['external_relative_modules']]
    assert x['qualified_readonly_files']==expected and x['SDK21_recompiled'] is False and x['source6153_entries']==6153
    for row in expected:auth(row)
    pub=checked(refs['source_publication'])
    assert refs['source_publication']['sha256']=='8b8aabe99a2687edbe85ca4458302a741dee32a9b113b32385de28056f1d343b'
    assert pub['commit']=='8d8a20cfc4206e1c7d2a5439b70cf18a86f17bb7' and len(pub['rows'])==736 and pub['runtime_authority'] is None
    assert pub['status'].startswith('PASS_FETCHED_CURRENT118_') and pub['unchanged_accepted_SDK'] is True and pub['passed_compiler_prefix_replayed'] is False
    published={}
    for row in pub['rows']:
        actual=row['actual'];auth(actual)
        gitpath=row['fetched_equivalent_path']
        blob=subprocess.run(['git','cat-file','blob',pub['commit']+':'+gitpath],cwd=ROOT,capture_output=True,check=True).stdout
        assert len(blob)==actual['bytes'] and hashlib.sha256(blob).hexdigest()==actual['sha256'], 'fetched actual byte mismatch '+actual['path']
        assert actual['path'] not in published
        published[actual['path']]=actual
    for key in ['profile','runner','worker','holder_source','publisher_source','request_payload','capture_source','finite_verifier','handoff_common','hot_predicates','root_capture_source','publisher_adapter','aggregate_job_policy','observer_schema','observer_schema_review']:
        assert published[refs[key]['path']]==refs[key]
    bootstrap=read(A/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')
    assert bootstrap['nonce']==b['nonce'] and bootstrap['maximum_invocations']==1 and bootstrap['permanent_mutex_path']=='/run/lock/mckernel-development.lock'
    for key,name in [('source','holder_source'),('runner','runner'),('worker','worker'),('profile','profile')]:assert bootstrap[key]==refs[name]
    rb=read(C/'ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json')
    assert rb['Root_capture_owner']=='/root' and rb['admission']==str(A) and rb['nonce']==b['nonce'] and rb['runtime_authority'] is None
    for key in ['capture_source','finite_verifier','publisher_source']:assert rb[key]==refs[key]
    policy=checked(refs['aggregate_job_policy']);auth(policy['original_authorization'])
    assert policy['aggregate_build_jobs_max']==7 and policy['heavy_compiler_jobs_reserved']==4 and policy['ordinary_CPU6_jobs_reserved']==1 and policy['total_reserved_build_jobs']==5 and policy['physical_occupancy_claim'] is False
    absent=[A/n for n in ['OUTPUT','HOLDER','ROOT-PREHOLDER-PHYSICAL-1.json','ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json','ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json','ACTUAL-INDEPENDENT-BUILD-EXECUTION-REVIEW.json','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json']]+[H/n for n in ['PREWARM_READY.json','ROOT-PHYSICAL-CAPTURE.ONCE-CLAIM.json','ROOT-HELD-CAPTURE.COMPLETE.json','INDEPENDENT-FINITE-REVIEW.PASS.json']]
    for path in absent:assert not os.path.lexists(path), 'runtime namespace already present '+str(path)
    result=dict(scope=__doc__.splitlines()[0],decision='PASS_CURRENT118_EXACT_STATIC_COLD_CLOSURE_NO_RUNTIME_QUERIES',reviewer='/root/observerreview',independent=True,implementation_ownership=False,bindings=ref(binding),profile=refs['profile'],source_publication=refs['source_publication'],published_commit=pub['commit'],independent_fetched_blob_checks=736,static_refs=26,qualified_readonly_files=len(expected),closed_Rust_files=len(rust),nonce=b['nonce'],unused_nonce=True,runtime_namespaces_absent=[str(z) for z in absent],root_capture_bindings=ref(C/'ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json'),holder_bootstrap=ref(A/'ROOT-HOLDER-BOOTSTRAP-GRANT.json'),observer_schema=refs['observer_schema'],observer_schema_review=refs['observer_schema_review'],guard_calls=0,observer_queries=0,finite_runs=0,producer_runs=0,native_cases=0,runtime_authority=None)
    with (H/'INDEPENDENT-STATIC-REVIEW.CORRECTION1.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(decision=result['decision'],result=ref(H/'INDEPENDENT-STATIC-REVIEW.CORRECTION1.json'),blobs=736,static_refs=26,qualified_files=len(expected))))

if __name__=='__main__':main()
