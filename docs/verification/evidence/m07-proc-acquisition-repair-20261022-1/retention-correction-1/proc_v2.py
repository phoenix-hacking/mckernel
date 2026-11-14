import json,os,sys,time
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

def fields(raw,pid):
    if len(raw)>65536: raise ValueError('stat-size')
    left,sep,right=raw.rpartition(b') ')
    if not sep or not left.startswith(str(pid).encode()+b' ('): raise ValueError('stat-prefix')
    values=right.split()
    if len(values)<50 or values[0] not in (b'R',b'S',b'D',b'Z',b'T',b't',b'X',b'x',b'K',b'W',b'P',b'I'): raise ValueError('stat-fields')
    for field in values[1:]:
        digits=field[1:] if field.startswith(b'-') else field
        if not digits or any(c<48 or c>57 for c in digits): raise ValueError('stat-number')
    if int(values[1])<0 or int(values[19])<0: raise ValueError('stat-number')
    return values

began=time.monotonic_ns();deadline=began+5_000_000_000
observed={};publishers=[];attempts=[];snapshots=[];boot=None
context=dict(pid=None,phase='root',path=None,identity=None)
def boundary(pid,phase,path,identity=None):
    context.update(pid=pid,phase=phase,path=path,identity=identity)
    if time.monotonic_ns()>=deadline: raise ValueError('process-acquisition-deadline')
def read_stat(pid,phase,identity=None):
    path='/proc/'+str(pid)+'/stat';boundary(pid,phase,path,identity)
    with open(path,'rb') as f:return fields(f.read(65537),pid)
def acquire():
    global boot
    if os.geteuid()!=0: raise ValueError('not-root')
    boundary(None,'boot','/proc/sys/kernel/random/boot_id')
    with open(context['path']) as f: boot=f.read().strip()
    initial=read_stat(caller[0],'caller')
    if str(int(initial[19]))!=caller[1]: raise ValueError('caller-raced')
    caller_parent=int(initial[1])
    for index in range(8):
        boundary(None,'list','/proc')
        attempt=dict(number=index+1,listed=[],identities=[],confirmed=[],failure=None)
        attempts.append(attempt)
        try:
            entries=os.listdir('/proc')
            if len(entries)>4096: raise ValueError('process-count')
            listed=sorted(int(name) for name in entries if name.isdigit())
            if any(pid<=0 for pid in listed) or len(set(listed))!=len(listed): raise ValueError('process-list')
            attempt['listed']=listed
            for pid in listed:
                values=read_stat(pid,'initial-stat')
                row=[pid,int(values[1]),str(int(values[19]))]
                attempt['identities'].append(row)
                context['identity']=row
                if pid in observed and observed[pid]!=row: raise ValueError('process-raced')
                observed[pid]=row
                if len(observed)>4096: raise ValueError('process-count')
                path='/proc/'+str(pid)+'/cmdline';boundary(pid,'cmdline',path,row)
                with open(path,'rb') as f:command=f.read(65537)
                if len(command)>65536 or (command and not command.endswith(b'\0')): raise ValueError('cmdline-size-or-termination')
                argv=[a.decode('utf-8','strict') for a in command[:-1].split(b'\0')] if command else []
                if len(argv)>256 or any(len(a)>16384 for a in argv): raise ValueError('cmdline-arguments')
                if not argv and values[0] not in (b'Z',b'X',b'x') and not (int(values[6]) & 0x200000): raise ValueError('live-cmdline-empty')
                exe=''
                if argv:
                    path='/proc/'+str(pid)+'/exe';boundary(pid,'exe',path,row)
                    exe=os.readlink(path)
                    if len(exe)>4096:raise ValueError('exe-size')
                if pid!=caller[0] and argv and not (pid==caller_parent and os.path.basename(exe)=='sudo') and publisher(exe,argv):
                    entry=[pid,row[2],exe]
                    if entry not in publishers:
                        if len(publishers)>=256:raise ValueError('publisher-count')
                        publishers.append(entry)
                again=read_stat(pid,'confirmation-stat',row)
                if [pid,int(again[1]),str(int(again[19]))]!=row:raise ValueError('process-raced')
                if pid==caller[0] and row[2]!=caller[1]:raise ValueError('caller-raced')
                attempt['confirmed'].append(pid)
            if 1 not in listed or caller[0] not in listed:raise ValueError('process-snapshot-incomplete')
            boundary(None,'complete','/proc')
            snapshots.append(attempt['identities'])
        except (OSError,ValueError,UnicodeError) as error:
            attempt['failure']=dict(context,kind=type(error).__name__,reason=str(error)[:512])
            # Only a missing member of this listed sweep can restart acquisition.
            retry=(isinstance(error,FileNotFoundError) and context['pid'] in attempt['listed'] and
                   context['phase'] in ('initial-stat','cmdline','exe','confirmation-stat') and error.filename==context['path'])
            if not retry:raise
        if len(snapshots)==2:break
        if index==7:raise ValueError('process-acquisition-exhausted')
        boundary(None,'backoff',None)
        time.sleep(min(0.01*(index+1),0.05))
    boundary(None,'boot-after','/proc/sys/kernel/random/boot_id')
    with open(context['path']) as f:after=f.read().strip()
    if boot!=after:raise ValueError('boot-raced')
    boundary(None,'finish',None)

status='COMPLETE';failure=None
try:acquire()
except (OSError,ValueError,UnicodeError) as error:
    status='REFUSED';failure=dict(context,kind=type(error).__name__,reason=str(error)[:512])
print(json.dumps(dict(schema='fp-save-image.proc.v2',uid=os.geteuid(),boot_id=boot,challenge=sys.argv[1],caller=caller,
    status=status,failure=failure,publishers=publishers,snapshots=snapshots,
    acquisition=dict(max_sweeps=8,window_ns=5_000_000_000,elapsed_ns=max(0,time.monotonic_ns()-began),
                     attempts=attempts,observed=sorted(observed.values()))),sort_keys=True))
