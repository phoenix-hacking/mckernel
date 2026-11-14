#!/usr/bin/python3
"""Single HOST toolchain inventory; no helper subprocesses; requires grant."""
import hashlib, json, mmap, os, re, stat, struct, time
from pathlib import Path
import host_gate_collector_v8 as gate

ROOT=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu')
HERE=Path(__file__).absolute().parent
RUSTC=ROOT/'bin/rustc'
TOOLS=[Path(x) for x in ['/usr/bin/taskset','/usr/bin/prlimit','/usr/bin/timeout','/usr/bin/time','/usr/bin/python3.8']]
MAX_BYTES=2*1024**3
MAX_FILES=20000
MAX_ELF_BYTES=512*1024**2
MAX_RUNTIME_BYTES=1024**3
MAX_RUNTIME_FILES=4096
WALL=180
SEARCH=[ROOT/'lib',ROOT/'lib/rustlib/x86_64-unknown-linux-gnu/lib',Path('/lib64'),Path('/usr/lib64'),Path('/lib/x86_64-linux-gnu'),Path('/usr/lib/x86_64-linux-gnu')]


def require(x,m):
    if not x: raise RuntimeError(m)


def record(p, deadline, remaining_budget):
    fd=os.open(p,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        s=os.fstat(fd); require(stat.S_ISREG(s.st_mode),'nonregular input')
        require(type(remaining_budget) is int and 0 <= s.st_size <= remaining_budget, 'opened file exceeds remaining byte budget: %s size=%s remaining=%s' % (p,s.st_size,remaining_budget))
        h=hashlib.sha256(); read_bytes=0
        while read_bytes<s.st_size:
            b=os.read(fd,min(1024*1024,s.st_size-read_bytes))
            require(bool(b),'short file read')
            read_bytes+=len(b); require(read_bytes<=s.st_size and read_bytes<=remaining_budget, 'read exceeds byte budget')
            h.update(b); require(time.monotonic()<deadline,'collector deadline')
        require(read_bytes==s.st_size,'short file read')
        t=os.fstat(fd)
        before=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_uid)
        after=(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns,t.st_mode,t.st_uid)
        require(before==after,'input changed')
        return {'path':str(p),'identity':list(before),'sha256':h.hexdigest()}
    finally: os.close(fd)


