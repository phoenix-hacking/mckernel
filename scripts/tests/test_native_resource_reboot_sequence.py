"""Actual two helper mains with shared injected state, never host devices."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "scripts/application-tests"
OLD = Path("/home/holden/mckernel-work/scratch/native-boot-running-prerequisite-20261017-1")
HEADER = Path("/home/holden/mckernel-work/scratch/native-lifecycle-probe-source-20261017-1/compiled-3/include")
RESOURCE = APP / "native_resource_release_probe.c"
DELIMITER = b"ND_REFERENCE_RESOURCE_END\n"

# Persistent state starts at the matched successful shutdown boundary. Actual
# resource main must destroy/release it before actual strict5 boot main runs.
STATE = r'''
#include <errno.h>
#include <time.h>
static int scenario, os_exists=1, reserved_cpu, reserved_memory=1, assigned_cpu, assigned_memory;
static int resource_calls, second_boot_entered, destroy_calls, release_calls;
static int admission_status, admission_cpu, admission_mem;
int actual_resource_main(int,char **);
int cycle_open(const char *p,int flags) {
    assert(flags & O_NOFOLLOW);
    if (!strcmp(p,"/dev/mcd0")) return 20;
    if (!strcmp(p,"/dev/mcos0")) { assert(os_exists); return 21; }
    assert(!strcmp(p,"/sys/devices/system/cpu/cpu1/online")); return 22;
}
int cycle_close(int fd) {assert(fd>=20 && fd<=22);return 0;}
long cycle_read(int fd,void *p,unsigned long n) {
    assert(fd==22 && n==3 && !reserved_cpu);memcpy(p,"1\n",2);return 2;
}
int cycle_ioctl(int fd,unsigned long op,unsigned long arg) {
    resource_calls++;
    if (op==OS_STATUS) {assert(fd==21 && os_exists);return admission_status;}
    if (op==OS_QUERY_CPU || op==OS_QUERY_MEM) {
        assert(fd==21 && os_exists);
        int value=op==OS_QUERY_CPU?admission_cpu:admission_mem;
        if ((scenario==6 && op==OS_QUERY_CPU)||(scenario==7 && op==OS_QUERY_MEM)) value=0;
        if(value<0) {errno=-value;return -1;} return value;
    }
    if (op==QUERY) {
        struct request *r=(void *)arg;assert(r->count==0);return 0;
    }
    if (op==MEM_QUERY) {
        struct memory_request *r=(void *)arg;assert(r->count==4096);
        r->count=(op==MEM_QUERY && reserved_memory)?2:0;
        if (r->count) {r->sizes[0]=r->sizes[1]=64*MIB;r->nodes[0]=r->nodes[1]=0;}
        return 0;
    }
    if (op==OS_DESTROY) {assert(fd==20 && arg==0 && os_exists);os_exists=0;destroy_calls++;return 0;}
    assert(fd==20 && op==MEM_RELEASE && !os_exists && reserved_memory);
    struct memory_request *r=(void *)arg;
    assert(r->count==2 && r->sizes[0]+r->sizes[1]==128*MIB);
    if (scenario==5) {errno=EBUSY;return -1;}
    reserved_memory=0;release_calls++;return 0;
}
static unsigned long long now_ns(void) {
    struct timespec value;assert(clock_gettime(CLOCK_MONOTONIC,&value)==0);
    return (unsigned long long)value.tv_sec*1000000000ULL+(unsigned long long)value.tv_nsec;
}
'''

TRANSITIONS = r'''
    if (step==0) {
        if (reserved_cpu) return -EBUSY;
        assert(!assigned_cpu);reserved_cpu=1;
    }
    if (step==1) {
        if (scenario==3) return -ENOMEM;
        assert(!reserved_memory && !assigned_memory);reserved_memory=1;
    }
    if (step==2) {
        if (os_exists) return 1;
        os_exists=1;
    }
    if (step==6) {assert(os_exists && reserved_cpu);reserved_cpu=0;assigned_cpu=1;}
    if (step==7) {assert(os_exists && reserved_memory);reserved_memory=0;assigned_memory=1;}
    if (step==9) {assert(assigned_cpu && assigned_memory && os_exists);second_boot_entered=1;}
'''

MAIN = r'''
int main(int argc,char **argv) {
    assert(argc==5);scenario=atoi(argv[1]);
    FILE *trace=fopen(argv[4],"r");assert(trace);
    assert(fscanf(trace,"%d %d %d",&admission_status,&admission_cpu,&admission_mem)==3);
    assert(fclose(trace)==0);observed_status=scenario==4?4:5;
    kernel_log_path=argv[2];
    char *resource_argv[]={"native-resource-release-probe",NULL};
    int rc=actual_resource_main(1,resource_argv);
    if(rc) {assert(!second_boot_entered);
        if(scenario==6 || scenario==7) assert(!destroy_calls && !release_calls);
        return rc;}
    unsigned long long released=now_ns();
    assert(resource_calls==11 && !os_exists && !reserved_cpu && !reserved_memory);
    assert(fputs("ND_REFERENCE_RESOURCE_END\n",stdout)>=0 && fflush(stdout)==0);
    if(scenario==1) os_exists=1;
    if(scenario==2) reserved_cpu=1;
    unsigned long long started=now_ns();
    rc=actual_boot_main();
    unsigned long long finished=now_ns();
    assert(!rc && second_boot_entered && assigned_cpu && assigned_memory && os_exists);
    assert(ioctl_calls==16 && naps==2 && service_reads==66 && service_eofs==66 && stores==64);
    for(int fd=10;fd<next_fd;fd++) assert(!descriptors[fd].live);
    FILE *out=fopen(argv[3],"wx");assert(out);
    assert(fprintf(out,"[%llu,%llu,%llu]\n",released,started,finished)>0);
    assert(fclose(out)==0);return rc;
}
'''


def literal_harness():
    tree = ast.parse((ROOT / "scripts/tests/test_native_boot_running.py").read_text())
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "HARNESS" for t in node.targets))


class PersistentActualMain(unittest.TestCase):
    def test_release_then_same_strict5_helper(self):
        case = Path(os.environ["RESOURCE_REBOOT_EVIDENCE"])
        case.mkdir(mode=0o700)
        helper = OLD / "source/native-boot-running.c"
        self.assertEqual(hashlib.sha256(helper.read_bytes()).hexdigest(), "6a39824cdcde3ddfa3508d3c229f195f6ecbe5a07d57eb748890d452cc729e03")
        self.assertEqual(hashlib.sha256(RESOURCE.read_bytes()).hexdigest(), "d87df88114863cc439e8a3931c80e369f77e4e4ffc6aee48cb9efe6afb7e91c2")
        binding = json.loads((OLD / "bindings.json").read_text())
        for entry in binding["source_bindings"]:
            p = Path(entry["staged"])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), entry["sha256"])
            (case / p.name).write_bytes(p.read_bytes())
        body = (case / "native-cpu-reservation.c").read_text()
        start = body.index('__asm__(".global _start')
        end = body.index('\n#else', start)
        (case / "native-cpu-reservation.c").write_text(body[:start] + "static long call(long nr,long a,long b,long c);\n" + body[end:])
        (case / "actual-helper.c").write_text(helper.read_text().replace("int main(void)\n{", "int actual_boot_main(void)\n{", 1))
        harness = literal_harness().replace('"HELPER_SOURCE"', '"actual-helper.c"')
        harness = harness.replace("static long fake_ioctl", STATE + "\nstatic long fake_ioctl", 1)
        anchor = "assert(fd==((step<=2 || step==15)?10:11) && descriptors[fd].live);"
        self.assertEqual(harness.count(anchor), 1)
        harness = harness.replace(anchor, anchor + TRANSITIONS, 1)
        start = harness.index("    if (number==SYS_EXIT)")
        end = harness.index('    assert(!"unreviewed syscall")', start)
        harness = harness[:start] + "    if(number==SYS_EXIT) {assert(fflush(stdout)==0);_Exit((int)a);}\n" + harness[end:]
        harness = harness[:harness.index("int main(int argc,char **argv)")] + MAIN
        (case / "harness.c").write_text(harness)
        (case / "probe.c").write_bytes(RESOURCE.read_bytes())
        (case / "resource-unit.c").write_text('''#define _GNU_SOURCE
#include <errno.h>
int cycle_open(const char *,int);int cycle_ioctl(int,unsigned long,unsigned long);
int cycle_close(int);long cycle_read(int,void *,unsigned long);
#define RELEASE_OPEN cycle_open
#define RELEASE_IOCTL cycle_ioctl
#define RELEASE_CLOSE cycle_close
#define RELEASE_READ cycle_read
#define main actual_resource_main
#include "probe.c"
''')
        env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL")}

        def capture(name, argv):
            (case / (name + ".command.json")).write_text(json.dumps({"argv": argv, "env": env, "cwd": str(case)}, indent=2) + "\n")
            result = subprocess.run(argv, cwd=case, env=env, capture_output=True, timeout=30)
            (case / (name + ".stdout")).write_bytes(result.stdout)
            (case / (name + ".stderr")).write_bytes(result.stderr)
            (case / (name + ".result.json")).write_text(json.dumps({"returncode": result.returncode}) + "\n")
            return result

        argv = ["/usr/bin/gcc", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror", "-static", "-fno-pie", "-no-pie", "-Wl,-z,noexecstack", "-I", str(HEADER), "-DCPUHP_FAILURE_STATE=234", "-DNATIVE_VDSO_REV3=1", "-DNATIVE_SYSFS_OS=1", "-DNATIVE_SYSFS_SETUP=1", "-DNATIVE_SYSFS_SERVICE=1", "-DNATIVE_MCCTRL_SERVICE=1", "-DBOOT_PREPARE_ONLY=0", "-DEXPECTED_STATUS=5", '-DTEST_KMSG_DEFAULT="unused"', "harness.c", "resource-unit.c", "-o", "harness"]
        result = capture("compile", argv)
        self.assertEqual(result.returncode, 0, result.stderr)
        sys.path.insert(0, str(APP))
        import native_resource_reboot_sequence as sequence
        trace = Path("/home/holden/mckernel-work/scratch/native-resource-release-v2-20261017-1/compiled-1/rust/native-admission.txt")
        self.assertEqual(trace.read_bytes(), b"0 -16 -16\n")
        for scenario in range(8):
            name = "scenario-%d" % scenario
            kmsg = case / (name + ".kmsg")
            times = case / (name + ".timestamps.json")
            result = capture(name, [str(case / "harness"), str(scenario), str(kmsg), str(times), str(trace)])
            self.assertEqual(result.returncode, 0 if scenario == 0 else 1, (scenario, result.stderr))
            self.assertEqual(result.stderr, b"")
            if scenario == 0:
                release, reboot = result.stdout.split(DELIMITER)
                timing = json.loads(times.read_text())
                args = [release, b"", 0, reboot, b"", 0, kmsg.read_bytes(), *timing]
                self.assertEqual(sequence.evaluate(*args)["public_release_then_strict5_boot_protocol"], "PASS")
                for index, bad in [(5, False), (5, 0.0), (6, b""), (6, sequence.BOOT_KMSG * 2), (3, reboot.replace(b"observed=5", b"observed=4")), (8, timing[0]), (7, True)]:
                    changed = list(args); changed[index] = bad
                    with self.assertRaises(ValueError): sequence.evaluate(*changed)
            elif scenario < 5:
                self.assertIn(DELIMITER, result.stdout)
                self.assertIn(b"FAIL", result.stdout.split(DELIMITER)[1])
            else:
                self.assertNotIn(DELIMITER, result.stdout)


class RetainedSequenceOracle(unittest.TestCase):
    def test_fresh_kernel_range_and_join_without_replaying_helpers(self):
        case = Path("/home/holden/mckernel-work/scratch/native-resource-reboot-sequence-20261017-2/compiled-1")
        sys.path.insert(0, str(APP))
        import native_resource_reboot_sequence as sequence
        release, reboot = (case / "scenario-0.stdout").read_bytes().split(DELIMITER)
        timing = json.loads((case / "scenario-0.timestamps.json").read_text())
        actual_marker = (case / "scenario-0.kmsg").read_bytes()
        self.assertEqual(actual_marker, sequence.BOOT_KMSG)
        # Synthetic first-boot prefix plus exact retained second-helper write:
        # tests cursor extraction only, never proof of an actual kernel log.
        before = sequence.BOOT_KMSG
        after = before + actual_marker
        observed = sequence.second_boot_status(before, after)
        args = [release, b"", 0, reboot, b"", 0, observed, *timing]
        self.assertEqual(sequence.evaluate(*args)["public_release_then_strict5_boot_protocol"], "PASS")
        timestamped = before + b"<6>[   123.456789] " + actual_marker[len(b"<6>"):]
        self.assertEqual(sequence.second_boot_status(before, timestamped), sequence.BOOT_KMSG)
        for left, right in [(before, before), (before, after + actual_marker),
                            (before, b"wrapped\n" + actual_marker), (before, after[:-1]),
                            (before, after.replace(b"observed=5", b"observed=4")),
                            (before, after.replace(b"\n", b"\r\n")),
                            (False, after), (before, b"x" * 262144)]:
            with self.assertRaises(ValueError): sequence.second_boot_status(left, right)
        for index, value in [(0, release[:-1]), (2, False), (2, 0.0), (5, False),
                             (5, 0.0), (6, b""), (6, actual_marker * 2),
                             (3, reboot.replace(b"observed=5", b"observed=4")),
                             (8, timing[0]), (7, True), (9, float(timing[2]))]:
            changed = list(args); changed[index] = value
            with self.assertRaises(ValueError): sequence.evaluate(*changed)


if __name__ == "__main__":
    unittest.main(failfast=True)
