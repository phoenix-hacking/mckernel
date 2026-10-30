"""Per-attempt SDK13 input snapshot; functional OS only, no security testing.
No global cache, launch, lease creation or authority. The trusted owner supplies
live, independently reviewed lease and admission/quiescence checks.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import time

HERE=Path(__file__).resolve().parent
BASE=HERE/'sdk13_data32_input_validation.py'
BASE_SHA='a9912953c35ce94a92713d93c39d28a40e788f334de548aadbda656e8dba0587'
if hashlib.sha256(BASE.read_bytes()).hexdigest()!=BASE_SHA:
    raise ValueError('frozen SDK13 validator bytes changed')
spec=importlib.util.spec_from_file_location('sdk13_frozen_inputs',BASE)
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)


def _fail_if(condition, text):
    if condition: raise ValueError(text)


def _canonical(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _birth():
    return Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]


def _meta_file(ref):
    p=base._safe_parents(ref['path']); s=os.lstat(p)
    _fail_if(not stat.S_ISREG(s.st_mode) or base._identity(s)!=tuple(ref['identity']), 'input file identity drift: '+str(p))


def _tree_metadata(tree, source_rows):
    root=base._safe_parents(tree['root']); before=os.lstat(root)
    _fail_if(not stat.S_ISDIR(before.st_mode) or base._identity(before)!=tuple(tree['identity']), 'source root changed: '+str(root))
    expected=tree['entries']; rows={r['relative']:r for r in source_rows}; actual={}; dirs=[]
    _fail_if(len(rows)!=len(source_rows) or set(rows)!=set(expected), 'snapshot/map tree disagreement')
    def walk_error(error): raise error
    for current, subdirs, files in os.walk(root,topdown=True,followlinks=False,onerror=walk_error):
        subdirs.sort(); files.sort()
        for name in subdirs+files:
            p=Path(current)/name; rel=p.relative_to(root).as_posix(); st=os.lstat(p)
            _fail_if(rel not in expected or base._identity(st)!=tuple(expected[rel]), 'source member changed: '+str(p))
            row=rows[rel]; kind=row['kind']
            if kind=='dir':
                _fail_if(not stat.S_ISDIR(st.st_mode), 'source directory changed: '+str(p)); dirs.append((p,base._identity(st)))
            elif kind=='file':
                _fail_if(not stat.S_ISREG(st.st_mode), 'source file changed: '+str(p))
            elif kind=='symlink':
                _fail_if(not stat.S_ISLNK(st.st_mode) or os.readlink(p)!=row['target'], 'source symlink changed: '+str(p))
                resolved=p.resolve(strict=True)
                _fail_if(resolved!=root and root not in resolved.parents, 'source symlink escaped: '+str(p))
            else:
                raise ValueError('unknown snapshot member kind')
            actual[rel]=True
    _fail_if(set(actual)!=set(expected), 'source tree membership changed: '+str(root))
    for p,identity in dirs:
        _fail_if(base._identity(os.lstat(p))!=identity, 'source directory changed during scan: '+str(p))
    _fail_if(base._identity(os.lstat(root))!=base._identity(before), 'source root changed during scan: '+str(root))


def _adopt_tree(root, expected, prehashed):
    """Adopt reviewed prior byte observations by actual identity, under lease.

    Files/symlinks must have independently observed hashes/identities. Directory
    identities are captured now and all exact map membership is checked now.
    The admission callback separately verifies genuine immutable ledger provenance.
    """
    root=base._safe_parents(root); start=os.lstat(root)
    _fail_if(prehashed.get('root')!=str(root) or tuple(prehashed.get('root_identity',()))!=base._identity(start), 'prehashed root identity differs')
    rows={r['relative']:r for r in expected}
    _fail_if(len(rows)!=len(expected), 'duplicate source map member')
    observed=prehashed.get('entries')
    _fail_if(not isinstance(observed,list), 'prehashed tree entries missing')
    recorded={r['relative']:r for r in observed}
    _fail_if(len(recorded)!=len(observed) or set(recorded)!={k for k,v in rows.items() if v['kind'] in ('file','symlink')}, 'prehashed tree membership differs')
    for rel,row in recorded.items():
        wanted=rows[rel]
        _fail_if(row.get('kind')!=wanted['kind'] or not isinstance(row.get('identity'),list) or len(row['identity'])!=9, 'prehashed member identity missing: '+rel)
        if wanted['kind']=='file':
            _fail_if(row.get('bytes')!=wanted['bytes'] or row.get('sha256')!=wanted['sha256'], 'prehashed byte digest differs: '+rel)
        else:
            _fail_if(row.get('target')!=wanted['target'], 'prehashed symlink differs: '+rel)
    entries={}; seen=set(); directories=[]
    def walk_error(error): raise error
    for current,subdirs,files in os.walk(root,topdown=True,followlinks=False,onerror=walk_error):
        subdirs.sort(); files.sort()
        for name in subdirs+files:
            path=Path(current)/name; rel=path.relative_to(root).as_posix(); st=os.lstat(path)
            _fail_if(rel not in rows, 'unlisted source member: '+str(path))
            row=rows[rel]; kind=row['kind']; identity=base._identity(st)
            if kind=='dir':
                _fail_if(not stat.S_ISDIR(st.st_mode), 'source directory differs: '+str(path)); directories.append((path,identity))
            elif kind=='file':
                _fail_if(not stat.S_ISREG(st.st_mode) or identity!=tuple(recorded[rel]['identity']), 'prehashed file identity changed: '+str(path))
            elif kind=='symlink':
                _fail_if(not stat.S_ISLNK(st.st_mode) or identity!=tuple(recorded[rel]['identity']) or os.readlink(path)!=row['target'], 'prehashed symlink identity changed: '+str(path))
                resolved=path.resolve(strict=True); _fail_if(resolved!=root and root not in resolved.parents, 'symlink escapes source root: '+str(path))
            else: raise ValueError('unsupported source entry')
            entries[rel]=identity; seen.add(rel)
    _fail_if(seen!=set(rows), 'source map directory membership differs: '+str(root))
    for path,identity in directories:
        _fail_if(base._identity(os.lstat(path))!=identity, 'directory changed while adopting: '+str(path))
    _fail_if(base._identity(os.lstat(root))!=base._identity(start), 'root changed while adopting: '+str(root))
    return {'root':str(root),'identity':base._identity(start),'entries':entries}


def _lease(lease_path, lease_check, request, owner_pid, owner_birth):
    # load_owned callback independently checks exact owner's exclusive lease;
    # compare actual named bytes and inode, not a supplied digest alone.
    named=base._safe_parents(lease_path); st=os.lstat(named)
    _fail_if(not stat.S_ISREG(st.st_mode) or st.st_size>1024*1024, 'lease file invalid')
    ref=base._file(named); raw=named.read_bytes()
    _fail_if(base._file(named)!=ref or hashlib.sha256(raw).hexdigest()!=ref['sha256'], 'lease changed while reading')
    checked=lease_check()
    _fail_if(not isinstance(checked,bytes) or checked!=raw, 'exclusive owned lease check failed')
    record=json.loads(raw)
    core={k:v for k,v in request.items() if k!='compile_only_release'}
    _fail_if(record.get('pid')!=owner_pid or str(record.get('starttime'))!=owner_birth or
             record.get('device')!=st.st_dev or record.get('inode')!=st.st_ino or
             record.get('request_core_sha256')!=_canonical(core) or
             record.get('profile_sha256')!=base.PROFILE_SHA or
             record.get('owner_nonce')!=request.get('owner_nonce'), 'lease does not bind this owner/request/profile')
    return ref


def _guard(admission_check, request, lease_ref, expires_ns, prehashed_sha256):
    # The callback is not a boolean/fact-hash verifier. It must perform the
    # owner's independently reviewed live root/controls/daemon/quiescence
    # checks and return their stable identity. Caller is responsible for this.
    result=admission_check()
    required={'request_sha256','profile_sha256','source_map_sha256','root_release_identity',
              'quiescence_identity','daemon_identity','lease_identity','expires_monotonic_ns',
              'prehashed_sha256','snapshot_receipt_identity'}
    _fail_if(not isinstance(result,dict) or set(result)!=required, 'actual admission identity incomplete')
    core={k:v for k,v in request.items() if k!='compile_only_release'}
    _fail_if(result['request_sha256']!=_canonical(core) or result['profile_sha256']!=base.PROFILE_SHA or
             result['source_map_sha256']!=request.get('source_map_sha256') or
             result['lease_identity']!=[lease_ref['identity'][0],lease_ref['identity'][1]] or
             result['prehashed_sha256']!=prehashed_sha256, 'actual admission binding differs')
    for key in ('root_release_identity','quiescence_identity','daemon_identity','snapshot_receipt_identity'):
        _fail_if(not isinstance(result[key],dict) or not result[key], 'actual live '+key+' absent')
    _fail_if(type(expires_ns) is not int or type(result['expires_monotonic_ns']) is not int or
             expires_ns>result['expires_monotonic_ns'] or time.monotonic_ns()>=expires_ns, 'snapshot admission expired')
    return result


def begin_snapshot(request, *, profile_path, request_path, source_map_path,
                   prehashed_trees, lease_check, admission_check, expires_monotonic_ns):
    """Adopt separately reviewed initial hashes under actual lease/quiescence.

    Any error ends the attempt; owner must retain lease and must not retry this
    snapshot under the same admission. An independent operation release is
    required for any successor. The callbacks must be independently reviewed.
    """
    _fail_if(not callable(lease_check) or not callable(admission_check), 'actual checks missing')
    pid=os.getpid(); birth=_birth(); lease_path=Path(request['lease_path'])
    lease_before=_lease(lease_path,lease_check,request,pid,birth)
    _fail_if(not isinstance(prehashed_trees,dict) or set(prehashed_trees)!={'/src','/src/kernel/rust','/nightly'}, 'prehashed tree set incomplete')
    prehashed_sha=_canonical(prehashed_trees)
    guard_before=_guard(admission_check,request,lease_before,expires_monotonic_ns,prehashed_sha)
    _fail_if(Path(request['work_root']).exists() or Path(request['attempt_root']).exists(), 'private paths not fresh')
    # Fresh private copy avoids monkeypatching data32 validator or sharing any mutable cache.
    private_spec=importlib.util.spec_from_file_location('sdk13_inputs_this_attempt',BASE)
    private=importlib.util.module_from_spec(private_spec); private_spec.loader.exec_module(private)
    roots={str(v['root']):v for v in prehashed_trees.values()}
    _fail_if(len(roots)!=3, 'prehashed root alias')
    private._tree=lambda root,expected:_adopt_tree(root,expected,roots[str(root)])
    bound=private._collect(request,profile_path,request_path,source_map_path)
    lease_after=_lease(lease_path,lease_check,request,pid,birth)
    guard_after=_guard(admission_check,request,lease_after,expires_monotonic_ns,prehashed_sha)
    _fail_if(lease_after!=lease_before or guard_after!=guard_before, 'lease/admission changed during initial byte pass')
    bound['_input_snapshot']={'valid':True,'pid':pid,'birth':birth,'lease':lease_before,
        'guard_sha256':_canonical(guard_before),'prehashed_sha256':prehashed_sha,'expires':expires_monotonic_ns,'request_full_sha256':_canonical(request),
        'bound_sha256':_canonical({k:bound[k] for k in ('profile_sha256','proposal_sha256','request_sha256','source_map','source_identities','snapshot','mounts','commands','outputs','profile_path','request_path','source_map_path')}),
        'lease_check':lease_check,'admission_check':admission_check}
    return bound


def bind_work(bound,request,created_identity):
    session=bound.get('_input_snapshot',{})
    _fail_if(not session.get('valid'), 'snapshot invalid')
    try: base.bind_work(bound,request,created_identity)
    except BaseException:
        session['valid']=False
        raise


def revalidate(bound,request):
    """Recheck complete metadata and directory membership; never rehash trees."""
    session=bound.get('_input_snapshot')
    _fail_if(not isinstance(session,dict) or session.get('valid') is not True, 'snapshot invalid')
    try:
        _fail_if(os.getpid()!=session['pid'] or _birth()!=session['birth'], 'snapshot owner changed')
        _fail_if(_canonical(request)!=session['request_full_sha256'], 'request changed')
        _fail_if(_canonical({k:bound[k] for k in ('profile_sha256','proposal_sha256','request_sha256','source_map','source_identities','snapshot','mounts','commands','outputs','profile_path','request_path','source_map_path')})!=session['bound_sha256'], 'snapshot binding changed')
        lease=_lease(bound['lease'],session['lease_check'],request,session['pid'],session['birth'])
        guard=_guard(session['admission_check'],request,lease,session['expires'],session['prehashed_sha256'])
        _fail_if(lease!=session['lease'] or _canonical(guard)!=session['guard_sha256'], 'lease or admission identity changed')
        snap=bound['snapshot']
        for name in ('profile','proposal','map','toolchain_manifest','toolchain_lock'): _meta_file(snap[name])
        for target,ref in snap['source_identities'].items():
            if target in ('/src','/src/kernel/rust','/nightly'):
                _tree_metadata(ref,bound['source_map']['trees'][target]['entries'])
            else:
                _meta_file(ref)
        for p,key in ((bound['work'].parent,'work_parent'),(bound['owner_evidence'].parent,'evidence_parent')):
            _fail_if(base._directory_identity(os.lstat(base._safe_parents(p)))!=tuple(snap[key]), 'private parent identity changed')
        work=base._safe_parents(bound['work'])
        if bound['work_identity'] is None:
            _fail_if(work.exists() or work.is_symlink(), 'unbound work appeared')
        else:
            _fail_if(base._directory_identity(os.lstat(work))!=tuple(bound['work_identity']), 'work root identity changed')
        lease_after=_lease(bound['lease'],session['lease_check'],request,session['pid'],session['birth'])
        guard_after=_guard(session['admission_check'],request,lease_after,session['expires'],session['prehashed_sha256'])
        _fail_if(lease_after!=lease or guard_after!=guard, 'lease/admission changed during metadata scan')
    except BaseException:
        session['valid']=False
        raise
    return None
