#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
SDK13 compile/link driver proposal; requires independently admitted container owner.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import subprocess
import sys
import time

PROFILE = Path('/work/sdk13-profile.json')
PROFILE_SHA256 = None  # SOURCE ONLY: must be replaced by independently reviewed profile hash
EVIDENCE = Path('/work/sdk13-driver-evidence')
CWD = '/work/output/build/kernel'
STAGES = ('Configure ON composite', 'Post-generation verification')
PER_STAGE_TIMEOUT = 600


def read_profile():
    fd = os.open(PROFILE, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 1024 * 1024:
            raise ValueError('profile must be bounded regular single-link file')
        data = b''
        while len(data) <= 1024 * 1024:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            data += chunk
        after = os.fstat(fd)
        if len(data) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('profile changed during read')
        if hashlib.sha256(data).hexdigest() != PROFILE_SHA256:
            raise ValueError('profile hash mismatch')
        value = json.loads(data)
        commands = value['commands']
        if PROFILE_SHA256 is None or len(commands) != 2 or tuple(x['stage'] for x in commands) != STAGES:
            raise ValueError('wrong command stages')
        if any(x['cwd'] != '/work' or not isinstance(x['argv'], list) or not x['argv'] or
               not all(isinstance(a, str) and '\0' not in a for a in x['argv']) for x in commands):
            raise ValueError('wrong command schema')
        return value,commands
    finally:
        os.close(fd)


def write_new(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


# Exact policy is bound by the parent and checked without emitting inherited values.
CLEAN_ENV = {'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C',
             'TMPDIR':'/tmp','HOSTNAME':'mckernel-sdk13'}
SOURCE_MAP = Path('/work/sdk13-source-map.json')
MOUNT_MANIFEST = Path('/work/sdk13-effective-mounts.json')
MAX_MOUNTINFO = 4 * 1024 * 1024
MAX_MAP = 64 * 1024 * 1024
MAX_ENTRIES = 500000
MAX_BYTES = 32 * 1024**3


def read_regular(path, maximum, expected_sha=None, identity=None, collect=True):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>maximum:
            raise ValueError('mounted file type or size mismatch: '+str(path))
        if identity is not None and (before.st_dev,before.st_ino,before.st_mode)!=(identity['device'],identity['inode'],identity['mode']):
            raise ValueError('mounted file identity mismatch: '+str(path))
        digest=hashlib.sha256();chunks=[];length=0
        while True:
            chunk=os.read(fd,65536)
            if not chunk: break
            length+=len(chunk)
            if length>maximum: raise ValueError('mounted file growth: '+str(path))
            digest.update(chunk)
            if collect: chunks.append(chunk)
        end=os.fstat(fd); named=os.lstat(path)
        keys=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
        if length!=before.st_size or any(getattr(before,k)!=getattr(end,k) or getattr(before,k)!=getattr(named,k) for k in keys):
            raise ValueError('mounted file changed during read: '+str(path))
        if expected_sha is not None and digest.hexdigest()!=expected_sha:
            raise ValueError('mounted file content mismatch: '+str(path))
        return b''.join(chunks) if collect else length
    finally:os.close(fd)


def decode_mount_path(raw):
    # mountinfo escapes only these four characters. Unknown escapes fail closed.
    replacements={'040':' ','011':'\t','012':'\n','134':'\\'}
    out=[];i=0
    while i<len(raw):
        if raw[i]=='\\':
            code=raw[i+1:i+4]
            if len(code)!=3 or code not in replacements: raise ValueError('invalid mountinfo escape')
            out.append(replacements[code]);i+=4
        else:out.append(raw[i]);i+=1
    return ''.join(out)


def validate_mountinfo(raw, expected):
    if len(raw)>MAX_MOUNTINFO:raise ValueError('mountinfo too large')
    text=raw.decode('utf8'); seen={}
    for line in text.splitlines():
        fields=line.split(' ')
        if len(fields)<10 or '-' not in fields:raise ValueError('malformed mountinfo')
        target=decode_mount_path(fields[4]);opts=fields[5].split(',')
        if target in seen:raise ValueError('duplicate effective mount point')
        seen[target]=opts
    for target,readonly in expected.items():
        opts=seen.get(target)
        if opts is None or ('ro' not in opts if readonly else 'rw' not in opts):
            raise ValueError('missing or wrong effective mount: '+target)
    for target in seen:
        if (target=='/src' or target.startswith('/src/') or target=='/work' or target.startswith('/work/') or target=='/nightly' or target.startswith('/nightly/') or target=='/out' or target.startswith('/out/')) and target not in expected:
            raise ValueError('unexpected nested mount: '+target)
    return len(seen)


def masked(path, shadows):
    return any(path==x or path.startswith(x+'/') for x in shadows)


def validate_tree(target, tree, shadows, counters):
    root=Path(target);rows=tree['entries']
    if not isinstance(rows,list) or len(rows)>MAX_ENTRIES:raise ValueError('tree entry bound')
    expected={}
    for row in rows:
        rel=row.get('relative'); kind=row.get('kind')
        if not isinstance(rel,str) or rel in ('','.') or rel.startswith('/') or '..' in Path(rel).parts or str(Path(rel))!=rel:
            raise ValueError('invalid manifest tree path')
        full=target+'/'+rel
        if masked(full,shadows):continue
        if rel in expected or kind not in ('file','dir','symlink'):raise ValueError('invalid tree entry')
        expected[rel]=row
    actual=set()
    def walk_error(exc): raise exc
    for current,dirs,files in os.walk(root,topdown=True,followlinks=False,onerror=walk_error):
        dirs.sort();files.sort();kept=[]
        for name in dirs+files:
            path=Path(current)/name; rel=path.relative_to(root).as_posix();full=target+'/'+rel
            if masked(full,shadows):continue
            row=expected.get(rel)
            if row is None:raise ValueError('unexpected tree path: '+full)
            st=os.lstat(path);actual.add(rel);counters['entries']+=1
            if counters['entries']>MAX_ENTRIES:raise ValueError('source entry bound')
            if stat.S_ISLNK(st.st_mode):
                if row.get('kind')!='symlink' or os.readlink(path)!=row.get('target'):raise ValueError('tree symlink mismatch: '+full)
                resolved=path.resolve(strict=True)
                if resolved!=root and root not in resolved.parents:raise ValueError('tree symlink escapes mounted root: '+full)
            elif stat.S_ISDIR(st.st_mode):
                if row.get('kind')!='dir':raise ValueError('tree directory mismatch: '+full)
                kept.append(name)
            elif stat.S_ISREG(st.st_mode):
                if row.get('kind')!='file' or st.st_size!=row.get('bytes') or not isinstance(row.get('sha256'),str) or len(row['sha256'])!=64:raise ValueError('tree file size/hash mismatch: '+full)
                counters['bytes']+=st.st_size
                if counters['bytes']>MAX_BYTES:raise ValueError('source byte bound')
                read_regular(path,st.st_size,row['sha256'],collect=False)
            else:raise ValueError('unsupported tree file type: '+full)
        dirs[:]=kept
    if actual!=set(expected):raise ValueError('tree inventory mismatch: '+target)


def validate_effective_view(profile, source_map_sha, manifest_sha, manifest_identity, driver_sha):
    if dict(os.environ)!=CLEAN_ENV:raise ValueError('container environment differs')
    args_identity={'device':manifest_identity[0],'inode':manifest_identity[1],'mode':manifest_identity[2]}
    manifest=json.loads(read_regular(MOUNT_MANIFEST,8*1024*1024,manifest_sha,args_identity))
    if manifest.get('schema')!='mckernel.sdk13.effective-mounts.v1' or manifest.get('profile_sha256')!=PROFILE_SHA256 or manifest.get('source_map_sha256')!=source_map_sha or manifest.get('driver_sha256')!=driver_sha:
        raise ValueError('mount manifest bindings differ')
    source_map=json.loads(read_regular(SOURCE_MAP,MAX_MAP,source_map_sha))
    if source_map.get('schema')!='mckernel.sdk13.source-map.v1' or source_map.get('profile_sha256')!=PROFILE_SHA256 or source_map.get('proposal_sha256')!='b9e0fbad132ae43fcd79459b9f2baee776679b4a972e4647d583f0d8ba26b594':
        raise ValueError('source map binding differs')
    read_regular(Path(__file__),8*1024*1024,driver_sha)
    expected_mounts={};manifest_rows=manifest.get('mounts')
    if not isinstance(manifest_rows,list) or len(manifest_rows)!=33:raise ValueError('mount manifest count')
    rows=profile['readonly_shared_inputs']+profile['readonly_config_and_eight_objects']
    expected_targets=['/work']+[row['container'] for row in rows]+['/work/sdk13-profile.json','/work/sdk13-driver.py','/work/sdk13-source-map.json']
    if [r.get('target') for r in manifest_rows]!=expected_targets:raise ValueError('mount manifest order differs')
    for i,row in enumerate(manifest_rows):
        target=row['target']; readonly=i!=0
        if row.get('readonly') is not readonly:raise ValueError('mount read-only flag differs')
        st=os.lstat(target)
        if (st.st_dev,st.st_ino,st.st_mode)!=(row.get('device'),row.get('inode'),row.get('mode')):
            raise ValueError('mounted source identity differs: '+target)
        expected_mounts[target]=readonly
    expected_mounts[str(MOUNT_MANIFEST)]=True
    fd=os.open('/proc/self/mountinfo',os.O_RDONLY|os.O_CLOEXEC)
    try:
        chunks=[];total=0
        while True:
            chunk=os.read(fd,65536)
            if not chunk:break
            total+=len(chunk)
            if total>MAX_MOUNTINFO:raise ValueError('mountinfo too large')
            chunks.append(chunk)
    finally:os.close(fd)
    mount_count=validate_mountinfo(b''.join(chunks),expected_mounts)
    for row in rows:
        if 'sha256' in row:
            length=read_regular(Path(row['container']),max(1,row.get('bytes',MAX_BYTES)),row['sha256'],collect=False)
            if 'bytes' in row and length!=row['bytes']:raise ValueError('mounted source length differs')
    trees=source_map.get('trees')
    if not isinstance(trees,dict) or set(trees)!={'/src','/src/kernel/rust','/nightly'}:raise ValueError('tree map differs')
    roots={r['container']:r['host'] for r in rows if r['container'] in trees}
    if any(trees[t].get('root')!=roots.get(t) for t in trees):raise ValueError('tree root binding differs')
    counters={'entries':0,'bytes':0}
    all_targets=list(expected_mounts)
    for target in ('/src','/src/kernel/rust','/nightly'):
        shadows=[x for x in all_targets if x.startswith(target+'/')]
        validate_tree(target,trees[target],shadows,counters)
    return {'status':'PASS_EFFECTIVE_MOUNTS_SOURCE_ENV','mount_count':mount_count,
            'verified_tree_entries':counters['entries'],'verified_tree_bytes':counters['bytes'],
            'profile_sha256':PROFILE_SHA256,'source_map_sha256':source_map_sha,
            'mount_manifest_sha256':manifest_sha,'driver_sha256':driver_sha}


def require_source_binding():
    raise RuntimeError('SOURCE_ONLY: successor profile, mount validation and owner admission are unbound')

def main():
    require_source_binding()
    if len(sys.argv)!=7 or any(re.fullmatch(r'[0-9a-f]{64}',x) is None for x in (sys.argv[1],sys.argv[2],sys.argv[6])):
        raise ValueError('SDK13 authenticated driver arguments missing')
    ident=tuple(int(x) for x in sys.argv[3:6])
    if any(x<=0 for x in ident):raise ValueError('SDK13 manifest identity invalid')
    profile,commands = read_profile()
    proof=validate_effective_view(profile,sys.argv[1],sys.argv[2],ident,sys.argv[6])
    EVIDENCE.mkdir(mode=0o700)
    write_new(EVIDENCE / 'precompiler-view.json',proof)
    write_new(EVIDENCE / 'intent.json', {'profile_sha256': PROFILE_SHA256, 'stages': STAGES,
                                        'per_stage_timeout': PER_STAGE_TIMEOUT})
    for i, command in enumerate(commands, 1):
        stamp = time.time()
        write_new(EVIDENCE / ('stage-%d-intent.json' % i), {'argv': command['argv'], 'cwd': command['cwd'],
                                                            'start_utc': stamp})
        child = None
        status = {'stage': command['stage'], 'returncode': None, 'timed_out': False,
                  'direct_wait_completed': False, 'descendant_closure': 'UNKNOWN'}
        try:
            with (EVIDENCE / ('stage-%d.stdout' % i)).open('xb') as out, \
                 (EVIDENCE / ('stage-%d.stderr' % i)).open('xb') as err:
                child = subprocess.Popen(command['argv'], cwd=command['cwd'], stdin=subprocess.DEVNULL,
                                         stdout=out, stderr=err, start_new_session=True,
                                         env=dict(CLEAN_ENV))
                status['child_pid'] = child.pid
                try:
                    status['returncode'] = child.wait(timeout=PER_STAGE_TIMEOUT)
                    status['direct_wait_completed'] = True
                except subprocess.TimeoutExpired:
                    status['timed_out'] = True
                    # Popen owns this unreaped direct child. Killing it does not prove
                    # any descendants or container have retired; owner must retain UNKNOWN.
                    child.terminate()
                    try:
                        status['returncode'] = child.wait(timeout=5)
                        status['direct_wait_completed'] = True
                    except subprocess.TimeoutExpired:
                        child.kill()
                        status['returncode'] = child.wait(timeout=5)
                        status['direct_wait_completed'] = True
                out.flush(); os.fsync(out.fileno()); err.flush(); os.fsync(err.fileno())
        except BaseException as exc:
            status['error'] = type(exc).__name__ + ': ' + str(exc)
        status['finish_utc'] = time.time()
        write_new(EVIDENCE / ('stage-%d-result.json' % i), status)
        if status.get('error') or status['timed_out'] or not status['direct_wait_completed'] or status['returncode'] != 0:
            write_new(EVIDENCE / 'result.json', {'status': 'FAIL_OR_UNKNOWN', 'last_stage': i,
                                                  'container_retirement': 'OWNER_REQUIRED'})
            return 1
        if i == 1:
            # Direct wait alone cannot establish that configure's descendants stopped.
            # No reviewed observer is yet bound, so this successor always defers.
            write_new(EVIDENCE / 'result.json', {'status':'DEFERRED_DESCENDANT_QUIESCENCE_UNKNOWN',
                                                  'last_stage':i, 'container_retirement':'OWNER_REQUIRED'})
            return 1
    write_new(EVIDENCE / 'result.json', {'status': 'COMMANDS_EXITED_ZERO',
                                          'artifact_validation': 'POST_GENERATION_STAGE_EXITED_ZERO_ONLY',
                                          'container_retirement': 'OWNER_REQUIRED'})
    return 0


if __name__ == '__main__':
    sys.exit(main())
