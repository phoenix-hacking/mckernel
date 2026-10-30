from pathlib import Path
p=Path('verify_probe.py');s=p.read_text();s=s.replace('import argparse\n','import argparse\nimport json\nimport shlex\n')
s=s.replace('etype, machine, version, _, _, shoff, _, ehsize, _, _, shentsize, shnum, _ = e','etype, machine, version, _, _, shoff, _, ehsize, _, _, shentsize, shnum, shstrndx = e')
a='''    sections = [struct.unpack_from('<IIQQQQIIQQ', module, shoff + i*64) for i in range(shnum)]
    candidates = []'''
b='''    sections = [struct.unpack_from('<IIQQQQIIQQ', module, shoff + i*64) for i in range(shnum)]
    require(0 < shstrndx < shnum and sections[shstrndx][1] == 3, 'invalid section name table')
    shnames = section(module, sections[shstrndx], 'section name table')
    names_by_index = [cstring(shnames, entry[0]) for entry in sections]
    require(all(b'\\n' not in name for name in names_by_index), 'invalid section name')
    # The original readelf/grep expression matches any character before data.
    # Require one match, the actual .data section, before its first bytes may
    # be equated to the symbol. Never infer first-byte equality from a symbol.
    matches = [i for i, name in enumerate(names_by_index) if re.search(rb'.data', name)]
    require(len(matches) == 1 and names_by_index[matches[0]] == b'.data', 'ambiguous data section extraction')
    candidates = []'''
assert s.count(a)==1;s=s.replace(a,b)
a="""    target = sections[index]
    require(target[1] == 1 and target[2] & 3 == 3, 'MAP_KERNEL_START must be in writable allocated bytes')
    data = section(module, target, 'symbol section')"""
b="""    target = sections[index]
    require(index == matches[0] and value == 0, 'MAP_KERNEL_START is not first .data bytes')
    require(target[1] == 1 and target[2] & 3 == 3, 'MAP_KERNEL_START must be in writable allocated bytes')
    require(not any(entry[1] in (4, 9) and entry[7] == index and entry[5] != 0 for entry in sections),
            'relocations target the MAP_KERNEL_START section')
    data = section(module, target, 'symbol section')"""
assert s.count(a)==1;s=s.replace(a,b)
a='''def verify(make_status, module_path, release_path, uts_path, uname_r, expected):'''
b='''def generated(cache_path, commands_path, uname_r, kernel_dir, expected):
    cache = blob(cache_path, 4*1024*1024).decode('utf-8')
    for name, want in [('UNAME_R', uname_r), ('KERNEL_DIR', kernel_dir)]:
        values = re.findall(r'^'+name+r':[A-Za-z_]+=(.*)$', cache, re.M)
        require(values == [want], 'generated CMake '+name+' mismatch')
    records = json.loads(blob(commands_path, 8*1024*1024).decode('utf-8'))
    require(isinstance(records, list), 'invalid compile_commands root')
    rows = [row for row in records if isinstance(row, dict) and
            row.get('file') == '/src/arch/x86_64/kernel/syscall.c']
    require(len(rows) == 1, 'expected one exact architecture source command')
    row = rows[0]
    argv = row.get('arguments')
    if argv is None:
        require(isinstance(row.get('command'), str), 'missing compiler command')
        argv = shlex.split(row['command'])
    require(isinstance(argv, list) and all(isinstance(x, str) for x in argv), 'invalid compiler argv')
    for prefix, want in [('-DMAP_KERNEL_START=', expected+'UL'), ('-DKERNEL_RAM_VADDR=', expected)]:
        values = [arg[len(prefix):] for arg in argv if arg.startswith(prefix)]
        require(values == [want], 'generated compiler '+prefix+' mismatch')

def verify(make_status, module_path, release_path, uts_path, uname_r, expected, cache_path, commands_path, kernel_dir):'''
assert s.count(a)==1;s=s.replace(a,b)
a="""    require(value == int(expected,16), 'MAP_KERNEL_START does not match expected value')
    return f'0x{value:016x}'"""
b="""    require(value == int(expected,16), 'MAP_KERNEL_START does not match expected value')
    generated(cache_path, commands_path, uname_r, kernel_dir, expected)
    return f'0x{value:016x}'"""
assert s.count(a)==1;s=s.replace(a,b)
a="""    for name in ('make-status','module','kernel-release','uts-release-header','uname-r','expected-map'):"""
b="""    for name in ('make-status','module','kernel-release','uts-release-header','uname-r','expected-map',
                 'cmake-cache','compile-commands','expected-kernel-dir'):"""
assert s.count(a)==1;s=s.replace(a,b)
s=s.replace('x.uname_r,x.expected_map))','x.uname_r,x.expected_map,x.cmake_cache,x.compile_commands,x.expected_kernel_dir))')
s=s.replace('except (ProbeError, OSError, UnicodeError, struct.error) as error:', 'except (ProbeError, OSError, UnicodeError, struct.error, json.JSONDecodeError, ValueError) as error:')
p.write_text(s)
