"""Exact current mckernel.img postgate; stdlib only, no subprocess or compiler."""
import copy
import json
from pathlib import PurePosixPath
import shlex

EXPECTED = {'/src/kernel/mem.c': 'kernel/CMakeFiles/mckernel.img.dir/mem.c.o', '/src/kernel/syscall.c': 'kernel/CMakeFiles/mckernel.img.dir/syscall.c.o', '/src/kernel/process.c': 'kernel/CMakeFiles/mckernel.img.dir/process.c.o', '/src/kernel/rust/abi_checks.c': 'kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o', '/src/arch/x86_64/kernel/context.S': 'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o', '/src/arch/x86_64/kernel/cpu.c': 'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o', '/src/arch/x86_64/kernel/interrupt.S': 'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o', '/src/arch/x86_64/kernel/memory.c': 'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o', '/src/arch/x86_64/kernel/syscall.c': 'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o', '/src/arch/x86_64/kernel/trampoline.S': 'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o'}
DIRECTORY = '/work/output/build/kernel'
MAP = '0xfffffffffe800000'

def _require(ok, diagnostic):
    if not ok:
        raise ValueError(diagnostic)

def _target(path):
    parts = PurePosixPath(path).parts
    return any(parts[i:i + 2] == ('CMakeFiles', 'mckernel.img.dir')
               for i in range(len(parts) - 1))

def image_compile_postgate(records, generated_linker, linker_template):
    _require(isinstance(records, list), 'project compilation database is not an array')
    selected = {}
    for index, row in enumerate(records):
        _require(isinstance(row, dict), 'project compilation record is not an object')
        _require(all(isinstance(row.get(k), str) for k in
                     ('directory', 'file', 'output', 'command')),
                 'project compilation record lacks exact string fields')
        argv = shlex.split(row['command'])
        outputs = [argv[i + 1] for i, value in enumerate(argv[:-1]) if value == '-o']
        candidate = (row['file'] in EXPECTED or _target(row['output']) or
                     any(_target(value) for value in outputs))
        if not candidate:
            continue
        source = row['file']
        _require(source in EXPECTED, 'extra or wrong-source mckernel.img record')
        _require(row['directory'] == DIRECTORY and row['output'] == EXPECTED[source],
                 'wrong target/output/directory for required image source')
        _require(source not in selected, 'duplicate required image record')
        _require(argv and argv[0] == '/usr/bin/cc', 'wrong image compiler')
        _require(argv.count('-o') == 1 and outputs == [EXPECTED[source][7:]],
                 'command output differs from exact target output')
        _require(argv.count('-c') == 1 and argv.index('-c') + 1 < len(argv) and
                 argv[argv.index('-c') + 1] == source,
                 'command source differs from exact required source')
        for name, value in [('MAP_KERNEL_START', MAP + 'UL'), ('KERNEL_RAM_VADDR', MAP)]:
            definitions = [arg for arg in argv if arg.startswith('-D' + name + '=')]
            _require(definitions == ['-D' + name + '=' + value],
                     'missing/duplicate/wrong paired ' + name)
        _require(('-D__ASSEMBLY__' in argv) == source.endswith('.S'),
                 'source C/assembly language pairing differs')
        selected[source] = {'index': index, 'directory': row['directory'],
                            'file': source, 'output': row['output'],
                            'command': row['command']}
    _require(set(selected) == set(EXPECTED), 'missing required image record')
    _require(generated_linker == linker_template.replace('@MAP_KERNEL_START@', MAP),
             'generated supported linker differs from exact MAP template substitution')
    return {'project_compile_rows': len(records), 'image_C_AS_compile_rows': len(selected),
            'MAP_KERNEL_START': MAP, 'KERNEL_RAM_VADDR': MAP,
            'linker_template_exact': True,
            'exact_image_records': [selected[name] for name in EXPECTED]}

def defined_rejection_checks(records, generated_linker, linker_template):
    """Six bounded data-only regressions for this actual postgate defect."""
    base = image_compile_postgate(records, generated_linker, linker_template)
    index = base['exact_image_records'][0]['index']
    cases = []
    missing = copy.deepcopy(records); del missing[index]
    cases.append(('missing', missing, 'missing required image record'))
    duplicate = copy.deepcopy(records); duplicate.append(copy.deepcopy(records[index]))
    cases.append(('duplicate', duplicate, 'duplicate required image record'))
    extra = copy.deepcopy(records); row = copy.deepcopy(records[index])
    row['file'] = '/src/kernel/not-an-expected-image-source.c'; extra.append(row)
    cases.append(('extra', extra, 'extra or wrong-source mckernel.img record'))
    wrong = copy.deepcopy(records)
    wrong[index]['output'] = wrong[index]['output'].replace('mckernel.img.dir', 'other.dir')
    cases.append(('wrong-target', wrong, 'wrong target/output/directory for required image source'))
    directory = copy.deepcopy(records); directory[index]['directory'] = '/work/output/build/other'
    cases.append(('wrong-directory', directory, 'wrong target/output/directory for required image source'))
    paired = copy.deepcopy(records)
    paired[index]['command'] = paired[index]['command'].replace('-DKERNEL_RAM_VADDR=' + MAP,
                                                              '-DKERNEL_RAM_VADDR=0x0')
    cases.append(('wrong-paired-MAP', paired, 'missing/duplicate/wrong paired KERNEL_RAM_VADDR'))
    results = []
    for name, data, diagnostic in cases:
        try:
            image_compile_postgate(data, generated_linker, linker_template)
        except ValueError as error:
            _require(str(error) == diagnostic, 'unexpected rejection diagnostic for ' + name)
            results.append({'case': name, 'rejected': True, 'diagnostic': diagnostic})
        else:
            raise ValueError('postgate accepted malformed ' + name)
    return {'positive_actual_record_count': base['project_compile_rows'],
            'positive_image_rows': base['image_C_AS_compile_rows'], 'rejections': results}
