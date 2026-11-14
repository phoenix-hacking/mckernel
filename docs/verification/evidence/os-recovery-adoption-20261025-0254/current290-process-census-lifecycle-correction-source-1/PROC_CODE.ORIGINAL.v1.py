
import json,os,sys
caller=[int(sys.argv[2]),sys.argv[3]]
caller_parent=int(open('/proc/'+str(caller[0])+'/stat','rb').read().rpartition(b') ')[2].split()[1])
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
def snapshot():
    rows=[]; publishers=[]; found=False
    entries=os.listdir('/proc')
    if len(entries)>4096: raise ValueError('process-count')
    for name in entries:
        if not name.isdigit(): continue
        pid=int(name)
        with open('/proc/'+name+'/stat','rb') as f: raw=f.read(65537)
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
        with open('/proc/'+name+'/cmdline','rb') as f: command=f.read(65537)
        if len(command)>65536 or (command and not command.endswith(b'\0')): raise ValueError('cmdline-size-or-termination')
        argv=[a.decode('utf-8','strict') for a in command[:-1].split(b'\0')] if command else []
        if len(argv)>256 or any(len(a)>16384 for a in argv): raise ValueError('cmdline-arguments')
        if not argv and fields[0] not in (b'Z',b'X',b'x') and not (int(fields[6]) & 0x200000): raise ValueError('live-cmdline-empty')
        exe=os.readlink('/proc/'+name+'/exe') if argv else ''
        with open('/proc/'+name+'/stat','rb') as f: again=f.read(65537)
        check=again.rpartition(b') ')[2].split()
        if len(check)<50 or check[19]!=fields[19]: raise ValueError('process-raced')
        if pid==caller[0]:
            if str(start)!=caller[1]: raise ValueError('caller-raced')
            found=True
        elif argv and not (pid==caller_parent and os.path.basename(exe)=='sudo') and publisher(exe,argv): publishers.append([pid,str(start),exe])
        rows.append([pid,ppid,str(start)])
    if not found: raise ValueError('caller-missing')
    return sorted(rows),publishers
if os.geteuid()!=0: raise ValueError('not-root')
with open('/proc/sys/kernel/random/boot_id') as f: boot=f.read().strip()
first,pubs1=snapshot(); second,pubs2=snapshot()
with open('/proc/sys/kernel/random/boot_id') as f: after=f.read().strip()
if boot!=after: raise ValueError('boot-raced')
print(json.dumps({'schema':'fp-save-image.proc.v1','uid':os.geteuid(),'boot_id':boot,
                  'challenge':sys.argv[1],'caller':caller,'publishers':pubs1+pubs2,'snapshots':[first,second]}))
