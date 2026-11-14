"""Compile the affected C translation unit and compare its actual ABI to retained Rust."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

packet = Path('/src/ci/c4-c-object')
output = Path('/work/output/build')
kernel = output / 'kernel'
(kernel / 'include').mkdir(parents=True, exist_ok=True)
(kernel / 'CMakeFiles/mckernel.img.dir').mkdir(parents=True, exist_ok=True)
config = (packet / 'config.h').read_bytes()
assert hashlib.sha256(config).hexdigest() == 'ca251af0e69e4c82df042063bb9ffc180cbba2bd1c34f246d7589f44ed7bfa3f'
(output / 'config.h').write_bytes(config)
compiler = Path('/usr/bin/gcc')
assert hashlib.sha256(compiler.read_bytes()).hexdigest() == '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2'
assert compiler.read_bytes() == Path('/usr/bin/cc').read_bytes()
toolchain = subprocess.check_output(['rpm', '-q', 'gcc', 'cpp', 'binutils'], text=True)
(output / 'toolchain.txt').write_text(toolchain)
subprocess.run(['/usr/bin/gcc', '--version'], check=True)
original = json.loads((packet / 'qualified-c-command.json').read_text())
args = original['argv'][:]
assert args[0] == '/usr/bin/cc' and args[-1] == '/src/kernel/syscall.c'
added = ['-DMCKERNEL_RUST_F03_UTIL_THREAD', '-DMCKERNEL_RUST_F03_EXECVEAT_COMPLETE']
assert not any(arg in args for arg in added)
args[1:1] = added
(output / 'command.json').write_text(json.dumps({'argv': args, 'directory': str(kernel), 'added_macros': added, 'qualified_original': original}, indent=2) + '\n')
subprocess.run(args, cwd=kernel, check=True)
c_object = kernel / 'CMakeFiles/mckernel.img.dir/syscall.c.o'
rust_object = Path('/src/c4-passed-rust/mckernel_rust.o')
rust_data = rust_object.read_bytes()
assert hashlib.sha256(rust_data).hexdigest() == 'cab24c893663a7c5c70f048e0496c3ea32edc1cfbfde3ca1dc7b9cf3b94dd875'

def witness(data, symbol):
    assert data[:6] == b'\x7fELF\x02\x01'
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    assert h[1:3] == (1, 62)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, h[6] + i * h[11]) for i in range(h[12])]
    found = []
    for section in sections:
        if section[1] != 2:
            continue
        strings = sections[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            name, info, other, index, value, size = struct.unpack_from('<IBBHQQ', data, offset)
            if names[name:names.find(b'\0', name)] == symbol.encode():
                assert size == 280 and 0 < index < len(sections)
                owner = sections[index]
                found.append(list(struct.unpack_from('<35Q', data, owner[4] + value - owner[3])))
    assert len(found) == 1, (symbol, len(found))
    return found[0]

c_data = c_object.read_bytes()
c_words = witness(c_data, 'f03_execveat_complete_c_abi_words')
rust_words = witness(rust_data, 'f03_execveat_complete_rust_abi_words')
assert c_words == rust_words, {'C': c_words, 'Rust': rust_words}
symbols = subprocess.check_output(['nm', '--defined-only', '--format=posix', str(c_object)], text=True)
(output / 'c-defined-symbols.txt').write_text(symbols)
retired = ['do_execveat', 'syscall_execveat_bridge', 'util_thread', 'syscall_util_indicate_clone_disabled_bridge']
for line in symbols.splitlines():
    fields = line.split()
    if len(fields) > 1 and fields[1] in {'T', 't', 'W', 'w'}:
        assert fields[0].split('.')[0] not in retired, line
result = {'result': 'PASS', 'scope': 'affected production C object and real C/Rust35word ABI equality only; final image/normal CMake/native remain pending', 'source_candidate': '7cc4e2001b2cd99aa27fbe808317fe7f9d9343e4', 'C_object_sha256': hashlib.sha256(c_data).hexdigest(), 'C_object_bytes': len(c_data), 'Rust_object_sha256': hashlib.sha256(rust_data).hexdigest(), 'Rust_source_ci': 43544756870, 'ABI_words': c_words, 'C_executable_owners_absent': retired, 'toolchain': toolchain}
(output / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
