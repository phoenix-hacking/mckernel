#!/usr/bin/env python3
"""Frozen isolated fork composite against the compatible942 Linux build basis.

The source identity is the exact66-file closure SHA256, not a Git commit.
Original09f fork changes are merged onto accepted d99 host sources, with
independently reviewed factory/status and fork-ledger corrections.
Default invocation records a plan. --execute runs one make without retries;
only the separately reviewed owner controls mounts, locks and retirement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import stat
import struct
import subprocess

PREPARATION_SHA256 = '12ed05aa024f7c4d077030769309e760e30bda4b6690bf696e522429df422c92'
BASELINE_SOURCE_SHA = "942c927b1ec93cc31284ff498455909d9bb2d0fc"
SOURCE_CANDIDATE_SHA = 'f656e2bd73549af2359520b9af94d5ece8774ceac9e3e26c6d0b5de67ed3abc1'
BASELINE = "/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output"
KERNEL = "source/linux-6.12.0-211.44.1.el10_2"
RELEASE = "6.12.0-211.44.1.el10_2.mckernel1.x86_64"
MODULES = {"ihk": "ihk", "ihk_smp_x86_64": "ihk-smp-x86_64", "mcctrl": "mcctrl"}
REPLACEMENTS = {'Kbuild': 'f6ea506d4fde9050d007ad168ce0f53c257e56853a9447f4a031fa1611028ba3', 'abi/application.rs': '9dc6ac72e1fbb458798764ffc0e8db2161b4004d6b498324f9647f9434a351c1', 'application_syscall.rs': '5602b9fc586425884ec4fe1dd028747b74ee6b9be3230e2359f7a78e3c994246', 'ihk_smp_x86_64.rs': '71ebc6c17ff76360d3b84da4df786e49f67a2ef314ca8c3739fb383cd83533d0', 'mcctrl_entry.rs': 'b3898d1a4d08ba5512ee9b12e66224409f6aed4db3adc293b47631aa16fa8030', 'mcctrl_process.rs': 'd1a9333c5eb548feadb24f07785e9986079c84d97c5002e2fe7270b2b23cba7a', 'mcctrl_vm.rs': '36edae289f70da1626a81cfa9a3484334ed5d40366d5d609833b8c7eca615163', 'mcctrl_vm_write_compat.c': 'dcbe065ede329b51b41abcaf0563015532920fe6a34391c7bf77ed1c2f0abdf0', 'mcctrl_vm_write_compat.h': 'ff25bb43907149fc9303b0dd0a7db1c84b9fc2c6f49f1922f18ca9c32b57c527', 'os_runtime.rs': 'df8a38f83c28dfc474ceea46e775f2ec935de0b56fb50cbd3c9921a9faa44893', 'private_fork_carrier_request_20261017.rs': '97d2e03d0651c0570aae9a08ce8f442d1c3ef504b0b7640f556488e1689c72a6', 'smp_application.rs': '9d7ed440f33295f6c5d2348b99d56808d38cd8c5ccb73977514ead5243726b39', 'smp_application_image.rs': '09998e15329ad9d73bf2f947524c20dc29992df63bea8c509dd0ce48e66424ac', 'smp_application_syscall.rs': 'ad239a66f649684674b0923a12492f7afe00a9464e2e576e730b17db36d2914c', 'smp_cpu.rs': '356853344bffaa5b3d625c97eb3928b8908d45abbc94d16902e19bdef45ea90c', 'smp_file_pager.rs': '655c029bcddf937b6445ee01d076978ff9606832d60fd038e07076bee939e96c', 'smp_fork_ingress.rs': 'e58027c1eb0e7b0b2ba3556bd816a3cf22447e1ffb669442f334ea3eba92621b', 'smp_fork_link.rs': 'da637b853fb42b0247f5aba8e21dedd63d2f0476b75ebea980dbe15030cb078f', 'smp_memory.rs': '253722f6b0a97cedabb901af8ad4b8d6b1d91568d96e479f65b64f5d7344cf39', 'smp_procfs.rs': '4ae39992d0354b2f0b32de4a3e26ce8a621ede6dff69dd92ce303d4ab90232ea', 'smp_service.rs': '7ee688c64dd34fb8dd0d4876cd2e41d5094abbf4ba0646b448e883bf63ba275a', 'sysfs_memory.rs': 'be333a5fc3b1eca331268f4579608eda6d2e7186c8c76f756c061e3030be11c6', 'sysfs_remote.rs': 'fe4ec42333148770a36843a82f0c4cdf675a27065dbed1f13449a2b61472dfa9'}

# Selected consumed tools/headers and modpost universe from immutable 942 build.
BASIS_DIGESTS = {
    "Module.symvers": "6093eaf14d92140acb07e086f5c1e7e25007f65b4cd218572abe99af3f4855df",
    "scripts/mod/modpost": "9de7e3698f946447f2c31cd41b268da60adfea8f6b26e1255642388b63d4463f",
    "tools/objtool/objtool": "b6a5cf759c86391d24463722d597d4d4e40b5094540b9d5f656c8146ea118e28",
    "scripts/basic/fixdep": "01506178f2868bd3fcff88d54a7ffe94dee924bb0aa995a9935a98ac7723d5e4",
    "scripts/target.json": "99841dcc659681b8bd45e47d0dee08d3c3c3fa04e0f3331dede10ba0fbb00ea7",
    "include/generated/rustc_cfg": "e2799dd37996a64ab04e0548be1bd7f4e22a375c74e77e19c09098cdb6bc3939",
    "include/generated/autoconf.h": "99d4fc58db2ad5a515e8af210b9b5fd2be624039dcffd1fa0f2e9fca320c2ca3",
    "include/generated/utsrelease.h": "46ec981be727b5e16bad989d768363964e8d4362fecb7661ee0bacdead15bbf0",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def plain(path):
    require(stat.S_ISREG(path.lstat().st_mode), "nonregular file: " + str(path))
    return path


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def load_preparation(path):
    require(digest(plain(path)) == PREPARATION_SHA256, "frozen preparation digest mismatch")
    result = json.loads(path.read_text())
    require(result["status"] == "INPUTS_PREPARED_EXECUTION_NOT_RELEASED", "preparation status")
    require(result["closure_files"] == 66 and result["closure_bytes"] == 1463836, "closure profile")
    changed = {row["path"]: row["sha256"] for row in result["closure"] if row["reviewed_replacement"]}
    require(changed == REPLACEMENTS, "reviewed replacement set")
    return result


def relative_path(value):
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts and str(path) == value, "unsafe relative path")
    return path


def files(root):
    result = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "symlink: " + str(path))
        if path.is_dir():
            continue
        plain(path)
        result[str(path.relative_to(root))] = path
    return result


def closure(manifest, candidate):
    directory = candidate / "modules"
    require(directory.is_dir() and directory.resolve() == directory, "unsafe module root")
    actual = files(directory)
    expected = {row["path"]: row for row in manifest["closure"]}
    require(len(expected) == 66, "duplicate or missing closure entries")
    for name, row in expected.items():
        relative_path(name)
        path = plain(candidate / "modules" / name)
        require(path.stat().st_nlink == 1, "source hardlink: " + name)
        require(path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], "source changed: " + name)
    return actual, expected


def validate(manifest, baseline, candidate, inputs):
    for root in (baseline, candidate, inputs):
        require(root.is_dir() and root.resolve() == root, "noncanonical root: " + str(root))
    require(baseline != candidate and baseline not in candidate.parents and candidate not in baseline.parents,
            "baseline/candidate overlap")
    actual, expected = closure(manifest, candidate)
    require(set(actual) == set(expected), "candidate has generated or unbound inputs")
    for row in manifest["references"].values():
        path = plain(inputs / Path(row["retained_copy"]).name)
        require(digest(path) == row["sha256"], "reference changed: " + path.name)
        origin = row["path"]
        if origin.startswith(BASELINE + "/"):
            original = plain(baseline / origin[len(BASELINE) + 1:])
            require(digest(original) == row["sha256"], "baseline reference changed: " + origin)
    for row in manifest["rust_support_exact_cmd_deps"]:
        require(row["path"].startswith(BASELINE + "/build/rust/"), "unexpected Rust support path")
        path = plain(baseline / row["path"][len(BASELINE) + 1:])
        require(digest(path) == row["sha256"], "Rust support changed: " + str(path))
    for row in manifest["build_support_stat_only"]:
        require(row["path"].startswith(BASELINE + "/"), "unexpected support path")
        plain(baseline / row["path"][len(BASELINE) + 1:])
    for name, expected_hash in BASIS_DIGESTS.items():
        require(digest(plain(baseline / "build" / name)) == expected_hash, "basis tool/header changed: " + name)
    for name in ("home", "tmp"):
        directory = candidate / name
        require(directory.is_dir() and not any(directory.iterdir()), "private directory not fresh: " + name)
    return {name: row["sha256"] for name, row in expected.items()}


def source_provenance(manifest):
    sources = {row["path"]: row["sha256"] for row in manifest["closure"]}
    encoded = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()
    deltas = [{"path": row["path"], "baseline_sha256": row["baseline_sha256"],
               "source_candidate_sha256": row["sha256"]}
              for row in manifest["closure"] if row["reviewed_replacement"]]
    return {"baseline_source_sha": BASELINE_SOURCE_SHA,
            "source_candidate_sha": SOURCE_CANDIDATE_SHA,
            "source_authority": manifest["source_authority"],
            "closure_sha256": hashlib.sha256(encoded).hexdigest(),
            "closure_hash_encoding": "SHA256 of UTF-8 JSON relative-path-to-SHA256 map, sorted keys, separators comma/colon",
            "reviewed_deltas": deltas,
            "compatibility_build_id": {"path": "ihk-compat-build-id.bin", "sha256": sources["ihk-compat-build-id.bin"],
                                       "meaning": "Retained baseline ABI compatibility blob; not proof of unchanged compiled source"},
            "excluded_working_tree": "All live working trees and future v10 work; frozen original09f/d99 composite plus reviewed errno/opaque-FFI and module-local C companion changes only; original mcctrl.rs is retained lineage, compiled root is mcctrl_entry.rs"}


def plan(manifest):
    command = manifest["proposed_external_command"]
    require(command[-2:] == ["-j2", "modules"], "external target changed")
    require(command.count("M=/candidate/modules") == 1 and "O=/out/build" in command,
            "external output binding changed")
    require(command[command.index("-C") + 1] == "/out/" + KERNEL, "kernel source binding")
    require("LOCALVERSION=" + RELEASE[len("6.12.0"):] in command, "LOCALVERSION changed")
    return {"argv": command, "cwd": "/out/build", "environment": manifest["environment"],
            "timeout_seconds": 1800, "read_only_mounts": ["/out", "/inputs"],
            "writable_mounts": ["/candidate"], "all_three_modules_required": list(MODULES.values()),
            "application_acceptance": False, "execution_release": False,
            "source_provenance": source_provenance(manifest)}


def modinfo(path):
    """Read ELF64 relocatable x86_64 .modinfo without invoking host tools."""
    data = plain(path).read_bytes()
    require(len(data) >= 64 and data[:6] == b"\x7fELF\x02\x01", "not ELF64 little-endian: " + path.name)
    require(struct.unpack_from("<HH", data, 16) == (1, 62), "not x86_64 relocatable: " + path.name)
    offset = struct.unpack_from("<Q", data, 40)[0]
    size, count, names = struct.unpack_from("<HHH", data, 58)
    require(size == 64 and 0 < names < count and offset + size * count <= len(data), "ELF sections invalid")
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, offset + i * size) for i in range(count)]
    def contents(section):
        start, length = section[4:6]
        require(start + length <= len(data), "ELF section outside file")
        return data[start:start + length]
    strings = contents(sections[names])
    found = []
    for section in sections:
        require(section[0] < len(strings), "ELF section name offset")
        name = strings[section[0]:].split(b"\0", 1)[0]
        if name == b".modinfo":
            found.append(contents(section))
    require(len(found) == 1, "missing or duplicate .modinfo")
    values = {}
    for entry in found[0].split(b"\0"):
        if b"=" in entry:
            key, value = entry.decode("ascii").split("=", 1)
            require(key not in values or key not in ("vermagic", "name"), "duplicate module identity")
            values[key] = value
    require(values.get("vermagic", "").startswith(RELEASE + " "), "wrong vermagic")
    return values


EXPECTED_MCCTRL_SOURCES = {'abi/application.rs': '9dc6ac72e1fbb458798764ffc0e8db2161b4004d6b498324f9647f9434a351c1', 'abi/os_service.rs': '9dac670ec6567d379c346106d3b164ddb6d607be1dedc2be21283d4adffa5937', 'abi/x86_64.rs': '89e0f72e821cbef91ad4771f4b4b24515d89035d357dc9c23c935a313b7d12c3', 'application_image.rs': '25b7810c273c9f4b5dbff073f54e67db52c69636e63760c7d5f62e471b7a61b2', 'mcctrl_entry.rs': 'b3898d1a4d08ba5512ee9b12e66224409f6aed4db3adc293b47631aa16fa8030', 'mcctrl_exec.rs': '4ebf73c46cf12a05fc76b078fbfcf218190dd372b335f886123125a012ae26b0', 'mcctrl_process.rs': 'd1a9333c5eb548feadb24f07785e9986079c84d97c5002e2fe7270b2b23cba7a', 'mcctrl_vm.rs': '36edae289f70da1626a81cfa9a3484334ed5d40366d5d609833b8c7eca615163', 'mcctrl_vm_write_compat.c': 'dcbe065ede329b51b41abcaf0563015532920fe6a34391c7bf77ed1c2f0abdf0', 'mcctrl_vm_write_compat.h': 'ff25bb43907149fc9303b0dd0a7db1c84b9fc2c6f49f1922f18ca9c32b57c527', 'user_string.rs': 'fa83818bc26d52ffff1a763a34a92684dff47775ba389fa6ac831d0835bf62d2'}

# Included into the existing frozen driver, not a standalone execution tool.
SDK_ROOT = Path('/out')
C_THUNKS = {'mckernel_inherited_mmap_write_lock', 'mckernel_inherited_mmap_write_unlock', 'mckernel_inherited_vma_start_write'}


def saved_command(path, target):
    text = plain(path).read_text()
    rows = re.findall(r'^savedcmd_([^\n]+?) := ([^\n]+)$', text, re.M)
    require(len(rows) == 1 and rows[0][0] == target, 'wrong saved command target')
    return text, rows[0][1], shlex.split(rows[0][1])


def dependency_rows(text):
    rows = re.findall(r'^deps_[^\n]+ := \\\n((?:[^\n]*\\\n)*)', text, re.M)
    require(len(rows) == 1, 'missing or ambiguous dependency block')
    result = []
    for line in rows[0].splitlines():
        value = line.strip().removesuffix('\\').strip()
        require(bool(value), 'empty dependency')
        result.append(value)
    require(len(result) == len(set(result)), 'duplicate dependency')
    return result


def elf_link_symbols(path):
    raw = plain(path).read_bytes()
    require(len(raw) >= 64 and raw[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<HH', raw, 16) == (1, 62),
            'not an x86_64 relocatable object')
    offset = struct.unpack_from('<Q', raw, 40)[0]
    size, count = struct.unpack_from('<HH', raw, 58)
    require(size == 64 and offset + count * size <= len(raw), 'invalid object section table')
    sections = [struct.unpack_from('<IIQQQQIIQQ', raw, offset + i * size) for i in range(count)]
    tables = [s for s in sections if s[1] == 2]
    require(len(tables) == 1, 'missing or duplicate symbol table')
    table = tables[0]
    require(table[6] < len(sections) and table[9] == 24 and table[5] % 24 == 0, 'invalid symbol table')
    strings = sections[table[6]]
    def contents(s):
        require(s[4] + s[5] <= len(raw), 'object section outside file')
        return raw[s[4]:s[4] + s[5]]
    names, symbols = contents(strings), contents(table)
    defined, undefined = [], []
    for i in range(0, len(symbols), 24):
        name, info, other, section, value, length = struct.unpack_from('<IBBHQQ', symbols, i)
        if info >> 4 not in (1, 2) or name == 0:
            continue
        require(name < len(names) and b'\0' in names[name:], 'invalid symbol name')
        text = names[name:names.index(b'\0', name)].decode('ascii')
        (undefined if section == 0 else defined).append(text)
    require(len(defined) == len(set(defined)), 'duplicate global object definition')
    return {'defined': sorted(defined), 'undefined': sorted(set(undefined))}


def c_command_expected(inputs):
    text = plain(inputs / 'baseline-C-mmap_lock.o.cmd').read_text()
    rows = [line.split(':=', 1)[1].strip() for line in text.splitlines() if line.startswith('savedcmd_')]
    require(len(rows) == 1, 'C reference command ambiguous')
    old = shlex.split(rows[0])
    require(old[0] == 'clang' and old.count('-c') == 1 and old.count('-o') == 1, 'C reference compiler')
    prefix = '/out/' + KERNEL
    result = []
    for token in old:
        if token.startswith('-DKBUILD_MODFILE='):
            result.append('-DMODULE')
        elif token.startswith('-DKBUILD_BASENAME='):
            result.append('-DKBUILD_BASENAME="mcctrl_vm_write_compat"')
        elif token.startswith('-DKBUILD_MODNAME='):
            result.append('-DKBUILD_MODNAME="mcctrl"')
        elif token.startswith('-D__KBUILD_MODNAME='):
            result.append('-D__KBUILD_MODNAME=mcctrl')
        else:
            token = token.replace('mm/.mmap_lock.o.d', '/candidate/modules/.mcctrl_vm_write_compat.o.d')
            token = token.replace('-I' + prefix + '/mm', '-I/candidate/modules').replace('-Imm', '-I/candidate/modules')
            token = token.replace(prefix + '/mm/mmap_lock.c', '/candidate/modules/mcctrl_vm_write_compat.c')
            token = token.replace('mm/mmap_lock.o', '/candidate/modules/mcctrl_vm_write_compat.o')
            result.append(token)
    return result


def c_dependencies(text, candidate):
    local, sdk, wildcards = {}, {}, {}
    prefix = '/candidate/modules/'
    for name in dependency_rows(text):
        if name.startswith(prefix):
            relative = name[len(prefix):]
            relative_path(relative)
            path = plain(candidate / 'modules' / relative)
            local[relative] = {'sha256': digest(path), 'bytes': path.stat().st_size}
        else:
            wildcard = re.fullmatch(r'\$\(wildcard (include/config/[A-Za-z0-9_]+)\)', name)
            if wildcard:
                path = SDK_ROOT / 'build' / wildcard[1]
                require(not path.is_symlink(), 'SDK wildcard symlink')
                wildcards[name] = {'present': path.exists(), 'sha256': digest(plain(path)) if path.exists() else None}
                continue
            if name.startswith('/out/'):
                relative = name[len('/out/'):]
                require(relative.startswith(KERNEL + '/') or relative.startswith('build/'), 'foreign absolute SDK dependency')
                relative_path(relative)
                path = SDK_ROOT / relative
            else:
                relative_path(name)
                require(name.startswith(('include/', 'arch/x86/')), 'foreign relative SDK dependency')
                path = SDK_ROOT / 'build' / name
            plain(path)
            sdk[name] = {'sha256': digest(path), 'bytes': path.stat().st_size}
    require(set(local) == {'mcctrl_vm_write_compat.h'}, 'C private-header dependency closure')
    require('/out/' + KERNEL + '/include/linux/mm.h' in sdk and
            '/out/' + KERNEL + '/include/linux/mmap_lock.h' in sdk, 'C Linux MM dependency missing')
    return {'private_headers': local, 'sdk_dependencies': sdk, 'config_wildcards': wildcards,
            'sdk_completeness_limit': 'All actual compiler-declared dependency entries retained; target compilation must supply this evidence.'}


def c_object_audit(candidate, inputs):
    directory = candidate / 'modules'
    for name in ('mcctrl_vm_write_compat.c', 'mcctrl_vm_write_compat.h'):
        require(digest(plain(directory / name)) == EXPECTED_MCCTRL_SOURCES[name], 'C phase source hash drift: ' + name)
    ctext, ccommand, ctokens = saved_command(directory / '.mcctrl_vm_write_compat.o.cmd', '/candidate/modules/mcctrl_vm_write_compat.o')
    require(re.findall(r'^source_[^\n]+ := ([^\n]+)$', ctext, re.M) == ['/candidate/modules/mcctrl_vm_write_compat.c'], 'wrong C compiler source')
    require(ctokens == c_command_expected(inputs), 'C compiler/flags/object binding changed')
    dependencies = c_dependencies(ctext, candidate)
    csyms = elf_link_symbols(directory / 'mcctrl_vm_write_compat.o')
    require(set(csyms['defined']) == C_THUNKS, 'C thunk definitions differ')
    exports = {line.split('\t')[1] for line in plain(SDK_ROOT / 'build/Module.symvers').read_text().splitlines() if len(line.split('\t')) >= 2}
    require(set(csyms['undefined']) <= exports, 'unresolved C object import')
    object_audit = {'status': 'PASS_C_THUNKS_AND_MATCHED_IMPORTS',
                    'definitions': csyms['defined'], 'undefined_imports': csyms['undefined'],
                    'matched_symvers_sha256': digest(plain(SDK_ROOT / 'build/Module.symvers'))}
    return {'kind': 'C_object', 'sources': ['mcctrl_vm_write_compat.c', 'mcctrl_vm_write_compat.h'],
            'command_sha256': digest(directory / '.mcctrl_vm_write_compat.o.cmd'),
            'saved_command': ccommand, 'source': 'mcctrl_vm_write_compat.c',
            'object': {'sha256': digest(directory / 'mcctrl_vm_write_compat.o'), 'symbols': csyms},
            'object_audit': object_audit, **dependencies}


def composite_source_bindings(candidate, inputs):
    directory = candidate / 'modules'
    baseline = plain(inputs / 'baseline-mcctrl.o.cmd').read_text()
    prefix = '/out/' + KERNEL + '/drivers/misc/mckernel/'
    expected = set(re.findall(r'^  ' + re.escape(prefix) + r'([^ \n]+) ', baseline, re.M))
    expected.add('mcctrl_entry.rs')
    require(len(expected) == 9 and 'mcctrl.rs' not in expected, 'Rust entry reference closure')
    text, command, tokens = saved_command(directory / '.mcctrl_entry.o.cmd', '/candidate/modules/mcctrl_entry.o')
    require(re.findall(r'^source_[^\n]+ := ([^\n]+)$', text, re.M) == ['/candidate/modules/mcctrl_entry.rs'], 'wrong composite Rust root')
    require(('rustc' in tokens or '/usr/bin/rustc' in tokens) and '--crate-name' in tokens and
            tokens[tokens.index('--crate-name') + 1] == 'mcctrl_entry', 'wrong composite Rust compiler/crate')
    require('/candidate/modules/mcctrl_entry.rs' in tokens and '--emit=obj=/candidate/modules/mcctrl_entry.o' in tokens,
            'wrong composite Rust object')
    actual = set(re.findall(r'^  /candidate/modules/([^ \n]+) ', text, re.M)); actual.add('mcctrl_entry.rs')
    require(actual == expected and not re.search(r'^  /out/.*drivers/misc/mckernel/', text, re.M), 'changed composite Rust dependency closure')
    require(bool(re.search(r'^deps_[^\n]+ :=', text, re.M)), 'missing Rust dependency information')
    for name in expected | {'mcctrl_vm_write_compat.c', 'mcctrl_vm_write_compat.h'}:
        require(digest(plain(directory / name)) == EXPECTED_MCCTRL_SOURCES[name], 'composite source hash drift: ' + name)
    c_binding = c_object_audit(candidate, inputs)
    csyms = c_binding['object']['symbols']
    rsyms = elf_link_symbols(directory / 'mcctrl_entry.o')
    require({'init_module', 'cleanup_module'} <= set(rsyms['defined']), 'Rust module entry missing')
    require(not (set(csyms['defined']) & set(rsyms['defined'])), 'duplicate composite definition')
    require(C_THUNKS <= set(rsyms['undefined']), 'Rust thunk imports missing')
    ldtext, ldcommand, ldtokens = saved_command(directory / '.mcctrl.o.cmd', '/candidate/modules/mcctrl.o')
    ldseed = plain(inputs / 'baseline-LD-ihk-smp-x86_64.o.cmd').read_text()
    ldrows = [line.split(':=', 1)[1].strip() for line in ldseed.splitlines() if line.startswith('savedcmd_')]
    require(len(ldrows) == 1, 'LD reference ambiguous')
    expected_ld = shlex.split(ldrows[0].replace('drivers/misc/mckernel/ihk-smp-x86_64', '/candidate/modules/mcctrl'))
    require(ldtokens == expected_ld and ldtokens[0] == 'ld.lld' and '-r' in ldtokens, 'composite LD command binding')
    response = plain(directory / 'mcctrl.mod')
    require(response.read_text().split() == ['/candidate/modules/mcctrl_entry.o', '/candidate/modules/mcctrl_vm_write_compat.o'], 'composite LD inputs differ')
    return {'kind': 'composite_Rust_C_LD',
            'sources': sorted(expected | {'mcctrl_vm_write_compat.c', 'mcctrl_vm_write_compat.h'}),
            'sources_scope': 'Consumed Rust entry/nested sources plus module-local C root/private header; unused mcctrl.rs lineage excluded',
            'rust': {'command_sha256': digest(directory / '.mcctrl_entry.o.cmd'), 'saved_command': command, 'sources': sorted(actual), 'object': {'sha256': digest(directory / 'mcctrl_entry.o'), 'symbols': rsyms}},
            'C': c_binding,
            'LD': {'command_sha256': digest(directory / '.mcctrl.o.cmd'), 'saved_command': ldcommand, 'response_sha256': digest(response), 'inputs': response.read_text().split()}}



def source_bindings(module, candidate, inputs):
    if module == "mcctrl":
        return composite_source_bindings(candidate, inputs)
    original = (inputs / ("baseline-" + module + ".o.cmd")).read_text()
    prefix = "/out/" + KERNEL + "/drivers/misc/mckernel/"
    expected = set(re.findall(r"^  " + re.escape(prefix) + r"([^ \n]+) ", original, re.M))
    expected.add(module + ".rs")
    if module == "ihk_smp_x86_64":
        expected.update({"private_fork_carrier_request_20261017.rs", "smp_fork_ingress.rs", "smp_fork_link.rs"})
    current_path = plain(candidate / "modules" / ("." + module + ".o.cmd"))
    current = current_path.read_text()
    source = "/candidate/modules/" + module + ".rs"
    assignment = re.findall(r"^source_[^\n]+ := ([^\n]+)$", current, re.M)
    require(assignment == [source], "wrong compiler source: " + module)
    saved = [line.split(":=", 1)[1].strip() for line in current.splitlines() if line.startswith("savedcmd_")]
    require(len(saved) == 1, "ambiguous compiler command")
    tokens = shlex.split(saved[0])
    require("rustc" in tokens or "/usr/bin/rustc" in tokens, "missing Rust compiler")
    require(source in tokens and "--crate-name" in tokens and tokens[tokens.index("--crate-name") + 1] == module,
            "wrong Rust crate binding")
    require("--emit=obj=/candidate/modules/" + module + ".o" in tokens, "wrong Rust object binding")
    actual = set(re.findall(r"^  /candidate/modules/([^ \n]+) ", current, re.M))
    actual.add(module + ".rs")
    require(actual == expected, "changed production dependency closure: " + module)
    require(not re.search(r"^  /out/.*drivers/misc/mckernel/", current, re.M), "old production dependency")
    require(bool(re.search(r"^deps_[^\n]+ :=", current, re.M)), "missing saved dependency information")
    return {"command_sha256": digest(current_path), "sources": sorted(actual), "saved_command": saved[0]}


def module_order(rows):
    """Linux 6.12 modules.order enumerates object paths, before the .ko link.

    Accept exactly the three canonical object paths for this external build;
    never reduce foreign paths to basenames or accept alias spellings.
    """
    objects = {"/candidate/modules/" + module + ".o": module for module in MODULES.values()}
    require(len(rows) == 3 and set(rows) == set(objects), "modpost module set mismatch")
    return [objects[row] for row in rows]


def outputs(candidate, inputs):
    directory = candidate / "modules"
    actual = files(directory)
    require({name for name in actual if name.endswith(".ko")} == {name + ".ko" for name in MODULES.values()},
            "missing or unexpected native module")
    order = plain(directory / "modules.order").read_text().splitlines()
    module_order(order)
    symbols = plain(directory / "Module.symvers").read_text()
    require(re.search(r"\tihk_os_create_unbooted_v6\t/candidate/modules/ihk\t", symbols) is not None,
            "missing rebuilt ihk v6 export")
    for version in (7, 8, 9):
        require(re.search(r"\tihk_os_create_unbooted_v" + str(version) + r"\t/candidate/modules/ihk\t", symbols) is not None,
                "missing rebuilt additive ihk factory export: " + str(version))
    artifacts = {}
    for crate, module in MODULES.items():
        path = directory / (module + ".ko")
        info = modinfo(path)
        require(info.get("name") == crate, "wrong module name")
        for suffix in (".o", ".mod.c", ".mod.o"):
            require(plain(directory / (module + suffix)).stat().st_size > 0, "empty generated module input")
        artifacts[module] = {"sha256": digest(path), "bytes": path.stat().st_size,
                             "modinfo": info, "compiler_binding": source_bindings(crate, candidate, inputs)}
    require(len({item["modinfo"]["vermagic"] for item in artifacts.values()}) == 1, "mixed vermagic set")
    return artifacts


def execute(preparation, baseline, candidate, inputs, *, run=False):
    """One attempt. Tests mock subprocess.run; CLI fixes all mount roots."""
    require(candidate.resolve() == candidate and candidate.is_dir(), "unsafe candidate root")
    require(baseline != candidate and baseline not in candidate.parents and candidate not in baseline.parents,
            "baseline/candidate overlap")
    evidence = candidate / "evidence"
    evidence.mkdir()  # Existing evidence means this attempt is never retried.
    receipt = {"status": "FAIL", "application_acceptance": False, "production_acceptance": False,
               "make_returncode": None, "preparation_sha256": PREPARATION_SHA256,
               "baseline_source_sha": BASELINE_SOURCE_SHA, "source_candidate_sha": SOURCE_CANDIDATE_SHA}
    try:
        require({path.name for path in candidate.iterdir()} == {"modules", "home", "tmp", "evidence"},
                "candidate root has unbound content")
        manifest = load_preparation(preparation)
        receipt["source_sha256"] = validate(manifest, baseline, candidate, inputs)
        receipt["source_provenance"] = source_provenance(manifest)
        request = plan(manifest)
        save(evidence / "request.json", request)
        if not run:
            receipt["status"] = "PLAN_VALIDATED_NO_BUILD"
        else:
            # Both explicit phases remain in this single owner/container call.
            # No full module build starts before the strict C object audit.
            receipt["module_phase"] = {"status": "NOT_RUN", "make_returncode": None}
            receipt["c_object_phase"] = {"status": "RUNNING", "make_returncode": None,
                                         "full_module_make_started": False}
            c_request = dict(request)
            c_request["argv"] = request["argv"][:-2] + ["-j1", "mcctrl_vm_write_compat.o"]
            c_request["timeout_seconds"] = 30
            save(evidence / "C-object-request.json", c_request)
            with (evidence / "C-object.stdout").open("xb") as stdout, (evidence / "C-object.stderr").open("xb") as stderr:
                c_result = subprocess.run(c_request["argv"], cwd=baseline / "build", env=c_request["environment"],
                                          stdout=stdout, stderr=stderr, timeout=c_request["timeout_seconds"], check=False)
            receipt["c_object_phase"]["make_returncode"] = c_result.returncode
            require(c_result.returncode == 0, "C object make failed")
            closure(manifest, candidate)
            c_binding = c_object_audit(candidate, inputs)
            receipt["c_object_phase"].update(status="C_OBJECT_AUDIT_PASS", compiler_binding=c_binding,
                                             object_audit=c_binding["object_audit"])
            save(evidence / "C-object-audit.json", receipt["c_object_phase"])
            receipt["c_object_phase"]["full_module_make_started"] = True
            receipt["module_phase"]["status"] = "RUNNING"
            with (evidence / "make.stdout").open("xb") as stdout, (evidence / "make.stderr").open("xb") as stderr:
                result = subprocess.run(request["argv"], cwd=baseline / "build", env=request["environment"],
                                        stdout=stdout, stderr=stderr, timeout=request["timeout_seconds"], check=False)
            receipt["make_returncode"] = receipt["module_phase"]["make_returncode"] = result.returncode
            require(result.returncode == 0, "external make failed")
            closure(manifest, candidate)  # Generated outputs allowed; original source bytes must stay exact.
            receipt["artifacts"] = outputs(candidate, inputs)
            require(receipt["artifacts"]["mcctrl"]["compiler_binding"]["C"]["object"]["sha256"] ==
                    receipt["c_object_phase"]["compiler_binding"]["object"]["sha256"], "C object changed between phases")
            receipt["module_phase"]["status"] = "PASS"
            receipt["status"] = "BUILD_ARTIFACT_CHECKS_PASS"
    except subprocess.TimeoutExpired as error:
        receipt["error"] = ("C object make timeout" if receipt.get("module_phase", {}).get("status") == "NOT_RUN"
                            else "external make timeout")
        receipt["timeout_seconds"] = error.timeout
    except Exception as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if "module_phase" in receipt and receipt["module_phase"]["status"] == "RUNNING":
            receipt["module_phase"].update(status="FAIL", error=receipt.get("error", "module phase did not complete"))
        if "c_object_phase" in receipt:
            phase = receipt["c_object_phase"]
            if phase["status"] != "C_OBJECT_AUDIT_PASS":
                phase.update(status="FAIL", error=receipt.get("error", "C object phase did not complete"))
            phase["captures"] = {}
            for label in ("stdout", "stderr"):
                path = evidence / ("C-object." + label)
                if path.exists():
                    phase["captures"][label] = {"path": str(path), "sha256": digest(plain(path)), "bytes": path.stat().st_size}
            save(evidence / "C-object-result.json", phase)
        receipt["retained_files"] = {}
        for path in sorted((candidate / "modules").rglob("*")):
            name = str(path.relative_to(candidate / "modules"))
            mode = path.lstat().st_mode
            if stat.S_ISREG(mode):
                receipt["retained_files"][name] = {"sha256": digest(path), "bytes": path.stat().st_size}
            elif not stat.S_ISDIR(mode):
                receipt["retained_files"][name] = {"nonregular": True}
        save(evidence / "receipt.json", receipt)
    return receipt



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    receipt = execute(Path("/inputs/preparation.json"), Path("/out"), Path("/candidate"), Path("/inputs"), run=args.execute)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
