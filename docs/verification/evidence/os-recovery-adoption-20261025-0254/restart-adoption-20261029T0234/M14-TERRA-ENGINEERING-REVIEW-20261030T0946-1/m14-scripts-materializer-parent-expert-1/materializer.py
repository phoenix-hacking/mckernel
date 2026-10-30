#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One ordinary exact private source materialization; no compiler, owner import, root,
Docker or guest. Existing COPY7 stable-copy body, explicit finite current manifest.
"""
from pathlib import Path
import hashlib,json,os,stat,time,subprocess
OUT=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1')
DEST=OUT/'materialized-source'
MANIFEST=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-inputs.CURRENT290-QUALIFIED-IHK3114.json')
MANIFEST_SHA='3a0653623cc1cdb7ebb0e217274ded31ea8fea5068140af4884c273b493b5018'
PLAN=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/COPY-PLAN.CURRENT290-QUALIFIED-IHK3114.SOURCE-ONLY.json')
PLAN_SHA='da8215e528453c8fe4596da066be5e3bac7f8c0a666702ba3f10060371cf034b'
MAX_GROWTH=256<<20
EXTRA=16<<20
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write(canonical(value));stream.flush();os.fsync(stream.fileno())


def main():
    raise RuntimeError('UNRELEASED SCRIPTS SUCCESSOR: owner, snapshot and operation authority not bound')
    begin=time.monotonic()
    need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6},'ordinary CPU6 grant required')
    need(not os.path.lexists(OUT),'fresh coherent whole output root required')
    raw=MANIFEST.read_bytes();need(sha(raw)==MANIFEST_SHA,'exact current source manifest')
    document=json.loads(raw)
    rawplan=PLAN.read_bytes();need(sha(rawplan)==PLAN_SHA,'exact finite source copy plan')
    plan=json.loads(rawplan)
    need(sha(canonical(document))==plan['manifest_canonical_sha256'],'exact canonical source authority')
    expected=dict(document['materialized_repository_files']);expected.update({p:r['sha256'] for p,r in document['retained_ihk_git_metadata'].items()})
    links=document['materialized_symlinks'];modes=document['materialized_modes'];sizes=plan['sizes'];origins=plan['origins']
    need(expected==plan['expected'] and set(expected)==set(modes)==set(sizes)==set(origins),'exact source/copy entry closure')
    need(len(expected)==6153 and len(links)==49 and sum(sizes.values())==105804031,'reviewed finite source extent')
    need(document['candidate_sha']=='eb3ce544eb1f479a56933a5c7fa8300ab6dfe533' and document['ihk_sha']=='3114d9e7101ad52030eb3effa849a5c108972a1f','current main + selected qualified IHK overlay')
    total=sum(sizes.values());need(total<=MAX_GROWTH,'bounded whole source growth')
    host=os.statvfs(OUT.parent);scratch=os.statvfs('/home/holden/mckernel-work/scratch')
    need(host.f_bavail*host.f_frsize>=16*2**30+total+EXTRA,'HOST floor plus complete source growth/capture')
    need(scratch.f_bavail*scratch.f_frsize>=14091616256,'existing greater scratch preservation floor; no scratch writes')
    OUT.mkdir(mode=0o700)
    admission=dict(host_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,source_growth_bytes=total,max_source_growth_bytes=MAX_GROWTH,capture_extra_bytes=EXTRA)
    write('admission.json',admission)
    DEST.mkdir(mode=0o700)
    for relative in document['gitlinks']:
        if relative!='ihk':(DEST/relative).mkdir(parents=True,exist_ok=True)
    copied = 0
    with (OUT / 'materialization-journal.jsonl').open('x') as journal:
        for relative, checksum in sorted(expected.items()):
            rel = Path(relative)
            need(not rel.is_absolute() and '..' not in rel.parts and '.' not in rel.parts, 'exact safe source relative path')
            origin=origins[relative]
            destination = DEST / relative;destination.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(origin,dict):
                need(relative in {'AGENTS.md','scripts/__pycache__/rust-source-retirement-audit.cpython-36.pyc'} and origin['kind']=='exact_committed_git_blob','finite committed-blob source only')
                tool=Path(origin['tool']['path']);need(tool.resolve()==tool and not tool.is_symlink() and sha(tool.read_bytes())==origin['tool']['sha256'],'authenticated exact existing Git tool')
                raw=subprocess.run([str(tool),'--git-dir='+origin['git_dir'],'cat-file','blob',origin['object']],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':'/usr/bin','LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}).stdout
                need(len(raw)==sizes[relative] and sha(raw)==checksum and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==origin['object'],'exact frozen committed blob bytes')
                with destination.open('xb') as output:output.write(raw);output.flush();os.fsync(output.fileno())
                destination.chmod(modes[relative]);need(destination.stat().st_nlink==1,'private committed-blob copy inode')
                entry=dict(path=relative,sha256=checksum,size=len(raw),kind='file',source_kind='exact_committed_git_blob')
                journal.write(json.dumps(entry,sort_keys=True)+'\n');journal.flush();copied+=entry['size'];continue
            source=Path(origin)
            before = source.lstat()
            if relative in links:
                row = links[relative];target = os.readlink(source);raw = os.fsencode(target)
                need(stat.S_ISLNK(before.st_mode) and target == row['target'] == Path(target).name
                     and sha(raw) == checksum and stat.S_IMODE(before.st_mode) == 0o777, 'exact tracked symlink')
                destination.symlink_to(target)
                entry = dict(path=relative, sha256=checksum, size=len(raw), kind='symlink', target=target)
            else:
                need(stat.S_ISREG(before.st_mode) and source.resolve() == source and before.st_size == sizes[relative],
                     'regular known source size/path: ' + relative)
                fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
                digest = hashlib.sha256();count = 0
                with os.fdopen(fd, 'rb') as inp, destination.open('xb') as output:
                    opened = os.fstat(inp.fileno())
                    for block in iter(lambda: inp.read(1 << 20), b''):
                        digest.update(block);output.write(block);count += len(block)
                    output.flush();os.fsync(output.fileno())
                    closed = os.fstat(inp.fileno())
                after = source.lstat()
                fields = ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
                need(all(getattr(before,key)==getattr(opened,key)==getattr(closed,key)==getattr(after,key) for key in fields)
                     and count == sizes[relative] and digest.hexdigest() == checksum,
                     'stable exact copy/hash: ' + relative)
                destination.chmod(modes[relative])
                need(destination.stat().st_nlink == 1, 'private copy, never shared hardlink')
                entry = dict(path=relative, sha256=checksum, size=count, kind='file')
            journal.write(json.dumps(entry, sort_keys=True) + '\n');journal.flush();copied += entry['size']
    # A names/type/mode closure check reads the newly owned tree only; copied
    # file bytes were hash-checked in their one copy pass, not recursively again.
    observed = set()
    for directory, directories, names in os.walk(DEST, followlinks=False):
        for name in names:
            path = Path(directory)/name;relative=str(path.relative_to(DEST));observed.add(relative)
            meta=path.lstat()
            need(relative in expected and stat.S_IMODE(meta.st_mode)==modes[relative], 'new tree file/mode closure')
            need(stat.S_ISLNK(meta.st_mode) if relative in links else stat.S_ISREG(meta.st_mode), 'new tree kind closure')
        for name in directories:
            need(not (Path(directory)/name).is_symlink(), 'no directory symlinks')
    need(observed == set(expected), 'complete copied entry closure')
    for relative,row in links.items():
        destination=DEST/relative;target=destination.parent/row['target']
        need(target.is_file() and not target.is_symlink() and row['target_path'] in expected
             and expected[row['target_path']]==row['target_sha256'], 'tracked symlink targets use copied verified files')
    result=dict(scope=SCOPE,status='PASS_CURRENT290_MAIN_WITH_QUALIFIED_COPY7_IHK3114_SOURCE_MATERIALIZATION_ONLY',source_root=str(DEST),source_entries=len(expected),regular_files=len(expected)-len(links),tracked_symlinks=len(links),copied_bytes=copied,source_derivative_sha256=document['source_derivative_sha256'],materialization_sha256=document['materialization_sha256'],source_manifest_path=str(MANIFEST),source_manifest_sha256=MANIFEST_SHA,source_manifest_canonical_sha256=sha(canonical(document)),copy_plan_sha256=PLAN_SHA,canonical_main_commit=document['candidate_sha'],selected_IHK=document['ihk_sha'],canonical_IHK_gitlink=document['canonical_main_gitlinks']['ihk'],vendor_override=document['selected_vendor_override'],operation_scope='IMAGE_BUILD_ONLY',native_fork_owned_transaction=False,kernel_native_fork_config=True,native_pair_acceptance='OPEN',canonical_source_written=False,frozen_image_or_build_written=False,builds=0,guests=0,seconds=time.monotonic()-begin)
    write('MATERIALIZATION-RESULT.json',result)
    print(json.dumps(result,sort_keys=True))

# FD-relative successor added below; CLI remains unconditionally blocked.
import sys
_FD_CHECKER_SHA='34bd9802c507b3408b685c6233f0a2f711edbdf7a6f31c5dcd3eaba70128ba8f'
_DIR=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
_READ=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
_FIELDS=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def _same(a,b):return all(getattr(a,k)==getattr(b,k) for k in _FIELDS)
def _id(s):return (s.st_dev,s.st_ino,stat.S_IFMT(s.st_mode))
def _dir_at(fd,name):
 before=os.stat(name,dir_fd=fd,follow_symlinks=False)
 need(stat.S_ISDIR(before.st_mode),'non-directory or symlink component: '+name)
 child=os.open(name,_DIR,dir_fd=fd)
 try:need(_id(os.fstat(child))==_id(before),'directory replaced during open: '+name)
 except BaseException:os.close(child);raise
 return child
def _absolute_dir(path):
 p=os.fspath(path);need(os.path.isabs(p) and os.path.normpath(p)==p,'absolute normalized directory')
 fd=os.open('/',_DIR)
 try:
  for name in pathlib_parts(p):
   child=_dir_at(fd,name);os.close(fd);fd=child
  return fd
 except BaseException:os.close(fd);raise
def pathlib_parts(p):return [x for x in p.split('/') if x]
def _absolute_dir_pins(path):
 p=os.fspath(path);need(os.path.isabs(p) and os.path.normpath(p)==p,'absolute normalized directory')
 fd=os.open('/',_DIR);pins=[_id(os.fstat(fd))]
 try:
  for name in pathlib_parts(p):
   child=_dir_at(fd,name);os.close(fd);fd=child;pins.append(_id(os.fstat(fd)))
  return fd,tuple(pins)
 except BaseException:os.close(fd);raise
def _revalidate_destination_parent(path,pins,held_fd):
 current,current_pins=_absolute_dir_pins(path)
 try:
  need(current_pins==pins and _id(os.fstat(current))==_id(os.fstat(held_fd)),
       'destination ancestor identity mismatch')
 finally:os.close(current)
def _relative_dir(rootfd,parts,pins):
 fd=os.dup(rootfd);prefix=[]
 try:
  for name in parts:
   prefix.append(name);child=_dir_at(fd,name);os.close(fd);fd=child;key='/'.join(prefix)
   if pins is not None:need(key in pins and _id(os.fstat(fd))==pins[key],'directory identity mismatch: '+key)
  return fd
 except BaseException:os.close(fd);raise
def _load_checker():
 p=Path(__file__).with_name('verify_scripts_fd.py');parent=_absolute_dir(str(p.parent));fd=None
 try:
  fd=os.open(p.name,_READ,dir_fd=parent);before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_size<=1<<20,'checker regular file and bounded size');data=b''
  while True:
   chunk=os.read(fd,65536)
   if not chunk:break
   data+=chunk
  need(_same(before,os.fstat(fd)) and hashlib.sha256(data).hexdigest()==_FD_CHECKER_SHA,'checker hash or stability mismatch')
 finally:
  if fd is not None:os.close(fd)
  os.close(parent)
 ns={'__name__':'bound_scripts_fd_checker','__file__':str(p)};exec(compile(data,str(p),'exec'),ns)
 need(callable(ns.get('index_manifest')) and callable(ns.get('check_fd')),'checker interface')
 return ns
def _verify(ns,fd,rootmode,entries):
 n=ns['check_fd'](fd,rootmode,entries);need(type(n) is int and n==len(entries),'checker success semantics mismatch')
def _copy_one(source_fd,source_name,dest_fd,dest_name,row):
 before=os.stat(source_name,dir_fd=source_fd,follow_symlinks=False)
 need(stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode)==int(row['mode'],8) and before.st_size==row['bytes'],'source file type/mode/size: '+dest_name)
 src=os.open(source_name,_READ,dir_fd=source_fd)
 try:
  opened=os.fstat(src);need(_same(before,opened),'source file replaced: '+dest_name)
  out=os.open(dest_name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=dest_fd)
  try:
   digest=hashlib.sha256();count=0
   while True:
    block=os.read(src,1<<20)
    if not block:break
    digest.update(block);count+=len(block);written=0
    while written<len(block):
     n=os.write(out,block[written:]);need(n>0,'short write: '+dest_name);written+=n
   need(count==row['bytes'] and digest.hexdigest()==row['sha256'],'source content mismatch: '+dest_name)
   need(_same(os.fstat(src),opened) and _same(os.stat(source_name,dir_fd=source_fd,follow_symlinks=False),before),'source changed: '+dest_name)
   os.fchmod(out,int(row['mode'],8));os.fsync(out);target=os.fstat(out)
   need(stat.S_ISREG(target.st_mode) and target.st_nlink==1,'destination link/type: '+dest_name)
  finally:os.close(out)
 finally:os.close(src)
def copy_scripts_body(source_root,destination,document):
 source_root=os.fspath(source_root);destination=os.fspath(destination)
 need(os.path.isabs(source_root) and os.path.normpath(source_root)==source_root and source_root!='/', 'source root')
 need(os.path.isabs(destination) and os.path.normpath(destination)==destination and destination!='/','destination root')
 need(not(destination==source_root or destination.startswith(source_root+'/')),'destination nested in source')
 ns=_load_checker();base={'base_root_mode':document['base_root_mode'],'base_members':document['base_members'],'additions':[]}
 rootmode,base_entries=ns['index_manifest'](base);_,union=ns['index_manifest'](document);additions=document['additions']
 need(len(additions)==6 and all(x['type']=='file' and '/' not in x['path'] for x in additions),'exact six top-level file additions')
 need(all(x['path'] not in base_entries for x in additions),'addition name collision')
 srcroot=_absolute_dir(source_root);destparent=None;dstroot=None
 try:
  destparent,destpins_absolute=_absolute_dir_pins(os.path.dirname(destination))
  source_identity=_id(os.fstat(srcroot));_verify(ns,srcroot,rootmode,base_entries)
  directories=sorted((p for p,x in union.items() if x['type']=='directory'),key=lambda x:(len(x.split('/')),x));srcpins={}
  for relative in directories:
   fd=_relative_dir(srcroot,relative.split('/'),None)
   try:srcpins[relative]=_id(os.fstat(fd))
   finally:os.close(fd)
  dest_name=os.path.basename(destination)
  _revalidate_destination_parent(os.path.dirname(destination),destpins_absolute,destparent)
  try:os.mkdir(dest_name,0o700,dir_fd=destparent)
  except FileExistsError:raise RuntimeError('destination already exists')
  dstroot=_dir_at(destparent,dest_name);dstpins={}
  for relative in directories:
   parts=relative.split('/');parent=_relative_dir(dstroot,parts[:-1],dstpins)
   try:
    os.mkdir(parts[-1],0o700,dir_fd=parent);d=_dir_at(parent,parts[-1]);dstpins[relative]=_id(os.fstat(d));os.close(d)
   finally:os.close(parent)
  added={x['path']:x for x in additions}
  for relative in sorted(p for p,x in union.items() if x['type']=='file'):
   parts=relative.split('/');dparent=_relative_dir(dstroot,parts[:-1],dstpins)
   try:
    if relative in added:
     candidate=added[relative]['source_candidate'];need(os.path.isabs(candidate) and os.path.normpath(candidate)==candidate and candidate!='/','addition source path');sparent=_absolute_dir(os.path.dirname(candidate));sname=os.path.basename(candidate)
    else:sparent=_relative_dir(srcroot,parts[:-1],srcpins);sname=parts[-1]
    try:_copy_one(sparent,sname,dparent,parts[-1],union[relative])
    finally:os.close(sparent)
   finally:os.close(dparent)
  for relative in reversed(directories):
   d=_relative_dir(dstroot,relative.split('/'),dstpins)
   try:os.fchmod(d,int(union[relative]['mode'],8))
   finally:os.close(d)
  os.fchmod(dstroot,int(rootmode,8))
  _verify(ns,srcroot,rootmode,base_entries);_verify(ns,dstroot,rootmode,union)
  current=_absolute_dir(source_root)
  try:need(_id(os.fstat(current))==source_identity,'source root replaced')
  finally:os.close(current)
  _revalidate_destination_parent(os.path.dirname(destination),destpins_absolute,destparent)
  need(_id(os.stat(dest_name,dir_fd=destparent,follow_symlinks=False))==_id(os.fstat(dstroot)),'destination root replaced')
  _revalidate_destination_parent(os.path.dirname(destination),destpins_absolute,destparent)
  return len(union)
 finally:
  if dstroot is not None:os.close(dstroot)
  os.close(srcroot)
  if destparent is not None:os.close(destparent)
if __name__=='__main__':main()
