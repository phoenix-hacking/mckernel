# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
def _m14_check_set_timer_symbols(process_symbols, rust_symbols, image_symbols):
    def rows(text, symbol):
        return [line.split() for line in text.splitlines() if line.split()[-1:] == [symbol]]
    def unique(text, symbol, kind, size=None):
        found = rows(text, symbol)
        _fail(len(found) == 1 and found[0][-2] == kind, 'M14 set_timer provider type/count: '+symbol)
        if size is not None:
            _fail(len(found[0]) == 4 and int(found[0][1], 16) == size, 'M14 set_timer provider width: '+symbol)
    _fail(not any(row[-2] in ('T','t') for row in rows(process_symbols, 'set_timer')),
          'M14 original C set_timer body selected')
    for symbol in ('set_timer','get_this_cpu_local_var','timer_set_timer_body_result','process_sched_set_timer_bridge'):
        unique(rust_symbols, symbol, 'T')
        unique(image_symbols, symbol, 'T')
    unique(process_symbols, 'process_timer_runtime_offsets', 'R', 120)
    unique(rust_symbols, 'process_timer_runtime_offsets', 'U')
    unique(image_symbols, 'process_timer_runtime_offsets', 'R', 120)
    unique(process_symbols, 'time_sharing', 'D', 4)
    unique(rust_symbols, 'time_sharing', 'U')
    unique(image_symbols, 'time_sharing', 'D', 4)
    for symbol in M14_TIMER_CALLBACKS:
        unique(process_symbols, symbol, 'T')
        unique(rust_symbols, symbol, 'U')
        unique(image_symbols, symbol, 'T')


def _validate_m14_set_timer_contract(source_root, build, tools, env, timeout, command_rows, objects):
    row, args = _m14_selected_row(source_root, build, 'kernel/process.c', 'MCKERNEL_RUST_PROCESS_HELPERS', tools)
    out = build/'m14-production'
    oi = args.index('-o')
    pp = _m14_observe(args[:oi]+['-E', str(source_root/'kernel/process.c')],
                      'selected-process-set-timer-preprocess', out, tools, env, timeout, command_rows)
    _fail(re.search(r'\bvoid\s+set_timer\s*\([^;{}]*\)\s*\{',pp,re.S) is None and
          re.search(r'\bvoid\s+set_timer\s*\([^;{}]*\)\s*;',pp,re.S) is not None,
          'M14 selected set_timer declaration/body exclusion')
    fields = ('thread_status_offset','thread_sched_list_offset','thread_spin_sleep_lock_offset',
              'thread_spin_sleep_offset','thread_itimer_enabled_offset','cpu_runq_lock_offset',
              'cpu_runq_offset','cpu_runq_len_offset','cpu_current_offset','cpu_timer_enabled_offset',
              'cpu_backlog_list_offset','timer_timeout_offset','timer_waitq_offset','timer_list_offset','timer_thread_offset')
    witness = ['_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8,"timer LP64");',
               '_Static_assert(sizeof(struct timer_runtime_offsets)==120 && _Alignof(struct timer_runtime_offsets)==8,"timer descriptor ABI");',
               '_Static_assert(__builtin_types_compatible_p(__typeof__(&set_timer),void(*)(int)),"set_timer ABI");']
    for index, field in enumerate(fields):
        witness.append('_Static_assert(__builtin_offsetof(struct timer_runtime_offsets,'+field+')=='+str(index*8)+',"timer field layout");')
        witness.append('_Static_assert(__builtin_types_compatible_p(__typeof__(((struct timer_runtime_offsets*)0)->'+field+'),unsigned long),"timer field type");')
    for name, prototype in (('process_timer_spin_lock_bridge','unsigned long(*)(unsigned long)'),
                            ('process_timer_spin_unlock_bridge','void(*)(unsigned long,unsigned long)'),
                            ('process_timer_lapic_enable_bridge','void(*)(unsigned int)'),
                            ('process_timer_lapic_disable_bridge','void(*)(void)')):
        witness.append('_Static_assert(__builtin_types_compatible_p(__typeof__(&'+name+'),'+prototype+'),"timer callback ABI");')
    abi_source=out/'actual-process-set-timer-ABI.c'
    abi_source.write_text((source_root/'kernel/process.c').read_text()+'\n'+'\n'.join(witness)+'\n')
    selected=args.copy();selected[oi+1]=str(out/'actual-process-set-timer-ABI.o');selected[-1]=str(abi_source)
    phase=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
               phase='m14-selected-complete-process-TU-timer-ABI',argv=selected,cwd=row['directory'],exit_code=None)
    command_rows.append(phase)
    phase['exit_code']=_run_process(selected,Path(row['directory']),env,out/'process-timer-ABI.stdout',out/'process-timer-ABI.stderr',timeout,phase['phase'])
    _fail(phase['exit_code']==0,'M14 actual whole process.c timer ABI witness compile')
    texts=[]
    for path,label in ((Path(objects['kernel/process.c']['path']),'default-process-timer-ownership'),
                       (build/'kernel/rust/mckernel_rust.o','Rust-timer-ownership'),
                       (build/'kernel/mckernel.img','image-timer-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'],'-S','-g',str(path)],label,out,tools,env,timeout,command_rows))
    _m14_check_set_timer_symbols(*texts)
    return dict(provider='set_timer',C_body_excluded=True,C_import_required=False,
                descriptor_bytes=120,descriptor_align=8,fields=fields,callbacks=M14_TIMER_CALLBACKS,
                time_sharing_bytes=4,actual_whole_process_ABI_compile=phase,native=False)
