"""Functional McKernel OS/apps and Rust migration only; no security testing.
Finite Startup grant publication and one NORMAL entry after exact independent PASS.
No resource refresh, retry, outer controller or alternate command interface.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
import stat
import subprocess
import time

BASE = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process235-native-entry-source-1')
STARTUP = BASE/'root-adopted-process235-entry-1'
AUTH = STARTUP/'ROOT-CONDITIONAL-ONCE-ENTRY-AUTHORIZATION.json'
STATIC = STARTUP/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'
PENDING = STARTUP/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json'
RESOURCE = STARTUP/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json'
PUBLICATION = STARTUP/'ACTUAL-STATIC-SOURCE-PUBLICATION.json'
REVIEW = STARTUP/'ACTUAL-INDEPENDENT-NATIVE-EXECUTION-REVIEW.json'
CLAIM = STARTUP/'ROOT-ONCE-ENTRY.CLAIM.json'
GRANT = STARTUP/'ROOT-ACTUAL-ONE-NATIVE-M15-STARTUP-GRANT.json'
REFUSAL = STARTUP/'ROOT-ONCE-ENTRY.REFUSAL.json'
JOINED = STARTUP/'ROOT-ONCE-ENTRY.JOINED.json'
SPAWNED = STARTUP/'ROOT-ONCE-ENTRY.SPAWNED.json'
STDOUT = STARTUP/'ROOT-ONCE-ENTRY.stdout'
STDERR = STARTUP/'ROOT-ONCE-ENTRY.stderr'
HELPER = STARTUP/'run_native_startup_capture.py'
GUARD = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')/'operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py'
STATIC_SHA = 'ROOT_FINAL_STATIC_SHA256'
HELPER_SHA = '32354b7717eb63e100ad04309c7cfcb4bcd75badf5d05704617e2e6487a6de68'
GUARD_SHA = '1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'
PROFILE_SHA = 'e5584b2c6fecbec0660dfeda3193468cf78af6a9dee0f4cc849e64abbdca1081'
NONCE = 'd21f4e17faf1b0b806419b1860bd0598'
CASE = 'P-M06-01-process-exec-wait-235B'
REVIEWER = '/root/daemon_execution_review'
HELPER_ARGV = ['/home/holden/anaconda3/bin/python3','-I','-B',str(HELPER)]
_guard = None
_entry_clamps = None
_native_helper_pid = None

def need(ok, why):
    if not ok:
        raise ValueError(why)

def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def read_file(path):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path,'canonical exact input path')
    descriptor = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(descriptor,'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 32*2**20,'bounded regular input')
        raw = stream.read(32*2**20+1)
        after = os.fstat(stream.fileno())
    need(len(raw) == before.st_size and (before.st_ino,before.st_size,before.st_mtime_ns) ==
         (after.st_ino,after.st_size,after.st_mtime_ns),'stable complete input')
    return raw

def file_ref(path):
    raw = read_file(path)
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def load_json(path):
    return json.loads(read_file(path))

def checked(reference, path=None):
    if path is not None:
        need(reference['path'] == str(path),'exact selected input path')
    need(file_ref(Path(reference['path'])) == reference,'exact input reference drift')
    return load_json(Path(reference['path']))

def durable_create(path, value):
    descriptor = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(descriptor,'wb') as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    parent = os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)

def guard_now():
    global _guard
    if _guard is None:
        need(file_ref(GUARD)['sha256'] == GUARD_SHA,'literal actual v2 guard')
        spec = importlib.util.spec_from_file_location('root3_once_literal_actual_guard',GUARD)
        _guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_guard)
        need(_guard.__file__ == str(GUARD) and _guard.__spec__.origin == str(GUARD),'true guard context')
    return _guard.guard(),_guard.current_cutoffs()

def clamps_for(packet, resource):
    global _entry_clamps
    if _entry_clamps is None:
        need(file_ref(HELPER)['sha256'] == HELPER_SHA,'unchanged normal entry helper')
        tree = ast.parse(read_file(HELPER))
        nodes = [node for node in tree.body if
                 (isinstance(node,ast.FunctionDef) and node.name in ('cutoff_triplet','entry_clamps')) or
                 (isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'AUTHORIZED_FIXED_LIMITS' for t in node.targets))]
        namespace = {'math':math}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER)+':UNCHANGED_PURE_CLAMPS_ONLY','exec'),namespace)
        _entry_clamps = namespace['entry_clamps']
    clocks,cutoffs = guard_now()
    return _entry_clamps(clocks,resource['observed_clocks'],resource['fixed_cutoffs'],packet['fixed_cutoffs'],cutoffs)

def bind_inputs(auth_sha):
    need(file_ref(AUTH)['sha256'] == auth_sha,'Root conditional authorization bytes')
    auth = load_json(AUTH)
    need(auth['decision'] == 'CONDITIONALLY_AUTHORIZE_ONE_EXACT_ORIGINAL_STARTUP_ENTRY_AFTER_PASS'
         and auth['authorized'] is True and auth['authorized_by'] == '/root'
         and type(auth['maximum_invocations']) is int and auth['maximum_invocations'] == 1,'Root one-shot authorization')
    need(auth['reviewer'] == REVIEWER and auth['nonce'] == NONCE and auth['case'] == CASE,'fixed Startup identity')
    need(auth['bridge_sha256'] == file_ref(Path(__file__))['sha256'],'adopted bridge bytes')
    need(file_ref(STATIC)['sha256'] == STATIC_SHA and auth['static_bindings'] == file_ref(STATIC),'sealed Startup static')
    static = load_json(STATIC)
    need(static['nonce'] == NONCE and static['expected_case'] == CASE and auth['exact_argv'] == static['exact_argv'],'sealed case/nonce/argv')
    need(hashlib.sha256(encoded(static['profile'])).hexdigest() == PROFILE_SHA and auth['profile_sha256'] == PROFILE_SHA,'exact approved profile')
    packet = load_json(PENDING)
    need(packet['decision'] == 'PENDING_ONE_EXACT_NATIVE_M15_STARTUP_RELEASE' and packet['nonce'] == NONCE
         and packet['expected_case'] == CASE and packet['maximum_invocations'] == 1,'exact pending Startup entry')
    need(packet['static_bindings'] == file_ref(STATIC) and packet['exact_argv'] == static['exact_argv']
         and packet['profile'] == static['profile'],'pending source/profile/argv binding')
    for key in ('source_authority','case_capability','stage_map_acceptance','root_ledger35','manifest',
                'scratch_manifest_stage','artifact_acceptance'):
        need(packet[key] == static[key],'pending/static binding '+key)
        checked(packet[key])
    need(packet['capture_sources'] == static['capture_sources'],'five unchanged helper bindings')
    for reference in packet['capture_sources'].values():
        need(file_ref(Path(reference['path'])) == reference,'selected helper source drift')
    need(file_ref(HELPER)['sha256'] == HELPER_SHA,'normal helper source')
    resource = checked(packet['fresh_resource_physical'],RESOURCE)
    publication = checked(packet['source_publication'],PUBLICATION)
    need(publication['status'] == 'PASS_ACTUAL_PUSH_FETCH_AND_EXACT_NATIVE_STATIC_BLOBS','actual source publication')
    need(file_ref(STATIC) in publication['files'] and all(r in publication['files'] for r in packet['capture_sources'].values()),'published exact static/helpers')
    need(resource['root_ledger35'] == static['root_ledger35'] and resource['actual_latest_operation_postjoin_acceptance'] == static['latest_serial_operation_physical_acceptance']
         and resource['no_existing_heavy'] is True and resource['pids_current'] == 0,'exact resource/current occupancy')
    refs = dict(authorization=file_ref(AUTH),static=file_ref(STATIC),pending=file_ref(PENDING),
                resource=file_ref(RESOURCE),publication=file_ref(PUBLICATION))
    return auth,packet,resource,refs

def validate_review(packet, refs):
    review = load_json(REVIEW)
    need(review['decision'] == 'PASS_EXECUTION' and review['reviewer'] == REVIEWER
         and review['implementation_ownership'] is False and review['maximum_invocations'] == 1,'exact independent PASS only')
    need(review['nonce'] == NONCE and review['payload_sha256'] == refs['pending']['sha256']
         and review['pending_execution_packet'] == refs['pending'],'PASS binds actual pending bytes')
    need(review['exact_argv'] == packet['exact_argv'] and review['static_bindings'] == refs['static']
         and review['fresh_resource_physical'] == refs['resource'] and review['source_publication'] == refs['publication'],'PASS exact source/resource/publication')
    need(review['manifest'] == packet['manifest'] and review['root_ledger35'] == packet['root_ledger35']
         and review['source_authority'] == packet['source_authority'],'PASS exact manifest/ledger/authority')
    return file_ref(REVIEW)

def enter_once(auth_sha):
    global _native_helper_pid
    need(os.getuid() == os.geteuid() == 1000,'ordinary Root-agent process context')
    for path in (CLAIM,GRANT,REFUSAL,JOINED,SPAWNED,STDOUT,STDERR):
        need(not path.exists(),'one-shot output already exists: '+str(path))
    auth,packet,resource,refs = bind_inputs(auth_sha)
    clamps_for(packet,resource)
    # Only the exact atomic independent PASS file is awaited. Resource/pending
    # must already exist; there is no resource refresh or second operation.
    while not REVIEW.exists():
        clamps_for(packet,resource)
        time.sleep(.25)
    review_ref = validate_review(packet,refs)
    # Recheck all immutable evidence and the real account/live clamp immediately
    # before the durable claim. Any refusal ends this invocation without retry.
    _,packet,resource,rechecked = bind_inputs(auth_sha)
    need(rechecked == refs and validate_review(packet,refs) == review_ref,'no evidence drift while waiting')
    clamps = clamps_for(packet,resource)
    durable_create(CLAIM,dict(status='ONE_STARTUP_ENTRY_CLAIMED_NO_RETRY',nonce=NONCE,case=CASE,
        maximum_invocations=1,operator_pid=os.getpid(),references=refs,execution_review=review_ref,
        normal_helper_argv=HELPER_ARGV,clampsUsed=clamps))
    grant = dict(author='/root',decision='GRANTED_ONE_EXACT_NATIVE_M15_STARTUP',maximum_invocations=1,
        nonce=NONCE,exact_argv=packet['exact_argv'],execution_review=review_ref,
        fresh_resource_physical=refs['resource'],pending_execution_packet=refs['pending'],
        runtime_authority='ONE_EXACT_NATIVE_M15_STARTUP_ORIGINAL_CONTRACT_OPERATION')
    durable_create(GRANT,grant)
    clamps_for(packet,resource)
    child = None
    try:
        with STDOUT.open('xb') as stdout, STDERR.open('xb') as stderr:
            child = subprocess.Popen(HELPER_ARGV,stdout=stdout,stderr=stderr)
            _native_helper_pid = child.pid
            evidence_error = None
            try:
                durable_create(SPAWNED,dict(status='NORMAL_NATIVE_HELPER_STARTED_NOT_JOINED',
                    operator_pid=os.getpid(),native_helper_pid=child.pid,nonce=NONCE,
                    normal_helper_argv=HELPER_ARGV,claim=file_ref(CLAIM),grant=file_ref(GRANT)))
            except BaseException as error:
                # A receipt writer failure must not skip the one owned wait.
                evidence_error = type(error).__name__+': '+str(error)
            returncode = child.wait()
            stdout.flush(); stderr.flush()
            os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
        durable_create(JOINED,dict(status='NORMAL_NATIVE_HELPER_POSITIVELY_JOINED',nonce=NONCE,
            operator_pid=os.getpid(),native_helper_pid=child.pid,returncode=returncode,
            direct_child_joined=True,streams_closed=True,stdout=file_ref(STDOUT),stderr=file_ref(STDERR),
            claim=file_ref(CLAIM),grant=file_ref(GRANT),evidence_error=evidence_error,native_acceptance=False))
        need(evidence_error is None,'spawn receipt writer failed after positive child wait')
        return returncode
    except BaseException:
        # Claim/grant remain consumed even if launch/wait becomes uncertain.
        # Existing normal owner/entry controls retain cleanup ownership.
        raise

def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--authorization-sha256',required=True)
    args = parser.parse_args()
    try:
        return enter_once(args.authorization_sha256)
    except BaseException as error:
        try:
            durable_create(REFUSAL,dict(status='REFUSED_OR_UNCERTAIN_NO_RETRY',nonce=NONCE,
                error=type(error).__name__+': '+str(error),native_helper_pid=_native_helper_pid,
                claim_present=CLAIM.exists(),grant_present=GRANT.exists()))
        except FileExistsError:
            pass
        raise

if __name__ == '__main__':
    raise SystemExit(main())
