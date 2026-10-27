"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One explicit Root-granted creation of missing empty nested read-only bind target.
No source file edits, compiler, subprocess, container, mount or cleanup operation.
"""
import argparse,hashlib,importlib.util,json,os,stat
from pathlib import Path
HERE=Path(__file__).resolve().parent
PLAN=HERE/'REPAIR-PLAN.json'
PLAN_SHA='8a516bac1c73d2fd1f40cf2953cad825212c3dd83df6ae30cc4570dd65531a93'
FIELDS=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def need(ok,why):
    if not ok:raise ValueError(why)
def ref(path):
    p=Path(path);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def bound(r):
    actual=ref(r['path']);need(all(actual[k]==v for k,v in r.items()),'bound input changed');return json.loads(Path(r['path']).read_bytes())
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def meta(s):return {k:getattr(s,k) for k in FIELDS}
def node(path):
    p=Path(path);s=p.lstat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
def directory(path):
    p=Path(path);need(p.is_absolute() and '..' not in p.parts,'canonical absolute directory')
    need(all(not x.is_symlink() for x in (p,*p.parents)),'no symlink component')
    s=p.lstat();need(stat.S_ISDIR(s.st_mode) and s.st_uid==s.st_gid==1000,'owned directory type');return node(p)
def inventory(root,rows):
    """Exact old file inventory plus stable metadata; excludes directory shape."""
    root=Path(root);seen=set()
    def failed(e):raise e
    for parent,dirs,names in os.walk(root,followlinks=False,onerror=failed):
        need(all(not (Path(parent)/n).is_symlink() for n in dirs),'no directory symlink')
        seen.update(str((Path(parent)/n).relative_to(root)) for n in names)
    need(seen=={r['relative'] for r in rows} and len(seen)==len(rows),'exact finite file names')
    digest=hashlib.sha256();total=0
    for r in rows:
        p=root/r['relative'];before=p.lstat()
        if r['kind']=='symlink':
            raw=os.fsencode(os.readlink(p));after=p.lstat();need(stat.S_ISLNK(before.st_mode) and raw==os.fsencode(r['target']) and meta(before)==meta(after),'stable original file symlink')
        else:
            need(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'regular singlelink source')
            fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
            try:
                opened=os.fstat(fd);h=hashlib.sha256();count=0
                for chunk in iter(lambda:os.read(fd,65536),b''):h.update(chunk);count+=len(chunk);need(count<=r['size'],'bounded source file')
                closed=os.fstat(fd);after=p.lstat();need(meta(before)==meta(opened)==meta(closed)==meta(after) and count==r['size'],'stable source FD/path')
                need(h.hexdigest()==r['sha256'],'original source bytes unchanged')
            finally:os.close(fd)
            raw=None
        if raw is not None:need(len(raw)==r['size'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'original symlink bytes unchanged')
        need(stat.S_IMODE(before.st_mode)==r['mode'],'source mode unchanged')
        digest.update(canonical(dict(relative=r['relative'],sha256=r['sha256'],metadata=meta(before))));total+=r['size']
    return dict(files=len(rows),bytes=total,all_file_bytes_and_metadata_sha256=digest.hexdigest())
def create_exact_empty(root,target,parent_expected):
    root=Path(root);target=Path(target);need(target.relative_to(root)==Path('executer/user/lib/libdwarf/libdwarf'),'only exact nested libdwarf target')
    before=directory(root);parent=directory(target.parent);need(parent==parent_expected,'exact original parent identity')
    need(not os.path.lexists(target),'target must be absent; no replacement or replay')
    fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        opened=os.fstat(fd);need(opened.st_dev==parent['device'] and opened.st_ino==parent['inode'],'parent FD identity')
        os.mkdir(target.name,mode=0o700,dir_fd=fd)
        after=directory(target);need(after['device']==before['device'] and after['mode']==0o700 and not list(target.iterdir()),'exact owned empty mountpoint')
        need(directory(root)==before and directory(target.parent)==parent,'root/parent identities preserved')
        return after
    finally:os.close(fd)
def campaign(p):
    r=p['guard'];need(ref(r['path'])==r,'exact actual guardv2')
    spec=importlib.util.spec_from_file_location('actual_mountpoint_repair_guard',r['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m.guard()
def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--grant',required=True);a.add_argument('--grant-sha256',required=True);args=a.parse_args()
    need(ref(PLAN)['sha256']==PLAN_SHA,'exact repair plan');p=json.loads(PLAN.read_bytes());clocks=campaign(p);g=bound(dict(path=str(Path(args.grant).resolve()),sha256=args.grant_sha256))
    need(g['status']=='PASS_ROOT_ORDINARY_EXACT_EMPTY_MOUNTPOINT_CREATION' and g['author']=='/root' and g['scope']==p['scope'],'exact Root ordinary shape grant')
    need(g['plan']==ref(PLAN) and g['script']==ref(Path(__file__).resolve()) and g['current_free_independently_accepted'] is True and g['one_heavy_absent'] is True,'actual source operation bindings/currentfree')
    need(len(g['observed_clocks'])==3 and all(0<=now-old<120 for now,old in zip(clocks,g['observed_clocks'])),'fresh current Root admission')
    ledger=bound(g['current_nonce_ledger']);need(ledger.get('author')=='/root' and ledger.get('complete_within_declared_current_boundary') is True and ledger.get('root_attests_no_unlisted_post_boundary_execution_or_custody_operation') is True and len(set(ledger['consumed_nonces']))==len(ledger['consumed_nonces'])>=p['required_current_ledger_minimum'] and p['failed_nonce'] in ledger['consumed_nonces'],'current Root29+ consumed ledger')
    bound(g['independent_current_free']);materialization=bound(p['source_materialization']);plan=bound(p['file_inventory']);root=Path(p['source_root']);target=Path(p['target']);receipt=Path(p['output_receipt'])
    need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary UID/GID1000')
    need(directory(root)==p['source_identity']==materialization['source_identity'] and directory(target.parent)==p['parent_identity'],'frozen qualified source/parent identities')
    need(not os.path.lexists(target) and not os.path.lexists(receipt),'fresh absent target/receipt')
    host=os.statvfs(root);scratch=os.statvfs('/home/holden/mckernel-work/scratch');need(host.f_bavail*host.f_frsize>=16*2**30 and scratch.f_bavail*scratch.f_frsize>=12*2**30,'retained HOST16/scratch12GiB floors')
    before_root_stat=meta(root.lstat());parent_metadata_before=meta(target.parent.lstat());before=inventory(root,plan['entries']);need(before['files']==p['files'] and before['bytes']==p['bytes'],'exact7015/121362296 byte inventory')
    campaign(p)
    intent=receipt.with_name('ROOT-MOUNTPOINT-REPAIR-INTENT.json')
    with intent.open('xb') as f:
        f.write(canonical(dict(status='ROOT_EXACT_EMPTY_DIRECTORY_REPAIR_INTENT',plan=ref(PLAN),grant=ref(args.grant),before=before,source_identity=p['source_identity'],target=p['target'])));f.flush();os.fsync(f.fileno())
    newdir=create_exact_empty(root,target,p['parent_identity']);after=inventory(root,plan['entries']);need(before==after and meta(root.lstat())==before_root_stat,'all file bytes/timestamps and source root metadata preserved')
    campaign(p);result=dict(status='PASS_EXACT_EMPTY_LIBDWARF_MOUNTPOINT_SHAPE_ONLY',scope=p['scope'],source_materialization=p['source_materialization'],plan=ref(PLAN),grant=ref(args.grant),source_identity_before=p['source_identity'],source_identity_after=node(root),before=before,after=after,mountpoint=newdir,mountpoint_empty=True,parent_metadata_before=parent_metadata_before,parent_metadata_after=meta(target.parent.lstat()),original_materialization_result_unchanged=True,original_file_inventory_unchanged=True,original19_and_outer5_source_files_unchanged=True,compiler_or_container=False,execution_authority=False)
    with receipt.open('xb') as f:f.write(canonical(result))
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
