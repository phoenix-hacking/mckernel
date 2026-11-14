"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded actual three-signal-body callers/entries allocated ELF relocations; no execution of kernel code.
ELF64LE/SYMTAB/RELA parsing follows accepted M14 callback reader; emit selected owners only.
"""
import json, os, pathlib, stat, struct, sys

def identity(fd, path):
    s = os.fstat(fd)
    assert stat.S_ISREG(s.st_mode) and s.st_nlink == 1
    return dict(path=str(path),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,
                mode=oct(stat.S_IMODE(s.st_mode)),nlink=s.st_nlink,size=s.st_size,
                mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)

def selected(raw):
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
    for n in ['sys_rt_sigpending','rt_sigpending_body_result','syscall_pending_mask_bridge','sys_pause','pause_body_result','sys_rt_sigsuspend','rt_sigsuspend_body_result','syscall_sigsuspend_bridge','sys_rt_sigaction','rt_sigaction_body_result','syscall_do_sigaction_bridge','do_sigaction','do_sigaction_body_result']:
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
    suspend_targets={r['target'] for r in owners['syscall_sigsuspend_bridge']['relocations']}
    action_targets={r['target'] for r in owners['do_sigaction']['relocations']}
    assert 'do_signal' in suspend_targets,'actual sigsuspend entry must retain unchanged C ownership handoff'
    assert 'syscall_forward_sigaction_update_bridge' in action_targets,'actual do_sigaction entry must retain exact existing C forwarding provider'
    assert sum(len(v['relocations']) for v in owners.values())<=256
    direct={}
    for n,expected in [('sys_rt_sigpending','syscall_pending_mask_bridge'),('sys_pause','syscall_sigsuspend_bridge'),('sys_rt_sigsuspend','syscall_sigsuspend_bridge'),('sys_rt_sigaction','syscall_do_sigaction_bridge')]:
        direct[n]=dict(expected_source_callback=expected,direct_named_callback_reference=any(r['target']==expected for r in owners[n]['relocations']))
    return dict(owners=owners,actual_caller_named_references=direct,
                sigsuspend_C_handoff_reference=True,sigaction_C_forward_reference=True,
                direct_named_callback_reference_is_observation_not_required_after_inlining=True,
                debug_relocations_excluded=True,relocation_types_not_hardcoded=True)

if __name__=='__main__':
    path=pathlib.Path(sys.argv[1]);receipt=json.loads(pathlib.Path(sys.argv[2]).read_bytes())
    expected=receipt['object'];fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        before=identity(fd,path);assert before=={k:expected[k] for k in before}
        assert before['size']<=32<<20
        with os.fdopen(os.dup(fd),'rb') as f:raw=f.read((32<<20)+1)
        assert len(raw)==before['size'];result=selected(raw)
        assert identity(fd,path)==before
    finally:os.close(fd)
    out=dict(scope=__doc__,status='PASS_ACTUAL_SIGNAL_CALLERS_ENTRIES_ALLOCATED_RELOCATIONS_AND_EXISTING_C_HANDOFFS',
             object_identity=before,object_sha256_durable_reference=expected['sha256'],
             object_rehashed=False,result=result,native=False)
    encoded=json.dumps(out,sort_keys=True,separators=(',',':')).encode()
    assert len(encoded)<=65536
    print(encoded.decode())
