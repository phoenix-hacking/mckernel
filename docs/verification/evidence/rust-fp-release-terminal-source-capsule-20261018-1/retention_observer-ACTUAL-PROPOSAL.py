"""One released finite ordinary-UID retention operation; no root/Docker/cleanup."""
import argparse,hashlib,importlib.util,json,os,resource,stat,sys
from pathlib import Path
P=Path(__file__).resolve().parent
ENGINE = P/'retention-engine-frozen.py'
JOIN=P/'retained_join.py'
DEST=P/'retained-production-objects'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
PROFILE = {'cpu': 6, 'jobs': 1, 'address_space_bytes': 1073741824, 'cpu_seconds': 30, 'wall_seconds': 35, 'max_file_bytes': 67108864, 'max_total_bytes': 83886080, 'host_floor_bytes': 17179869184, 'scratch_floor_bytes': 12884901888, 'full_campaign_reserve_bytes': 536870912}

def need(value,why):
    if not value:raise RuntimeError(why)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def load(path):
    spec=importlib.util.spec_from_file_location(path.stem,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def checked_json(ref):
    path=Path(ref['path']);need(path.stat().st_size<=1048576,'bounded authority required');need(sha(path)==ref['sha256'],'authority digest differs');return json.loads(path.read_bytes())

def validate(release):
    need(release.get('schema')=='mckernel.rust-image.finite-retention-release.v1' and release.get('status')=='PASS_EXECUTION_RELEASE','finite retention not released')
    need(release.get('author') and release.get('boot_id')==BOOT and release.get('output')==str(DEST) and release.get('resource_profile')==PROFILE,'exact finite operation binding differs')
    for key,path in [('observer',Path(__file__).resolve()),('engine',ENGINE),('join',JOIN)]:
        need(release.get(key)==dict(path=str(path),sha256=sha(path)),'exact source map differs:'+key)
    payload={k:v for k,v in release.items() if k!='execution_review'}
    for role in ('source_review','execution_review'):
        review=checked_json(release[role]);need(review.get('status')=='PASS' and isinstance(review.get('reviewer'),str) and review['reviewer'] and review['reviewer']!=release['author'] and review.get('implementation_ownership') is False,'independent finite retention review required')
        need(review.get('source_map')=={k:release[k] for k in ('observer','engine','join')},'exact finite source map required')
        if role=='execution_review':need(review.get('reviewed_retention_payload_sha256')==hashlib.sha256(canonical(payload)).hexdigest(),'exact finite retention payload differs')
    return release

def put(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())

ARTIFACT_PATHS = {'CMakeCache.txt': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/CMakeCache.txt', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/CMakeCache.txt'}, 'build.make': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/build.make'}, 'build.stderr.log': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/evidence/build.stderr.log', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/build.stderr.log'}, 'build.stdout.log': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/evidence/build.stdout.log', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/build.stdout.log'}, 'compile_commands.json': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/compile_commands.json', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/compile_commands.json'}, 'cpu.c.o': {'action': 'reuse', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/heavy-proposal-1/postbuild-first-stage-1/retained-artifacts/cpu.artifact'}, 'link.txt': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/link.txt'}, 'mckernel.img': {'action': 'reuse', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/mckernel.img', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/heavy-proposal-1/postbuild-first-stage-1/retained-artifacts/image.artifact'}, 'mckernel.img.map': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/mckernel.img.map', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/mckernel.img.map'}, 'mckernel_rust.o': {'action': 'reuse', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/rust/mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/heavy-proposal-1/postbuild-first-stage-1/retained-artifacts/rust.artifact'}, 'process.c.o': {'action': 'reuse', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/heavy-proposal-1/postbuild-first-stage-1/retained-artifacts/process.artifact'}, 'production-abi-checks.json': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/evidence/production-abi-checks.json', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/production-abi-checks.json'}, 'production-abi-cpu.c': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/production-abi-cpu.c', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/production-abi-cpu.c'}, 'production-abi-process.c': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/production-abi-process.c', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/production-abi-process.c'}, 'receipt.json': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/evidence/receipt.json', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/receipt.json'}, 'release-fallback-cpu.o': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/fallback-cpu.o', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-fallback-cpu.o'}, 'release-fallback-cpu.o.nm': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/fallback-cpu.o.nm', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-fallback-cpu.o.nm'}, 'release-fallback-cpu.o.nm.stderr': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/fallback-cpu.o.nm.stderr', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-fallback-cpu.o.nm.stderr'}, 'release-fp-regs-production-checks.json': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/evidence/release-fp-regs-production-checks.json', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-fp-regs-production-checks.json'}, 'release-legacy-mckernel_rust.o': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/legacy-mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-legacy-mckernel_rust.o'}, 'release-legacy-mckernel_rust.o.nm': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/legacy-mckernel_rust.o.nm', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-legacy-mckernel_rust.o.nm'}, 'release-legacy-mckernel_rust.o.nm.stderr': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/legacy-mckernel_rust.o.nm.stderr', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-legacy-mckernel_rust.o.nm.stderr'}, 'release-native-mckernel_rust.o': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/native-mckernel_rust.o', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-native-mckernel_rust.o'}, 'release-native-mckernel_rust.o.nm': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/native-mckernel_rust.o.nm', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-native-mckernel_rust.o.nm'}, 'release-native-mckernel_rust.o.nm.stderr': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/native-mckernel_rust.o.nm.stderr', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-native-mckernel_rust.o.nm.stderr'}, 'release-production-c-abi-assertions.h': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/production-c-abi-assertions.h', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-production-c-abi-assertions.h'}, 'release-selected-cpu.o': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/selected-cpu.o', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-selected-cpu.o'}, 'release-selected-cpu.o.nm': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/selected-cpu.o.nm', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-selected-cpu.o.nm'}, 'release-selected-cpu.o.nm.stderr': {'action': 'copy', 'original': '/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/owner-work/output/build/release-fp-regs-production/selected-cpu.o.nm.stderr', 'retained': '/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/retained-production-objects/release-selected-cpu.o.nm.stderr'}}

