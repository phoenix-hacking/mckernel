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
        if target == PERF_CHILD:
            _require(RUST_TARGET in targets and host == PERF_OVERLAY_SOURCE and readonly, 'perf child binding/order')
        _require((i==0 and target=='/work' and not readonly) or (i>0 and readonly), 'unexpected writable mount')
        for prior in targets:
            exact_perf = (prior == RUST_TARGET and target == PERF_CHILD and
                          host == PERF_OVERLAY_SOURCE and readonly)
            _require(not (PurePosixPath(prior) in p.parents and prior not in ('/src','/work')) or exact_perf, 'unsupported overlap')
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
    # Full argv comparison rejects typed definitions, -U, -C and all extra options.
    fixed = ['/usr/bin/cmake',
 '-S',
 '/src',
 '-B',
 '/work/output/build',
 '-G',
 'Unix Makefiles',
 '-DCMAKE_BUILD_TYPE=Debug',
 '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
 '-DCMAKE_C_COMPILER=/usr/bin/cc',
 '-DCMAKE_ASM_COMPILER=/usr/bin/cc',
 '-DCMAKE_LINKER=/usr/bin/ld',
 '-DCMAKE_MAKE_PROGRAM=/usr/bin/make',
 '-DRUSTC=/nightly/bin/rustc',
 '-DBUILD_TARGET=smp-x86',
 '-DKERNEL_DIR=/out/build',
 '-DENABLE_RUST_KERNEL=ON',
 '-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL=ON',
 '-DMCKERNEL_HOST_IRQ_ABI=linux-6.12',
 '-DENABLE_PERF=ON',
 '-DPROFILE_ENABLE=ON',
 '-DENABLE_RUSAGE=ON',
 '-DENABLE_UBSAN=OFF',
 '-DENABLE_TOFU=OFF',
 '-DENABLE_PER_CPU_ALLOC_CACHE=OFF',
 '-DENABLE_FUGAKU_HACKS=OFF',
 '-DENABLE_NATIVE_SYSFS_VERIFY=OFF',
 '-DENABLE_NATIVE_FORK_OWNED_TRANSACTION=ON',
 '-DENABLE_RUST_PROCESS_VERBOSE_DATA=ON',
 '-DENABLE_RUST_PROCESS_VERBOSE_LOCAL_COMPANIONS=ON',
 '-DENABLE_PROCESS_DEBUG_PRINT=OFF']
    names = ['UNAME_R', 'MCKERNEL_M14_EXPECTED_UNAME_R', 'MCKERNEL_M14_EXPECTED_MAP_KERNEL_START', 'MCKERNEL_M14_EXPECTED_MAKE_SHA256', 'KBUILD_MAKE_FLAGS', 'MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS']
    values=profile.get('required_actual_values')
    _require(isinstance(values,dict), 'required values missing')
    _require(all(isinstance(values.get(n),str) and '\0' not in values[n] for n in names), 'unbound configure values')
    _require(all(values[n] for n in names[:4]), 'empty required identity')
    _require(re.fullmatch(r'[0-9a-f]{64}',values['MCKERNEL_M14_EXPECTED_MAKE_SHA256']) is not None, 'make hash malformed')
    _require(values['UNAME_R']==values['MCKERNEL_M14_EXPECTED_UNAME_R'], 'uname mismatch')
    _require(values['KBUILD_MAKE_FLAGS']==values['MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS'], 'flags mismatch')
    _require(a==fixed+['-D'+n+'='+values[n] for n in names], 'exact configure argv differs')
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
    if PERF_CHILD in source:
        delta, _ = _document(PERF_DELTA_PATH, PERF_DELTA_SHA, 'perf source integration')
        child=delta.get('prospective_on_mount_delta',{})
        _require(child.get('target')==PERF_CHILD and child.get('parent_target')==RUST_TARGET and
                 child.get('host_candidate')==PERF_OVERLAY_SOURCE and source[PERF_CHILD]==PERF_OVERLAY_SOURCE,
                 'perf source proposal mismatch')
        _require(expected.get(RUST_TARGET)==child.get('parent_host_candidate'), 'perf parent source mismatch')
        original=_file(Path(expected[RUST_TARGET])/PERF_NAME); replacement=_file(Path(PERF_OVERLAY_SOURCE))
        _require(original['sha256']==PERF_PRE and replacement['sha256']==PERF_POST, 'perf source hash mismatch')
        _require(original['identity'][:2]!=replacement['identity'][:2], 'perf source inode alias')
        del source[PERF_CHILD]
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

