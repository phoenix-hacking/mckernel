"""V2 public-release regression: compiled native admission -> actual C -> parser."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/application-tests/native_resource_release_probe.c"
PARSER = ROOT / "scripts/application-tests/native_resource_release_capture.py"
HEADER = Path("/home/holden/mckernel-work/scratch/native-lifecycle-probe-source-20261017-1/compiled-3/include")

HARNESS = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static int mock_open(const char *, int);
static int mock_ioctl(int, unsigned long, unsigned long);
static int mock_close(int);
static long mock_read(int, void *, unsigned long);
#define RELEASE_OPEN mock_open
#define RELEASE_IOCTL mock_ioctl
#define RELEASE_CLOSE mock_close
#define RELEASE_READ mock_read
#define main release_main
#include "probe.c"
#undef main
/* Matched source 3f7b: ShutdownOnline commits Online/None; memory prepare_release_all
 * clears the OS owner into the reserved map. No CPU release remains necessary. */
static int scenario, call_index, device_memory_released, online_reads;
static int admission_status, admission_cpu, admission_mem, destroy_calls, release_calls;
static int mock_open(const char *path, int flags) {
    assert(flags & O_NOFOLLOW);
    if (!strcmp(path,"/dev/mcd0")) return 10;
    if (!strcmp(path,"/dev/mcos0")) return 11;
    assert(!strcmp(path,"/sys/devices/system/cpu/cpu1/online"));
    return 12;
}
static int mock_close(int fd) {
    assert(fd >= 10 && fd <= 12);
    if (0 && fd == 11) { errno=EIO; return -1; }
    return 0;
}
static long mock_read(int fd, void *buf, unsigned long size) {
    assert(fd == 12 && size == 3);
    char *s=buf; online_reads++; s[0]='1'; s[1]='\n';
    return 2;
}
static int mock_ioctl(int fd, unsigned long op, unsigned long arg) {
    static const unsigned long expected[] = {
        IHK_OS_QUERY_STATUS,IHK_DEVICE_QUERY_CPU,IHK_DEVICE_QUERY_MEM,
        IHK_OS_QUERY_CPU,IHK_OS_QUERY_MEM,IHK_DEVICE_DESTROY_OS,
        IHK_DEVICE_QUERY_CPU,IHK_DEVICE_QUERY_MEM,IHK_DEVICE_RELEASE_MEM,
        IHK_DEVICE_QUERY_CPU,IHK_DEVICE_QUERY_MEM};
    int index=call_index++;
    assert(index < 11 && op == expected[index]);
    assert(fd == ((index==0 || index==3 || index==4) ? 11 : 10));
    if (op == IHK_OS_QUERY_STATUS) return admission_status;
    if(op==IHK_OS_QUERY_CPU || op==IHK_OS_QUERY_MEM) {
        int value=op==IHK_OS_QUERY_CPU?admission_cpu:admission_mem;
        if((scenario==1 && op==IHK_OS_QUERY_CPU)||(scenario==2 && op==IHK_OS_QUERY_MEM)) value=0;
        if((scenario==3 && op==IHK_OS_QUERY_CPU)||(scenario==4 && op==IHK_OS_QUERY_MEM)) value=-5;
        if((scenario==5 && op==IHK_OS_QUERY_CPU)||(scenario==6 && op==IHK_OS_QUERY_MEM)) value=-2;
        if(value<0) {errno=-value;return -1;}
        return value;
    }
    if(op==IHK_DEVICE_DESTROY_OS) {destroy_calls++;if(scenario==7){errno=EBUSY;return -1;}}
    if(op==IHK_DEVICE_RELEASE_MEM) {release_calls++;if(scenario==8){errno=EBUSY;return -1;}}
    if (op == IHK_OS_QUERY_CPU || op == IHK_DEVICE_QUERY_CPU) {
        struct ihk_cpu_req *r=(void *)arg;
        assert(r->num_cpus == 0);
        
        return 0;
    }
    if (op == IHK_OS_QUERY_MEM || op == IHK_DEVICE_QUERY_MEM) {
        struct ihk_mem_req *r=(void *)arg;
        int owned=op == IHK_DEVICE_QUERY_MEM && !device_memory_released;
        assert(r->num_chunks == CAPACITY);
        r->num_chunks=owned ? 2 : 0;
        if (owned) {
            r->sizes[0]=64UL*1024*1024; r->sizes[1]=64UL*1024*1024;
            r->numa_ids[0]=0; r->numa_ids[1]=0;
            
        }
        return 0;
    }
    if (op == IHK_DEVICE_RELEASE_MEM) {
        struct ihk_mem_req *r=(void *)arg;
        assert(r->num_chunks==2 && r->sizes[0]+r->sizes[1]==BYTES);
        assert(r->numa_ids[0]==0 && r->numa_ids[1]==0);
        device_memory_released=1;
    } else { assert(op==IHK_DEVICE_DESTROY_OS && arg==0); }
    return 0;
}
int main(int argc,char **argv) {
    assert(argc==3);scenario=atoi(argv[1]);
    FILE *input=fopen(argv[2],"r");assert(input);
    assert(fscanf(input,"%d %d %d",&admission_status,&admission_cpu,&admission_mem)==3);
    assert(fclose(input)==0);
    char *args[]={"native-resource-release-probe",NULL};
    int rc=release_main(1,args);
    if(!scenario) assert(call_index==11 && online_reads==2 && destroy_calls==1 && release_calls==1);
    if(scenario>=1 && scenario<=6) assert(destroy_calls==0 && release_calls==0);
    return rc;
}
'''

class V2ActualBody(unittest.TestCase):
    def test_closed_source_body_to_actual_c_main_to_parser(self):
        case = Path(os.environ["RESOURCE_RELEASE_EVIDENCE"])
        case.mkdir(mode=0o700)
        env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL")}
        sequence = 0
        def capture(directory, label, argv, extra=None):
            actual_env = dict(env)
            if extra: actual_env.update(extra)
            (directory / (label + ".command.json")).write_text(json.dumps({"argv": argv, "env": actual_env, "cwd": str(directory)}, indent=2) + "\n")
            result = subprocess.run(argv, cwd=directory, env=actual_env, capture_output=True, timeout=90)
            (directory / (label + ".stdout")).write_bytes(result.stdout)
            (directory / (label + ".stderr")).write_bytes(result.stderr)
            (directory / (label + ".result.json")).write_text(json.dumps({"returncode": result.returncode}) + "\n")
            self.assertEqual(result.returncode, 0, (label, result.stderr))
            return result
        rust = case / "rust"; rust.mkdir(mode=0o700)
        base = Path("/home/holden/mckernel-work/scratch/nsd-c-79b00103de104607b182b374a2a396ae/modules")
        template = (ROOT / "scripts/tests/fixtures/ihk_os_runtime_compile.rs").read_text()
        template, private = template.split("// RUNTIME_PRIVATE_TESTS\n")
        private, registry = private.split("// REGISTRY_FIXTURE_FAULT\n")
        modules = []
        bindings = []
        for name in ("abi", "application_abi", "service_abi", "device_registry", "os_registry", "ihk_ioctl", "os_service", "os_runtime"):
            relative = {"abi": "abi/x86_64.rs", "application_abi": "abi/application.rs", "service_abi": "abi/os_service.rs"}.get(name, name + ".rs")
            source = base / relative
            data = source.read_bytes()
            bindings.append({"path": str(source), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
            out = rust / (name + ".rs")
            supplement = {"os_runtime": private, "os_registry": registry}.get(name, "")
            out.write_text(data.decode() + ("\n" + supplement if supplement else ""))
            attributes = '#[allow(unreachable_pub)]\n' if name == "abi" else ""
            modules.append(attributes + '#[path = "' + str(out) + '"]\nmod ' + name + ';')
        (rust / "bindings.json").write_text(json.dumps(bindings, indent=2) + "\n")
        fixture = template.replace("// SOURCE_MODULES", "\n".join(modules))
        fixture += "\n" + (ROOT / "scripts/tests/fixtures/native_resource_release_v2_admission.rs").read_text()
        (rust / "fixture.rs").write_text(fixture)
        rustc = "/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc"
        capture(rust, "compile", [rustc, "--edition=2021", "--test", "--cfg", "CONFIG_COMPAT", "-Wrust_2018_idioms", "-Dwarnings", "-Dunreachable-pub", "fixture.rs", "-o", "tests"], {"RUSTC_BOOTSTRAP": "1"})
        trace = rust / "native-admission.txt"
        capture(rust, "run-selected", [str(rust / "tests"), "--exact", "resource_v2_closed_admission_status_bypass", "--nocapture", "--test-threads=1"], {"NATIVE_RESOURCE_ADMISSION_TRACE": str(trace)})
        self.assertEqual(trace.read_bytes(), b"0 -16 -16\n")
        c = case / "c"; c.mkdir(mode=0o700)
        (c / "probe.c").write_bytes(SOURCE.read_bytes())
        (c / "harness.c").write_text(HARNESS)
        capture(c, "compile", ["/usr/bin/gcc", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror", "-I", str(HEADER), "harness.c", "-o", "harness"])
        spec = importlib.util.spec_from_file_location("v2_parser", PARSER)
        parser = importlib.util.module_from_spec(spec); spec.loader.exec_module(parser)
        for scenario in range(9):
            label = "scenario-%02d" % scenario
            argv = [str(c / "harness"), str(scenario), str(trace)]
            (c / (label + ".command.json")).write_text(json.dumps({"argv": argv, "env": env, "cwd": str(c)}, indent=2) + "\n")
            result = subprocess.run(argv, cwd=c, env=env, capture_output=True, timeout=20)
            (c / (label + ".stdout")).write_bytes(result.stdout)
            (c / (label + ".stderr")).write_bytes(result.stderr)
            (c / (label + ".result.json")).write_text(json.dumps({"returncode": result.returncode}) + "\n")
            self.assertEqual(result.returncode, 0 if scenario == 0 else 1, (scenario, result.stderr))
            if scenario == 0:
                self.assertEqual(parser.evaluate(result.stdout, result.stderr, result.returncode)["public_release_protocol"], "PASS")
                self.assertNotIn(b'"stage":"cpu_inventory","count":0,"cpus":[]}\n{"stage":"assigned', result.stdout)
            else:
                with self.assertRaises(ValueError): parser.evaluate(result.stdout, result.stderr, result.returncode)
                with self.assertRaises(ValueError): parser.evaluate(result.stdout, b"", 0)


class V2ParserOnly(unittest.TestCase):
    """Reuse retained actual-C output; no compiler or helper invocation."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("release_parser_only", PARSER)
        cls.parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.parser)
        cls.positive = Path("/home/holden/mckernel-work/scratch/native-resource-release-v2-20261017-1/compiled-1/c/scenario-00.stdout").read_bytes()
        cls.records = [json.loads(line) for line in cls.positive.splitlines()]

    def reject(self, stdout, stderr=b"", status=0):
        with self.assertRaises(ValueError):
            self.parser.evaluate(stdout, stderr, status)

    def test_actual_c_positive(self):
        self.assertLess(len(self.positive), 4096)
        self.assertEqual(self.parser.evaluate(self.positive, b"", 0),
                         {"public_release_protocol": "PASS", "native_execution_verified": False,
                          "resource_restoration_verified": False})

    def test_duplicate_keys(self):
        for old, new in [(b'"count":0', b'"count":1,"count":0'),
                         (b'"value":1', b'"value":0,"value":1'),
                         (b'"generation_verified":false', b'"generation_verified":true,"generation_verified":false'),
                         (b'"stage":"open_control"', b'"stage":"wrong","stage":"open_control"')]:
            self.assertIn(old, self.positive)
            self.reject(self.positive.replace(old, new, 1))

    def test_complete_lf_framing(self):
        for value in [self.positive[:-1], self.positive + b"\n",
                      self.positive.replace(b"\n", b"\r\n"), self.positive + b" ",
                      b"\n" + self.positive]:
            self.reject(value)

    def test_outer_capture_exact_types(self):
        for status in [False, True, 0.0, 1.0, "0", None]:
            self.reject(self.positive, status=status)
        for stdout in [self.positive.decode(), bytearray(self.positive), None, False]:
            self.reject(stdout)
        for stderr in ["", bytearray(), None, False]:
            self.reject(self.positive, stderr=stderr)

    def test_every_numeric_scalar_exact_type(self):
        cases = 0
        for index, record in enumerate(self.records):
            for field, item in record.items():
                if type(item) is not int:
                    continue
                for replacement in [float(item), bool(item)]:
                    rows = [dict(row) for row in self.records]
                    rows[index][field] = replacement
                    value = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
                    with self.subTest(row=index, field=field, replacement=replacement):
                        self.reject(value)
                    cases += 1
        self.assertGreater(cases, 100)

    def test_scope_exact_boolean_false(self):
        for field in ["physical_identity_verified", "generation_verified", "reboot_verified"]:
            for replacement in [0, 0.0, True, "false", None]:
                rows = [dict(row) for row in self.records]
                rows[-1][field] = replacement
                self.reject(("\n".join(json.dumps(row) for row in rows) + "\n").encode())

    def test_chunk_numeric_types_and_nonfinite(self):
        for old, replacement in [(b'[67108864,0]', b'[67108864.0,0]'),
                                 (b'[67108864,0]', b'[67108864,false]'),
                                 (b'"count":0', b'"count":NaN'),
                                 (b'"count":0', b'"count":Infinity')]:
            self.assertIn(old, self.positive)
            self.reject(self.positive.replace(old, replacement, 1))

if __name__ == "__main__":
    unittest.main(failfast=True)
