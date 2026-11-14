
import errno,json,os,sys
caller=[int(sys.argv[2]),sys.argv[3]]
heavy={'qemu-system-x86_64','qemu-system-aarch64','qemu-kvm','mcexec','firecracker',
       'rustc','cargo','make','ninja','buildah','gcc','g++','cc','clang','clang++'}
def publisher(exe,argv):
    name=os.path.basename(exe[:-10] if exe.endswith(' (deleted)') else exe)
    if name in heavy or name.startswith('qemu-system-'): return True
    if name in ('docker','podman') and any(a in ('build','run','start') for a in argv[1:]): return True
    for arg in argv:
        base=os.path.basename(arg)
        if (base.startswith(('native_rust_exact_','native-exact-','native_exact_')) and
            base.endswith(('.py','.sh')) and any(term in base for term in ('build','cleanup','recovery','prepare'))): return True
    return False
class EnumeratedProcessExit(RuntimeError):
    def __init__(self,pid,operation,path):
        self.failure={'schema':'mckernel.process-census.enumerated-exit.v1','attempt':attempt_index,
                      'snapshot':snapshot_index,'pid':pid,'operation':operation,'path':path,'errno':errno.ENOENT}
        super().__init__(json.dumps(self.failure,sort_keys=True))
def caller_check():
    # Protected caller reads are intentionally outside the transient classifier.
    with open('/proc/'+str(caller[0])+'/stat','rb') as f: raw=f.read(65537)
    left,sep,right=raw.rpartition(b') ');fields=right.split()
    if len(raw)>65536 or not sep or not left.startswith(str(caller[0]).encode()+b' (') or len(fields)<50: raise ValueError('protected-caller-stat')
    if fields[0] not in (b'R',b'S',b'D',b'Z',b'T',b't',b'X',b'x',b'K',b'W',b'P',b'I'): raise ValueError('protected-caller-state')
    for field in fields[1:]:
        digits=field[1:] if field.startswith(b'-') else field
        if not digits or any(c<48 or c>57 for c in digits): raise ValueError('protected-caller-stat-number')
    if fields[0] in (b'Z',b'X',b'x') or not fields[19].isdigit() or fields[19].decode()!=caller[1]: raise ValueError('protected-caller-birth')
    if int(fields[1])<0: raise ValueError('protected-caller-parent')
    return int(fields[1])
def classify_exit(exc,pid,operation,path,argv=()):
    if (type(exc) is not FileNotFoundError or exc.errno!=errno.ENOENT or exc.filename!=path or
        pid==caller[0] or operation not in ('stat','cmdline','exe')): raise exc
    if attempt_publishers or (argv and publisher(argv[0],argv)):
        raise ValueError('native-publisher-observed-before-enumerated-exit')
    raise EnumeratedProcessExit(pid,operation,path)
def read_enumerated(pid,name):
    path='/proc/'+str(pid)+'/'+name
    try:
        with open(path,'rb') as f:return f.read(65537)
    except FileNotFoundError as exc:classify_exit(exc,pid,name,path)
def read_enumerated_exe(pid,argv):
    path='/proc/'+str(pid)+'/exe'
    try:return os.readlink(path)
    except FileNotFoundError as exc:classify_exit(exc,pid,'exe',path,argv)
def snapshot():
    rows=[]; publishers=[]; found=False
    entries=os.listdir('/proc')
    if len(entries)>4096: raise ValueError('process-count')
    for name in entries:
        if not name.isdigit(): continue
        pid=int(name)
        raw=read_enumerated(pid,'stat')
        if len(raw)>65536: raise ValueError('stat-size')
        left,sep,right=raw.rpartition(b') ')
        if not sep or not left.startswith(str(pid).encode()+b' ('): raise ValueError('stat-prefix')
        fields=right.split()
        if len(fields)<50 or fields[0] not in (b'R',b'S',b'D',b'Z',b'T',b't',b'X',b'x',b'K',b'W',b'P',b'I'): raise ValueError('stat-fields')
        for field in fields[1:]:
            digits=field[1:] if field.startswith(b'-') else field
            if not digits or any(c<48 or c>57 for c in digits): raise ValueError('stat-number')
        ppid=int(fields[1]); start=int(fields[19])
        if ppid<0 or start<0: raise ValueError('stat-number')
        command=read_enumerated(pid,'cmdline')
        if len(command)>65536 or (command and not command.endswith(b'\0')): raise ValueError('cmdline-size-or-termination')
        argv=[a.decode('utf-8','strict') for a in command[:-1].split(b'\0')] if command else []
        if len(argv)>256 or any(len(a)>16384 for a in argv): raise ValueError('cmdline-arguments')
        if not argv and fields[0] not in (b'Z',b'X',b'x') and not (int(fields[6]) & 0x200000): raise ValueError('live-cmdline-empty')
        exe=read_enumerated_exe(pid,argv) if argv else ''
        known_publisher=pid!=caller[0] and argv and not (pid==caller_parent and os.path.basename(exe)=='sudo') and publisher(exe,argv)
        if known_publisher:attempt_publishers.append([pid,str(start),exe])
        again=read_enumerated(pid,'stat')
        check=again.rpartition(b') ')[2].split()
        if len(check)<50 or check[19]!=fields[19]: raise ValueError('process-raced')
        if pid==caller[0]:
            if str(start)!=caller[1]: raise ValueError('caller-raced')
            found=True
        elif known_publisher: publishers.append([pid,str(start),exe])
        rows.append([pid,ppid,str(start)])
    if not found: raise ValueError('caller-missing')
    return sorted(rows),publishers
if os.geteuid()!=0: raise ValueError('not-root')
caller_parent=caller_check()
with open('/proc/sys/kernel/random/boot_id') as f: boot=f.read().strip()
failures=[]
for attempt_index in range(1,4):
    attempt_publishers=[]
    if caller_check()!=caller_parent: raise ValueError('protected-caller-parent-raced')
    with open('/proc/sys/kernel/random/boot_id') as f: before=f.read().strip()
    if boot!=before: raise ValueError('boot-raced')
    try:
        snapshot_index=1;first,pubs1=snapshot()
        if caller_check()!=caller_parent: raise ValueError('protected-caller-parent-raced')
        snapshot_index=2;second,pubs2=snapshot()
    except EnumeratedProcessExit as exc:
        failures.append(exc.failure)
        # A failed partial pair is never returned, merged, or reused.
        if caller_check()!=caller_parent: raise ValueError('protected-caller-parent-raced')
        with open('/proc/sys/kernel/random/boot_id') as f: after=f.read().strip()
        if boot!=after: raise ValueError('boot-raced')
        if attempt_index==3: raise RuntimeError('process-census-lifecycle-exhausted:'+json.dumps({'attempts':3,'retry_failures':failures},sort_keys=True))
        continue
    with open('/proc/sys/kernel/random/boot_id') as f: after=f.read().strip()
    if boot!=after: raise ValueError('boot-raced')
    if caller_check()!=caller_parent: raise ValueError('protected-caller-parent-raced')
    print(json.dumps({'schema':'fp-save-image.proc.lifecycle.v2','uid':os.geteuid(),'boot_id':boot,
        'challenge':sys.argv[1],'caller':caller,'publishers':pubs1+pubs2,'snapshots':[first,second],
        'attempts':attempt_index,'retry_failures':failures}))
    break