# Source-only exact-one-perf-file model. _collect remains hard-disabled.
# Its evidence objects are synthetic/untrusted until independently authenticated
# against actual source and effective mount identities by a reviewed owner.
PERF_PARENT_MANIFEST_SHA='ad611913d8965e1140443c29678c2e1180a90a91095ea0141929b8767a92ada7'
PERF_PLAN_SHA='48b2c25266784641b28100c08c7c7baa4559d0aaffe670223ee71936f3deaffa'
PERF_DELTA_SHA='cb63bb9c156525c0a70ee3b4ff3cd29a0b7356dd1a928ac33398a534f567bc5d'
PERF_CHILD='/src/kernel/rust/f03_perf_group_cleanup.rs'
PERF_OVERLAY_SOURCE='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-perf-standalone-integration-1/postimage/kernel/rust/f03_perf_group_cleanup.rs'
PERF_DELTA_PATH=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-perf-standalone-integration-1/INTEGRATION.json')
PERF_PARENT='/src/kernel/rust'
PERF_NAME='f03_perf_group_cleanup.rs'
PERF_PRE='0dc2c777c39a9b2f31bc5e3d80badd2d3de8db35bcd0adba205776bb58517293'
PERF_POST='7b13e1975636f0c496394e4fb6b0243ae926837a03099a498a69b9c3ab04b8b1'

def _perf_json(raw,expected):
    _require(type(raw) is bytes and hashlib.sha256(raw).hexdigest()==expected,'source manifest digest mismatch')
    def unique(pairs):
        d={}
        for key,value in pairs:
            _require(key not in d,'duplicate JSON key');d[key]=value
        return d
    value=json.loads(raw,object_pairs_hook=unique)
    _require(type(value) is dict,'source manifest type')
    return value

def _perf_identity(row,kind):
    _require(type(row) is dict and set(row)=={'device','inode','kind'},'source identity shape')
    _require(type(row['device']) is int and row['device']>=0 and type(row['inode']) is int and row['inode']>0 and row['kind']==kind,'source identity type')
    return (row['device'],row['inode'])

def validate_perf_one_file_model(rows,parent_members,bindings,plan_bytes,parent_bytes,delta_bytes):
    """Validate a hypothetical mount proposal; not live identity or authority."""
    plan=_perf_json(plan_bytes,PERF_PLAN_SHA)
    parent=_perf_json(parent_bytes,PERF_PARENT_MANIFEST_SHA)
    delta=_perf_json(delta_bytes,PERF_DELTA_SHA)
    proposed=plan['future_mounts_parent_first'];base_targets=[x['target'] for x in proposed]
    _require(len(base_targets)==14 and len(set(base_targets))==14,'base target closure')
    _require(PERF_CHILD not in base_targets and PERF_PARENT in base_targets,'perf target collision')
    known=parent['rust_regular_file_hashes']
    _require(type(known) is dict and len(known)==157 and known.get(PERF_NAME)==PERF_PRE,'parent original membership/hash')
    _require(type(parent_members) is dict and parent_members==known,'parent membership differs')
    child=delta['prospective_on_mount_delta']
    _require(child['target']==PERF_CHILD and child['parent_target']==PERF_PARENT and delta['preimage']['sha256']==PERF_PRE and delta['private_postimage']['sha256']==PERF_POST,'perf delta binding')
    _require(type(rows) is list and len(rows)==15,'successor target count')
    ts=[]
    for row in rows:
        _require(type(row) is dict and set(row)=={'target','host_candidate','access','live_identity'},'mount row schema')
        t=row['target'];_require(type(t) is str and t.startswith('/') and str(PurePosixPath(t))==t and '..' not in PurePosixPath(t).parts,'mount target')
        _require(t not in ts,'duplicate mount');_require(row['access']==('rw' if t=='/work' else 'ro'),'mount access')
        _require(row['live_identity'] is None,'live identity must stay unbound')
        for prev in ts:
            _require(not (PurePosixPath(t) in PurePosixPath(prev).parents),'parent after child')
            if PurePosixPath(prev) in PurePosixPath(t).parents:
                _require(prev in ('/src','/src/kernel/rust') and (prev!='/src/kernel/rust' or t==PERF_CHILD),'unapproved nested shadow')
        ts.append(t)
    _require(ts[0]=='/work','work must be first')
    _require(set(ts)==set(base_targets)|{PERF_CHILD},'target membership differs')
    _require(ts.index('/src')<ts.index(PERF_PARENT)<ts.index(PERF_CHILD),'perf mount order')
    by={x['target']:x for x in rows}
    for x in proposed:
        t=x['target'];_require(by[t]['host_candidate']==x['host_candidate'] and by[t]['access']==x['access'],'base target binding differs: '+t)
    _require(by[PERF_CHILD]['host_candidate']==child['host_candidate'],'perf source path differs')
    _require(type(bindings) is dict and set(bindings)=={'parent_dir','parent_file','child_file','parent_file_sha256','child_file_sha256'},'binding shape')
    ids=[_perf_identity(bindings['parent_dir'],'directory'),_perf_identity(bindings['parent_file'],'file'),_perf_identity(bindings['child_file'],'file')]
    _require(len(set(ids))==3,'source inode alias')
    _require(bindings['parent_file_sha256']==PERF_PRE and bindings['child_file_sha256']==PERF_POST,'source content binding differs')
    return {'status':'SOURCE_MODEL_ONLY_LIVE_VALIDATION_DISABLED','authority':None,'source_identity':None,'effective_mount_identity':None,'target_count':len(ts)}
