#!/usr/bin/env python3
"""Frozen isolated fork composite against the compatible942 Linux build basis.

The source identity is the exact63-file closure SHA256, not a Git commit.
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

PREPARATION_SHA256 = '84625c53c9f5628a52d68ca350997eb0f3a3b0823ee4bd522349df66e5014f13'
BASELINE_SOURCE_SHA = "942c927b1ec93cc31284ff498455909d9bb2d0fc"
SOURCE_CANDIDATE_SHA = '1cf8409d8e3f1e1b7c7787c1760da0acf863f0626f5c613466e62be974b6bae4'
BASELINE = "/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output"
KERNEL = "source/linux-6.12.0-211.44.1.el10_2"
RELEASE = "6.12.0-211.44.1.el10_2.mckernel1.x86_64"
MODULES = {"ihk": "ihk", "ihk_smp_x86_64": "ihk-smp-x86_64", "mcctrl": "mcctrl"}
REPLACEMENTS = {'abi/application.rs': '9dc6ac72e1fbb458798764ffc0e8db2161b4004d6b498324f9647f9434a351c1', 'application_syscall.rs': '5602b9fc586425884ec4fe1dd028747b74ee6b9be3230e2359f7a78e3c994246', 'ihk_smp_x86_64.rs': '71ebc6c17ff76360d3b84da4df786e49f67a2ef314ca8c3739fb383cd83533d0', 'mcctrl_process.rs': 'd1a9333c5eb548feadb24f07785e9986079c84d97c5002e2fe7270b2b23cba7a', 'mcctrl_vm.rs': 'da7596b172bf8b62ca620f9dc88deb82e6913d1c789c8c80189e464849f983e8', 'os_runtime.rs': 'df8a38f83c28dfc474ceea46e775f2ec935de0b56fb50cbd3c9921a9faa44893', 'private_fork_carrier_request_20261017.rs': '97d2e03d0651c0570aae9a08ce8f442d1c3ef504b0b7640f556488e1689c72a6', 'smp_application.rs': '9d7ed440f33295f6c5d2348b99d56808d38cd8c5ccb73977514ead5243726b39', 'smp_application_image.rs': '09998e15329ad9d73bf2f947524c20dc29992df63bea8c509dd0ce48e66424ac', 'smp_application_syscall.rs': 'ad239a66f649684674b0923a12492f7afe00a9464e2e576e730b17db36d2914c', 'smp_cpu.rs': '356853344bffaa5b3d625c97eb3928b8908d45abbc94d16902e19bdef45ea90c', 'smp_file_pager.rs': '655c029bcddf937b6445ee01d076978ff9606832d60fd038e07076bee939e96c', 'smp_fork_ingress.rs': 'e58027c1eb0e7b0b2ba3556bd816a3cf22447e1ffb669442f334ea3eba92621b', 'smp_fork_link.rs': 'da637b853fb42b0247f5aba8e21dedd63d2f0476b75ebea980dbe15030cb078f', 'smp_memory.rs': '253722f6b0a97cedabb901af8ad4b8d6b1d91568d96e479f65b64f5d7344cf39', 'smp_procfs.rs': '4ae39992d0354b2f0b32de4a3e26ce8a621ede6dff69dd92ce303d4ab90232ea', 'smp_service.rs': '7ee688c64dd34fb8dd0d4876cd2e41d5094abbf4ba0646b448e883bf63ba275a', 'sysfs_memory.rs': '5a92b9be1a107c9f7ad37b54117714d18a39fd3db3ea02cc656115928e40d0f8', 'sysfs_remote.rs': 'fe4ec42333148770a36843a82f0c4cdf675a27065dbed1f13449a2b61472dfa9'}

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
    require(result["closure_files"] == 63 and result["closure_bytes"] == 1453689, "closure profile")
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
    require(len(expected) == 63, "duplicate or missing closure entries")
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
            "excluded_working_tree": "All live working trees and future v10 work; only frozen original09f/d99 composite plus independently reviewed two-file corrections are included"}


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


def source_bindings(module, candidate, inputs):
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
