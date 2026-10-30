"""HOST-only coordinator grant guard; no SDK mount/source-view claims."""
import datetime, hashlib, json, math, os, stat, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parent
RUN = Path('/home/holden/mckernel/.git/os-autopilot/runs/20261030T175456Z-0e492844')
THREAD = '01a18bc3-e072-7810-9426-75101b0856c0'
RESET = 1793774133
PROFILE_HASH = '1d65b544d4af52505b91c5ffde5fd8786bf5e7bac16ee84835d2b4175ca01ccf'


def require(ok, message):
    if not ok: raise RuntimeError(message)


def secure_read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == os.getuid() and st.st_size <= 8*1048576, 'control identity')
        data = bytearray()
        while len(data) <= 8*1048576:
            b = os.read(fd, 65536)
            if not b: break
            data.extend(b)
        st2 = os.fstat(fd)
        require((st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(st2.st_dev,st2.st_ino,st2.st_size,st2.st_mtime_ns,st2.st_ctime_ns), 'control changed')
        return bytes(data)
    finally: os.close(fd)


def birth(pid):
    s = Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid, 'ppid':int(s[1]), 'start':s[19], 'state':s[0]}


def live_binding(expected):
    require(type(expected.get('pid')) is int, 'bad process pid')
    actual = birth(expected['pid'])
    require(actual['start']==expected.get('start') and actual['ppid']==expected.get('ppid') and actual['state'] not in ('Z','X','x'), 'process owner changed')
    return actual


