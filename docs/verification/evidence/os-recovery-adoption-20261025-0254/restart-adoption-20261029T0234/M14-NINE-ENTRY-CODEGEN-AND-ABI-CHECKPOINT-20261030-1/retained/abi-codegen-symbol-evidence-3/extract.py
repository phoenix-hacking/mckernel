#!/usr/bin/python3
"""Fixed nine Rust v0 symbol references, no execution of generated code.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import hashlib,json,os,pathlib,stat,struct,time

B=pathlib.Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1')
OUT=B/'abi-codegen-symbol-evidence-3'
OBJECT=B/'m14-abi-codegen-candidate-1/work-1/out/mckernel_rust.o'
POST=B/'m14-abi-codegen-candidate-1/POSTFLIGHT.SOURCE-ONLY.json'
OBJ_SHA='4ae88ea95ad229725334df27fe4bd0e10c4dbe04ca5109212e578bed4e18da6e'
POST_SHA='93cd283f8b987f1a9c46177d8eb2fe0de63a2aa45242d29f3cc013a61929c7e0'
SPECS=[
 ('REF_CRED_UID','f03_credential_snapshot_typecheck','do_setresuid'),
 ('REF_CRED_GID','f03_credential_snapshot_typecheck','do_setresgid'),
 ('REF_DO_SYSCALL','m14_private_do_syscall','f03_do_syscall_supported_v1'),
 ('REF_UTIL_THREAD','m14_private_util_thread','f03_util_thread_whole_v1'),
 ('REF_DO_SYSCALL2','m14_private_request_constructors','syscall_do_syscall2_bridge'),
 ('REF_POLICY_SYSCALL2','m14_private_request_constructors','syscall_policy_do_syscall2_bridge'),
 ('REF_DO_SYSCALL3','m14_private_request_constructors','syscall_do_syscall3_bridge'),
 ('REF_POLICY_SYSCALL3','m14_private_request_constructors','syscall_policy_do_syscall3_bridge'),
 ('REF_WAIT4','m14_private_request_constructors','wait_host_wait4_bridge')]
ARRAYS=[('f03_do_fork_Rust_ABI_v1',46),('f03_clone_lifetime_vm_Rust_ABI_v1',10)]


def need(test,message):
    if not test:raise RuntimeError(message)


def process_identity(pid):
    fields=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,ppid=int(fields[1]),pgid=int(fields[2]),session=int(fields[3]),start=fields[19],state=fields[0])


def record(data):
    q=OUT/'PROGRESS.json';tmp=OUT/'PROGRESS.new'
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        v=memoryview((json.dumps(data,sort_keys=True,indent=2)+'\n').encode())
        while v:
            n=os.write(fd,v);need(n>0,'progress short write');v=v[n:]
        os.fsync(fd)
    finally:os.close(fd)
    os.replace(tmp,q)


def stable(path,expected,limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    try:
        a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and 0<a.st_size<=limit,'input size/type: '+str(path))
        chunks=[];total=0
        while total<a.st_size:
            z=os.read(fd,min(1024*1024,a.st_size-total));need(bool(z),'input short read');chunks.append(z);total+=len(z)
        b=os.fstat(fd);need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns),'input changed')
        raw=b''.join(chunks);need(hashlib.sha256(raw).hexdigest()==expected,'input digest mismatch: '+str(path))
        return raw,dict(device=a.st_dev,inode=a.st_ino,size=a.st_size,mode=a.st_mode,uid=a.st_uid,mtime_ns=a.st_mtime_ns,ctime_ns=a.st_ctime_ns)
    finally:os.close(fd)


def main():
    me=process_identity(os.getpid());chain=[me];cur=me
    for _ in range(4):
        if cur['ppid']<=1:break
        try:cur=process_identity(cur['ppid']);chain.append(cur)
        except (OSError,ValueError,IndexError):break
    proof={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','grant':'ROOT_FIXED9_EXPERT_20261030','status':'STARTED','process_chain':chain,'resolved':[],'arrays':[],'artifact':str(OBJECT),'limitations':['Source prototypes are not proven by ELF alone.','No object code executed; no production link, default, native or C retirement claim.']}
    record(proof)
    postbytes,_=stable(POST,POST_SHA,1024*1024);post=json.loads(postbytes)
    need([(x['static'],x['target']) for x in post['codegen_symbol_postflight']['required_reference_statics']]==[(s,t) for s,m,t in SPECS],'fixed source specification differs')
    raw,ident=stable(OBJECT,OBJ_SHA,64*1024*1024);need(len(raw)==18948144,'object size mismatch');proof['object_identity']=ident;proof['object_sha256']=OBJ_SHA;record(proof)
    need(raw[:6]==b'\x7fELF\x02\x01' and len(raw)>=64,'ELF64 little endian')
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw,0);need(h[1]==1 and h[2]==62,'x86_64 ET_REL required')
    need(h[11]>=64 and 0<h[12]<=32768 and h[6]+h[11]*h[12]<=len(raw) and h[13]<h[12],'section table bounds')
    sh=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])]
    def section(i):
        need(0<=i<len(sh),'bad section index');v=sh[i];need(v[1]==8 or v[4]+v[5]<=len(raw),'bad section bounds');return raw[v[4]:v[4]+v[5]]
    def string(table,pos):
        need(pos<len(table),'string offset');end=table.find(b'\0',pos);need(end>=0,'unterminated string');return table[pos:end].decode('ascii')
    shstr=section(h[13]);section_names=[string(shstr,s[0]) for s in sh]
    ids=[i for i,s in enumerate(sh) if s[1]==2];need(len(ids)==1,'exactly one symtab required');symidx=ids[0];tab=sh[symidx];need(tab[9]==24 and tab[5]%24==0 and tab[6]<len(sh) and sh[tab[6]][1]==3,'bad symtab');strings=section(tab[6]);symbols=[]
    for off in range(tab[4],tab[4]+tab[5],24):
        name,info,other,sec,val,size=struct.unpack_from('<IBBHQQ',raw,off)
        symbols.append(dict(name=string(strings,name),type=info&15,binding=info>>4,section=sec,value=val,size=size,index=len(symbols)))
    rels={}
    for i,s in enumerate(sh):
        if s[1] not in (4,9):continue
        es=24 if s[1]==4 else 16;need(s[9]==es and s[5]%es==0 and s[6]==symidx and s[7]<len(sh),'relocation section binding')
        section(i);items=[]
        for off in range(s[4],s[4]+s[5],es):
            if es==24:where,info,add=struct.unpack_from('<QQq',raw,off)
            else:where,info=struct.unpack_from('<QQ',raw,off);add=None
            idx=info>>32;need(idx<len(symbols),'relocation symbol index');items.append(dict(offset=where,type=info&0xffffffff,addend=add,symbol=symbols[idx]))
        rels[i]=items
    def allrels(target):
        return [(i,x) for i,entries in rels.items() if sh[i][7]==target for x in entries]
    def terminal(module,name):
        return str(len(module))+module+str(len(name))+name
    def unique(module,name,typ):
        suffix=terminal(module,name)
        matches=[s for s in symbols if s['name'].startswith('_R') and s['name'].endswith(suffix) and s['type']==typ and 0<s['section']<len(sh)]
        need(len(matches)==1,'unique v0 terminal %s/%s found=%d'%(module,name,len(matches)))
        return matches[0]
    for static,module,target in SPECS:
        proof['status']='CHECKING_REF';proof['next']=static;record(proof)
        ref=unique('m14_private_codegen_refs',static,1);need(ref['size']==8,'reference extent: '+static)
        rr=[(i,x) for i,x in allrels(ref['section']) if ref['value']<=x['offset']<ref['value']+8]
        need(len(rr)==1 and rr[0][1]['offset']==ref['value'],'reference relocation count/offset: '+static)
        ri,rel=rr[0];need(rel['type']==1 and rel['addend'] is not None,'nonabsolute pointer relocation: '+static)
        origin=rel['symbol'];need(origin['type'] in (2,3) and 0<origin['section']<len(sh),'relocation target is not function or section: '+static)
        sec=origin['section'];where=origin['value']+rel['addend'];target_sym=unique(module,target,2)
        need(target_sym['section']==sec and target_sym['value']==where and target_sym['size']>0,'intended function not at relocation target: '+static)
        aliases=[s for s in symbols if s['type']==2 and s['section']==sec and s['value']==where and s['size']>0]
        need(any(s['index']==target_sym['index'] for s in aliases),'expected function missing from alias extent')
        proof['resolved'].append(dict(reference=ref,target=target_sym,relocation_section=section_names[ri],relocation=rel,body_key=[sec,where],named_same_entry_aliases=aliases))
        record(proof)
    for name,count in ARRAYS:
        proof['status']='CHECKING_ABI';proof['next']=name;record(proof)
        s=unique('f03_clone_lifetime',name,1);need(s['size']==count*8,'ABI extent: '+name);need(not allrels(s['section']),'ABI section contains relocations: '+name)
        sec=sh[s['section']];need(sec[1]!=8 and sec[2]&2 and s['value']+s['size']<=sec[5],'ABI data range: '+name);start=sec[4]+s['value'];need(start+s['size']<=len(raw),'ABI data outside object')
        vals=list(struct.unpack_from('<'+'Q'*count,raw,start));proof['arrays'].append(dict(identifier=name,symbol=s,section_name=section_names[s['section']],section_relocations=0,words=vals));record(proof)
    keys={tuple(x['body_key']) for x in proof['resolved']};proof.update(status='PASS_FIXED9_AND_RUST_ABI_SOURCE_EVIDENCE',next=None,entry_count=len(proof['resolved']),unique_body_count=len(keys),symtab_index=symidx,undefined_count=sum(s['section']==0 and bool(s['name']) for s in symbols));record(proof)
    print(json.dumps({'status':proof['status'],'entry_count':proof['entry_count'],'unique_body_count':proof['unique_body_count'],'array_counts':[len(a['words']) for a in proof['arrays']],'array_section_relocations':[a['section_relocations'] for a in proof['arrays']]},sort_keys=True))


if __name__=='__main__':main()
