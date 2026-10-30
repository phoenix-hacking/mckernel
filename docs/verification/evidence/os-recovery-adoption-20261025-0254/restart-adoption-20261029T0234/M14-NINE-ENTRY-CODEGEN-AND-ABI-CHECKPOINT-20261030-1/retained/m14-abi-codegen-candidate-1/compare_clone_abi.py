#!/usr/bin/python3
"""Compare observed x86_64 C/Rust clone ABI object arrays, without linking.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The caller binds actual owner evidence and object hashes separately. No release.
"""
import argparse, hashlib, json, os, stat, struct

MAX_BYTES=64*1024*1024


def need(ok,message):
    if not ok: raise ValueError(message)


def read_stable(path,expected):
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        a=os.fstat(fd)
        need(stat.S_ISREG(a.st_mode) and 0<a.st_size<=MAX_BYTES,'object size/type')
        chunks=[]; count=0
        while count<a.st_size:
            data=os.read(fd,min(1024*1024,a.st_size-count));need(bool(data),'short object')
            chunks.append(data);count+=len(data)
        b=os.fstat(fd)
        need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns),'object changed')
        raw=b''.join(chunks);actual=hashlib.sha256(raw).hexdigest();need(actual==expected,'object hash differs')
        return raw,actual
    finally:os.close(fd)


def sections(raw):
    need(len(raw)>=64 and raw[:6]==b'\x7fELF\x02\x01','ELF64 little-endian required')
    typ,machine=struct.unpack_from('<HH',raw,16)
    need(typ==1 and machine==62,'x86_64 relocatable object required')
    shoff=struct.unpack_from('<Q',raw,40)[0]
    shentsize,shnum=struct.unpack_from('<HH',raw,58)
    need(shentsize>=64 and 0<shnum<=32768 and shoff+shentsize*shnum<=len(raw),'bad section table')
    out=[]
    for i in range(shnum):
        h=struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*shentsize)
        sec={'type':h[1],'flags':h[2],'offset':h[4],'size':h[5],'link':h[6],'info':h[7],'entsize':h[9]}
        need(sec['type']==8 or sec['offset']+sec['size']<=len(raw),'bad section range')
        out.append(sec)
    return out


def symtabs(raw,secs):
    symbols=[]
    for sec in secs:
        if sec['type']!=2:continue
        need(sec['entsize']==24 and sec['size']%24==0 and sec['link']<len(secs),'bad symbol table')
        strings=secs[sec['link']];need(strings['type']==3,'bad symbol strings')
        table=raw[strings['offset']:strings['offset']+strings['size']]
        for off in range(sec['offset'],sec['offset']+sec['size'],24):
            name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,off)
            need(name<len(table),'bad symbol name offset')
            end=table.find(b'\0',name);need(end>=0,'unterminated symbol name')
            symbols.append({'name':table[name:end],'type':info&15,'index':index,'value':value,'size':size})
    need(bool(symbols),'no symbol table')
    return symbols


def array(raw,secs,symbols,name,count,exact):
    key=name.encode('ascii')
    matches=[s for s in symbols if s['type']==1 and (s['name']==key if exact else key in s['name']) and s['index']!=0]
    need(len(matches)==1,'missing or ambiguous symbol: '+name)
    s=matches[0];need(s['size']==count*8 and 0<s['index']<len(secs),'wrong symbol extent: '+name)
    sec=secs[s['index']];need(sec['type']!=8 and sec['flags']&2 and s['value']+s['size']<=sec['size'],'bad array section: '+name)
    for r in secs:
        if r['type'] not in (4,9) or r['info']!=s['index']:continue
        expected_ent=24 if r['type']==4 else 16
        need(r['entsize']==expected_ent and r['size']%expected_ent==0,'bad relocation section')
        for off in range(r['offset'],r['offset']+r['size'],expected_ent):
            target=struct.unpack_from('<Q',raw,off)[0]
            need(not (max(0,s['value']-7)<=target<s['value']+s['size']),'relocation touches ABI data: '+name)
    start=sec['offset']+s['value'];need(start+s['size']<=len(raw),'array outside object')
    return {'symbol':s['name'].decode('ascii'),'words':list(struct.unpack_from('<'+'Q'*count,raw,start))}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rust-object',required=True);p.add_argument('--rust-sha256',required=True)
    p.add_argument('--c-object',required=True);p.add_argument('--c-sha256',required=True)
    args=p.parse_args()
    rust,rsha=read_stable(args.rust_object,args.rust_sha256)
    c,csha=read_stable(args.c_object,args.c_sha256)
    rs=sections(rust);cs=sections(c);rt=symtabs(rust,rs);ct=symtabs(c,cs)
    need(not any(s['type']==2 and s['index']!=0 for s in ct),'C witness has function definitions')
    result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','rust_sha256':rsha,'c_sha256':csha,'pairs':[]}
    for rname,cname,n in [('f03_do_fork_Rust_ABI_v1','f03_do_fork_C_ABI_v1',46),('f03_clone_lifetime_vm_Rust_ABI_v1','f03_clone_lifetime_vm_C_ABI_v1',10)]:
        rv=array(rust,rs,rt,rname,n,False);cv=array(c,cs,ct,cname,n,True)
        need(rv['words']==cv['words'],'ABI words differ: '+rname)
        result['pairs'].append({'rust_symbol':rv['symbol'],'c_symbol':cv['symbol'],'word_count':n,'words':rv['words']})
    result['status']='ABI_WORDS_EQUAL_SOURCE_CONFIGURATION_STILL_REQUIRES_REVIEW'
    print(json.dumps(result,sort_keys=True,indent=2))


if __name__=='__main__':main()
