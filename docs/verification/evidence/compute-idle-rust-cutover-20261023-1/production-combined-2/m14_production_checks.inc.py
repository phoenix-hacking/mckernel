# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Inserted into the existing pinned image driver; uses its owned command/capture path.
M14_SOURCE_PINS = {
    'kernel/process.c': '7203019d2ba8143f9240a03d11bc8c5cfcd495d89183aa7ab643c6159a6bd02d',
    'kernel/rust/sched_helpers.rs': '449df570965855f992a0fe024fca7cd6527b20622b4b8e3b33af04900b02e923',
    'kernel/include/sched_helpers.h': '9712a3df59eb0251f517ce01254e4576119868924b35f7da6fbee294bff966ae',
    'arch/x86_64/kernel/memory.c': '95bb6a4a916a802e98eb9f7eac98eef990d6f75a3e42b06f29ac0a73ef2a452b',
    'kernel/rust/x86_memory_helpers.rs': '689b9741821609a7c2e3aadb8cd46b0dbc57948090b38758f0b3eb120a5297fb',
}
M14_IDLE_IMPORTS = ('sched_idle_loop_body_result', 'sched_idle_current_cpu_bridge')
M14_MEMORY_IMPORTS = ('x86_clear_old_action_bridge', 'x86_clear_phys_to_virt_bridge')
M14_RUST_EXPORTS = M14_IDLE_IMPORTS + M14_MEMORY_IMPORTS + (
    'sched_idle_begin_body_result', 'sched_idle_iteration_body_result',
    'sched_idle_runqueue_has_running_result', 'process_sched_cpu_local_bridge',
    'get_cpu_local_var', 'ihk_mc_get_processor_id')


def _validate_m14_source_pins(source_root):
    for relative, checksum in M14_SOURCE_PINS.items():
        _fail(_sha256(_regular(source_root / relative, 'M14 selected source')) == checksum,
              'M14 exact postimage differs: ' + relative)


def _m14_selected_row(source_root, build, relative, macro, tools):
    rows = json.loads((build / 'compile_commands.json').read_text())
    selected = [r for r in rows if r.get('file') == str(source_root / relative)]
    _fail(len(selected) == 1, 'M14 unique actual compile row: ' + relative)
    row = selected[0]
    args = list(row['arguments']) if 'arguments' in row else shlex.split(row['command'])
    _fail(args[0] == tools['tools']['cc']['path'] and '14.3.1' in tools['tools']['cc']['version'],
          'M14 pinned GCC14 actual compiler differs')
    _fail(args.count('-D' + macro) == 1 and args.count('-o') == 1 and
          args[-2:] == ['-c', str(source_root / relative)], 'M14 exact selected C flags')
    return row, args


def _m14_observe(command, name, out, tools, env, timeout, command_rows):
    stdout, stderr = out / (name + '.stdout'), out / (name + '.stderr')
    row = dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
               phase='m14-' + name, argv=command, cwd=str(out), exit_code=None)
    command_rows.append(row)
    row['exit_code'] = _run_process(command, out, env, stdout, stderr, timeout,
                                    row['phase'], output_fsize=32 << 20)
    _fail(row['exit_code'] == 0 and stderr.stat().st_size == 0, 'M14 observer failed: ' + name)
    row.update(stdout_sha256=_sha256(stdout), stderr_sha256=_sha256(stderr))
    return stdout.read_text()


def _validate_m14_selected_memory_TU(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows):
    _validate_m14_source_pins(source_root)
    row, args = _m14_selected_row(source_root, build, 'arch/x86_64/kernel/memory.c',
                                'MCKERNEL_RUST_X86_MEMORY_PUBLIC', tools)
    out = build / 'm14-production'
    out.mkdir(mode=0o700)
    oi = args.index('-o')
    pp = _m14_observe(args[:oi] + ['-E', str(source_root / 'arch/x86_64/kernel/memory.c')],
                      'selected-memory-preprocess', out, tools, env, timeout, command_rows)
    for name in ('clear_range_old_action',) + M14_MEMORY_IMPORTS:
        _fail(re.search(r'\b' + name + r'\s*\([^;{}]*\)\s*\{', pp, re.S) is None,
              'M14 original C definition selected: ' + name)
    _fail(all('extern ' in pp[max(0, match.start()-20):match.start()]
              for match in [re.search(r'\b'+name+r'\s*\(', pp) for name in M14_MEMORY_IMPORTS]
              if match is not None) and all(re.search(r'\b'+name+r'\s*\(', pp) is not None
                                          for name in M14_MEMORY_IMPORTS),
          'M14 selected external Rust declarations missing')
    selected = args.copy()
    selected[oi+1] = str(out / 'selected-memory.o')
    phase = dict(phase='m14-selected-complete-memory-TU', argv=selected,
                 cwd=row['directory'], source_sha256=M14_SOURCE_PINS['arch/x86_64/kernel/memory.c'], exit_code=None)
    command_rows.append(phase)
    phase['exit_code'] = _run_process(selected, Path(row['directory']), env, stdout, stderr,
                                      timeout, phase['phase'])
    _fail(phase['exit_code'] == 0, 'M14 selected actual memory TU failed')
    _atomic_json(evidence / 'm14-selected-memory-TU.json', dict(status='PASS_PINNED_MEMORY_TU_ONLY',
        compile=phase, object=_artifact(out/'selected-memory.o', 'selected memory object'),
        actual_default_link='PENDING', native=False))


