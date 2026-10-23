# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _validate_m14_clear_range_contract(source_root,build,tools,env,timeout,command_rows,objects):
    row,args=_m14_selected_row(source_root,build,'arch/x86_64/kernel/memory.c','MCKERNEL_RUST_X86_MEMORY_PUBLIC',tools)
    out=build/'m14-production';oi=args.index('-o')
    abi=out/'actual-clear-range-header-ABI.c'
    abi.write_text('#include '+json.dumps(str(source_root/'arch/x86_64/kernel/memory.c'))+'\n'+M14_CLEAR_RANGE_HEADER_ABI_ASSERTIONS)
    _m14_observe(args[:oi]+['-fsyntax-only',str(abi)],'selected-clear-range-real-header-ABI',out,tools,env,timeout,command_rows)
    paths=(Path(objects['arch/x86_64/kernel/memory.c']['path']),Path(objects['kernel/mem.c']['path']),
           build/'kernel/rust/mckernel_rust.o',build/'kernel/mckernel.img')
    texts=[]
    for path,label in zip(paths,('default-memory-clear-range-ownership','default-mem-remote-flush-ownership',
                                'Rust-clear-range-ownership','image-clear-range-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(path)],label,out,tools,env,timeout,command_rows))
    def rows(text,name):return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    def unique(text,name,kind):
        found=rows(text,name)
        _fail(len(found)==1 and found[0][-2]==kind,'M14 clear-range provider/import: '+name)
    unique(texts[0],'x86_clear_range_public_body','U')
    for name in ('ihk_mc_pt_clear_range','ihk_mc_pt_free_range','x86_clear_range_public_body'):
        _fail(not any(r[-2] in ('T','t') for r in rows(texts[0],name)),'M14 old clear/free C body selected')
        unique(texts[2],name,'T');unique(texts[3],name,'T')
    for name,index in (('remote_flush_tlb_array_cpumask',1),('x86_clear_range_top_log_bridge',0),
                       ('x86_clear_range_walk_l4_bridge',0)):
        unique(texts[index],name,'T');unique(texts[2],name,'U');unique(texts[3],name,'T')
    return dict(Rust_providers=('ihk_mc_pt_clear_range','ihk_mc_pt_free_range','x86_clear_range_public_body'),
                actual_C_memory_import='x86_clear_range_public_body',clear_free_C_imports_required=False,
                actual_C_providers=('remote_flush_tlb_array_cpumask','x86_clear_range_top_log_bridge','x86_clear_range_walk_l4_bridge'),
                real_header_ABI_assertions=8,all3_C_providers_remain_computeC_debt=True,native=False)
