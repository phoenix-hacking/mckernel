def _m14_Rust_callback_relocations(path,targets):
    """Count only required callback relocations; keep the 1MiB observer cap."""
    import struct
    raw=Path(path).read_bytes();eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    _fail(eh[0][:6]==b'\x7fELF\x02\x01' and eh[1]==1 and eh[2]==62 and eh[11]==64,'M14 Rust relocation object ABI')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,eh[6]+i*64) for i in range(eh[12])]
    tables=[(i,s) for i,s in enumerate(sections) if s[1]==2]
    _fail(len(tables)==1 and tables[0][1][9]==24,'M14 Rust actual symbol table')
    index,table=tables[0];strings_sec=sections[table[6]];strings=raw[strings_sec[4]:strings_sec[4]+strings_sec[5]]
    names=[]
    for i in range(table[5]//24):
        offset=struct.unpack_from('<I',raw,table[4]+i*24)[0];names.append(strings[offset:strings.index(b'\0',offset)].decode())
    counts={name:0 for name in targets}
    for sec in sections:
        if sec[1]!=4 or sec[6]!=index or not sections[sec[7]][2]&2:continue
        _fail(sec[9]==24,'M14 Rust actual RELA stride')
        for i in range(sec[5]//24):
            off,info,addend=struct.unpack_from('<QQq',raw,sec[4]+i*24);name=names[info>>32]
            if name in counts:counts[name]+=1
    _fail(all(counts.values()),'M14 actual Rust callback relocation missing')
    return counts