def validate_artifact_rows(rows):
    need(isinstance(rows,list) and len(rows)==29,'exact finite twenty-nine-artifact authority required')
    need({r.get('kind') for r in rows}==set(ARTIFACT_PATHS),'exact twenty-nine artifact kinds required')
    need(sum(row['original']['size'] for row in rows)<=PROFILE['max_total_bytes'],'finite retention total bound')
    nm_rows=[r for r in rows if r['kind'].startswith('release-') and (r['kind'].endswith('.nm') or r['kind'].endswith('.nm.stderr'))]
    need(len(nm_rows)==8 and all(r['original']['size']<1048576 for r in nm_rows),'finite nm per-stream cap')
    objects=[r for r in rows if r['kind'].endswith('.o') or r['kind']=='mckernel.img']
    need(sum(r['original']['size'] for r in objects)<=67108864,'64MiB combined object cap')
    other=[r for r in rows if r not in nm_rows and r not in objects]
    need(sum(r['original']['size'] for r in other)<=8388608,'aggregate8MiB prior metadata plus new header/proof')
    names=[]
    for row in rows:
        fixed=ARTIFACT_PATHS[row['kind']]
        need(row.get('action')==fixed['action'] and row['original']['path']==fixed['original'] and row['retained']==fixed['retained'],'exact copy/reuse paths required')
        names.append(row['retained'])
        if row['action']=='reuse':
            need(row.get('retained_authority',{}).get('path')==row['retained'],'existing retained descriptor authority required')
        else:
            need(Path(row['retained']).parent==DEST and not os.path.lexists(row['retained']),'fresh exact copied destination required')
    need(len(set(names))==29,'unique finite destinations required')
    return rows

