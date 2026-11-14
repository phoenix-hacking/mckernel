"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded actual CPU-time production/witness callers and genuine ROOT entry relocations; no kernel execution.
ELF64LE/SYMTAB/RELA parsing follows accepted M14 callback reader; emit selected owners only.
"""
import json, os, pathlib, stat, struct, sys

def identity(fd, path):
    s = os.fstat(fd)
    assert stat.S_ISREG(s.st_mode) and s.st_nlink == 1
    return dict(path=str(path),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,
                mode=oct(stat.S_IMODE(s.st_mode)),nlink=s.st_nlink,size=s.st_size,
                mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)

def selected(raw,mode):
    eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    assert eh[0][:6]==b'\x7fELF\x02\x01' and eh[1]==1 and eh[2]==62 and eh[11]==64
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,eh[6]+i*64) for i in range(eh[12])]
    tables=[(i,s) for i,s in enumerate(sections) if s[1]==2]
    assert len(tables)==1 and tables[0][1][9]==24
    ti,table=tables[0]; strings_sec=sections[table[6]]
    strings=raw[strings_sec[4]:strings_sec[4]+strings_sec[5]]
    def name(off):return strings[off:strings.index(b'\0',off)].decode()
    symbols=[]
    for i in range(table[5]//24):
        off,info,other,ndx,value,size=struct.unpack_from('<IBBHQQ',raw,table[4]+i*24)
        symbols.append(dict(name=name(off),info=info,section=ndx,value=value,size=size))
    owners={}
    names={'C-TU':['syscall'],'C-WITNESS':['f03_cputime_ABI_reset_caller','f03_cputime_ABI_set_caller'],'ROOT-Rust':['reset_cputime','set_cputime','process_sched_reset_cputime_bridge']}[mode]
    for n in names:
        found=[s for s in symbols if s['name']==n]
        assert len(found)==1 and found[0]['info']==0x12 and 0<found[0]['section']<len(sections) and found[0]['size']>0,n
        owners[n]=dict(symbol=found[0],relocations=[])
    for ri,rela in enumerate(sections):
        if rela[1]!=4 or rela[6]!=ti:continue
        assert 0<=rela[7]<len(sections)
        if not sections[rela[7]][2]&2:continue
        assert rela[9]==24
        for i in range(rela[5]//24):
            offset,info,addend=struct.unpack_from('<QQq',raw,rela[4]+i*24)
            si=info>>32;assert si<len(symbols)
            for owner in owners.values():
                s=owner['symbol']
                if rela[7]==s['section'] and s['value']<=offset<s['value']+s['size']:
                    owner['relocations'].append(dict(target=symbols[si]['name'],type=info&0xffffffff,
                        offset_in_function=offset-s['value'],addend=addend,relocation_section_index=ri,target_symbol_index=si,target_symbol_section=symbols[si]['section'],applied_section_index=rela[7]))
    assert sum(len(v['relocations']) for v in owners.values())<=256
    def targets(owner):return {v['target'] for v in owners[owner]['relocations']}
    observations={}
    if mode=='C-TU':
        assert 'set_cputime' in targets('syscall'),'real production syscall owner lacks set_cputime allocated reference'
        observations['actual_production_syscall_to_set_cputime']=True
    elif mode=='C-WITNESS':
        assert 'reset_cputime' in targets('f03_cputime_ABI_reset_caller')
        assert 'set_cputime' in targets('f03_cputime_ABI_set_caller')
        observations['explicit_ABI_callers_not_production_runtime']=True
    else:
        entry_targets=targets('set_cputime')
        assert 'syscall_do_kill_thread_bridge' in entry_targets,'unchanged actual C signal provider reference missing'
        assert 'gettime_local_support' in entry_targets,'original early-return clock support access missing'
        observations['process_bridge_named_reset_reference']=('reset_cputime' in targets('process_sched_reset_cputime_bridge'))
        observations['named_reset_reference_observed_not_required_after_inlining']=True
        observations['unchanged_signal_C_provider_and_clock_gate_references']=True
    return dict(owners=owners,mode=mode,observations=observations,debug_relocations_excluded=True,relocation_types_not_hardcoded=True)

if __name__=='__main__':
    mode=sys.argv[1];assert mode in ['C-TU','C-WITNESS','ROOT-Rust'];path=pathlib.Path(sys.argv[2]);receipt=json.loads(pathlib.Path(sys.argv[3]).read_bytes())
    expected=receipt['object'];fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        before=identity(fd,path);assert before=={k:expected[k] for k in before}
        assert before['size']<=32<<20
        with os.fdopen(os.dup(fd),'rb') as f:raw=f.read((32<<20)+1)
        assert len(raw)==before['size'];result=selected(raw,mode)
        assert identity(fd,path)==before
    finally:os.close(fd)
    out=dict(scope=__doc__,status='PASS_ACTUAL_CPUTIME_ALLOCATED_RELOCATIONS_SELECTED_OWNER_SCOPE',
             object_identity=before,object_sha256_durable_reference=expected['sha256'],
             object_rehashed=False,result=result,native=False)
    encoded=json.dumps(out,sort_keys=True,separators=(',',':')).encode()
    assert len(encoded)<=65536
    print(encoded.decode())
