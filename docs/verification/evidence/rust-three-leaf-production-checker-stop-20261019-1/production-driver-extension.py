RELEASE_TID_PROCESS_ASSERTIONS = '\n_Static_assert(sizeof(struct thread)==5568,"Thread.size");\n_Static_assert(_Alignof(struct thread)==64,"Thread.align");\n_Static_assert(__builtin_offsetof(struct thread,hash_list)==0,"Thread.hash_list");\n_Static_assert(__builtin_offsetof(struct thread,tid)==20,"Thread.tid");\n_Static_assert(__builtin_offsetof(struct thread,proc)==4304,"Thread.proc");\n_Static_assert(__builtin_offsetof(struct thread,system_tsc)==5040,"Thread.system_tsc");\n_Static_assert(__builtin_offsetof(struct thread,user_tsc)==5048,"Thread.user_tsc");\n_Static_assert(sizeof(struct process)==1728,"Process.size");\n_Static_assert(_Alignof(struct process)==64,"Process.align");\n_Static_assert(__builtin_offsetof(struct process,update_lock)==64,"Process.update_lock");\n_Static_assert(__builtin_offsetof(struct process,tids)==256,"Process.tids");\n_Static_assert(__builtin_offsetof(struct process,nr_tids)==264,"Process.nr_tids");\n_Static_assert(__builtin_offsetof(struct process,stime)==1296,"Process.stime");\n_Static_assert(__builtin_offsetof(struct process,utime)==1312,"Process.utime");\n_Static_assert(sizeof(struct cpu_local_var)==8128,"CPU.size");\n_Static_assert(_Alignof(struct cpu_local_var)==64,"CPU.align");\n_Static_assert(__builtin_offsetof(struct cpu_local_var,resource_set)==7912,"CPU.resource_set");\n_Static_assert(sizeof(struct resource_set)==384,"ResourceSet.size");\n_Static_assert(_Alignof(struct resource_set)==64,"ResourceSet.align");\n_Static_assert(__builtin_offsetof(struct resource_set,thread_hash)==32,"ResourceSet.thread_hash");\n_Static_assert(sizeof(struct thread_hash)==5888,"ThreadHash.size");\n_Static_assert(_Alignof(struct thread_hash)==64,"ThreadHash.align");\n_Static_assert(__builtin_offsetof(struct thread_hash,lock)==1216,"ThreadHash.lock");\n_Static_assert(sizeof(((struct thread_hash*)0)->lock)/sizeof(((struct thread_hash*)0)->lock[0])==73,"ThreadHash.bucket_count");\n_Static_assert(HASH_SIZE==73,"ThreadHash.hash_size");\n_Static_assert(sizeof(((struct thread_hash*)0)->lock[0])==64,"ThreadHash.bucket_size");\n_Static_assert(_Alignof(__typeof__(((struct thread_hash*)0)->lock[0]))==64,"ThreadHash.bucket_align");\n_Static_assert(sizeof(struct mcs_rwlock_node_irqsave)==64,"McsNode.size");\n_Static_assert(_Alignof(struct mcs_rwlock_node_irqsave)==64,"McsNode.align");\n_Static_assert(__builtin_offsetof(struct mcs_rwlock_node_irqsave,irqsave)==0,"McsNode.irqsave");\n_Static_assert(sizeof(struct timespec)==16,"TimeSpec.size");\n_Static_assert(_Alignof(struct timespec)==8,"TimeSpec.align");\n_Static_assert(sizeof(struct list_head)==16,"List.size");\n_Static_assert(__builtin_offsetof(struct list_head,next)==0,"List.next");\n_Static_assert(__builtin_offsetof(struct list_head,prev)==8,"List.prev");\n_Static_assert(sizeof(struct mcexec_tid)==16,"TidEntry.size");\n_Static_assert(_Alignof(struct mcexec_tid)==8,"TidEntry.align");\n_Static_assert(__builtin_offsetof(struct mcexec_tid,thread)==8,"TidEntry.thread");\n_Static_assert(sizeof(struct ddebug)==32,"Ddebug.size");\n_Static_assert(_Alignof(struct ddebug)==8,"Ddebug.align");\n_Static_assert(_Alignof(struct list_head)==8,"List.align");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->tids),struct mcexec_tid*),"three-leaf ABI type 0");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->nr_tids),int),"three-leaf ABI type 1");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread*)0)->tid),int),"three-leaf ABI type 2");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread*)0)->system_tsc),unsigned long),"three-leaf ABI type 3");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread*)0)->user_tsc),unsigned long),"three-leaf ABI type 4");\n_Static_assert(__builtin_types_compatible_p(__typeof__(get_this_cpu_local_var()),struct cpu_local_var*),"three-leaf ABI type 5");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct resource_set*)0)->thread_hash),struct thread_hash*),"three-leaf ABI type 6");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&__release_tid),void(*)(struct process*,struct thread*)),"three-leaf ABI type 7");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_destroy_thread_time_account_bridge),void(*)(void*)),"three-leaf ABI type 8");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_destroy_thread_hash_detach_bridge),void(*)(void*)),"three-leaf ABI type 9");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_destroy_thread_release_tid_bridge),void(*)(void*,void*)),"three-leaf ABI type 10");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_mcs_writer_lock_bridge),void(*)(unsigned long,void*)),"three-leaf ABI type 11");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_mcs_writer_unlock_bridge),void(*)(unsigned long,void*)),"three-leaf ABI type 12");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&thread_hash),int(*)(int)),"three-leaf ABI type 13");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&tsc_to_ts),void(*)(unsigned long,struct timespec*)),"three-leaf ABI type 14");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&ts_add),void(*)(struct timespec*,const struct timespec*)),"three-leaf ABI type 15");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_release_tid_body_result),int(*)(void*,int,unsigned long,unsigned long,void*,int,process_tid_log_fn_t)),"three-leaf ABI type 16");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_list_is_linked_result),int(*)(const struct list_head*)),"three-leaf ABI type 17");\n_Static_assert(__builtin_types_compatible_p(__typeof__(&process_list_detach_result),void(*)(struct list_head*)),"three-leaf ABI type 18");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var*)0)->resource_set),struct resource_set*),"three-leaf ABI type 19");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread*)0)->hash_list),struct list_head),"three-leaf ABI type 20");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread_hash*)0)->lock[0]),mcs_rwlock_lock_t),"three-leaf ABI type 21");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process*)0)->update_lock),mcs_rwlock_lock_t),"three-leaf ABI type 22");\n_Static_assert(__builtin_types_compatible_p(__typeof__(((struct mcs_rwlock_node_irqsave*)0)->irqsave),unsigned long),"three-leaf ABI type 23");\n'