def elf_dynamic(p):
    """Read ELF64 little-endian PT_INTERP and DT_NEEDED/RUNPATH without ldd."""
    fd=os.open(p,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
    before=None
    try:
        st=os.fstat(fd); require(stat.S_ISREG(st.st_mode) and 64<=st.st_size<=MAX_ELF_BYTES,'ELF input size/type: %s size=%s mode=%s' % (p,st.st_size,oct(st.st_mode)))
        before=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,st.st_mode,st.st_uid)
        with mmap.mmap(fd,0,access=mmap.ACCESS_READ) as mm:
            require(mm[:4]==b'\x7fELF','missing ELF magic: %s size=%s' % (p,st.st_size))
            require(mm[4:6]==b'\x02\x01' and len(mm)>=64,'unsupported ELF class/endian')
            require(struct.unpack_from('<H',mm,18)[0]==62,'unsupported ELF machine')
            off=struct.unpack_from('<Q',mm,32)[0]; entsize,num=struct.unpack_from('<HH',mm,54)
            require(entsize>=56 and num<=1024 and off+entsize*num<=len(mm),'program headers')
            loads=[]; dynamic=None; interp=None
            for i in range(num):
                typ,_,fo,va,_,fs,_,_=struct.unpack_from('<IIQQQQQQ',mm,off+i*entsize)
                require(fo+fs<=len(mm),'segment range')
                if typ==1: loads.append((va,va+fs,fo))
                if typ==2: dynamic=(fo,fs)
                if typ==3:
                    raw=bytes(mm[fo:fo+fs]); require(fs>1 and raw[-1:]==b'\0' and b'\0' not in raw[:-1],'bad interpreter')
                    interp=raw[:-1].decode('utf8');require(interp.startswith('/'),'relative interpreter')
            if dynamic is None: return {'needed':[],'runpath':[],'interpreter':interp}
            fo,fs=dynamic; require(fs%16==0 and fs//16<65536,'dynamic segment')
            tags=[]; terminated=False
            for i in range(fs//16):
                tag,val=struct.unpack_from('<qQ',mm,fo+i*16)
                if tag==0: terminated=True; break
                tags.append((tag,val))
            require(terminated,'unterminated dynamic section')
            staddr=next((v for t,v in tags if t==5),None); strsize=next((v for t,v in tags if t==10),None)
            require(staddr is not None and strsize is not None and strsize<=16*1024*1024,'string table')
            loc=next((start+(staddr-v) for v,end,start in loads if v<=staddr and staddr+strsize<=end),None)
            require(loc is not None and loc+strsize<=len(mm),'string mapping')
            table=bytes(mm[loc:loc+strsize])
            def cstr(i):
                require(i<len(table),'string offset'); end=table.find(b'\0',i); require(end>=0,'string terminator'); return table[i:end].decode('utf8')
            needed=[cstr(v) for t,v in tags if t==1]
            paths=[cstr(v) for t,v in tags if t in (15,29)]
            return {'needed':needed,'runpath':paths,'interpreter':interp}
    finally:
        t=os.fstat(fd)
        after=(t.st_dev,t.st_ino,t.st_size,t.st_mtime_ns,t.st_ctime_ns,t.st_mode,t.st_uid)
        try: require(before is None or after==before,'ELF identity changed during parsing')
        finally: os.close(fd)



def classify_nonelf(p, expected, selected):
    """Recognize bounded inventory-only GNU INPUT(single sibling) scripts.

    A dynamic loader does not accept such a script as a DT_NEEDED provider;
    any selected non-ELF stays a hard failure. The caller has already hashed
    and bound expected identity/content under the cooperating source owner.
    """
    fd=os.open(p,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd); ident=[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,st.st_mode,st.st_uid]
        require(ident==expected['identity'] and stat.S_ISREG(st.st_mode),'input identity mismatch: %s size=%s' % (p,st.st_size))
        head=os.read(fd,min(4,st.st_size))
        if head==b'\x7fELF': return None
        require(not selected,'selected dependency is non-ELF: %s size=%s' % (p,st.st_size))
        require(st.st_size<=4096,'unrecognized non-ELF size: %s size=%s' % (p,st.st_size))
        os.lseek(fd,0,os.SEEK_SET); data=bytearray()
        while len(data)<st.st_size:
            chunk=os.read(fd,st.st_size-len(data)); require(bool(chunk),'short linker input: %s size=%s' % (p,st.st_size)); data.extend(chunk)
        after=os.fstat(fd); ident_after=[after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns,after.st_mode,after.st_uid]
        require(ident_after==ident and hashlib.sha256(data).hexdigest()==expected['sha256'],'linker input changed: %s size=%s' % (p,st.st_size))
        match=re.fullmatch(rb'\s*INPUT\s*\(\s*([A-Za-z0-9_.+\-]+)\s*\)\s*',bytes(data))
        require(match is not None,'unsupported non-ELF input: %s size=%s' % (p,st.st_size))
        name=match.group(1).decode('ascii');require(name not in ('.','..'),'bad INPUT target')
        target=p.parent/name;require(target.is_file(),'missing INPUT target: %s size=%s' % (p,st.st_size))
        return {'kind':'linker_input_script','size':st.st_size,'sha256':expected['sha256'],'target':str(target)}
    finally: os.close(fd)

def inventory(grant,caps):
    require(grant.get('root')==str(ROOT),'wrong toolchain root')
    deadline=time.monotonic()+WALL; entries=[]; links=[]; elf=[]; total=0; count=0
    def walk_error(exc): raise exc
    for base, dirs, files in os.walk(ROOT,followlinks=False,onerror=walk_error):
        require(time.monotonic()<deadline,'inventory deadline during walk')
        dirs.sort();files.sort()
        for name in dirs+files:
            require(time.monotonic()<deadline,'inventory deadline during entry')
            count+=1; require(count<=MAX_FILES,'directory/entry bound')
            p=Path(base)/name;s=p.lstat()
            if stat.S_ISLNK(s.st_mode): links.append({'path':str(p),'target':os.readlink(p),'identity':[s.st_dev,s.st_ino,s.st_mtime_ns,s.st_ctime_ns]}); continue
            if stat.S_ISDIR(s.st_mode): continue
            require(stat.S_ISREG(s.st_mode),'toolchain special file')
            require(len(entries)<MAX_FILES,'inventory bound')
            item=record(p,deadline,MAX_BYTES-total)
            total+=item['identity'][2]; entries.append(item)
            if name=='rustc' or '.so' in name: elf.append(p)
    existing={e['path']:e for e in entries}; runtime={}; runtime_bytes=0; pending=[(x,x==RUSTC) for x in elf]+[(x,True) for x in TOOLS]; observed={}
    while pending:
        require(time.monotonic()<deadline,'inventory deadline')
        p,selected=pending.pop();p=p.resolve(strict=True)
        if str(p) in observed:
            require(not selected or observed[str(p)].get('kind')!='linker_input_script','selected dependency is linker script: %s' % p)
            continue
        key=str(p)
        if key not in existing and key not in runtime:
            require(len(runtime)<MAX_RUNTIME_FILES,'runtime closure count bound')
            item=record(p,deadline,MAX_RUNTIME_BYTES-runtime_bytes); runtime_bytes+=item['identity'][2]
            runtime[key]=item
        expected=existing.get(key) or runtime[key]
        try: script=classify_nonelf(p,expected,selected)
        except (OSError,RuntimeError,ValueError) as exc:
            raise RuntimeError('input path=%s size=%s: %s' % (p,expected['identity'][2],exc)) from exc
        if script is not None:
            observed[key]=script
            pending.append((Path(script['target']),False))
            continue
        try: meta=elf_dynamic(p)
        except (OSError,RuntimeError,ValueError,struct.error) as exc:
            raise RuntimeError('ELF path=%s size=%s: %s' % (p,expected['identity'][2],exc)) from exc
        meta['kind']='elf'
        st=p.stat();require([st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,st.st_mode,st.st_uid]==expected['identity'],'ELF differs from hashed identity: %s size=%s' % (p,st.st_size))
        observed[key]=meta
        dirs=[]
        for group in meta['runpath']:
            for entry in group.split(':'):
                expanded=entry.replace('${ORIGIN}',str(p.parent)).replace('$ORIGIN',str(p.parent))
                require(expanded.startswith('/') and '$' not in expanded,'unsupported ELF path')
                dirs.append(Path(expanded))
        dirs.extend(SEARCH)
        if meta['interpreter']: pending.append((Path(meta['interpreter']),True))
        for name in meta['needed']:
            require('/' not in name,'unhandled DT_NEEDED path')
            found=next((d/name for d in dirs if (d/name).is_file()),None)
            require(found is not None,'unresolved DT_NEEDED '+name+' from '+str(p));pending.append((found,True))
        require(len(observed)<=MAX_FILES,'ELF graph bound')
    gate.check(active=True,collector=True)
    result={'status':'OBSERVED_REQUIRES_REVIEW','rustc':str(RUSTC),'root':str(ROOT),'entries':entries,'symlinks':links,'runtime':sorted(runtime.values(),key=lambda x:x['path']),'elf_dynamic':observed,'bytes_hashed_tree':total,'runtime_bytes':runtime_bytes,'walk_entries':count,'limitations':['Static DT_NEEDED resolver has a bounded search and does not prove dlopen, subprocess, loader-cache or plugin paths; independent comparison to actual loader semantics required','Whole toolchain tree is conservative, selected tools and runtime closure under cooperating exclusion','No process launched by this collector; outer direct-owner custody and timeout remain separate']}
    raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    fd=os.open(HERE/('HOST-TOOLCHAIN-MANIFEST-'+grant['nonce']+'.json'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        view=memoryview(raw)
        while view:
            n=os.write(fd,view);require(n>0,'short write');view=view[n:]
        os.fsync(fd)
    finally: os.close(fd)
    directory=os.open(HERE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try: os.fsync(directory)
    finally: os.close(directory)


def durable_record(name, value):
    directory=os.open(HERE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory)
        try:
            remaining=memoryview((json.dumps(value,sort_keys=True)+'\n').encode())
            while remaining:
                n=os.write(fd,remaining);require(n>0,'short record write');remaining=remaining[n:]
            os.fsync(fd)
        finally: os.close(fd)
        os.fsync(directory)
    finally: os.close(directory)


def main():
    grant,caps=gate.check(collector=True)
    gate.consume(grant)
    try:
        durable_record('TOOLCHAIN-INVENTORY-'+grant['nonce']+'-INTENT.json',{'state':'INTENT','nonce':grant['nonce'],'pid':os.getpid(),'owner':gate.birth(os.getpid()),'lease_release':False})
        inventory(grant,caps)
    except BaseException as exc:
        try: durable_record('TOOLCHAIN-INVENTORY-'+grant['nonce']+'-UNKNOWN.json',{'state':'UNKNOWN','nonce':grant['nonce'],'error':type(exc).__name__,'lease_release':False})
        except BaseException: pass
        raise


if __name__=='__main__':main()
