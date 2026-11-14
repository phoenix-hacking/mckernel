"""Actual captured boot-helper main under syscall stubs; never a live boot.

Requires explicit scratch source/bindings/evidence paths. Only x86_64 entry and
raw syscall boundaries are replaced in test copies; boot assertions execute.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include "HELPER_SOURCE"
struct fake_descriptor { int live, kind, reads, host_fd; };
static struct fake_descriptor descriptors[512];
static int next_fd=10, ioctl_calls, naps, service_reads, service_eofs, stores, closed;
static int observed_status, log_fault;
static const char *kernel_log_path=TEST_KMSG_DEFAULT;
static int fake_open(const char *path, long flags)
{
    int kind=0;
    if (!strcmp(path,"/dev/mcd0")) { assert(next_fd==10 && flags==2); kind=1; }
    else if (!strcmp(path,"/dev/mcos0")) { assert(next_fd==11 && flags==2); kind=2; }
    else if (!strcmp(path,"/sys/class/mcos/mcos0/sys")) { assert(flags==0);kind=3; }
    else if (!strcmp(path,"/sys/class/mcos/mcos0/sys/setup_complete")) { assert(flags==0);kind=4; }
    else if (!strcmp(path,"/sys/devices/system/cpu/online")) { assert(flags==0);kind=5; }
    else if (!strcmp(path,"/sys/devices/system/cpu/cpu1/online")) { assert(flags==0);kind=6; }
    else if (!strcmp(path,"/sys/devices/system/cpu/cpu2/online")) { assert(flags==0);kind=7; }
    else if (!strcmp(path,"/sys/devices/system/cpu/cpu3/online")) { assert(flags==0);kind=8; }
    else if (!strcmp(path,"/sys/class/mcos/mcos0/sys/devices/system/cpu/num_processors")) { assert(flags==0);kind=9; }
    else if (!strcmp(path,"/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online")) { assert(flags==0 || flags==1);kind=flags?11:10; }
    int host_fd=-1;
    if (!strcmp(path,"/dev/kmsg")) {
        assert(flags==0xa0001 && EXPECTED_STATUS==5);
        if (log_fault==1) return -13;
        host_fd=open(kernel_log_path,O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC|O_NOFOLLOW,0600);
        assert(host_fd>=0);kind=12;
    }
    assert(kind && next_fd<512);
    descriptors[next_fd]=(struct fake_descriptor){1,kind,0,host_fd};
    return next_fd++;
}
static long fake_ioctl(long fd, unsigned long request_number, long argument)
{
    static const unsigned long requests[]={RESERVE,MEM_RESERVE,OS_CREATE,
        0x30a02907,0x30a0290c,OS_KARGS,OS_ASSIGN_CPU,OS_ASSIGN_MEM,OS_LOAD,
        OS_BOOT,OS_STATUS,OS_KARGS,OS_BOOT,OS_RELEASE_CPU,OS_RELEASE_MEM,OS_DESTROY};
    int step=ioctl_calls++;
    assert(step<16 && request_number==requests[step]);
    assert(fd==((step<=2 || step==15)?10:11) && descriptors[fd].live);
    if (step==0 || step==6 || step==13) {
        struct request *r=(struct request *)argument;
        assert(r->count==1 && r->cpus && r->cpus[0]==1);
        return step==13?-EBUSY:0;
    }
    if (step==1 || step==7 || step==14) {
        struct memory_request *r=(struct memory_request *)argument;
        assert(r->count==1 && r->sizes[0]==128*MIB && r->nodes[0]==0);
        assert(r->minimum==4*1024*1024 && r->ratio==95 && r->timeout==30);
        return step==14?-EBUSY:0;
    }
    if (step==5 || step==11) {
        assert(!strcmp((const char *)argument,step==5?"hidos allow_oversubscribe":"changed"));
        return step==11?-EBUSY:0;
    }
    if (step==8) { assert(!strcmp((const char *)argument,"/images/mckernel.img"));return 0; }
    assert(argument==0);
    if (step==10) return observed_status;
    return (step==3 || step==4 || step==12 || step==15)?-EBUSY:0;
}
static long call(long number,long a,long b,long c)
{
    if (number==SYS_OPEN) { assert(c==0);return fake_open((const char *)a,b); }
    if (number==SYS_IOCTL) return fake_ioctl(a,(unsigned long)b,c);
    if (number==SYS_WRITE && a==1) {
        assert(c>0 && c<512);
        assert(fwrite((const void *)b,1,(size_t)c,stdout)==(size_t)c);
        return c;
    }
    if (number==SYS_READ) {
        assert(a>=12 && a<next_fd && descriptors[a].live);
        struct fake_descriptor *d=&descriptors[a];
        if (d->kind>=5 && d->kind<=8) {
            assert(c==1 && d->reads++==0);
            *(char *)b=d->kind<=6?'0':'1';return 1;
        }
        assert((d->kind==9 || d->kind==10) && c==32 && d->reads<2);
        if (d->reads++==0) { ((char *)b)[0]='1';((char *)b)[1]='\n';service_reads++;return 2; }
        service_eofs++;return 0;
    }
    if (number==SYS_WRITE && a>=12 && a<next_fd && descriptors[a].kind==12) {
        assert(descriptors[a].live && c>0 && c<128);
        char expected[128];
        int n=snprintf(expected,sizeof expected,"<6>NATIVE_BOOT_STATUS x86_64 observed=%d expected=5\n",observed_status);
        assert(c==n && !memcmp((const void *)b,expected,(size_t)c));
        if (log_fault==2) return -5;
        assert(write(descriptors[a].host_fd,(const void *)b,(size_t)c)==c);return c;
    }
    if (number==SYS_WRITE) {
        assert(a>=12 && a<next_fd && descriptors[a].live && descriptors[a].kind==11);
        assert(c==2 && ((char *)b)[0]==(stores%2?'1':'0') && ((char *)b)[1]=='\n');
        stores++;return c;
    }
    if (number==SYS_CLOSE) {
        assert(a>=10 && a<next_fd && descriptors[a].live && b==0 && c==0);
        if (descriptors[a].kind==9 || descriptors[a].kind==10) assert(descriptors[a].reads==2);
        if (descriptors[a].kind>=5 && descriptors[a].kind<=8) assert(descriptors[a].reads==1);
        if (descriptors[a].kind==12) assert(close(descriptors[a].host_fd)==0);
        descriptors[a].live=0;closed++;return 0;
    }
    if (number==SYS_NANOSLEEP) {
        const long *delay=(const long *)a;
        assert(delay[0]==10 && delay[1]==0 && b==0 && c==0 && ioctl_calls==15 && naps<2);
        naps++;return 0;
    }
    if (number==SYS_DELETE_MODULE) {
        assert(!strcmp((const char *)a,"ihk_smp_x86_64") && b==2048 && c==0);
        assert(ioctl_calls==16 && !descriptors[10].live && !descriptors[11].live);
        return -EAGAIN;
    }
    if (number==SYS_EXIT) {
        assert(a==1 && b==0 && c==0 && (observed_status!=EXPECTED_STATUS || log_fault));
        assert(ioctl_calls==11 && naps==0);
        int logged=(EXPECTED_STATUS==5 && log_fault!=1);
        assert(next_fd==(logged?13:12) && closed==(logged?1:0));
        assert(service_reads==0 && service_eofs==0 && stores==0);
        assert(fflush(stdout)==0);_Exit(1);
    }
    assert(!"unreviewed syscall");return -999;
}
int main(int argc,char **argv)
{
    assert(argc>=2 && argc<=4);observed_status=atoi(argv[1]);
    if (argc>=3) kernel_log_path=argv[2];
    if (argc==4) { log_fault=!strcmp(argv[3],"open")?1:2;assert(!strcmp(argv[3],"open") || !strcmp(argv[3],"write")); }
    struct stat out_stat,err_stat;
    assert(fstat(1,&out_stat)==0 && fstat(2,&err_stat)==0);
    assert(S_ISFIFO(out_stat.st_mode) && S_ISFIFO(err_stat.st_mode) && out_stat.st_ino!=err_stat.st_ino);
    int rc=actual_boot_main();
    assert(observed_status==EXPECTED_STATUS && rc==0);
    assert(ioctl_calls==16 && next_fd==(EXPECTED_STATUS==5?151:150) && closed==(EXPECTED_STATUS==5?141:140));
    assert(naps==2 && service_reads==66 && service_eofs==66 && stores==64);
    for (int fd=10;fd<next_fd;fd++) assert(!descriptors[fd].live);
    return rc;
}
'''


@unittest.skipUnless(os.environ.get("NATIVE_BOOT_RUNNING_EVIDENCE"),
                     "requires explicitly admitted private scratch helper fixture")
class RunningBootHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=Path(os.environ["NATIVE_BOOT_RUNNING_EVIDENCE"])
        cls.out.mkdir(mode=0o700,exist_ok=False)
        cls.source=Path(os.environ["NATIVE_BOOT_RUNNING_SOURCE"])
        cls.binding=json.loads(Path(os.environ["NATIVE_BOOT_RUNNING_BINDINGS"]).read_text())
        cls.env={"PATH":"/usr/bin:/bin","LANG":"C","LC_ALL":"C","TZ":"UTC"}
        for key in ("HOME","TMPDIR"):
            p=Path(os.environ[key]);p.relative_to(cls.out.parent.resolve(strict=True))
            if p.resolve(strict=True)!=p or not p.is_dir() or p.stat().st_uid!=os.getuid() or p.stat().st_mode&0o077:
                raise RuntimeError("private environment directory mismatch")
            cls.env[key]=str(p)
        cls.sequence=0
        cls.binaries={}
        for selection,expected in (("legacy",4),("running",5)):
            directory=cls.out/selection;directory.mkdir(mode=0o700)
            for row in cls.binding["source_bindings"]:
                p=Path(row["staged"])
                if hashlib.sha256(p.read_bytes()).hexdigest()!=row["sha256"]:
                    raise RuntimeError("captured dependency drift")
                (directory/p.name).write_bytes(p.read_bytes())
            chosen=cls.source if selection=="running" else cls.source.parent/"native-boot.c"
            text=chosen.read_text()
            anchor="int main(void)\n{"
            if text.count(anchor)!=1:
                raise RuntimeError("helper main anchor changed")
            staged=directory/"actual-helper.c"
            staged.write_text(text.replace(anchor,"int actual_boot_main(void)\n{",1))
            cpu=directory/"native-cpu-reservation.c"
            body=cpu.read_text();start=body.index('__asm__(".global _start');end=body.index('\n#else',start)
            # Exact x86_64 entry/syscall boundary only; all helper bodies remain.
            cpu.write_text(body[:start]+"static long call(long nr,long a,long b,long c);\n"+body[end:])
            harness=directory/"harness.c"
            harness.write_text(HARNESS.replace("HELPER_SOURCE",str(staged)))
            binary=directory/"harness"
            cls.binaries[selection]=binary
            result=cls.capture(["/usr/bin/gcc","-std=gnu11","-O2","-Wall","-Wextra","-Werror",
                "-static","-fno-pie","-no-pie","-Wl,-z,noexecstack",
                "-DCPUHP_FAILURE_STATE=234","-DNATIVE_VDSO_REV3=1","-DNATIVE_SYSFS_OS=1",
                "-DNATIVE_SYSFS_SETUP=1","-DNATIVE_SYSFS_SERVICE=1","-DNATIVE_MCCTRL_SERVICE=1",
                "-DBOOT_PREPARE_ONLY=0","-DEXPECTED_STATUS="+str(expected),
                "-DTEST_KMSG_DEFAULT="+json.dumps(str(cls.out/"helper-default-kmsg.log")),str(harness),"-o",str(binary)])
            if result.returncode:
                raise RuntimeError("actual-main compile failed; stop retained evidence")

    @classmethod
    def capture(cls,argv):
        cls.sequence+=1;stem=cls.out/f"{cls.sequence:03d}"
        stem.with_suffix(".command.json").write_text(json.dumps(dict(argv=argv,environment=cls.env),indent=2)+"\n")
        try:r=subprocess.run(argv,env=cls.env,capture_output=True,timeout=20)
        except subprocess.TimeoutExpired as exc:
            stem.with_suffix(".stdout").write_bytes(exc.stdout or b"")
            stem.with_suffix(".stderr").write_bytes(exc.stderr or b"")
            stem.with_suffix(".json").write_text(json.dumps(dict(timeout_seconds=20))+"\n");raise
        stem.with_suffix(".stdout").write_bytes(r.stdout);stem.with_suffix(".stderr").write_bytes(r.stderr)
        stem.with_suffix(".json").write_text(json.dumps(dict(returncode=r.returncode,stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),stderr_sha256=hashlib.sha256(r.stderr).hexdigest()),indent=2)+"\n")
        return r

    def test_only_status_contract_and_diagnostic_change(self):
        original=(self.source.parent/"native-boot.c").read_text()
        self.assertEqual(self.source.read_text(),original.replace(self.binding["replaced_anchor"],self.binding["replacement"],1).replace(self.binding["function_anchor"],self.binding["inserted_function"]+self.binding["function_anchor"],1))
        self.assertEqual(self.source.read_text().count("require("),original.count("require(")+3)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),self.binding["running_source_sha256"])

    def run_scenario(self,selection,status):
        result=self.capture([str(self.binaries[selection]),str(status)])
        expected=5 if selection=="running" else 4
        positive=status==expected
        self.assertEqual(result.returncode,0 if positive else 1,(selection,status))
        self.assertEqual(result.stderr,b"",(selection,status))
        text="NATIVE_MCCTRL_PREREADY x86_64 PASS rejected=2\nNATIVE_BOOT_SERVICE x86_64 boot_errno=0\n"
        if selection=="running":text+=f"NATIVE_BOOT_STATUS x86_64 observed={status} expected=5\n"
        if positive:
            text+=("NATIVE_BOOT_CAPTURE x86_64 ready\n"
                   "NATIVE_SYSFS_SERVICE x86_64 PASS read_checks=66 store_checks=64 rounds=32\n"
                   "NATIVE_BOOT_CAPTURE x86_64 ready\n"
                   "NATIVE_BOOT_START x86_64 CAPTURED ready=1 resources_retained=1\n"
                   "NATIVE_OS_SYSFS x86_64 PASS checks=2 setup_completed=1\n")
        else:
            source=self.source if selection=="running" else self.source.parent/"native-boot.c"
            anchor="require(observed_status == 5);" if selection=="running" else "require(call(SYS_IOCTL, os, OS_STATUS, 0) == 4);"
            line=next(i for i,row in enumerate(source.read_text().splitlines(),1) if anchor in row)
            text+=f"NATIVE_OS_RESOURCE x86_64 FAIL\nNATIVE_CPU_RESERVATION x86_64 FAIL line={line}\n"
        self.assertEqual(result.stdout,text.encode(),(selection,status))

    def test_kmsg_open_failure_rejects_helper(self):
        self.run_log_failure("open","require(log_fd >= 0);")

    def test_kmsg_write_failure_rejects_helper(self):
        self.run_log_failure("write","require(log_written == (long)used);")

    def run_log_failure(self,kind,anchor):
        result=self.capture([str(self.binaries["running"]),"5",str(self.out/("fault-"+kind+"-kmsg.log")),kind])
        self.assertEqual(result.returncode,1)
        self.assertEqual(result.stderr,b"")
        line=next(i for i,row in enumerate(self.source.read_text().splitlines(),1) if anchor in row)
        expected=("NATIVE_MCCTRL_PREREADY x86_64 PASS rejected=2\n"
                  "NATIVE_BOOT_SERVICE x86_64 boot_errno=0\n"
                  "NATIVE_BOOT_STATUS x86_64 observed=5 expected=5\n"
                  "NATIVE_OS_RESOURCE x86_64 FAIL\n"
                  f"NATIVE_CPU_RESERVATION x86_64 FAIL line={line}\n")
        self.assertEqual(result.stdout,expected.encode())

    def test_running_five_positive(self):self.run_scenario("running",5)
    def test_running_four_rejected(self):self.run_scenario("running",4)
    def test_running_zero_rejected(self):self.run_scenario("running",0)
    def test_running_failed_nine_rejected(self):self.run_scenario("running",9)
    def test_running_errno_rejected_and_logged(self):self.run_scenario("running",-5)
    def test_legacy_four_positive(self):self.run_scenario("legacy",4)
    def test_legacy_five_rejected(self):self.run_scenario("legacy",5)


if __name__=="__main__":
    unittest.main(failfast=True)
