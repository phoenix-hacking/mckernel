# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _m14_l4_callback_object(path):
    """Accepted section/RELA observer semantics; resolve compiler-selected indices."""
    import struct
    raw=Path(path).read_bytes()
    eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    _fail(eh[0][:6]==b'\x7fELF\x02\x01' and eh[1]==1 and eh[2]==62 and eh[11]==64,'M14 L4 ELF64 relocatable object')
    sections=[dict(zip(('name_off','type','flags','addr','offset','size','link','info','align','entsize'),struct.unpack_from('<IIQQQQIIQQ',raw,eh[6]+i*64))) for i in range(eh[12])]
    def payload(sec):return raw[sec['offset']:sec['offset']+sec['size']]
    def string(tab,off):return tab[off:tab.index(b'\0',off)].decode()
    names=payload(sections[eh[13]])
    for i,sec in enumerate(sections):sec.update(index=i,name=string(names,sec['name_off']))
    tables=[s for s in sections if s['type']==2]
    _fail(len(tables)==1 and tables[0]['entsize']==24,'M14 L4 actual symbol table')
    table=tables[0];strings=payload(sections[table['link']]);symbols=[]
    for i in range(table['size']//24):
        name,info,other,ndx,value,size=struct.unpack_from('<IBBHQQ',raw,table['offset']+i*24)
        symbols.append(dict(index=i,name=string(strings,name),bind=info>>4,type=info&15,shndx=ndx,value=value,size=size))
    def symbol(name):
        found=[s for s in symbols if s['name']==name]
        _fail(len(found)==1,'M14 unique callback/helper '+name)
        return found[0]
    child=symbol('x86_clear_range_walk_l3_bridge')
    _fail(child['bind']==0 and child['type']==2 and 0<child['shndx']<len(sections),'M14 retained private L3 C child')
    proof={}
    for name in ('x86_clear_range_l4_callback','x86_clear_range_l3_callback'):
        sym=symbol(name)
        _fail(sym['bind']==1 and sym['type']==1 and sym['size']==8 and 0<sym['shndx']<len(sections),'M14 callback pointer binding/extent')
        sec=sections[sym['shndx']]
        _fail(sec['flags']&2 and not sec['flags']&4 and sec['align']>=8 and sym['value']+8<=sec['size'],'M14 allocated nonexecuting pointer section')
        relsecs=[s for s in sections if s['type']==4 and s['info']==sym['shndx']]
        _fail(len(relsecs)==1 and relsecs[0]['link']==table['index'] and relsecs[0]['entsize']==24,'M14 callback owning RELA section')
        rs=relsecs[0];found=[]
        for i in range(rs['size']//24):
            off,info,addend=struct.unpack_from('<QQq',raw,rs['offset']+i*24)
            if off==sym['value']:found.append(dict(offset=off,type=info&0xffffffff,target=symbols[info>>32],addend=addend))
        _fail(len(found)==1 and found[0]['type']==1,'M14 callback exact R_X86_64_64 pointer relocation')
        rel=found[0];target=rel['target']
        if name=='x86_clear_range_l4_callback':
            _fail(target['name']=='x86_clear_range_l4_body' and target['bind']==1 and target['shndx']==0 and rel['addend']==0,'M14 L4 pointer targets public Rust entry')
        else:
            direct=target['name']==child['name'] and target['type']==2 and rel['addend']==0
            section=target['type']==3 and target['shndx']==child['shndx'] and target['value']+rel['addend']==child['value']
            _fail(direct or section,'M14 L3 pointer targets exact retained private C child')
        proof[name]=dict(symbol=sym,section=sec,relocation_section=rs,relocation=rel)
    return dict(callbacks=proof,retained_private_C_child=child,section_indices_and_function_offsets_not_hardcoded=True,C_const_pointer_ABI_checked_separately=True,lower_C_callback_chain_remains=True)


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


def _validate_m14_successor_contract(source_root,build,tools,env,timeout,command_rows,objects):
    out=build/'m14-production';texts={};selection=[]
    def rows(text,name):return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    def unique(text,name,kind):
        found=rows(text,name);_fail(len(found)==1 and found[0][-2]==kind,'M14 successor owner/import '+name)
        return found[0]
    for relative,macro,retired in M14_SUCCESSOR_SELECTION:
        row,args=_m14_selected_row(source_root,build,relative,macro,tools)
        obj=(Path(row['directory'])/args[args.index('-o')+1]).resolve(strict=True)
        objects[relative]=_artifact(obj,'M14 successor actual complete default C object')
        tag=relative.replace('/','-').replace('.','-');oi=args.index('-o')
        pp=_m14_observe(args[:oi]+['-E',str(source_root/relative)],'successor-selected-'+tag,out,tools,env,timeout,command_rows)
        for name in retired:_fail(re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',pp,re.S) is None,'M14 successor C implementation selected '+name)
        texts[relative]=_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(obj)],'successor-symbols-'+tag,out,tools,env,timeout,command_rows)
        assertions=M14_SUCCESSOR_ABI.get(relative)
        if assertions:
            witness=out/('successor-ABI-'+tag+'.c');witness.write_text('#include '+json.dumps(str(source_root/relative))+'\n'+assertions)
            _m14_observe(args[:oi]+['-fsyntax-only',str(witness)],'successor-real-ABI-'+tag,out,tools,env,timeout,command_rows)
        selection.append(dict(source=relative,macro=macro,excluded_C_bodies=retired))
    rust=_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(build/'kernel/rust/mckernel_rust.o')],'successor-Rust-symbols',out,tools,env,timeout,command_rows)
    image=_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(build/'kernel/mckernel.img')],'successor-image-symbols',out,tools,env,timeout,command_rows)
    callback_relocations=_m14_Rust_callback_relocations(build/'kernel/rust/mckernel_rust.o',tuple(name for names in M14_SUCCESSOR_C_CALLBACKS.values() for name in names))
    for relative,names in M14_SUCCESSOR_C_CALLBACKS.items():
        for name in names:
            unique(texts[relative],name,'T');unique(rust,name,'U');unique(image,name,'T')
    geometry=unique(texts['kernel/mem.c'],'mem_remote_tlb_geometry','R')
    _fail(len(geometry)==4 and int(geometry[1],16)==12,'M14 actual three-int readonly remote geometry')
    unique(rust,'mem_remote_tlb_geometry','U');unique(image,'mem_remote_tlb_geometry','R')
    vector=rows(texts['kernel/mem.c'],'tlb_flush_vector')
    _fail(len(vector)==1 and vector[0][-2] in ('B','C'),'M14 retained ordinary C TLB vector')
    for name in ('syscall_signalfd_publish_bridge','arch_ptrace','vm_range_insert','init_pstate_and_turbo','remote_flush_tlb_array_cpumask','x86_clear_range_walk_l4_bridge','x86_clear_range_l4_body'):
        unique(rust,name,'T');unique(image,name,'T')
    unique(texts['kernel/syscall.c'],'arch_ptrace','U')
    kernel_reloc=_m14_observe([tools['tools']['readelf']['path'],'-rW',objects['kernel/syscall.c']['path']],'successor-kernel-syscall-relocations',out,tools,env,timeout,command_rows)
    _fail(any(line.split()[4:5]==['arch_ptrace'] for line in kernel_reloc.splitlines()),'M14 actual C arch_ptrace consumer relocation')
    callbacks=_m14_l4_callback_object(Path(objects['arch/x86_64/kernel/memory.c']['path']))
    for name in ('x86_clear_range_l4_callback','x86_clear_range_l3_callback'):
        found=rows(image,name);_fail(len(found)==1 and found[0][-2] in ('D','R') and int(found[0][1],16)==8,'M14 final callback global pointer extent')
    return dict(actual_default_C_selections=selection,actual_C_callbacks=M14_SUCCESSOR_C_CALLBACKS,actual_Rust_callback_relocation_counts=callback_relocations,remote_readonly_geometry_bytes=12,retained_TLB_vector=True,L4_section_aware_pointer_proof=callbacks,signalfd_Rust_internal_no_C_import_required=True,arch_ptrace_exact_C_import_relocation=True,compute_C_callback_debt_remains=True,native=False)

