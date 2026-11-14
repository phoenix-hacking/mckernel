"""Build orchestration only; functional McKernel OS/Rust work, no security testing.
Generate real selected-header metadata, then compile one existing Rust staticlib.
No device/library API is executed. Lifecycle/resource ownership belongs to the
existing CMake build owner. This helper adds no independent runtime controller.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
from rust_diagnostics import qualify_rust_diagnostics


def require(ok, message):
    if not ok:
        raise ValueError(message)


def replace_bytes(path, data):
    temporary = path.with_name(path.name + ".new")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


DIAGNOSTIC_ORIGINS = (
    ("_ihk_reserve_cpu_str", "ihk_reserve_cpu"),
    ("_ihk_reserve_mem_str", "ihk_reserve_mem"),
    ("_ihk_os_assign_cpu_str", "ihk_os_assign_cpu"),
    ("_ihk_os_set_ikc_map_str", "ihk_os_set_ikc_map"),
    ("os_assign_cpu_all", "ihk_get_num_reserved_cpus"),
    ("os_assign_cpu_all", "ihk_query_cpu"),
    ("os_assign_cpu_all", "ihk_os_assign_cpu"),
    ("os_assign_mem_all", "ihk_get_num_reserved_cpus"),
    ("os_assign_mem_all", "ihk_query_mem"),
    ("release_cpu_all", "ihk_get_num_reserved_cpus"),
    ("release_cpu_all", "ihk_query_cpu"),
    ("release_cpu_all", "ihk_release_cpu"),
    ("os_assign_mem_all", "ihk_os_assign_mem"),
    ("ihk_create_os_str", "ihk_get_num_reserved_cpus"),
    ("ihk_create_os_str", "ihk_get_num_reserved_mem_chunks"),
    ("ihk_create_os_str", "ihk_release_mem"),
    ("ihk_create_os_str", "ihk_create_os"),
    ("ihk_create_os_str", "ihk_os_load"),
    ("ihk_create_os_str", "ihk_os_kargs"),
)


def validate_diagnostic_origins(source):
    """Bind only the selected nineteen diagnostic macro sites; execute no C body."""
    original = source.parent.parent / "ihklib.c"
    witness = source / "abi" / "diagnostic_origins.selected_target_C_witness.c"
    raw, witness_raw = original.read_bytes(), witness.read_bytes()
    text, metadata = raw.decode("utf-8"), witness_raw.decode("utf-8")
    # Phase-two splices can hide a directive keyword. Reject comment-bearing
    # directive heads conservatively rather than introducing a C lexer here.
    logical_text = re.sub(r"\\\r?\n", "", text)
    require(not re.search(r"#[ \t\v\f\r]*(?:line\b|[0-9]|/\*)", logical_text),
            "unsupported C source #line/line-control directive")
    rows = re.findall(
        r'^#line ([1-9][0-9]*) "([^"\n]+)"\n'
        r'static const struct origin origin([0-9]+) = '
        r'\{ __FILE__, __LINE__, "([^"\n]+)" \};$', metadata, re.MULTILINE)
    require(len(rows) == len(DIAGNOSTIC_ORIGINS), "exact nineteen diagnostic origin rows")
    declarations = re.findall(r"\bstatic\s+const\s+struct\s+origin\s+origin[0-9]+\s*=", metadata)
    require(len(declarations) == len(rows), "no unbound diagnostic origin declaration")
    controls = re.findall(r"(?m)^[ \t]*#[ \t]*(?:line\b|[0-9])[^\n]*", metadata)
    expected_controls = [f'#line {line} "{file}"' for line, file, _, _ in rows]
    expected_controls.append('#line 1 "metadata-witness-main"')
    require(controls == expected_controls, "only selected origin #line directives and main reset")
    unbound_controls = metadata
    for control in expected_controls:
        unbound_controls = unbound_controls.replace(control + "\n", "", 1)
    unbound_controls = re.sub(r"\\\r?\n", "", unbound_controls)
    require(not re.search(r"#[ \t\v\f\r]*(?:line\b|[0-9]|/\*)", unbound_controls),
            "no unsupported witness line-control directive")
    joined, mismatches = [], []
    for origin, ((function, operation), (line, file, row_id, row_operation)) in enumerate(
            zip(DIAGNOSTIC_ORIGINS, rows)):
        require(row_id == str(origin) and row_operation == operation,
                "exact diagnostic origin identity " + str(origin))
        require(file == "/src/ihk/linux/user/ihklib.c", "selected diagnostic logical file")
        definitions = list(re.finditer(
            r"^(?:static\s+)?int\s+" + re.escape(function) + r"\([^;{}]*\)\s*\{",
            text, re.MULTILINE))
        require(len(definitions) == 1, "one diagnostic function definition " + function)
        definition = definitions[0]
        # Selected source functions close at column zero. Unsupported formatting
        # fails closed rather than guessing a different C definition or site.
        end = text.find("\n}", definition.end())
        require(end >= 0, "selected diagnostic function boundary " + function)
        body = text[definition.end():end]
        sites = list(re.finditer(
            r'"%s:%d: ' + re.escape(operation) + r' failed with %d\\n"\s*,\s*'
            r'__FILE__\s*,\s*(?P<line>__LINE__)\s*,\s*ret\b', body))
        require(len(sites) == 1,
                "one diagnostic operation site " + function + "/" + operation)
        site = sites[0]
        position = definition.end() + site.start("line")
        actual_line = text.count("\n", 0, position) + 1
        joined.append(dict(origin=origin, function=function, operation=operation,
                           logical_file=file, line=actual_line,
                           line_macro_byte_offset=len(text[:position].encode("utf-8")),
                           site=site.group(0),
                           site_sha256=hashlib.sha256(site.group(0).encode("utf-8")).hexdigest()))
        if int(line) != actual_line:
            mismatches.append(f"origin{origin}: expected {actual_line}, got {line}")
    require(not mismatches, f"diagnostic origin source-line mismatch ({len(mismatches)}): "
            + "; ".join(mismatches))
    return dict(original_C=str(original), original_C_sha256=hashlib.sha256(raw).hexdigest(),
                witness=str(witness), witness_sha256=hashlib.sha256(witness_raw).hexdigest(),
                metadata_only=True, C_function_bodies_emitted=False, rows=joined)


def source_export_contracts(source, output):
    """Metadata-only contracts from exact original C definitions, not new headers."""
    original = source.parent.parent / "ihklib.c"
    raw = original.read_bytes()
    text = raw.decode("utf-8")
    snippets = []
    declarations = ["/* Actual source-only contracts; metadata witness only. */\n"]
    for name in ("_ihk_os_assign_cpu_str", "_ihk_os_set_ikc_map_str",
                 "parse_env", "dump_reserve_mem_conf"):
        pattern = r"^(?:int|void) " + name + r"\([^;{}]*\)\s*(?=\{)"
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        require(len(matches) == 1, "one original source signature " + name)
        match = matches[0]
        header = match.group(0).rstrip()
        declarations.append("extern " + header + ";\n")
        snippets.append(dict(symbol=name, kind="function_definition_header",
                             start=match.start(), end=match.end(), text=header))
    for name, pattern in (
        ("__argc", r"^int __argc;"),
        ("__argv", r"^char \*\*__argv;"),
        ("namespace_files", r"^struct namespace_file namespace_files\[\] = \{.*?^\};"),
    ):
        matches = list(re.finditer(pattern, text, re.MULTILINE | re.DOTALL))
        require(len(matches) == 1, "one original source data definition " + name)
        match = matches[0]
        definition = match.group(0)
        declarations.append(definition + "\n")
        snippets.append(dict(symbol=name, kind="data_definition",
                             start=match.start(), end=match.end(), text=definition))
    replace_bytes(output / "source_export_actual_contracts.inc",
                  "\n".join(declarations).encode())
    receipt = dict(original_C=str(original), sha256=hashlib.sha256(raw).hexdigest(),
                   metadata_only=True, C_function_bodies_emitted=False,
                   snippets=snippets)
    replace_bytes(output / "source-export-contracts.json",
                  (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc", required=True)
    parser.add_argument("--rustc", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--include-dir", action="append", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    source = Path(args.source_dir).resolve()
    output = Path(args.out_dir).resolve()
    origin_contracts = validate_diagnostic_origins(source)
    output.mkdir(parents=True, exist_ok=True)
    rows = []

    def run(argv, label, environment=None):
        stdout = output / (label + ".stdout")
        stderr = output / (label + ".stderr")
        with stdout.open("wb") as out, stderr.open("wb") as err:
            result = subprocess.run(argv, cwd=output, env=environment, stdout=out, stderr=err)
        rows.append(dict(argv=argv, returncode=result.returncode, stdout=str(stdout),
                         stderr=str(stderr)))
        require(result.returncode == 0, "failed build phase " + label)
        require(stdout.stat().st_size <= 1 << 20 and stderr.stat().st_size <= 1 << 20,
                "bounded metadata/compiler diagnostics " + label)
        return stdout.read_bytes(), stderr.read_bytes()

    replace_bytes(output / "diagnostic-origin-source-contracts.json",
                  (json.dumps(origin_contracts, sort_keys=True, indent=2) + "\n").encode())
    source_export_contracts(source, output)
    include = ["-I" + str(output)] + ["-I" + path for path in args.include_dir]
    common = [args.cc, "-std=gnu11", "-O0", "-Wall", "-Wextra", "-Werror"] + include
    witnesses = [
        ("perf_pages_abi_witness.c", "perf", []),
        ("dump_abi_witness.c", "dump", ["-DPAGE_SIZE=4096"]),
        ("diagnostic_origins.selected_target_C_witness.c", "origins", []),
        ("combined_selected_SDK_actual_header_ABI.c", "platform", ["-DPAGE_SIZE=4096"]),
    ]
    for filename, label, defines in witnesses:
        out, err = run(common + defines + [str(source / "abi" / filename), "-o",
                       str(output / (label + "-witness"))], label + "-compile")
        require(out == err == b"", "unexpected header compiler diagnostics")
    generators = [
        ("perf", [], "perf_pages_abi.rs"),
        ("dump", [], "dump_abi.rs"),
        ("origins", ["raw"], "diagnostic_origins.rs"),
        ("origins", ["create"], "create_diagnostic_origins.rs"),
    ]
    for label, arguments, filename in generators:
        out, err = run([str(output / (label + "-witness"))] + arguments, filename)
        require(out and b"pub const " in out and not err, "real header metadata")
        replace_bytes(output / filename, out)
    out, err = run([str(output / "platform-witness")], "platform-select")
    require(out == b"ihklib_stat_abi_stat\n" and not err, "actual supported stat ABI")
    stat_cfg = out.decode().strip()
    replace_bytes(output / "actual-stat-cfg.txt", out)
    environment = dict(os.environ)
    for key, name in [
        ("MCKERNEL_DUMP_ABI_RS", "dump_abi.rs"),
        ("MCKERNEL_PERF_PAGES_ABI_RS", "perf_pages_abi.rs"),
        ("MCKERNEL_IHKLIB_DIAGNOSTIC_ORIGINS_RS", "diagnostic_origins.rs"),
        ("MCKERNEL_IHKLIB_CREATE_DIAGNOSTIC_ORIGINS_RS", "create_diagnostic_origins.rs"),
    ]:
        environment[key] = str(output / name)
    archive = output / "libihklib_whole70.a"
    temporary_archive = output / "libihklib_whole70.a.new"
    argv = [args.rustc, "--edition=2021", "--crate-name", "ihklib_supported_whole70_host",
            "--crate-type", "staticlib", "--cfg", "ihklib_host_std_runtime", "--cfg",
            stat_cfg, "-C", "panic=abort", "-C", "codegen-units=1", "-C",
            "relocation-model=pic", "-C", "opt-level=2", "--print", "native-static-libs",
            "-o", str(temporary_archive), str(source / "libihklib_whole70.rs")]
    out, err = run(argv, "whole70-rust", environment)
    require(not out, "no compiler stdout")
    native = qualify_rust_diagnostics(err, source)
    require(temporary_archive.is_file() and temporary_archive.stat().st_size > 0,
            "actual Rust staticlib output")
    replace_bytes(output / "native-static-libs.rsp", ("\n".join(native) + "\n").encode())
    os.replace(temporary_archive, archive)
    replace_bytes(output / "producer-receipt.json", (json.dumps(dict(
        status="PASS_REAL_HEADERS_AND_ONE_RUST_STATICLIB_BUILD_ONLY", commands=rows,
        stat_cfg=stat_cfg, native_static_libs=native, archive=str(archive),
        C_runtime_TU=False, native=False), sort_keys=True, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()