def _validate_m14_default_link(source_root, build, tools, evidence, env, timeout, command_rows):
    _validate_m14_source_pins(source_root)
    out = build / 'm14-production'
    objects = {}
    for relative, macro, imports in (
        ('kernel/process.c', 'MCKERNEL_RUST_PROCESS_HELPERS', M14_IDLE_IMPORTS),
        ('arch/x86_64/kernel/memory.c', 'MCKERNEL_RUST_X86_MEMORY_PUBLIC', M14_MEMORY_IMPORTS)):
        row, args = _m14_selected_row(source_root, build, relative, macro, tools)
        obj = Path(row['directory']) / args[args.index('-o')+1]
        obj = obj.resolve(strict=True)
        objects[relative] = _artifact(obj, 'M14 actual default C object')
        label = 'default-process' if relative == 'kernel/process.c' else 'default-memory'
        nm = _m14_observe([tools['tools']['nm']['path'], '-u', str(obj)], label+'-imports', out,
                          tools, env, timeout, command_rows)
        reloc = _m14_observe([tools['tools']['readelf']['path'], '-rW', str(obj)], label+'-relocations', out,
                             tools, env, timeout, command_rows)
        for name in imports:
            _fail(sum(line.split()[-1:] == [name] for line in nm.splitlines()) == 1 and
                  any(name in line for line in reloc.splitlines()), 'M14 default C import/relocation: '+name)
    makefile = (build/'kernel/CMakeFiles/mckernel_rust_obj.dir/build.make').read_text()
    _fail(all('--cfg '+cfg in makefile for cfg in
              ('native_linux_irq_work_v6_12','enable_profile','enable_perf','enable_rusage')),
          'M14 full production Rust configuration differs')
    _fail('mckernel_equivalence' not in makefile, 'M14 test equivalence CPU provider selected')
    for filename, name in [('kernel/rust/mckernel_rust.o','Rust object'),('kernel/mckernel.img','final image')]:
        path = build/filename
        objects[filename] = _artifact(path, 'M14 '+name)
        text = _m14_observe([tools['tools']['nm']['path'], '-g', '--defined-only', str(path)],
                            'Rust-definitions' if filename.endswith('.o') else 'image-definitions', out,
                            tools, env, timeout, command_rows)
        for symbol in M14_RUST_EXPORTS:
            found = [line.split() for line in text.splitlines() if line.split()[-1:] == [symbol]]
            _fail(len(found) == 1 and found[0][-2] == 'T', 'M14 unique Rust/final owner missing: '+symbol)
    undefined = _m14_observe([tools['tools']['nm']['path'], '-u', str(build/'kernel/mckernel.img')],
                             'final-undefined', out, tools, env, timeout, command_rows)
    _fail(undefined.strip() == '', 'M14 final unresolved provider')
    proof = dict(status='PASS_PINNED_FULLCRATE_DEFAULT_C_CONSUMERS_AND_FINAL_LINK_ONLY',
        source_pins=M14_SOURCE_PINS, objects=objects, idle_imports=M14_IDLE_IMPORTS,
        memory_imports=M14_MEMORY_IMPORTS, unique_Rust_and_image_exports=M14_RUST_EXPORTS,
        native=False, whole_M14_area_retired=False)
    _revalidate_m14_objects(proof)
    _atomic_json(evidence/'m14-combined-default-link.json', proof)
    return proof


def _revalidate_m14_objects(proof):
    for item in proof['objects'].values():
        _fail(_artifact(Path(item['path']), 'M14 final stable object') == item,
              'M14 default object changed before publication')

