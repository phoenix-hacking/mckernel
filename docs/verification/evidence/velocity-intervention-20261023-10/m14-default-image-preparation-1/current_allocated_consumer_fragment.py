# Functional OS/Rust only; no security testing. Exact named consumer evidence.
def _m14_completion_reference_encoding(rel):
    _fail(rel['symbol']=='mem_tlb_atomic_dec_bridge' and rel['binding']==1 and rel['shndx']==0 and rel['addend']==0 and rel['allocated'], 'M14 exact completion consumer symbol/addend/section')
    if rel['type']==1:return 'R_X86_64_64_direct_64bit_provider_address'
    if rel['type']==27:return 'R_X86_64_GOT64_64bit_provider_GOT_offset'
    raise ImageBuildError('M14 unsupported completion-pointer encoding')

def _m14_allocated_provider_relocations(path, names, required_completion=False):
    import struct
    raw=Path(path).read_bytes();eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    _fail(eh[0][:6]==b'\x7fELF\x02\x01' and eh[1:3]==(1,62) and eh[11]==64,'M14 current provider ELF64 ET_REL x86_64')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,eh[6]+i*64) for i in range(eh[12])]
    def string(sec,off):
        data=raw[sec[4]:sec[4]+sec[5]]
        return data[off:data.index(b'\0',off)].decode()
    section_names=sections[eh[13]];proof=[]
    for index,sec in enumerate(sections):
        if sec[1]!=4:continue
        _fail(sec[7]<len(sections) and sec[6]<len(sections),'M14 relocation section identity')
        target=sections[sec[7]]
        if not target[2]&2:continue
        table=sections[sec[6]];_fail(sec[9]==24 and table[1]==2 and table[9]==24,'M14 current RELA/symtab stride')
        strings=sections[table[6]]
        for i in range(sec[5]//24):
            offset,info,addend=struct.unpack_from('<QQq',raw,sec[4]+i*24)
            symbol_index=info>>32;_fail(symbol_index<table[5]//24,'M14 relocation symbol index')
            name,attr,other,ndx,value,size=struct.unpack_from('<IBBHQQ',raw,table[4]+symbol_index*24)
            name=string(strings,name)
            if name not in names:continue
            _fail(offset<target[5] and attr>>4==1 and ndx==0,'M14 allocated provider reference must import exact global Rust provider')
            proof.append(dict(symbol=name,binding=attr>>4,symbol_type=attr&15,shndx=ndx,type=info&0xffffffff,addend=addend,allocated=True,relocation_section_index=index,relocation_section=string(section_names,sec[0]),target_section_index=sec[7],target_section=string(section_names,target[0]),offset=offset))
    if required_completion:
        selected=[r for r in proof if r['symbol']=='mem_tlb_atomic_dec_bridge']
        _fail(len(selected)==1,'M14 one actual handler completion-pointer reference')
        selected[0]['encoding']=_m14_completion_reference_encoding(selected[0])
    return proof