def _validate_release_tid_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows):
    """Affected actual process TU and already-compiled real native/legacy crates."""
    rows = json.loads((build / 'compile_commands.json').read_text())
    process = source_root / 'kernel/process.c'
    _fail(_sha256(process) == '7c2cee5f29a659923579ef8664c8fc31d01fe2ec7e19c570dd9ac3cc2e7d18a7', 'actual integrated process source drift')
    _fail(_sha256(source_root / 'kernel/rust/process_helpers.rs') == 'a5ac237dc120af18ee9555874967e0da387e6c62cb92b5f054fdf00ed62a2043', 'actual current lifecycle/Rust source drift')
    matches = [r for r in rows if Path(r['file']).resolve() == process.resolve()]
    _fail(len(matches) == 1, 'release TID actual process compile row count')
    row = matches[0]
    args = list(row['arguments']) if 'arguments' in row else shlex.split(row['command'])
    _fail(args[0] == tools['tools']['cc']['path'] and '14.3.1' in tools['tools']['cc']['version'], 'release TID pinned GCC14')
    _fail(args.count('-DMCKERNEL_RUST_PROCESS_HELPERS') == 1, 'release TID default selected process macro')
    out = build / 'release-tid-production'
    out.mkdir(mode=0o700)
    fixture = out / 'production-process.c'
    # No release prototype is injected: real source must supply the declaration
    # before its destroy bridge. Truthful source provenance remains source-root.
    fixture.write_text('#line 1 ' + json.dumps(str(process)) + chr(10) + process.read_text() +
                       chr(10) + '#line 1 "release_tid_assertions.inc"' + chr(10) + RELEASE_TID_PROCESS_ASSERTIONS)
    common = [args[0]]
    skip = False
    for token in args[1:]:
        if skip:
            skip = False
            continue
        if token in ('-o', '-MF', '-MT', '-MQ'):
            skip = True
            continue
        if token in ('-c', '-MD', '-MMD', '-MP') or token == str(process):
            continue
        common.append(token)
    proof = []
    for mode in ('selected', 'fallback'):
        command = list(common)
        if mode == 'fallback':
            command.remove('-DMCKERNEL_RUST_PROCESS_HELPERS')
        command += ['-Werror=implicit-function-declaration', '-c', str(fixture), '-o', str(out / (mode + '-process.o'))]
        phase = 'release-tid-full-process-' + mode
        row_proof = {'phase': phase, 'argv': command, 'cwd': row['directory'],
                     'source_sha256': _sha256(process), 'full_TU_fixture_sha256': _sha256(fixture),
                     'exit_code': None, 'no_injected_release_prototype': True}
        command_rows.append(row_proof)
        row_proof['exit_code'] = _run_process(command, Path(row['directory']), env, stdout, stderr, timeout, phase)
        proof.append(row_proof)
        _atomic_json(evidence / 'release-tid-production-checks.json', {'status': 'PENDING', 'checks': proof})
        _fail(row_proof['exit_code'] == 0, phase + ' failed')
    # Existing FP gate immediately before this extension produces both full crates
    # once. Do not repeat those compiler invocations or accept extracted fixtures.
    objects = [('selected-process.o', out / 'selected-process.o', False),
               ('fallback-process.o', out / 'fallback-process.o', True),
               ('native-mckernel_rust.o', build / 'release-fp-regs-production/native-mckernel_rust.o', True),
               ('legacy-mckernel_rust.o', build / 'release-fp-regs-production/legacy-mckernel_rust.o', True)]
    for name, obj, defined in objects:
        nmout = out / (name + '.nm')
        nmerr = out / (name + '.nm.stderr')
        command = [tools['tools']['nm']['path'], '-S', str(obj)]
        code = _run_process(command, out, env, nmout, nmerr, timeout, 'release-tid-export-' + name, output_fsize=1048576)
        _fail(code == 0 and nmerr.stat().st_size == 0 and nmout.stat().st_size < 1048576, 'release TID symbol capture ' + name)
        symbols = [line.split() for line in nmout.read_text().splitlines()]
        definitions = [v for v in symbols if len(v) >= 4 and v[-1] == '__release_tid' and v[-2] == 'T']
        unresolved = [v for v in symbols if len(v) >= 2 and v[-1] == '__release_tid' and v[-2] == 'U']
        _fail(len(definitions) == int(defined), 'release TID symbol definition ' + name)
        for normal_symbol in ('process_destroy_thread_time_account_bridge', 'process_destroy_thread_hash_detach_bridge'):
            normal_definitions = [v for v in symbols if len(v) >= 4 and v[-1] == normal_symbol and v[-2] == 'T']
            normal_unresolved = [v for v in symbols if len(v) >= 2 and v[-1] == normal_symbol and v[-2] == 'U']
            _fail(len(normal_definitions) == int(defined), 'normal teardown symbol definition ' + name + ':' + normal_symbol)
            _fail(len(normal_unresolved) == 0, 'normal teardown unresolved symbol ' + name + ':' + normal_symbol)
        if name == 'selected-process.o':
            _fail(len(unresolved) == 1, 'release TID actual selected destroy callback reference')
        else:
            _fail(len(unresolved) == 0, 'release TID unresolved symbol ' + name)
        if 'mckernel_rust' in name:
            descriptors = [v for v in symbols if len(v) >= 4 and 'RELEASE_TID_DEBUG' in v[-1]]
            _fail(len(descriptors) == 1 and int(descriptors[0][-3], 16) == 32, 'release TID real crate descriptor size ' + name)
        proof.append({'phase': 'release-tid-export-' + name, 'argv': command, 'exit_code': code,
                      'object_sha256': _sha256(obj), 'stdout_sha256': _sha256(nmout), 'stderr_bytes': nmerr.stat().st_size})
    _atomic_json(evidence / 'release-tid-production-checks.json',
                 {'status': 'PASS', 'checks': proof, 'full_native_legacy_crates_reused': True,
                  'default_link': 'PENDING_IMAGE_MAKE', 'body_consumer_descriptor': 'PENDING_POSTBUILD', 'three_leaf_symbols': ['__release_tid', 'process_destroy_thread_time_account_bridge', 'process_destroy_thread_hash_detach_bridge']})
