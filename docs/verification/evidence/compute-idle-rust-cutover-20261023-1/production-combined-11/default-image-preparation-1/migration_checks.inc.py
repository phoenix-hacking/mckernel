# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _validate_m14_migration_contract(source_root, build, tools, env, timeout, command_rows, objects):
    row, args = _m14_selected_row(source_root, build, 'kernel/process.c', 'MCKERNEL_RUST_PROCESS_HELPERS', tools)
    out = build/'m14-production'
    oi = args.index('-o')
    pp = _m14_observe(args[:oi]+['-E',str(source_root/'kernel/process.c')],
                      'selected-process-migration-preprocess',out,tools,env,timeout,command_rows)
    getter='sched_request_migrate'
    _fail(re.search(r'\bvoid\s+'+getter+r'\s*\([^;{}]*\)\s*\{',pp,re.S) is None and
          re.search(r'\bvoid\s+'+getter+r'\s*\([^;{}]*\)\s*;',pp,re.S) is not None,
          'M14 migration selected declaration/C body exclusion')
    log='process_sched_migrate_log_bridge'
    texts=[]
    for path,label in ((Path(objects['kernel/process.c']['path']),'default-process-migration-ownership'),
                       (build/'kernel/rust/mckernel_rust.o','Rust-migration-ownership'),
                       (build/'kernel/mckernel.img','image-migration-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(path)],label,out,tools,env,timeout,command_rows))
    def rows(text,name):
        return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    _fail(not any(row[-2] in ('T','t') for row in rows(texts[0],getter)),
          'M14 original C migration getter selected')
    for text in texts[1:]:
        for name in (getter,'sched_request_migrate_body_result'):
            found=rows(text,name)
            _fail(len(found)==1 and found[0][-2]=='T','M14 migration unique Rust/final provider: '+name)
    found=rows(texts[1],log)
    _fail(len(found)==1 and found[0][-2]=='U','M14 actual fullRust migration C log import')
    for text in (texts[0],texts[2]):
        found=rows(text,log)
        _fail(len(found)==1 and found[0][-2]=='T','M14 existing PUBLIC C migration log provider')
    # No C getter-U or descriptor model is required. Rust resolves internal
    # callers using reviewed actual shared types; immutable sourcepins bind it.
    return dict(getter=getter,Rust_body='sched_request_migrate_body_result',C_body_excluded=True,
                C_getter_import_required=False,actual_Rust_C_log_import=log,
                default_C_log_provider=objects['kernel/process.c'],migration_numeric_layout_credit=False,native=False)
