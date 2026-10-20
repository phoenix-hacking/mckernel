#!/usr/bin/env python3
"""Frozen CPU reacquisition sources against the compatible942 kernel build basis.

The source package is accepted3f7 closure plus one isolated CPU candidate.
Exact root-integrated reviewed source commit is 41b16e6440eb6539cdbb0768ba641d87a965c4f534d13a9961f5205c767475ff.
Its retained compatibility build-ID blob identifies the existing ABI; it does
not identify the new compiled source. A separately reviewed owner is required.

Default invocation validates inputs and records a plan. --execute runs one make,
without retries. This driver does not own containers, mounts, locks or retirement.
The owner must enforce read-only /out and /inputs and fresh writable /candidate.
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

PREPARATION_SHA256 = "d84e7d8ff3b3cb2b8a25439eb9a52c86d4282756b11a6641adf862e2439e73ce"
BASELINE_SOURCE_SHA = "942c927b1ec93cc31284ff498455909d9bb2d0fc"
SOURCE_CANDIDATE_SHA = "41b16e6440eb6539cdbb0768ba641d87a965c4f534d13a9961f5205c767475ff"
BASELINE = "/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output"
KERNEL = "source/linux-6.12.0-211.44.1.el10_2"
RELEASE = "6.12.0-211.44.1.el10_2.mckernel1.x86_64"
MODULES = {"ihk": "ihk", "ihk_smp_x86_64": "ihk-smp-x86_64", "mcctrl": "mcctrl"}
REPLACEMENTS = {'ihk_smp_x86_64.rs': '5b12bf77664095c966245ac8a1312a41c2fc16dd4a8233abd9e6c602305ecd6d', 'os_runtime.rs': '6b736f94751c21a6b745f0476484d516c0de536c1cc2f4e1717eb899bf8be5e7', 'smp_application.rs': 'fd375f11a43dbd205c08decdff10d94c2bb82935ae2ddfeaf1ea7142a5c70146', 'smp_cpu.rs': '356853344bffaa5b3d625c97eb3928b8908d45abbc94d16902e19bdef45ea90c', 'smp_file_pager.rs': '655c029bcddf937b6445ee01d076978ff9606832d60fd038e07076bee939e96c', 'smp_memory.rs': '8785b1be4dffe2ef24bc54dc8f861c290418ce13773d46177692c709d69fb525', 'smp_procfs.rs': '4ae39992d0354b2f0b32de4a3e26ce8a621ede6dff69dd92ce303d4ab90232ea', 'smp_service.rs': 'cd97c1528602323c43aaf70f528342fc3874fe9da1660cf1a767d27284cb5b5a', 'sysfs_memory.rs': 'd64efe15ff3545e6f21733cdc6dcbf026df370049484a7221a653d502612bfc1', 'sysfs_remote.rs': 'fe4ec42333148770a36843a82f0c4cdf675a27065dbed1f13449a2b61472dfa9', 'smp_application_syscall.rs': '33e7b92712ca90fdc2b88cff234ad2a981f3538fbd38fc705dfc2cde937a7378'}

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
    require(result["closure_files"] == 64 and result["closure_bytes"] == 1280976, "closure profile")
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
    require(len(expected) == 64, "duplicate or missing closure entries")
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
            "closure_sha256": hashlib.sha256(encoded).hexdigest(),
            "closure_hash_encoding": "SHA256 of UTF-8 JSON relative-path-to-SHA256 map, sorted keys, separators comma/colon",
            "reviewed_deltas": deltas,
            "compatibility_build_id": {"path": "ihk-compat-build-id.bin", "sha256": sources["ihk-compat-build-id.bin"],
                                       "meaning": "Retained baseline ABI compatibility blob; not proof of unchanged compiled source"},
            "excluded_working_tree": "Every unreviewed working-tree file excluded; retained current61 closure plus reviewed kmsg reader and mailbox failed-invalidation ownership pair included"}


def plan(manifest):
    command = manifest["proposed_external_command"]
    require(command[-2:] == ["-j2", "modules"], "external target changed")
    require(command.count("--jobserver-style=pipe") == 1 and
            command[-3:] == ["--jobserver-style=pipe", "-j2", "modules"], "exact pipe jobserver argv")
    require(command.count("M=/candidate/modules") == 1 and "O=/out/build" in command,
            "external output binding changed")
    require(command[command.index("-C") + 1] == "/out/" + KERNEL, "kernel source binding")
    require("LOCALVERSION=" + RELEASE[len("6.12.0"):] in command, "LOCALVERSION changed")
    return {"argv": command, "cwd": "/out/build", "environment": manifest["environment"],
            "timeout_seconds": 1800, "read_only_mounts": ["/out", "/inputs"],
            "writable_mounts": ["/candidate"], "all_three_modules_required": list(MODULES.values()),
            "application_acceptance": False, "execution_release": False,
            "source_provenance": source_provenance(manifest)}


def pipe_probe(manifest, inputs):
    # Same pinned GNU make/image and accepted recipe as the actual IHK pipe proof.
    row = manifest.get("make_pipe_probe")
    require(isinstance(row, dict), "pinned make pipe recipe observation required")
    path = plain(inputs / row["input_name"])
    require(digest(path) == row["sha256"], "pipe probe drift")
    proof = json.loads(path.read_text())
    require(proof["status"] == "PASS_PINNED_MAKE_PIPE_RECIPE" and
            proof["image_id"] == "sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d" and
            proof["make_path"] == "/usr/bin/make", "pinned make probe identity")
    require(proof["returncode"] == 0 and proof["direct_child_joined"] is True and
            proof["pipe_jobserver_observed"] is True and proof["fifo_count"] == 0,
            "pipe recipe proof")
    require(proof["argv"] == ["/usr/bin/make", "--jobserver-style=pipe", "-j2", "-f", "/probe/Makefile", "all"],
            "exact bounded recipe probe")
    require(proof["make_sha256"] == "97539f226fb36b8a39b147b6efe50a44f50c65773f7ad7013c0dc1e633f11362" and
            digest(plain(Path("/usr/bin/make"))) == proof["make_sha256"], "actual pinned make binary")


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


def source_bindings(module, candidate, inputs):
    original = (inputs / ("baseline-" + module + ".o.cmd")).read_text()
    prefix = "/out/" + KERNEL + "/drivers/misc/mckernel/"
    expected = set(re.findall(r"^  " + re.escape(prefix) + r"([^ \n]+) ", original, re.M))
    expected.add(module + ".rs")
    if module == "ihk_smp_x86_64":
        expected.add("current_fork_task_mm.rs")
    leaf = "mcctrl_rust" if module == "mcctrl" else module
    if module == "mcctrl":
        expected.remove("mcctrl.rs")
        expected.add("mcctrl_rust.rs")
    current_path = plain(candidate / "modules" / ("." + leaf + ".o.cmd"))
    current = current_path.read_text()
    source = "/candidate/modules/" + leaf + ".rs"
    assignment = re.findall(r"^source_[^\n]+ := ([^\n]+)$", current, re.M)
    require(assignment == [source], "wrong compiler source: " + module)
    saved = [line.split(":=", 1)[1].strip() for line in current.splitlines() if line.startswith("savedcmd_")]
    require(len(saved) == 1, "ambiguous compiler command")
    tokens = shlex.split(saved[0])
    require("rustc" in tokens or "/usr/bin/rustc" in tokens, "missing Rust compiler")
    require(source in tokens and "--crate-name" in tokens and tokens[tokens.index("--crate-name") + 1] == leaf,
            "wrong Rust crate binding")
    require("--emit=obj=/candidate/modules/" + leaf + ".o" in tokens, "wrong Rust object binding")
    actual = set(re.findall(r"^  /candidate/modules/([^ \n]+) ", current, re.M))
    actual.add(leaf + ".rs")
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


MM_BRIDGES = ('mckernel_inherited_mmap_write_lock', 'mckernel_inherited_mmap_write_unlock', 'mckernel_inherited_vma_start_write')

def provider_symbols(path):
    raw = path.read_bytes()
    if len(raw) < 64 or raw[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<HH",raw,16) != (1,62):
        raise ValueError("provider must be x86_64 ELF64 LE ET_REL")
    off=struct.unpack_from("<Q",raw,40)[0]
    stride,count=struct.unpack_from("<HH",raw,58)
    if stride != 64 or not count or off+stride*count > len(raw): raise ValueError("section table bounds")
    sections=[struct.unpack_from("<IIQQQQIIQQ",raw,off+i*64) for i in range(count)]
    def data(s):
        start,size=s[4:6]
        if start+size > len(raw): raise ValueError("section bounds")
        return raw[start:start+size]
    tables=[s for s in sections if s[1] == 2]
    if len(tables)!=1: raise ValueError("exact one SHT_SYMTAB required")
    tab=tables[0]
    if tab[9]!=24 or tab[5]%24 or tab[6]>=count: raise ValueError("symbol table shape")
    strings=data(sections[tab[6]]); rows=[]; symbols=data(tab)
    for offset in range(0,len(symbols),24):
        name,info,other,ndx,value,size=struct.unpack_from("<IBBHQQ",symbols,offset)
        if name>=len(strings): raise ValueError("symbol name bounds")
        end=strings.find(b"\0",name)
        if end<0: raise ValueError("symbol name termination")
        text=strings[name:end].decode("ascii")
        if text in MM_BRIDGES:
            rows.append((text,ndx,info>>4,info&15))
    return raw,rows

def actual_mm_provider_check(directory):
    directory=Path(directory)
    result={}
    ccmd = plain(directory / ".mcctrl_vm_write_compat.o.cmd")
    text = ccmd.read_text()
    require(re.findall(r"^source_[^\n]+ := ([^\n]+)$", text, re.M) == ["/candidate/modules/mcctrl_vm_write_compat.c"], "wrong MM compat compiler source")
    saved = [line.split(":=", 1)[1].strip() for line in text.splitlines() if line.startswith("savedcmd_")]
    require(len(saved) == 1, "ambiguous MM compat compiler command")
    tokens = shlex.split(saved[0])
    require("-c" in tokens and "/candidate/modules/mcctrl_vm_write_compat.c" in tokens and "-o" in tokens and tokens[tokens.index("-o")+1] == "/candidate/modules/mcctrl_vm_write_compat.o", "wrong MM compat C object")
    require("/candidate/modules/mcctrl_vm_write_compat.h" in text, "MM compat bound header missing from actual deps")
    members = plain(directory / "mcctrl.mod").read_text().split()
    require(members == ["/candidate/modules/mcctrl_rust.o", "/candidate/modules/mcctrl_vm_write_compat.o"], "wrong composite members")
    linkcmd = plain(directory / ".mcctrl.o.cmd")
    lines = [line.split(":=",1)[1].strip() for line in linkcmd.read_text().splitlines() if line.startswith("savedcmd_")]
    require(len(lines) == 1, "ambiguous composite linker command")
    lt = shlex.split(lines[0])
    require("-r" in lt and "-o" in lt and lt[lt.index("-o")+1] == "/candidate/modules/mcctrl.o" and "@/candidate/modules/mcctrl.mod" in lt, "wrong MM composite link command")
    result["command_bindings"] = {"C_cmd_sha256": digest(ccmd), "composite_cmd_sha256": digest(linkcmd), "members": members}
    for name,expected_defs,expected_undefs in (("mcctrl_rust.o",0,None),("mcctrl_vm_write_compat.o",1,0),("mcctrl.o",1,0),("mcctrl.ko",1,0)):
        raw,rows=provider_symbols(directory/name)
        counts={}
        for symbol in MM_BRIDGES:
            entries=[r for r in rows if r[0]==symbol and r[2] in (1,2)]
            defs=sum(r[1]!=0 for r in entries); undefs=sum(r[1]==0 for r in entries)
            if defs!=expected_defs or (undefs not in (0,1) if expected_undefs is None else undefs!=expected_undefs): raise ValueError("MM provider D/U mismatch: "+name+":"+symbol)
            if expected_defs and any(r[3]!=2 for r in entries): raise ValueError("MM provider is not STT_FUNC")
            counts[symbol]={"definitions":defs,"undefined":undefs}
        result[name]={"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"symbols":counts}
    return {"status":"PASS_ACTUAL_COMPOSITE_MM_PROVIDER_SYMBOLS","artifacts":result,"module_load":False}


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
    provider_proof = actual_mm_provider_check(directory)
    require(re.search(r"\tihk_os_application_adopt_current_v4\t/candidate/modules/ihk\t", symbols) is not None, "missing current v4 adoption export")
    artifacts = {}
    for crate, module in MODULES.items():
        path = directory / (module + ".ko")
        info = modinfo(path)
        require(info.get("name") == crate, "wrong module name")
        for suffix in (".o", ".mod.c", ".mod.o"):
            require(plain(directory / (module + suffix)).stat().st_size > 0, "empty generated module input")
        artifacts[module] = {"sha256": digest(path), "bytes": path.stat().st_size,
                             "modinfo": info, "compiler_binding": source_bindings(crate, candidate, inputs)}
        if module == "mcctrl": artifacts[module]["MM_provider_proof"] = provider_proof
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
        pipe_probe(manifest, inputs)
        receipt["source_provenance"] = source_provenance(manifest)
        request = plan(manifest)
        save(evidence / "request.json", request)
        if not run:
            receipt["status"] = "PLAN_VALIDATED_NO_BUILD"
        else:
            with (evidence / "make.stdout").open("xb") as stdout, (evidence / "make.stderr").open("xb") as stderr:
                result = subprocess.run(request["argv"], cwd=baseline / "build", env=request["environment"],
                                        stdout=stdout, stderr=stderr, timeout=request["timeout_seconds"], check=False)
            receipt["make_returncode"] = result.returncode
            require(result.returncode == 0, "external make failed")
            closure(manifest, candidate)  # Generated outputs allowed; original source bytes must stay exact.
            receipt["artifacts"] = outputs(candidate, inputs)
            receipt["status"] = "BUILD_ARTIFACT_CHECKS_PASS"
    except subprocess.TimeoutExpired as error:
        receipt["error"] = "external make timeout"
        receipt["timeout_seconds"] = error.timeout
    except Exception as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
    finally:
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
