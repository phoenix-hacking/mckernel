"""Functional install-only Root DATA publication; source only.

The already-reviewed parent owns authority, proof verification and lease close.
This module emits DATA on its actual fd 1 and never closes an operation FD.
"""
import fcntl
import hashlib
import json
import os
import stat
import time

MAX_RECORD=2*1024*1024
_STATE='NEW'
_HANDOFF=None


def _hex64(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def _canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')


def _remaining(caps):
    if type(caps) is not dict or set(caps)!={'boot_ns','mono_ns','utc_ns'} or any(type(value) is not int or value<=0 for value in caps.values()):
        raise ValueError('actual absolute caps required')
    return min(caps['boot_ns']-time.clock_gettime_ns(time.CLOCK_BOOTTIME),
               caps['mono_ns']-time.monotonic_ns(),caps['utc_ns']-time.time_ns())


def _self_identity():
    if os.getuid()!=0 or os.geteuid()!=0:raise ValueError('actual root parent required')
    pid=os.getpid()
    if type(pid) is not int or pid<=1:raise ValueError('actual parent PID required')
    with open('/proc/self/stat','r') as stream:
        raw=stream.read(65537)
    if len(raw)>65536 or ')' not in raw:raise ValueError('actual self stat unavailable')
    prefix,body=raw.rsplit(')',1)
    try:observed_pid=int(prefix.split('(',1)[0].strip())
    except (ValueError,IndexError):raise ValueError('actual self PID unavailable')
    fields=body.split()
    if observed_pid!=pid or len(fields)<20 or fields[0] in ('Z','X','x') or not fields[19].isdigit():
        raise ValueError('actual self birth unavailable')
    if os.getpid()!=pid:raise ValueError('actual parent changed')
    return {'pid':pid,'birth':fields[19]}


def _write_record(value,caps,identity):
    if _remaining(caps)<=0:raise TimeoutError('output cap expired')
    data=_canonical(value)
    if not 0<len(data)<=MAX_RECORD:raise ValueError('bounded DATA record required')
    before=os.fstat(1)
    flags=fcntl.fcntl(1,fcntl.F_GETFL)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or (flags&os.O_ACCMODE)==os.O_RDONLY:
        raise ValueError('actual writable regular stdout capture required')
    count=os.write(1,data)
    if type(count) is not int or count!=len(data):raise OSError('short DATA write; no retry')
    os.fsync(1)
    after=os.fstat(1)
    if ((before.st_dev,before.st_ino,before.st_mode,before.st_uid,before.st_gid,before.st_nlink)!=
        (after.st_dev,after.st_ino,after.st_mode,after.st_uid,after.st_gid,after.st_nlink)):
        raise ValueError('stdout capture identity changed')
    if _remaining(caps)<=0 or _self_identity()!=identity:raise TimeoutError('output cap or parent identity changed')
    return hashlib.sha256(data).hexdigest()


def _validate_result(nonce,result):
    if (type(result) is not dict or result.get('status')!='INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ' or
        result.get('nonce')!=nonce or result.get('authority') is not None or result.get('native_release') is not False or
        result.get('native_currentfree') is not None or result.get('lease_disposition')!='HELD' or
        type(result.get('proof')) is not dict or type(result.get('independent_verification')) is not dict):
        raise ValueError('already verified held result required')
    proof=result['proof'];terminal=result.get('terminal_evidence')
    if (proof.get('nonce')!=nonce or proof.get('native_release') is not False or
        proof.get('native_currentfree') is not None or proof.get('global_descendants')!='UNKNOWN' or
        type(terminal) is not dict or set(terminal)!={'keeper','installer'}):
        raise ValueError('truthful scope and terminal evidence required')
    keeper,installer=terminal['keeper'],terminal['installer']
    if (type(keeper) is not dict or set(keeper)!={'pid','birth','direct_wait_status'} or
        type(installer) is not dict or set(installer)!={'pid','birth','pidfd_terminal','keeper_direct_wait_status'}):
        raise ValueError('terminal roles')
    for role in (keeper,installer):
        if type(role['pid']) is not int or role['pid']<=1 or type(role['birth']) is not str or not role['birth'].isdigit():
            raise ValueError('terminal actual PID/birth')
    if (type(keeper['direct_wait_status']) is not int or keeper['direct_wait_status']!=0 or
        type(installer['keeper_direct_wait_status']) is not int or installer['keeper_direct_wait_status']!=0 or
        installer['pidfd_terminal'] is not True):raise ValueError('terminal roles not positively completed')
    if (_canonical(proof.get('keeper'))!=_canonical({'pid':keeper['pid'],'birth':keeper['birth']}) or
        _canonical(proof.get('installer'))!=_canonical({'pid':installer['pid'],'birth':installer['birth'],'pgid':installer['pid']}) or
        type(proof.get('installer_wait_status')) is not int or proof['installer_wait_status']!=installer['keeper_direct_wait_status']):
        raise ValueError('verified proof and actual role identities differ')


def publish_full(nonce,profile_sha256,verified_result,caps):
    """Publish full DATA once before lease disposition; return exact wire SHA."""
    global _STATE,_HANDOFF
    if _STATE!='NEW':raise ValueError('DATA publication already attempted')
    if not _hex64(nonce) or not _hex64(profile_sha256):raise ValueError('nonce/profile binding')
    _validate_result(nonce,verified_result)
    identity=_self_identity()
    terminal=verified_result['terminal_evidence']
    if len({identity['pid'],terminal['keeper']['pid'],terminal['installer']['pid']})!=3:
        raise ValueError('distinct actual operation roles required')
    record={'record_type':'ROOT_INSTALL_FULL_DATA_V1','scope':'ROOT_CODE_INSTALL_ONLY',
            'nonce':nonce,'profile_sha256':profile_sha256,'root_parent':identity,
            'native_release':False,'native_currentfree':None,'result':verified_result}
    _STATE='FULL_IN_PROGRESS'
    try:
        digest=_write_record(record,caps,identity)
        _HANDOFF={'nonce':nonce,'profile_sha256':profile_sha256,'full_sha256':digest,'root_parent':identity}
        _STATE='FULL_DURABLE'
        return digest
    except BaseException:
        _STATE='UNKNOWN'
        raise


def publish_disposition(nonce,profile_sha256,full_sha256,lease_disposition,outcome,caps):
    """Publish one truthful final disposition; never retry an ambiguous write."""
    global _STATE
    if _STATE!='FULL_DURABLE' or type(_HANDOFF) is not dict:raise ValueError('full DATA not durable')
    if (nonce!=_HANDOFF['nonce'] or profile_sha256!=_HANDOFF['profile_sha256'] or full_sha256!=_HANDOFF['full_sha256'] or
        (lease_disposition,outcome) not in (('HELD','UNKNOWN'),('CLOSURE_UNKNOWN','UNKNOWN'),
                                            ('VERIFIED_CLOSED','UNKNOWN'),('VERIFIED_CLOSED','COMPLETE'))):
        raise ValueError('final disposition binding')
    identity=_self_identity()
    if identity!=_HANDOFF['root_parent']:raise ValueError('different actual Root parent')
    record={'record_type':'ROOT_INSTALL_DISPOSITION_DATA_V1','scope':'ROOT_CODE_INSTALL_ONLY',
            'nonce':nonce,'profile_sha256':profile_sha256,'root_parent':identity,'full_sha256':full_sha256,
            'lease_disposition':lease_disposition,'outcome':outcome,'native_release':False,'native_currentfree':None}
    _STATE='DISPOSITION_IN_PROGRESS'
    try:
        digest=_write_record(record,caps,identity)
        _STATE='COMPLETE'
        return digest
    except BaseException:
        _STATE='UNKNOWN'
        raise
