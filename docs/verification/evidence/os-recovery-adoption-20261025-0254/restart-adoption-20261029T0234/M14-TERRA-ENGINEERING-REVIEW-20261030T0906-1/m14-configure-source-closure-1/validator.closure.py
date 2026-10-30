"""SDK13 input-domain validation, source only; no launch or authority.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Callers must separately authenticate the current root-sealed operation and actual
resource/daemon/nonce/CPU ownership; source maps are evidence, never authority.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

PROFILE_SHA = 'e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3'
PROPOSAL_SHA = 'b9e0fbad132ae43fcd79459b9f2baee776679b4a972e4647d583f0d8ba26b594'
IMAGE = 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
RUST_TARGET = '/src/kernel/rust'
WORK_TARGET = '/work'
HELD = frozenset(('f03_direct_tid_candidate','f03_terminate_host_candidate',
                  'f03_execve_transfer_candidate','f03_execve_ack_candidate',
                  'f06_full28_candidate','sigreturn_abi_witness_only'))
PARTIAL = frozenset(('f06_handler_commit_candidate','f06_xsave_copy_candidate',
                     'f06_frame_copy_candidate','f06_core_termination_candidate',
                     'f06_trap_stop_candidate'))


def _require(condition, why):
    if not condition:
        raise ValueError(why)


def _identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid,
            st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _directory_identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid)


def _safe_parents(path):
    p=Path(path)
    _require(p.is_absolute() and str(p)==os.path.normpath(str(p)), 'noncanonical path: '+str(path))
    for item in (p, *p.parents):
        try: s=os.lstat(item)
        except FileNotFoundError: continue
        _require(not stat.S_ISLNK(s.st_mode), 'symlink path component: '+str(item))
    return p


def _file(path):
    path=_safe_parents(path)
    fd=os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode), 'not a regular file: '+str(path))
        h=hashlib.sha256()
        while True:
            chunk=os.read(fd, 1024*1024)
            if not chunk: break
            h.update(chunk)
        after=os.fstat(fd); named=os.lstat(path)
        _require(_identity(before)==_identity(after)==_identity(named), 'file changed during read: '+str(path))
        return {'path':str(path),'bytes':before.st_size,'sha256':h.hexdigest(),'identity':_identity(before)}
    finally:
        os.close(fd)


def _document(path, sha, label):
    p=_safe_parents(path); ref=_file(p)
    _require(ref['sha256']==sha, label+' digest mismatch')
    data=p.read_bytes()
    _require(hashlib.sha256(data).hexdigest()==sha and _file(p)==ref, label+' changed on read')
    result=json.loads(data)
    _require(isinstance(result,dict), label+' must be an object')
    return result,ref


def _relative(value):
    p=PurePosixPath(value)
    _require(isinstance(value,str) and not p.is_absolute() and str(p)==value and value not in ('','.')
             and all(part not in ('.','..') for part in p.parts), 'invalid relative source path: '+repr(value))
    return p


def _tree(root, expected):
    root=_safe_parents(root); root_stat=os.lstat(root)
    _require(stat.S_ISDIR(root_stat.st_mode), 'tree root is not directory: '+str(root))
    _require(isinstance(expected,list), 'tree entries missing: '+str(root))
    rows={}
    for row in expected:
        _require(isinstance(row,dict) and set(row) in ({'relative','kind','bytes','sha256'}, {'relative','kind','target'}, {'relative','kind'}), 'bad tree entry')
        rel=str(_relative(row['relative'])); _require(rel not in rows, 'duplicate tree entry: '+rel); rows[rel]=row
    actual={}; snapshot={}
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        dirs.sort(); files.sort()
        for name in dirs+files:
            path=Path(current)/name; rel=path.relative_to(root).as_posix(); s=os.lstat(path)
            if stat.S_ISLNK(s.st_mode):
                target=os.readlink(path); resolved=path.resolve(strict=True)
                _require(resolved==root or root in resolved.parents, 'tree symlink escapes root: '+rel)
                actual[rel]={'relative':rel,'kind':'symlink','target':target}; snapshot[rel]=_identity(s)
            elif stat.S_ISDIR(s.st_mode):
                actual[rel]={'relative':rel,'kind':'dir'}; snapshot[rel]=_identity(s)
            elif stat.S_ISREG(s.st_mode):
                f=_file(path); actual[rel]={'relative':rel,'kind':'file','bytes':f['bytes'],'sha256':f['sha256']}; snapshot[rel]=f['identity']
            else:
                raise ValueError('unsupported tree entry: '+str(path))
    _require(actual==rows, 'tree inventory or bytes differ: '+str(root))
    _require(_identity(root_stat)==_identity(os.lstat(root)), 'tree root changed during scan: '+str(root))
    return {'root':str(root),'identity':_identity(root_stat),'entries':snapshot}


def _mount_graph(mounts):
    _require(isinstance(mounts,list) and len(mounts)>=4, 'mount count')
    targets=[]
    for i,row in enumerate(mounts):
        _require(isinstance(row,(tuple,list)) and len(row)==3, 'mount shape')
        host,target,readonly=row
        _require(isinstance(host,str) and isinstance(target,str) and type(readonly) is bool, 'mount row shape')
        p=PurePosixPath(target)
        _require(p.is_absolute() and str(p)==target and '..' not in p.parts, 'mount target invalid')
        _require(target not in targets, 'duplicate mount target')
        _require((i==0 and target=='/work' and not readonly) or (i>0 and readonly), 'unexpected writable mount')
        for prior in targets:
            _require(not (PurePosixPath(prior) in p.parents and prior not in ('/src','/work')), 'unsupported overlap')
            _require(not (p in PurePosixPath(prior).parents), 'mount parent masks child')
        targets.append(target)
    _require({'/work','/src','/src/kernel/rust','/nightly','/out'}<=set(targets), 'required mount absent')

def _selectors(profile, proposal):
    commands=profile['commands']
    _require(commands==proposal['commands'] and len(commands)==2, 'command proposal differs')
    _require([c['stage'] for c in commands]==['Configure ON composite','Post-generation verification'], 'stage order differs')
    _require(all(c.get('cwd')=='/work' and isinstance(c.get('argv'),list) and c['argv'] and
                 all(isinstance(x,str) and x and '\0' not in x for x in c['argv']) for c in commands), 'bad command schema')
    a=commands[0]['argv']
    _require(a[:7]==['/usr/bin/cmake','-S','/src','-B','/work/output/build','-G','Unix Makefiles'], 'configure argv differs')
    _require([x for x in a if x.startswith('-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL=')]==['-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL=ON'] and
             [x for x in a if x.startswith('-DKERNEL_DIR=')]==['-DKERNEL_DIR=/out/build'], 'ON or kernel selector differs')
    for flag in ('UNAME_R','MCKERNEL_M14_EXPECTED_UNAME_R','MCKERNEL_M14_EXPECTED_MAP_KERNEL_START',
                 'MCKERNEL_M14_EXPECTED_MAKE_SHA256','KBUILD_MAKE_FLAGS','MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS'):
        values=[x for x in a if x.startswith('-D'+flag+'=')]
        _require(len(values)==1 and len(values[0])>len('-D'+flag+'='), 'missing or duplicate '+flag)
    v=commands[1]['argv']
    _require(v[:4]==['/usr/bin/python3','-I','-B','/src/scripts/verify_m14_elf.py'], 'separate verifier differs')
    def cvalue(flag): return next(x.split('=',1)[1] for x in a if x.startswith('-D'+flag+'='))
    expected={'--make-status':'0','--module':'/work/output/build/tmp.resolve_MODULES_END/driver.ko',
              '--kernel-release':'/out/build/include/config/kernel.release',
              '--uts-release-header':'/out/build/include/generated/utsrelease.h',
              '--uname-r':cvalue('UNAME_R'),'--expected-map':cvalue('MCKERNEL_M14_EXPECTED_MAP_KERNEL_START'),
              '--cmake-cache':'/work/output/build/CMakeCache.txt','--compile-commands':'/work/output/build/compile_commands.json',
              '--expected-kernel-dir':'/out/build','--expected-build-dir':'/work/output/build'}
    _require(cvalue('UNAME_R')==cvalue('MCKERNEL_M14_EXPECTED_UNAME_R'), 'uname mismatch')
    _require(len(v)==4+2*len(expected), 'verifier argv length differs')
    for flag,value in expected.items():
        _require(v.count(flag)==1 and v[v.index(flag)+1]==value, 'verifier flag differs: '+flag)
    _require(not any(any(x in arg for x in ('FULL28','WITNESS','EXECVE_TRANSFER','TERMINATE_HOST','DIRECT_TID')) for c in commands for arg in c['argv']), 'held selector')

# Source-only proposal binding; this is not an admission, snapshot or live identity.
COMPOSITE_PROPOSAL_SHA = '8cb23a435a512bff5cc8a80d28fe9c70764ef047918c60722e535fa721738593'

def _check_composite_proposal(path, mounts):
    proposal, ref = _document(path, COMPOSITE_PROPOSAL_SHA, 'ON composite source proposal')
    _require(proposal.get('status')=='SOURCE_ONLY_UNRELEASED', 'unexpected composite proposal status')
    expected=proposal.get('on_source_mount_proposal')
    _require(isinstance(expected,dict) and expected, 'ON source mounts missing')
    _mount_graph(mounts)
    source={target:host for host,target,ro in mounts if target not in ('/work','/out')}
    _require(source==expected, 'ON source mount proposal mismatch')
    return ref

def _collect(request, profile_path, request_path, source_map_path):
    raise ValueError('SOURCE_ONLY: configure source closure and live bindings are unbound')
    profile,pref=_document(profile_path,PROFILE_SHA,'SDK13 profile')
    proposal,qref=_document(request_path,PROPOSAL_SHA,'SDK13 proposal')
    _require(isinstance(request,dict),'request must be object')
    _require(request.get('profile_sha256')==PROFILE_SHA and request.get('proposal_sha256')==PROPOSAL_SHA, 'request profile/proposal binding')
    _require(request.get('image_id')==IMAGE==profile['image_and_tools']['image_digest'], 'SDK image differs')
    _require(request.get('source_map_path')==str(source_map_path), 'source map path differs')
    mapsha=request.get('source_map_sha256'); _require(isinstance(mapsha,str) and re.fullmatch('[0-9a-f]{64}',mapsha), 'source map digest missing')
    source_map,mref=_document(source_map_path,mapsha,'reviewed source map')
    _require(source_map.get('schema')=='mckernel.sdk13.source-map.v1' and source_map.get('profile_sha256')==PROFILE_SHA and source_map.get('proposal_sha256')==PROPOSAL_SHA, 'source map domain')
    _selectors(profile,proposal)
    rows=proposal['mounts_proposed']; expected=[(r['host'],r['container'],r['mode']=='ro') for r in rows]
    _require(request.get('mounts')==[list(r) for r in expected], 'request mount list differs')
    _mount_graph(expected)
    _require(rows[1:]==profile['readonly_shared_inputs']+profile['readonly_config_and_eight_objects'], 'proposal mount profile differs')
    _require(request.get('commands')==profile['commands'], 'request command list differs')
    work=_safe_parents(request.get('work_root',''))
    _require(str(work)==profile['private_work']['host_fresh_output_root']==rows[0]['host'], 'work root differs')
    evidence=_safe_parents(request.get('owner_evidence_root','')); attempt=_safe_parents(request.get('attempt_root','')); lease=_safe_parents(request.get('lease_path',''))
    _require(attempt.parent==evidence and lease.parent==evidence and attempt!=lease, 'private operation paths differ')
    _require(work!=evidence and work not in evidence.parents and evidence not in work.parents, 'private paths overlap')
    parent=os.lstat(work.parent); eparent=os.lstat(evidence.parent)
    _require(stat.S_ISDIR(parent.st_mode) and stat.S_ISDIR(eparent.st_mode), 'private parent missing')
    _require(eparent.st_uid==1000 and not stat.S_IMODE(eparent.st_mode)&0o077, 'private evidence parent permissions')
    identities={}; dirs={r['container']:r['host'] for r in rows[1:] if 'sha256' not in r}
    _require(set(dirs)=={'/src','/src/kernel/rust','/nightly'}, 'source directory mount set')
    trees=source_map.get('trees'); _require(isinstance(trees,dict) and set(trees)==set(dirs), 'source map tree set')
    for target,host in dirs.items():
        _require(trees[target].get('root')==host, 'source tree root differs: '+target)
        identities[target]=_tree(host,trees[target].get('entries'))
    rustentries=trees[RUST_TARGET]['entries']
    _require(sum(r['kind']=='file' for r in rustentries)==157, 'Rust subtree file count')
    _require(profile['successor_delta_data32']['rust_subtree_files']==157, 'data32 Rust scope differs')
    for rel,row in profile['source_bindings']['overlay_hashes'].items():
        if rel.startswith('kernel/rust/'):
            sub=rel[len('kernel/rust/'):]; match=[x for x in rustentries if x['relative']==sub and x['kind']=='file']
            _require(len(match)==1 and match[0]['sha256']==row['sha256'], 'Rust overlay differs: '+rel)
    mount_inodes=set()
    for row in rows[1:]:
        host=_safe_parents(row['host']); _require(work not in host.parents and host!=work and host not in work.parents, 'work/source path overlap')
        _require(evidence not in host.parents and host!=evidence and host not in evidence.parents, 'evidence/source path overlap')
        st=os.lstat(host); identity=(st.st_dev,st.st_ino)
        _require(identity not in mount_inodes, 'mount source inode alias: '+row['container'])
        mount_inodes.add(identity)
        if 'sha256' in row:
            f=_file(host); _require(f['sha256']==row['sha256'] and ('bytes' not in row or f['bytes']==row['bytes']), 'mounted file mismatch: '+row['container'])
            identities[row['container']]=f
    retained={r['token']:r for r in profile['link']['retained_8']}
    _require(len(retained)==8, 'duplicate retained object')
    for token,row in retained.items():
        target='/work/output/build/kernel/'+token; _require(target in identities, 'retained object mount absent: '+token)
        f=identities[target]; _require(f['sha256']==row['sha256'] and f['bytes']==row['bytes'], 'retained object mismatch: '+token)
    toolref=profile['image_and_tools']['retained_image_tool_manifest']; tool=_file(toolref['path'])
    _require(tool['sha256']==toolref['sha256'], 'toolchain manifest mismatch')
    lockref=source_map.get('toolchain_lock'); _require(isinstance(lockref,dict) and set(lockref)=={'path','sha256'}, 'toolchain lock reference missing')
    lock=_file(lockref['path'])
    _require(lock['sha256']==lockref['sha256']==profile['image_and_tools']['toolchain_lock_sha256'], 'toolchain lock mismatch')
    snapshot={'profile':pref,'proposal':qref,'map':mref,'source_identities':identities,'toolchain_manifest':tool,'toolchain_lock':lock,'work_parent':_directory_identity(parent),'evidence_parent':_directory_identity(eparent)}
    core={key:value for key,value in request.items() if key!='compile_only_release'}
    request_sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return {'profile_sha256':PROFILE_SHA,'proposal_sha256':PROPOSAL_SHA,'request_sha256':request_sha,'source_map':source_map,
            'source_identities':identities,'readonly_mounts':expected[1:],'mounts':expected,
            'commands':profile['commands'],'outputs':[c['output'] for c in profile['commands']],
            'source':Path(dirs['/src']),'work':work,'owner_evidence':evidence,'attempt':attempt,'lease':lease,
            'snapshot':snapshot,'profile_path':str(profile_path),'request_path':str(request_path),'source_map_path':str(source_map_path),
            'actual_authority':None,'work_identity':None}


def validate(request, *, profile_path, request_path, source_map_path):
    bound=_collect(request,profile_path,request_path,source_map_path)
    _require(not bound['work'].exists() and not bound['work'].is_symlink(), 'work root is not fresh')
    for key in ('owner_evidence','attempt','lease'):
        _require(not bound[key].exists() and not bound[key].is_symlink(), 'private path already exists: '+key)
    return bound


def bind_work(bound, request, created_identity):
    """Owner must create the directory exclusively and supply its observed identity."""
    _require(bound['work_identity'] is None, 'work already bound')
    p=_safe_parents(bound['work']); s=os.lstat(p)
    _require(stat.S_ISDIR(s.st_mode) and stat.S_IMODE(s.st_mode)==0o700 and _identity(s)==tuple(created_identity), 'created work identity differs')
    bound['work_identity']=(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid)


def revalidate(bound, request):
    fresh=_collect(request,bound['profile_path'],bound['request_path'],bound['source_map_path'])
    _require(fresh['request_sha256']==bound['request_sha256'] and fresh['snapshot']==bound['snapshot'] and fresh['mounts']==bound['mounts'] and fresh['commands']==bound['commands'], 'input identity changed')
    p=_safe_parents(bound['work'])
    if bound['work_identity'] is None:
        _require(not p.exists() and not p.is_symlink(), 'unbound work path appeared')
    else:
        s=os.lstat(p)
        _require((s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid)==bound['work_identity'], 'bound work identity changed')
    return None
