"""Current production create-OS C/Rust routing, using local observations only.

Default execution checks C then Rust serially with explicitly selected CC and
RUSTC. Callbacks observe indices/error ordering and genuine libc ownership;
this does not qualify real IHK providers, devices, or native creation.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(os.environ.get("M15_REPO", Path(__file__).resolve().parents[2]))
FIXTURES = Path(__file__).resolve().parent / "fixtures/m15-create-os-routing"


def selected_languages():
    selected = os.environ.get("M15_ROUTING_LANGUAGE")
    if selected is None:
        return ("c", "rust")
    if selected not in ("c", "rust"):
        raise ValueError("M15_ROUTING_LANGUAGE must be c or rust")
    return (selected,)


def selected_sources(baseline, root=ROOT):
    if baseline:
        # Historical behavior is opt-in and must bind both explicit snapshots.
        return (Path(os.environ["M15_ROUTING_C_SOURCE"]),
                Path(os.environ["M15_ROUTING_RUST_SOURCE"]))
    return (root / "ihk/linux/user/ihklib.c",
            root / "ihk/linux/user/rust/whole70/ihklib_create_os_environment.rs")


def render_c_source(source, observer, baseline):
    start = source.index("static int os_assign_cpu_all(")
    end = source.index("static int os_release_cpu_all(", start)
    helpers = source[start:end]
    main = source.index("int ihk_create_os_str(")
    phase_start = re.search(r"\bret\s*=\s*os_assign_cpu_all\(", source[main:]).start() + main
    phase_start = source.rfind("\n", 0, phase_start) + 1
    phase_end = source.index("\n\tfor (i = 0; i < num_env; i++) {", phase_start)
    phase = source[phase_start:phase_end]
    header = helpers[helpers.index("static int os_assign_mem_all("):]
    header = header[:header.index("{")]
    memory_call = ("os_assign_mem_all(dev_index,os_index,NULL)" if "dev_index" in header
                   else "os_assign_mem_all(os_index,NULL)")
    defines = "\n#define dprintf(...) ((void)0)\n#define calloc observation_calloc\n#define free observation_free\n"
    aliases = [
        ("ihk_get_num_reserved_cpus", "observation_reserved_cpu_count"),
        ("ihk_query_cpu", "observation_query_cpu"),
        ("ihk_os_assign_cpu", "observation_assign_cpu"),
        ("ihk_get_num_reserved_mem_chunks", "observation_reserved_mem_count"),
        ("ihk_query_mem", "observation_query_mem"),
        ("ihk_os_assign_mem", "observation_assign_mem"),
    ]
    defines += "".join("#define " + name + " " + target + "\n" for name, target in aliases)
    return (observer + defines + helpers
            + "\nstatic int phase(int dev_index,int os_index){(void)dev_index;int ret;char *err_msg=NULL;\n"
            + phase + "\nout:return ret;}\nstatic int memory(int dev_index,int os_index){(void)dev_index;return "
            + memory_call + ";}\nint main(void){return observation_run("
            + str(int(baseline)) + ",phase,memory);}\n")


def render_rust_source(source, template):
    start = source.index("unsafe fn cpu_all(")
    end = source.index("unsafe fn release_assigned_cpu(", start)
    helpers = source[start:end]
    published = source.index("output_index.write(index)")
    phase_start = re.search(r"let\s+value\s*=\s*unsafe\s*\{\s*cpu_all\(", source[published:]).start() + published
    phase_start = source.rfind("\n", 0, phase_start) + 1
    phase_end = source.index("        for i in 0..count as usize {", phase_start)
    phase = source[phase_start:phase_end]
    header = helpers[helpers.index("unsafe fn memory_all("):]
    header = header[:header.index("{")]
    memory_call = ("unsafe{memory_all(device,index,null_mut())}"
                   if re.search(r"fn memory_all\(\s*device\s*:", header)
                   else "unsafe{memory_all(index,null_mut())}")
    return (template.replace("__HELPERS__", helpers).replace("__PHASE__", phase)
            .replace("__MEMORY_CALL__", memory_call))


class M15CreateOsRoutingTests(unittest.TestCase):
    def test_actual_assignment_routes(self):
        compilers = {}
        for name in ("CC", "RUSTC"):
            self.assertIn(name, os.environ, "Explicitly bind the admitted " + name)
            compiler = Path(os.environ[name])
            self.assertTrue(compiler.is_absolute() and compiler.is_file(),
                            name + " must identify an existing absolute compiler file")
            compilers[name] = str(compiler)
        baseline = os.environ.get("M15_ROUTING_BASELINE_ONLY") == "1"
        languages = selected_languages()
        for language in languages:
            # Propagate the first compile/run failure before another language runs.
            self.check_language(language, baseline, compilers, len(languages) > 1)

    def check_language(self, language, baseline, compilers, both):
        c_path, rust_path = selected_sources(baseline)
        # Read the current production files for each language invocation.
        c_source, rust_source = c_path.read_text(), rust_path.read_text()
        observer = Path(os.environ.get("M15_ROUTING_OBSERVER", FIXTURES / "observations.c"))
        template = Path(os.environ.get("M15_ROUTING_RUST_TEMPLATE", FIXTURES / "rust.rs.in"))
        with tempfile.TemporaryDirectory(prefix="m15-routing-", dir=os.environ.get("TMPDIR")) as directory:
            work = Path(directory)
            binary = work / "routing"
            includes = ["-I" + str(ROOT / "ihk/linux/include"),
                        "-I" + str(ROOT / "ihk/linux/include/ihk/arch/x86_64")]
            if language == "c":
                unit = work / "routing.c"
                unit.write_text(render_c_source(c_source, observer.read_text(), baseline))
                artifacts = [unit, binary]
                commands = [("c-compile", [compilers["CC"], "-std=gnu11", "-Wall", "-Wextra",
                                          "-Werror", *includes, str(unit), "-o", str(binary)])]
            else:
                unit = work / "routing.rs"
                unit.write_text(render_rust_source(rust_source, template.read_text()))
                object_file = work / "observations.o"
                artifacts = [unit, object_file, binary]
                commands = [
                    ("observer-compile", [compilers["CC"], "-std=gnu11", "-Wall", "-Wextra",
                                          "-Werror", *includes, "-c", str(observer), "-o", str(object_file)]),
                    ("rust-compile", [compilers["RUSTC"], "--edition=2021", "-Dwarnings", str(unit),
                                      "-C", "link-arg=" + str(object_file), "-o", str(binary)]),
                ]
            receipt = None
            if os.environ.get("M15_ROUTING_RECEIPT_DIR"):
                receipt = Path(os.environ["M15_ROUTING_RECEIPT_DIR"])
                if both:
                    receipt /= language
                receipt.mkdir(parents=True, exist_ok=False)
            rows = []
            commands.append(("routing-run", [str(binary)]))
            for label, argv in commands:
                result = subprocess.run(argv, capture_output=True, text=True)
                if receipt:
                    rows.append({"label": label, "argv": argv, "returncode": result.returncode})
                    (receipt / "commands.json").write_text(json.dumps(rows, indent=2) + "\n")
                    (receipt / (label + ".stdout")).write_text(result.stdout)
                    (receipt / (label + ".stderr")).write_text(result.stderr)
                    hashes = {}
                    for artifact in artifacts:
                        if artifact.is_file():
                            shutil.copyfile(artifact, receipt / artifact.name)
                            hashes[artifact.name] = hashlib.sha256(artifact.read_bytes()).hexdigest()
                    (receipt / "artifacts.json").write_text(json.dumps(hashes, indent=2) + "\n")
                self.assertEqual(result.returncode, 0, repr(argv) + "\n" + result.stdout + result.stderr)
                if label == "routing-run":
                    expected = ("baseline routing checks=2 wrong-device-indices-observed\n" if baseline else
                                "candidate routing checks=9 device-count-query=0 assign-os=1 default0-0-preserved\n")
                    self.assertEqual(result.stdout, expected)


if __name__ == "__main__":
    unittest.main()
