#!/usr/bin/env python3
"""Prepare (never build or execute) the exact scratch17 candidate delta.

The packet deliberately owns only checkout construction.  It imports the
target commit and trees into private Git metadata, materializes worktree blobs
with exclusive writes, and may share only authenticated, unchanged large
evidence documents with scratch15.  No Docker, root, lease, build, or guest
operation is present in this file.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, stat, subprocess, sys, time
from pathlib import Path
import importlib.util
from contextlib import contextmanager

OLD = "1e95abdc2b124c19f16b88cdb21600c768a10c2d"
TARGET = "50b084322610a9326b1b7b528edd4cd73b635632"
IHK = "3114d9e7101ad52030eb3effa849a5c108972a1f"
OVERLAY_REL = 'host-kernel/exact-build/ihk-clear-host-pte-overlay.patch'
OVERLAY_SHA256 = 'cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7'
OVERLAY_RESULT_REL = 'test/ihklib/whitebox/src/driver/mckernel/syscall.c'
OVERLAY_RESULT_SHA256 = '7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77'
OVERLAY_BASE_SHA='3114d9e7101ad52030eb3effa849a5c108972a1f'
OVERLAY_RESULT_COMMIT_SHA='21a0d1eb1705c3ee597aed41358ba4c0a92d5f8c'
OVERLAY_BASE_BLOB_SHA='91fe5688f3282c1617a75f08c4b435a793200f2cf9beafe432cef7ad3ca0bd4c'
IMAGE_ID='sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d'
DEFAULT_SCRATCH = Path('/home/holden/mckernel-work/scratch')
PREVIOUS_CANDIDATE_NAME = 'mckernel-exact-candidate-ddb8d7d5-scratch-16'
EXPECTED_SHARED_FILES = 486
CANDIDATE_NAME = 'mckernel-exact-candidate-50b08432-scratch-17'
MANIFEST_NAME = 'native-exact-inputs-50b08432-scratch-17.json'
REQUEST_NAME = 'native-exact-delta-request-50b08432-scratch-17.json'
LOG_NAME = 'native-exact-candidate-delta-preparation-50b08432-scratch-17.log'
TERMINAL_NAME = 'native-exact-candidate-delta-preparation-50b08432-scratch-17-terminal.json'
ASSETS = DEFAULT_SCRATCH/'native-exact-assets-16445ab2'
RECEIPT = Path('/home/holden/mckernel-exact-image-evidence-d0947e0c-1/image-receipt.json')
RECEIPT_SHA256 = '18225919a44e2c07e87a66711c8d1c9483d10e15da91fa5d7fcb7339ff888172'
HOST_FLOOR = 16 << 30
SCRATCH_FLOOR = 12 << 30
EMERGENCY = 512 << 20

class Refusal(RuntimeError): pass

def git(repo, *args, input=None):
    env = {'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C',
           'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null',
           'GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
    repo=Path(repo); gd=repo/'.git' if (repo/'.git').is_dir() else repo
    cmd=['/usr/bin/git','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null',
         '--git-dir',str(gd)]
    if (repo/'.git').is_dir(): cmd += ['--work-tree',str(repo)]
    p = subprocess.run(cmd+list(args), input=input,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if p.returncode: raise Refusal('git failed: '+(' '.join(args))+': '+p.stderr.decode('utf-8','replace'))
    return p.stdout

def sha(b): return hashlib.sha256(b).hexdigest()
def regular(p):
    s=os.lstat(p)
    if not stat.S_ISREG(s.st_mode): raise Refusal('not regular: '+str(p))
    return s
def private_git(g):
    g=Path(g)
    if g.is_symlink() or not g.is_dir() or (g/'commondir').exists() or any(
            (g/'objects/info'/name).exists() for name in ('alternates','http-alternates')):
        raise Refusal('non-private git metadata')
    if any(p.is_symlink() for p in g.rglob('*')):
        raise Refusal('symlink in private git metadata')

def tree_entries(source, commit, recursive=True):
    raw=git(source,'ls-tree',*(('-r',) if recursive else ()), '-z',commit)
    out=[]
    for row in raw.split(b'\0'):
        if not row: continue
        left,path=row.split(b'\t',1); mode,kind,oid=left.split()
        out.append((mode.decode(),kind.decode(),oid.decode(),path.decode('utf-8')))
    return out

def object_bytes(source, kind, oid): return git(source,'cat-file',kind,oid)

def install_private_objects(source, destination, commit):
    # Ordinary blobs deliberately remain worktree inputs, as in canonical
    # candidate_metadata(full_objects=False). Historical ABI blobs are retained
    # by the private scratch15 metadata copy; symlink blobs are needed by Git.
    private_git(destination)
    raw=object_bytes(source,'commit',commit)
    got=git(destination,'hash-object','-t','commit','-w','--stdin',input=raw).decode().strip()
    if got != commit: raise Refusal('commit identity changed')
    tree=git(source,'rev-parse',commit+'^{tree}').decode().strip()
    stack=[tree]; seen=set()
    while stack:
        oid=stack.pop()
        if oid in seen: continue
        seen.add(oid); raw=object_bytes(source,'tree',oid)
        if git(destination,'hash-object','-t','tree','-w','--stdin',input=raw).decode().strip()!=oid:
            raise Refusal('tree identity changed')
        for mode,kind,child,_ in tree_entries(source, oid, recursive=False):
            if kind=='tree': stack.append(child)
            elif mode=='120000':
                raw=object_bytes(source,'blob',child)
                if git(destination,'hash-object','-w','--stdin',input=raw).decode().strip()!=child:
                    raise Refusal('symlink object identity changed')
    return tree

def write_exclusive(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode & 0o7777)
    try:
        off=0
        while off<len(data):
            n=os.write(fd,data[off:])
            if n<=0: raise Refusal('short write')
            off+=n
        os.fchmod(fd,mode & 0o7777); os.fsync(fd)
    finally: os.close(fd)
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)

def raw_delta(source, old=OLD, target=TARGET):
    rows=git(source,'diff','--name-status','--no-renames','-z',old,target).split(b'\0')[:-1]
    if len(rows)%2: raise Refusal('malformed raw delta')
    parsed=[(rows[i].decode(),rows[i+1].decode()) for i in range(0,len(rows),2)]
    if sum(r[0]=='A' for r in parsed)!=21 or sum(r[0]=='M' for r in parsed)!=13 or any(r[0] not in ('A','M') for r in parsed):
        raise Refusal('unexpected raw delta')
    return parsed

def validate_git_roots(root):
    root=Path(root); g=root/'.git'; private_git(g)
    if not (g/'HEAD').is_file() or (g/'index').is_symlink(): raise Refusal('main metadata')
    ihk=root/'ihk'; private_git(ihk/'.git')
    for p in (root,ihk):
        if p.is_symlink(): raise Refusal('root symlink')

@contextmanager
def candidate_modules(candidate):
    """Bind imports to this candidate, including the shared provenance module."""
    names = ('native_rust_exact_build_offline', 'native_rust_exact_build_input_manifest',
             'native_rust_exact_build_container_owner')
    saved = {name: sys.modules.get(name) for name in names}
    old_path, old_bytecode = sys.path[:], sys.dont_write_bytecode
    try:
        sys.path[:] = [str(Path(candidate)/'scripts')] + [
            x for x in old_path if x and 'site-packages' not in x]
        sys.dont_write_bytecode = True
        modules = []
        for name in names:
            helper = Path(candidate)/'scripts'/(name+'.py')
            regular(helper)
            spec = importlib.util.spec_from_file_location(name, helper)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            modules.append(module)
        yield tuple(modules)
    finally:
        sys.path[:] = old_path
        sys.dont_write_bytecode = old_bytecode
        for name, previous in saved.items():
            if previous is None: sys.modules.pop(name, None)
            else: sys.modules[name] = previous


def digest(path):
    regular(path)
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def identity(path):
    s = regular(path)
    return {'device': s.st_dev, 'inode': s.st_ino, 'mode': stat.S_IMODE(s.st_mode),
            'size': s.st_size, 'nlink': s.st_nlink, 'mtime_ns': s.st_mtime_ns}


def snapshot(path):
    before = identity(path)
    result = dict(before, sha256=digest(path))
    if identity(path) != before: raise Refusal('input changed while hashing: '+str(path))
    return result


def capacity(scratch, required=0):
    row = {'host_free_bytes': shutil.disk_usage('/').free,
           'scratch_free_bytes': shutil.disk_usage(scratch).free,
           'host_floor_bytes': HOST_FLOOR, 'scratch_floor_bytes': SCRATCH_FLOOR,
           'private_bytes_budget': required, 'emergency_bytes': EMERGENCY}
    if row['host_free_bytes'] < HOST_FLOOR + required + EMERGENCY:
        raise Refusal('host capacity floor: '+json.dumps(row, sort_keys=True))
    if row['scratch_free_bytes'] < SCRATCH_FLOOR + required + EMERGENCY:
        raise Refusal('scratch capacity floor: '+json.dumps(row, sort_keys=True))
    return row


def private_size(root):
    return sum(p.stat().st_size + 4096 for p in Path(root).rglob('*') if p.is_file())


def check_shared(candidate, scratch15, previous_candidate, shared):
    for row in shared:
        left = snapshot(scratch15/row['path'])
        owner = snapshot(previous_candidate/row['path'])
        right = snapshot(candidate/row['path'])
        expected_final = dict(row['before'], nlink=3)
        if (left != expected_final or owner != expected_final or
                right != expected_final or left['inode'] != owner['inode'] or
                right['inode'] != left['inode']):
            raise Refusal('shared evidence identity/mode/hash changed: '+row['path'])


class Journal:
    def __init__(self, paths):
        self.paths = paths
        self.phase = 'preflight'
        raw = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
        self.record = {'pid': os.getpid(), 'pid_starttime': raw[19],
                       'started_ns': time.time_ns(), 'preparation_only': True}
        write_exclusive(paths['log'], b'', 0o600)
        self.event('started')

    def event(self, phase, **values):
        self.phase = phase
        row = dict(self.record, phase=phase, **values)
        with self.paths['log'].open('ab', buffering=0) as stream:
            stream.write((json.dumps(row, sort_keys=True)+'\n').encode())
            os.fsync(stream.fileno())

    def finish(self, returncode, exception=None):
        self.event(self.phase, returncode=returncode, exception=exception)
        row = dict(self.record, phase=self.phase, returncode=returncode, exception=exception,
                   log=str(self.paths['log']), log_sha256=digest(self.paths['log']))
        write_exclusive(self.paths['terminal'],
                        (json.dumps(row, sort_keys=True)+'\n').encode(), 0o600)


def prepare(source, scratch15, scratch, *, execute=False, old=OLD, target=TARGET,
            ihk_expected=IHK, overlay_sha=OVERLAY_SHA256,
            overlay_result_sha=OVERLAY_RESULT_SHA256, assets_root=ASSETS,
            image_receipt=RECEIPT, image_id=IMAGE_ID, exclusion=None,
            image_receipt_sha256=RECEIPT_SHA256,
            overlay_base_sha256=OVERLAY_BASE_BLOB_SHA,
            overlay_result_commit=OVERLAY_RESULT_COMMIT_SHA,
            previous_candidate=None, expected_shared_files=EXPECTED_SHARED_FILES):
    source, scratch15, scratch = map(Path, (source, scratch15, scratch))
    candidate = scratch/CANDIDATE_NAME
    previous_candidate = Path(previous_candidate) if previous_candidate else scratch/PREVIOUS_CANDIDATE_NAME
    paths = {'candidate': candidate, 'backup': scratch/(CANDIDATE_NAME+'-metadata-backup'),
             'output': scratch/(CANDIDATE_NAME+'-output'),
             'evidence': scratch/(CANDIDATE_NAME+'-evidence'),
             'manifest': scratch/MANIFEST_NAME, 'request': scratch/REQUEST_NAME,
             'log': scratch/LOG_NAME, 'terminal': scratch/TERMINAL_NAME,
             'lease': scratch/'native-exact-build-lease-50b08432-scratch-17.json',
             'exclusion': Path(exclusion) if exclusion else
                 scratch/'native-exact-candidate-operational-exclusion-scratch17.json'}
    for root in (source, scratch15, scratch):
        if not root.is_absolute() or root.is_symlink() or not root.is_dir():
            raise Refusal('invalid root: '+str(root))
        if root.resolve() != root: raise Refusal('root alias: '+str(root))
    if any(os.path.lexists(p) for p in paths.values()): raise Refusal('destination-present')
    # The journal exists before the first candidate mutation. Every Python
    # exception, including argparse SystemExit, produces a terminal failure.
    journal = Journal(paths) if execute else None
    try:
        if git(source,'rev-parse','--verify',target+'^{commit}').decode().strip()!=target:
            raise Refusal('target not fetched')
        if git(scratch15,'rev-parse','HEAD').decode().strip()!=old:
            raise Refusal('scratch15 main HEAD mismatch')
        validate_git_roots(scratch15)
        if (not previous_candidate.is_absolute() or previous_candidate.is_symlink() or
                not previous_candidate.is_dir() or previous_candidate.resolve()!=previous_candidate):
            raise Refusal('invalid prior candidate root: '+str(previous_candidate))
        delta = raw_delta(source, old, target)
        # Authenticate the immutable scratch15<->scratch16 pair before either
        # validate-only return or candidate mutation.  This is deliberately
        # read-only and is the same admission used by the execute path.
        entries = tree_entries(source, target)
        old_entries = {rel:(mode,kind,oid) for mode,kind,oid,rel in tree_entries(source,old)}
        sizes = {}
        for row in git(source,'ls-tree','-rlz',target).split(b'\0'):
            if row:
                metadata, rel = row.split(b'\t',1)
                fields = metadata.split()
                if fields[1] == b'blob': sizes[rel.decode()] = int(fields[3])
        shared = []
        private_bytes = 0
        for mode, kind, oid, rel in entries:
            if kind!='blob': continue
            prior = scratch15/rel
            can_share = (sizes[rel] > 1 << 20 and
                         rel.startswith('docs/verification/evidence/') and
                         old_entries.get(rel)==(mode,kind,oid) and
                         mode in ('100644','100755'))
            if can_share:
                before = snapshot(prior)
                owner_path = previous_candidate/rel
                owner = snapshot(owner_path)
                if (before['nlink']!=2 or owner['nlink']!=2 or before != owner or
                        before['mode']!=int(mode,8)&0o777 or
                        before['device']!=scratch.stat().st_dev or
                        git(source,'hash-object','--no-filters',str(prior)).decode().strip()!=oid):
                    raise Refusal('unauthenticated prior shared evidence: '+rel)
                if snapshot(prior)!=before: raise Refusal('shared input raced: '+rel)
                if snapshot(owner_path)!=owner: raise Refusal('prior shared evidence raced: '+rel)
                shared.append({'path':rel, 'before':before, 'blob':oid})
            else: private_bytes += sizes[rel] + 4096
        if len(shared) != expected_shared_files:
            raise Refusal('unexpected authenticated shared-file count: '+str(len(shared)))
        if not execute:
            return {'status': 'PASS_VALIDATE_ONLY', 'old': old, 'target': target,
                    'delta': delta, 'shared_files': len(shared),
                    'roots': {k:str(v) for k,v in paths.items()}}
        assets, receipt = Path(assets_root), Path(image_receipt)
        if digest(receipt) != image_receipt_sha256: raise Refusal('image receipt hash')
        receipt_data = json.loads(receipt.read_text())
        if receipt_data.get('status')!='PASS' or receipt_data.get('image_id')!=image_id:
            raise Refusal('image receipt identity')
        # Two private metadata copies plus IHK and target commit/tree growth.
        required = (private_bytes + 2*private_size(scratch15/'.git') +
                    2*private_size(scratch15/'ihk') + (32 << 20))
        pre = capacity(scratch, required)
        journal.event('preflight-passed', capacity=pre, shared_files=len(shared))
        ihk_src = scratch15/'ihk'
        if git(ihk_src,'rev-parse','HEAD').decode().strip()!=ihk_expected:
            raise Refusal('IHK HEAD mismatch')
        candidate.mkdir()
        journal.event('copy-private-metadata')
        shutil.copytree(scratch15/'.git',candidate/'.git',symlinks=False)
        g = candidate/'.git'
        install_private_objects(source,g,target)
        git(g,'read-tree',target)
        git(g,'update-ref','--no-deref','HEAD',target)
        journal.event('materialize-target')
        shared_by_path = {row['path']:row for row in shared}
        for mode,kind,oid,rel in entries:
            if kind=='commit': continue
            dst=candidate/rel
            if kind!='blob': raise Refusal('unexpected target entry')
            dst.parent.mkdir(parents=True,exist_ok=True)
            if rel in shared_by_path:
                prior=scratch15/rel
                if snapshot(prior)!=shared_by_path[rel]['before']:
                    raise Refusal('shared input changed before link')
                os.link(prior,dst,follow_symlinks=False)
            else:
                raw=object_bytes(source,'blob',oid)
                if mode=='120000': os.symlink(os.fsdecode(raw),dst)
                else: write_exclusive(dst,raw,int(mode,8))
        check_shared(candidate,scratch15,previous_candidate,shared)
        journal.event('copy-ihk')
        shutil.copytree(ihk_src,candidate/'ihk',symlinks=True)
        overlay=candidate/OVERLAY_REL
        if digest(overlay)!=overlay_sha: raise Refusal('overlay hash')
        if digest(candidate/'ihk'/OVERLAY_RESULT_REL)!=overlay_result_sha:
            raise Refusal('overlay result hash')
        if sha(git(candidate/'ihk','show','HEAD:'+OVERLAY_RESULT_REL))!=overlay_base_sha256:
            raise Refusal('overlay base hash')
        paths['backup'].mkdir()
        shutil.copytree(g,paths['backup']/'main.git',symlinks=False)
        shutil.copytree(candidate/'ihk/.git',paths['backup']/'ihk.git',symlinks=False)
        validate_git_roots(candidate)
        paths['output'].mkdir()
        paths['evidence'].mkdir()
        journal.event('canonical-manifest')
        with candidate_modules(candidate) as (driver_mod, manifest_mod, owner_mod):
            # These are the real candidate implementations, never a substitute
            # schema. main consumes the same argv as the canonical CLI.
            rc=manifest_mod.main(['--repo',str(candidate),'--assets',str(assets),
                '--output',str(paths['manifest']),'--candidate-sha',target])
            if rc!=0: raise Refusal('canonical manifest returned nonzero')
            manifest=json.loads(paths['manifest'].read_text())
            journal.event('canonical-input-verification')
            driver_mod.verify_inputs(candidate,target,assets,manifest,driver_mod.Runner())
            driver=candidate/'scripts/native_rust_exact_build_offline.py'
            owner=candidate/'scripts/native_rust_exact_build_container_owner.py'
            request={'candidate_sha':target,'image_id':image_id,
                'operational_exclusion_path':str(paths['exclusion']),
                'operational_exclusion_consumed':False,'preparation_only':True,
                'execution_released':False,'executable':False,'release_required':True,
                'launcher_aggregate_memory_gib':'16.2158',
                'source_root':str(candidate),'assets_root':str(assets),
                'output_root':str(paths['output']),'evidence_root':str(paths['evidence']),
                'input_manifest':str(paths['manifest']),
                'input_manifest_sha256':digest(paths['manifest']),
                'image_receipt':str(receipt),'image_receipt_sha256':digest(receipt),
                'driver_path':str(driver),'driver_path_sha256':digest(driver),
                'owner_path':str(owner),'owner_path_sha256':digest(owner),
                'provenance_path':str(driver),'provenance_path_sha256':digest(driver),
                'ihk_overlay_path':str(overlay),'ihk_overlay_sha256':overlay_sha,
                'ihk_overlay_base_sha':ihk_expected,
                'ihk_overlay_result_sha':overlay_result_commit,
                'ihk_overlay_base_blob_sha256':overlay_base_sha256,
                'ihk_overlay_result_blob_sha256':overlay_result_sha,
                'limits':dict(owner_mod.LIMITS),'host_measure_root':'/',
                'scratch_measure_root':str(scratch),
                'memory_allocation_roots':[str(candidate),str(paths['backup'])],
                'timeout':19800,'host_floor':HOST_FLOOR,'scratch_floor':SCRATCH_FLOOR,
                'lease_path':str(paths['lease'])}
            write_exclusive(paths['request'],
                (json.dumps(request,sort_keys=True,separators=(',',':'))+'\n').encode(),0o600)
            journal.event('canonical-owner-validation', request_sha256=digest(paths['request']))
            admitted=owner_mod.BuildOwner(json.loads(paths['request'].read_text()))
            admitted.validate()
            if admitted.docker is not None: raise Refusal('unexpected Docker construction')
            journal.event('canonical-owner-validated', measurement=admitted.measurement)
        check_shared(candidate,scratch15,previous_candidate,shared)
        post=capacity(scratch)
        for key in ('lease','exclusion'):
            if os.path.lexists(paths[key]): raise Refusal('unexpected runtime state: '+key)
        journal.event('complete', capacity=post, shared=shared)
        journal.finish(0)
        return {'status':'PASS_PREPARE_ONLY','old':old,'target':target,'delta':delta,
                'shared':[row['path'] for row in shared], 'manifest':str(paths['manifest']),
                'request':str(paths['request'])}
    except BaseException as error:
        if journal:
            journal.finish(2, type(error).__name__+': '+str(error))
        raise


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-root',default='/home/holden/mckernel')
    ap.add_argument('--scratch15-root',default=str(DEFAULT_SCRATCH/'mckernel-exact-candidate-1e95abdc-scratch-15'))
    ap.add_argument('--scratch-root',default=str(DEFAULT_SCRATCH))
    ap.add_argument('--execute',action='store_true')
    a=ap.parse_args(argv)
    try:
        print(json.dumps(prepare(a.source_root,a.scratch15_root,a.scratch_root,execute=a.execute),sort_keys=True))
        return 0
    except (Exception, SystemExit) as error:
        print('REFUSED: '+type(error).__name__+': '+str(error),file=sys.stderr)
        return 2

if __name__=='__main__': raise SystemExit(main())
