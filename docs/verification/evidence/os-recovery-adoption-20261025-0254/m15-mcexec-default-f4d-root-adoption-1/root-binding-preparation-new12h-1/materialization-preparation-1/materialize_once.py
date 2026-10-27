"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fresh finite source materialization only. Explicit current Root source grant required.
No compiler, subprocess, container, native, canonical edit, timestamp normalization.
"""
import argparse, hashlib, importlib.util, json, os, stat, time
from decimal import Decimal
from pathlib import Path
HERE=Path(__file__).resolve().parent
PLAN=HERE/'MATERIALIZATION-PLAN.json'
PLAN_SHA='d18fc623e9b8a866381b7ae567500ec1f02b58e860aa22b4d086f7965b031b61'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(ok,why):
    if not ok:raise RuntimeError(why)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bound(ref):
    p=Path(ref['path']);need(digest(p)==ref['sha256'],'bound reference hash');return json.loads(p.read_bytes())
def write(path,value):
    with path.open('x') as f:json.dump(value,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def node(p):
    s=p.stat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
def raise_walk_error(error):raise error
def validate_entries(p):
    rows=p['entries'];need(len(rows)==p['files'] and sum(r['size'] for r in rows)==p['bytes']<256<<20,'finite count/byte bound')
    seen=set()
    for r in rows:
        rel=Path(r['relative']);need(r['relative']==str(rel) and not rel.is_absolute() and '..' not in rel.parts and rel.parts and r['relative'] not in seen,'unique finite relative')
        seen.add(r['relative']);need(r['kind'] in ('file','symlink') and isinstance(r['size'],int) and r['size']>=0,'known finite entry')
    return seen
def copy_entries(p,dest,journal,guard):
    """Accepted stable-FD/no-hardlink loop, also used by tiny fixture tests."""
    wanted=validate_entries(p);copied=0
    for row in p['entries']:
        guard();source=Path(row['source']);target=dest/row['relative'];target.parent.mkdir(parents=True,exist_ok=True);before=source.lstat()
        fields=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        if row['kind']=='symlink':
            raw=os.fsencode(os.readlink(source));after=source.lstat()
            need(stat.S_ISLNK(before.st_mode) and all(getattr(before,k)==getattr(after,k) for k in fields) and raw==os.fsencode(row['target']) and len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'stable exact tracked symlink')
            target.symlink_to(row['target'])
        else:
            need(stat.S_ISREG(before.st_mode) and source.resolve()==source and before.st_size==row['size'],'known source regular/size')
            fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC);h=hashlib.sha256();count=0
            with os.fdopen(fd,'rb') as inp,target.open('xb') as out:
                opened=os.fstat(inp.fileno())
                for block in iter(lambda:inp.read(1<<20),b''):guard();h.update(block);out.write(block);count+=len(block)
                out.flush();os.fsync(out.fileno());closed=os.fstat(inp.fileno())
            after=source.lstat()
            need(all(getattr(before,k)==getattr(opened,k)==getattr(closed,k)==getattr(after,k) for k in fields) and count==row['size'] and h.hexdigest()==row['sha256'],'stable exact source copy')
            target.chmod(row['mode']);need(target.stat().st_nlink==1,'never hardlink')
        journal.write(json.dumps(row,sort_keys=True)+'\n');journal.flush();copied+=row['size']
    seen=set()
    for directory,dirs,names in os.walk(dest,followlinks=False,onerror=raise_walk_error):
        need(all(not (Path(directory)/n).is_symlink() for n in dirs),'no directory symlink')
        seen.update(str((Path(directory)/name).relative_to(dest)) for name in names)
    need(seen==wanted,'exact finite source closure');return copied

def current_window(p):
    w=p['window'];need(digest(w['path'])==w['sha256'],'actual activation unchanged')
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==w['boot_id'],'same actual boot')
    g=p['guardian'];need(digest(g['path'])==g['sha256'],'actual guardian receipt unchanged')
    j=json.loads(Path(g['path']).read_bytes())['journal_state']
    need(j['boot_id']==w['boot_id'] and j['credit_run_id']==w['credit_run_id'],'actual guardian same boot/credit run')
    epoch=min(w['deadline_epoch'],g['deadline_epoch'],j['deadline'])
    boot=min(w['boot_deadline'],g['boot_deadline'],j['boot_deadline'])
    mono=min(w['monotonic_deadline'],g['monotonic_deadline'],j['finite_watcher_monotonic_deadline'])
    need(time.time()<epoch and time.clock_gettime(time.CLOCK_BOOTTIME)<boot and time.monotonic()<mono,'fixed actual inherited guardian cutoff expired')
def operation_guard(p):
    r=p['operation_guard'];need(digest(r['path'])==r['sha256'],'reviewed operation guard unchanged')
    spec=importlib.util.spec_from_file_location('actual_guardian_operation_guard',r['path']);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.guard()
def floors(p):
    need(int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024>=p['profile']['minimum_available_memory_bytes'],'fresh aggregate memory floor')
    host=os.statvfs(HERE);scratch=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512)
    need(host.f_bavail*host.f_frsize>=16*2**30+gap+p['bytes']+(16<<20) and scratch.f_bavail*scratch.f_frsize>=12*2**30,'floors/fullgap/complete growth')
def canonical_postimages(p):
    for r in p['canonical_postimages']:
        f=Path(r['path']);need(f.is_file() and not f.is_symlink() and f.stat().st_size==r['bytes'] and digest(f)==r['sha256'],'Root canonical postimage '+r['path'])
def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--grant',required=True);a.add_argument('--grant-sha256',required=True);args=a.parse_args()
    begin=time.monotonic();need(digest(PLAN)==PLAN_SHA,'exact fresh plan');p=json.loads(PLAN.read_bytes());validate_entries(p)
    need(p['scope']==SCOPE and os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0},'ordinary source-only CPU0 grant')
    operation_guard(p);current_window(p);g=bound(dict(path=args.grant,sha256=args.grant_sha256))
    need(g['status']=='PASS_ROOT_ORDINARY_SOURCE_MATERIALIZATION_ONLY' and g['scope']==SCOPE,'Root source-only grant')
    need(g['plan']==dict(path=str(PLAN),sha256=PLAN_SHA) and g['script']==dict(path=str(Path(__file__).resolve()),sha256=digest(__file__)),'exact source command bindings')
    need(g['window']==p['window'] and g['credit_run_id']==p['window']['credit_run_id'] and g['credit_ceiling']==p['window']['credit_ceiling'] and Decimal(g['cumulative_spent'])>=Decimal(p['window']['minimum_cumulative_spent']),'same actual clocks/credit ledger')
    need(g['current_account_guard_passed'] is True and g['real_holds_absent'] is True,'actual current Root account/holds admission')
    need(Decimal(g['cumulative_spent'])<Decimal(g['credit_ceiling']),'existing cumulative credit ceiling exhausted')
    bound(g['current_account_guard']);bound(g['current_native_ownership']);bound(p['adoption_manifest'])
    need(time.time()-g['observed_epoch']>=0 and time.time()-g['observed_epoch']<=60,'fresh actual Root observation')
    canonical_postimages(p);floors(p);out=Path(p['output_root']);dest=Path(p['destination'])
    need(out.parent==HERE and dest==out/'materialized-source' and not os.path.lexists(out),'fresh exact namespace')
    out.mkdir(mode=0o700);write(out/'ROOT-GRANT-BOUND.json',dict(grant=dict(path=args.grant,sha256=args.grant_sha256),plan=dict(path=str(PLAN),sha256=PLAN_SHA)))
    dest.mkdir(mode=0o700)
    with (out/'materialization-journal.jsonl').open('x') as journal:copied=copy_entries(p,dest,journal,lambda:current_window(p))
    canonical_postimages(p);floors(p);operation_guard(p)
    result=dict(status='PASS_FINITE_TARGET_SOURCE_MATERIALIZATION_ONLY',scope=SCOPE,plan=dict(path=str(PLAN),sha256=PLAN_SHA),source_root=str(dest),source_identity=node(dest),files=p['files'],copied_bytes=copied,source_overrides=p['source_overrides'],compiler_or_native=False,seconds=time.monotonic()-begin)
    write(out/'MATERIALIZATION-RESULT.json',result);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