def run(release):
    need(os.getuid()==os.geteuid()==1000,'ordinary UID1000 required')
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'boot differs')
    need(set(os.sched_getaffinity(0))=={6},'exact cheap CPU6 profile required')
    resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    m=load(ENGINE);j=load(JOIN)
    for ref in release['physical_join'].values():checked_json(ref)
    guard=checked_json(release['physical_join']['guard']);owner=checked_json(release['physical_join']['owner']);post=checked_json(release['physical_join']['postjoin'])
    need(guard==dict(container_id=owner['container_id'],interrupted_signal=None,owner_receipt_sha256=release['physical_join']['owner']['sha256'],owner_status='PASS',retained_for_separate_cleanup=True,retired=True),'positive exact owner/guard join required')
    need(owner['retired'] is True and owner['terminal_container_retained'] is True and owner['exit_code']==0 and post['guard_direct_joined'] is True and post['root27_4_reacquired_after_join'] is True and post['guard_result_sha256']==release['physical_join']['guard']['sha256'] and post['owner_receipt_sha256']==release['physical_join']['owner']['sha256'],'positive physical postjoin required')
    state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());need(state.get('stop_reason') is None and state['last_rate_limits']['primary']['usedPercent']<97,'usage/service stop')
    for path,floor in [(Path('/home/holden'),PROFILE['host_floor_bytes']),(m.ROOT,PROFILE['scratch_floor_bytes'])]:
        fs=os.statvfs(path);need(fs.f_bavail*fs.f_frsize>=floor+PROFILE['full_campaign_reserve_bytes'],'full capacity floor/reserve required')
    need(not os.path.lexists(DEST),'fresh retention destination required')
    rows=validate_artifact_rows(release['artifacts'])
    before=[j.join_one(m,row['original']) for row in rows]
    need(all(row['nlink']==1 and row['uid']==1000 and row['device']==66306 and row['size']<=PROFILE['max_file_bytes'] for row in before),'finite source identity/size bound')
    DEST.mkdir(mode=0o700)
    try:
        results=[]
        for authority,original in zip(rows,before):
            if authority['action']=='reuse':
                retained=j.join_one(m,authority['retained_authority'])
                fresh=j.join_one(m,authority['original']);need(fresh==original,'source changed during reuse')
                pair=dict(original=original,retained=retained,outside_generic_receipt_inventory=True)
                j.join_pairs(m,[pair]);results.append(pair)
                continue
            # Both descriptors are bound before copying; never mutate source.
            source=Path(original['path']);parent,_=m.directory(source.parent);fd=None
            try:
                fd=os.open(source.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);opened=os.fstat(fd)
                need((opened.st_dev,opened.st_ino,opened.st_size)==(original['device'],original['inode'],original['size']),'source descriptor differs')
                raw=bytearray()
                while len(raw)<=original['size']:
                    part=os.read(fd,min(1<<20,original['size']+1-len(raw)))
                    if not part:break
                    raw.extend(part)
                need(len(raw)==original['size'] and hashlib.sha256(raw).hexdigest()==original['sha256'],'source bytes differ')
                target=Path(authority['retained']);put(target,raw)
                os.utime(target,ns=(opened.st_atime_ns,opened.st_mtime_ns),follow_symlinks=False)
                retained=j.join_one(m,m.observe_identity(target));fresh=j.join_one(m,authority['original']);need(fresh==original,'source changed during retention')
                pair=dict(original=original,retained=retained,outside_generic_receipt_inventory=True);j.join_pairs(m,[pair]);results.append(pair)
            finally:
                if fd is not None:os.close(fd)
                os.close(parent)
        need([j.join_one(m,row['original']) for row in rows]==before,'source changed after retention')
        put(DEST/'retained-objects.json',canonical(results))
        put(DEST/'result.json',canonical(dict(status='PASS_FINITE_EXACT_RETENTION_ONLY',pairs=len(results),total_bytes=sum(row['original']['size'] for row in results),source_release_sha256=sha(P/'retention-execution-release.json'),cleanup_authorized=False,artifact_acceptance=False,root=False,docker=False)))
        print(json.dumps(dict(status='PASS_FINITE_EXACT_RETENTION_ONLY',retained_objects_sha256=sha(DEST/'retained-objects.json'),output=str(DEST),cleanup_authorized=False)))
    except Exception as exc:
        put(DEST/'failure.json',canonical(dict(status='FAIL_PRESERVED_NO_RETRY',exception=type(exc).__name__,reason=str(exc))));raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--release',required=True);parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    need(Path(args.release)==P/'retention-execution-release.json' and sha(Path(args.release))==args.release_sha256,'exact released input required')
    run(validate(json.loads(Path(args.release).read_bytes())))
