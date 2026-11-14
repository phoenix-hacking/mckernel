"""Link the actual thirteen-input image, reusing both qualified changed objects."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile

packet = Path('/src/ci/c4-image-link')
output = Path('/work/output')
output.mkdir(exist_ok=True)
manifest = json.loads((packet / 'LINK-INPUTS.json').read_text())
archive = packet / 'retained-link-inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archive']['sha256']
with tarfile.open(archive) as data:
    assert sorted(item.name for item in data.getmembers()) == sorted(manifest['archive']['members'])
    assert all(item.isfile() for item in data.getmembers())
    data.extractall(output, filter='data')
for item in manifest['objects'] + [manifest['linker_script']]:
    data = (output / item['path']).read_bytes()
    assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
changes = [
    (Path('/src/c4-passed-rust/mckernel_rust.o'), output / 'kernel/rust/mckernel_rust.o', 'cab24c893663a7c5c70f048e0496c3ea32edc1cfbfde3ca1dc7b9cf3b94dd875'),
    (Path('/src/c4-passed-c/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o'), output / 'kernel/CMakeFiles/mckernel.img.dir/syscall.c.o', 'c23dce74540c9290966c82e9af36f26efa007b877a1a653a72159060e3556516'),
]
for source, target, expected in changes:
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
command = json.loads((packet / 'qualified-link-command.json').read_text())
args = command['hosted_relocated_argv']
assert len(command['actual_link_inputs']) == 13 and len(manifest['objects']) == 11
kernel = output / 'kernel'
ld = Path('/usr/bin/ld')
linker = {'sha256': hashlib.sha256(ld.read_bytes()).hexdigest(), 'version': subprocess.check_output([str(ld), '--version'], text=True), 'package': subprocess.check_output(['rpm', '-qf', str(ld.resolve())], text=True), 'baseline_identity_limit': command['linker_profile']['identity_limit']}
receipt = {'source_candidate': '7cc4e2001b2cd99aa27fbe808317fe7f9d9343e4', 'scope': 'actual thirteen-input direct-recipe image link and structural/provider checks; normal CMake regeneration/deployment/native remain pending', 'argv': args, 'cwd': str(kernel), 'linker': linker, 'retained_inputs': manifest, 'reused_changed_artifacts': [14093736217, 14094200720]}
(output / 'command.json').write_text(json.dumps(receipt, indent=2) + '\n')
subprocess.run(args, cwd=kernel, check=True)
image = kernel / 'mckernel.img'
data = image.read_bytes()
assert data[:6] == b'\x7fELF\x02\x01'
h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
assert h[1:3] == (2, 62)
segments = [struct.unpack_from('<IIQQQQQQ', data, h[5] + i * h[9]) for i in range(h[10])]
loads = [p for p in segments if p[0] == 1]
assert loads and all(p[5] <= p[6] and p[2] + p[5] <= len(data) for p in loads)
assert any(p[1] & 1 and p[3] <= h[4] < p[3] + p[6] for p in loads)
assert not any(p[0] in (2, 3) for p in segments)
sections = [struct.unpack_from('<IIQQQQIIQQ', data, h[6] + i * h[11]) for i in range(h[12])]
symbols = {}
for section in sections:
    if section[1] != 2:
        continue
    strings = sections[section[6]]
    names = data[strings[4]:strings[4] + strings[5]]
    for off in range(section[4], section[4] + section[5], section[9]):
        name, info, other, index, value, size = struct.unpack_from('<IBBHQQ', data, off)
        name = names[name:names.find(b'\0', name)].decode('utf-8')
        if name:
            symbols.setdefault(name, []).append((info, index, value, size))
assert not [name for name, rows in symbols.items() if any(row[1] == 0 for row in rows)]
required = ['arch_start', 'util_thread', 'syscall_execveat_bridge', 'syscall_util_indicate_clone_disabled_bridge']
exports = {}
for name in required:
    assert len(symbols.get(name, [])) == 1, name
    info, index, value, size = symbols[name][0]
    assert 0 < index < len(sections) and sections[index][2] & 4, (name, symbols[name])
    if name != 'arch_start':
        assert info >> 4 == 1 and info & 15 == 2, (name, symbols[name])
    exports[name] = {'binding': info >> 4, 'type': info & 15, 'section': index, 'value': value, 'size': size}
assert symbols['arch_start'][0][2] == h[4]
abi = []
for name in ['f03_execveat_complete_c_abi_words', 'f03_execveat_complete_rust_abi_words']:
    assert len(symbols.get(name, [])) == 1
    info, index, value, size = symbols[name][0]
    assert size == 280 and 0 < index < len(sections)
    owner = sections[index]
    assert owner[1] != 8 and owner[3] <= value and value + size <= owner[3] + owner[5]
    assert owner[4] + value - owner[3] + size <= len(data)
    abi.append(list(struct.unpack_from('<35Q', data, owner[4] + value - owner[3])))
assert abi[0] == abi[1]
for flag, filename in [('-h', 'elf-header.txt'), ('-l', 'elf-loads.txt'), ('-s', 'elf-symbols.txt'), ('-r', 'elf-relocations.txt')]:
    (output / filename).write_text(subprocess.check_output(['readelf', '-W', flag, str(image)], text=True))
receipt.update(result='PASS', image_bytes=len(data), image_sha256=hashlib.sha256(data).hexdigest(), entry=h[4], load_segments=loads, named_undefined_symbols=[], required_unique_functions=required, required_unique_exports=exports, final_C_Rust_ABI_words=abi[0])
(output / 'RESULT.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({key: receipt[key] for key in ['result', 'scope', 'image_bytes', 'image_sha256', 'entry', 'named_undefined_symbols', 'required_unique_functions']}, indent=2))