def check(active=False, collector=False):
    # Grant is written by cooperating coordinator after independent review, never by this runner.
    grant = json.loads(secure_read(HERE/('TOOLCHAIN-COLLECT-GRANT.json' if collector else 'HOST-GRANT.json')))
    require(grant.get('status')==('ROOT_ADMITS_ONE_HOST_TOOLCHAIN_INVENTORY' if collector else 'ROOT_ADMITS_ONE_HOST_RUST_COMPILE') and grant.get('thread_id')==THREAD and grant.get('profile_sha256')==PROFILE_HASH, 'grant not bound')
    require(grant.get('native_access') is False and grant.get('jobs')==1 and grant.get('cpu')==[6] and grant.get('address_space_bytes')==4294967296, 'grant scope differs')
    nonce=grant.get('nonce'); require(isinstance(nonce,str) and len(nonce)==64 and all(c in '0123456789abcdef' for c in nonce), 'fresh nonce required')
    require(nonce != 'cf0a2a5bd31bdc0441ba1b9e2b1d2c7551ebb3690e867873fce632dfe6b2f507', 'abandoned nonce')
    require(type(grant.get('at')) in (float,int) and 0 <= time.time()-grant['at'] <= (240 if active else 60), 'grant stale')
    live_binding(grant['coordinator'])
    a=json.loads(secure_read(CAMPAIGN/'ACTUAL-CONTROLS-ARMED.json'))
    b=json.loads(secure_read(CAMPAIGN/'ACTUAL-CAPACITY-FALLBACK-ARMED.json'))
    journal=json.loads(secure_read(CAMPAIGN/'journal.json'))
    require(a.get('thread_id')==b.get('thread_id')==THREAD and b.get('status')=='PASS_ACTUAL_MANUAL_SAME_ROOT_RESUME' and b.get('billing_mode')=='included_only' and journal.get('status')=='armed', 'actual controls inactive')
    require(a['binding']==b['binding'] and a['caps']==b['caps'], 'controls differ')
    for row in a['binding'].values(): live_binding(row)
    live_binding(b['supervisor'])
    caps=a['caps']; require(caps['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'boot changed')
    for key, now in [('deadline',time.time()),('boot_deadline',time.clock_gettime(time.CLOCK_BOOTTIME)),('monotonic_deadline',time.monotonic())]:
        bound=caps[key]; require(type(bound) in (int,float) and math.isfinite(bound) and now+(0 if active else 195)<bound, 'inherited clock bound')
    quota=grant['weekly']; used=quota.get('usedPercent'); qtime=quota.get('observed_at')
    require(quota.get('limitId')=='codex' and quota.get('windowDurationMins')==10080 and quota.get('resetsAt')==RESET and type(used) in (int,float) and math.isfinite(used) and 0<=used<100 and type(qtime) in (int,float) and 0<=time.time()-qtime<=(240 if active else 60), 'fresh original weekly observation required')
    require(grant.get('source_owner_exclusion')=='HELD_BY_COORDINATOR_AND_COOPERATING_OWNERS', 'source custody not granted')
    gate_sha=hashlib.sha256(secure_read(HERE/'host_gate_direct_v2.py')).hexdigest()
    runner = 'collect_host_toolchain_v4.py' if collector else 'host_exec_direct_v2.py'
    require(hashlib.sha256(secure_read(HERE/runner)).hexdigest()==grant.get('runner_sha256') and gate_sha==grant.get('gate_sha256'), 'runner source differs from grant')
    if not collector:
        require(grant.get('toolchain_manifest_status')=='REVIEWED_HELD_MATCH', 'toolchain custody not granted')
        manifest=secure_read(HERE/'HOST-TOOLCHAIN-MANIFEST.json')
        require(hashlib.sha256(manifest).hexdigest()==grant.get('toolchain_manifest_sha256'), 'tool manifest mismatch')
        m=json.loads(manifest); require(m.get('status')=='OBSERVED_REQUIRES_REVIEW' and m.get('rustc')=='/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc', 'wrong compiler closure')
        if not active: verify_manifest(m)
    require(6 in os.sched_getaffinity(0), 'CPU6 unavailable')
    memory={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in Path('/proc/meminfo').read_text().splitlines() if ':' in x}
    require(int(memory['MemAvailable'].split()[0])*1024 >= grant['minimum_memavailable_bytes'], 'memory headroom')
    for p, minimum in grant['minimum_free_bytes'].items():
        v=os.statvfs(p); require(v.f_bavail*v.f_frsize >= minimum, 'storage headroom')
    require(grant['minimum_memavailable_bytes'] >= 4*1024**3 and set(grant['minimum_free_bytes'])=={'/home/holden/mckernel','/home/holden/mckernel-work/scratch'} and grant['minimum_free_bytes']['/home/holden/mckernel']>=16*1024**3 and grant['minimum_free_bytes']['/home/holden/mckernel-work/scratch']>=12*1024**3, 'weakened resource floors')
    return grant, caps



def verify_manifest(m):
    # The coordinator promises exclusion; metadata revalidation is not a content
    # substitute without that promise and the single admitted inventory pass.
    entries=m['entries']+m['runtime']; require(entries and len(entries)<=20000, 'bad tool entries')
    for e in entries:
        fd=os.open(e['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            t=os.fstat(fd); actual=[t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns,t.st_mode,t.st_uid]
            require(actual==e['identity'] and stat.S_ISREG(t.st_mode), 'tool identity changed')
        finally: os.close(fd)
    for e in m['symlinks']:
        t=os.lstat(e['path']); require(stat.S_ISLNK(t.st_mode) and [t.st_dev,t.st_ino,t.st_mtime_ns,t.st_ctime_ns]==e['identity'] and os.readlink(e['path'])==e['target'], 'tool link changed')

def consume(grant):
    require(grant.get('nonce') != 'cf0a2a5bd31bdc0441ba1b9e2b1d2c7551ebb3690e867873fce632dfe6b2f507', 'abandoned nonce')
    # A nonce is permanently consumed before any staging, even on later error.
    directory=os.open(HERE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        fd=os.open('USED-'+grant['nonce'],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory)
        try:
            remaining=memoryview((grant['profile_sha256']+'\n').encode())
            while remaining:
                n=os.write(fd,remaining);require(n>0,'nonce short write');remaining=remaining[n:]
            os.fsync(fd)
        finally: os.close(fd)
        os.fsync(directory)
    finally: os.close(directory)
