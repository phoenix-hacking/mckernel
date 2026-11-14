# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _validate_m14_migration_contract(source_root, build, tools, env, timeout, command_rows, objects):
    row,args=_m14_selected_row(source_root,build,'kernel/process.c','MCKERNEL_RUST_PROCESS_HELPERS',tools)
    out=build/'m14-production';oi=args.index('-o')
    pp=_m14_observe(args[:oi]+['-E',str(source_root/'kernel/process.c')],
                     'selected-process-migration-preprocess',out,tools,env,timeout,command_rows)
    getter='sched_request_migrate';log='process_sched_migrate_log_bridge';descriptor='process_sched_migrate_debug'
    for name in (getter,log):
        _fail(re.search(r'\bvoid\s+'+name+r'\s*\([^;{}]*\)\s*\{',pp,re.S) is None,
              'M14 selected original C migration implementation: '+name)
    _fail(re.search(r'\bvoid\s+'+getter+r'\s*\([^;{}]*\)\s*;',pp,re.S) is not None,
          'M14 migration public declaration missing')
    texts=[]
    process_object=Path(objects['kernel/process.c']['path'])
    for path,label in ((process_object,'default-process-migration-ownership'),
                       (build/'kernel/rust/mckernel_rust.o','Rust-migration-ownership'),
                       (build/'kernel/mckernel.img','image-migration-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(path)],label,out,tools,env,timeout,command_rows))
    def rows(text,name):
        return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    for name in (getter,log):
        _fail(not any(r[-2] in ('T','t') for r in rows(texts[0],name)),
              'M14 original C migration body selected: '+name)
    for text in texts[1:]:
        for name in (getter,'sched_request_migrate_body_result',log):
            found=rows(text,name)
            _fail(len(found)==1 and found[0][-2]=='T','M14 unique actual Rust/final migration provider: '+name)
    found=rows(texts[1],descriptor)
    _fail(len(found)==1 and found[0][-2]=='U','M14 actual fullRust diagnostic descriptor import')
    for text in (texts[0],texts[2]):
        found=rows(text,descriptor)
        _fail(len(found)==1 and len(found[0])==4 and found[0][-2]=='D' and
              int(found[0][1],16)==32 and int(found[0][0],16)%8==0,
              'M14 unique aligned32byte diagnostic descriptor data')
    symbols=_m14_observe([tools['tools']['readelf']['path'],'-sW',str(process_object)],
                         'default-process-migration-debug-symbol',out,tools,env,timeout,command_rows)
    found=[l.split() for l in symbols.splitlines() if l.split()[-1:]==[descriptor]]
    _fail(len(found)==1 and found[0][2]=='32' and found[0][3]=='OBJECT' and
          found[0][4]=='GLOBAL' and found[0][-2].isdigit(),'M14 actual C descriptor object binding')
    section_index=int(found[0][-2])
    sections=_m14_observe([tools['tools']['readelf']['path'],'-SW',str(process_object)],
                          'default-process-migration-debug-section',out,tools,env,timeout,command_rows)
    verbose=[int(m.group(1)) for m in re.finditer(r'^\s*\[\s*(\d+)\]\s+__verbose\s+PROGBITS\b',sections,re.M)]
    _fail(verbose==[section_index],'M14 diagnostic descriptor not in original __verbose input section')
    # Exact canonical source binds file/function/line422/default0/fmtNULL;
    # this proves actual object data/type/section, never native log execution.
    return dict(getter=getter,Rust_body='sched_request_migrate_body_result',Rust_log=log,
                C_implementation_bodies_excluded=True,C_getter_import_required=False,
                C_descriptor=descriptor,descriptor_bytes=32,descriptor_alignment=8,
                C_input_section='__verbose',original_selector_source_bound=True,
                migration_numeric_layout_credit=False,native=False)
