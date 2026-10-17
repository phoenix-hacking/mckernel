"""Real collector supervision/private pipes plus exact retained-log finish block.

Only privileged kmsg and guest evidence paths map to ordinary scratch files.
Helper main uses the separately tested syscall mock, never a live device.
"""
import hashlib
import json
import os
from pathlib import Path
import unittest
import scripts.tests.test_native_boot_running as helpers

HARNESS = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/klog.h>
#include <sys/prctl.h>
#include <unistd.h>
static int mapped_open(const char *,int,...);
static int mapped_close(int);
static ssize_t mapped_write(int,const void *,size_t);
static int mapped_klogctl(int,char *,int);
#define open mapped_open
#define close mapped_close
#define write mapped_write
#define klogctl mapped_klogctl
#define main collector_pid1_main_never_called
#include "COLLECTOR_SOURCE"
#undef main
#undef open
#undef close
#undef write
#undef klogctl
static char kmsg_path[512],evidence_path[512];
static int collector_log_fd=-1,log_fault,fault_errno;
static int mapped_open(const char *path,int flags,...)
{
    mode_t mode=0;
    if (flags&O_CREAT) { va_list args;va_start(args,flags);mode=(mode_t)va_arg(args,int);va_end(args); }
    if (!strcmp(path,"/dev/kmsg")) {
        assert(flags==(O_WRONLY|O_CLOEXEC|O_NOFOLLOW));
        if (log_fault==1) { fault_errno=errno=EACCES;return -1; }
        collector_log_fd=open(kmsg_path,flags|O_APPEND);return collector_log_fd;
    }
    const char prefix[]="/case/evidence/";
    if (!strncmp(path,prefix,sizeof prefix-1)) {
        char destination[768];
        int n=snprintf(destination,sizeof destination,"%s/%s",evidence_path,path+sizeof prefix-1);
        assert(n>0 && (size_t)n<sizeof destination);
        return open(destination,flags,mode);
    }
    return open(path,flags,mode);
}
static int mapped_close(int fd)
{
    if (fd==collector_log_fd) collector_log_fd=-1;
    return close(fd);
}
static ssize_t mapped_write(int fd,const void *bytes,size_t count)
{
    if (fd==collector_log_fd && log_fault==2) { fault_errno=errno=EIO;return -1; }
    return write(fd,bytes,count);
}
static int mapped_klogctl(int command,char *bytes,int size)
{
    assert(command==3 && size==262144);
    int fd=open(kmsg_path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);assert(fd>=0);
    ssize_t n=read(fd,bytes,(size_t)size);assert(n>=0 && n<size);assert(close(fd)==0);
    return (int)n;
}
int main(int argc,char **argv)
{
    assert(argc==5);
    int path_n=snprintf(kmsg_path,sizeof kmsg_path,"%s/kmsg.log",argv[3]);assert(path_n>0 && (size_t)path_n<sizeof kmsg_path);
    path_n=snprintf(evidence_path,sizeof evidence_path,"%s/case-evidence",argv[3]);assert(path_n>0 && (size_t)path_n<sizeof evidence_path);
    log_fault=!strcmp(argv[4],"open")?1:!strcmp(argv[4],"write")?2:0;
    assert(log_fault || !strcmp(argv[4],"none"));
    int fd=open(kmsg_path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);assert(fd>=0 && close(fd)==0);
    assert(prctl(PR_SET_CHILD_SUBREAPER,1,0,0,0)==0);
    struct result captured;
    int safe=1;
    int rc=helper_capture("boot",argv[1],(char *const[]){argv[1],argv[2],kmsg_path,NULL},&safe,&captured);
    int expected_status=atoi(argv[2])==5?0:256;
    int expected_good=expected_status==0 && !log_fault;
    assert(rc==(expected_good?0:-1) && safe==1);
    assert(captured.status==expected_status && captured.fault==0 && captured.timeout==0 && captured.clean==1);
    assert(captured.child_stage==0 && captured.child_errno==0);
    assert(captured.out.eof && captured.err.eof && captured.out.observed==captured.out.kept && captured.err.observed==0);
    assert(captured.out.kept<1024 && captured.out.kept>0);
    int good=expected_good,console=STDOUT_FILENO;
#define klogctl mapped_klogctl
/* EXACT_FINISH_BLOCK */
#undef klogctl
    assert(good==expected_good);
    char record_path[768];path_n=snprintf(record_path,sizeof record_path,"%s/integration-result.json",argv[3]);assert(path_n>0 && (size_t)path_n<sizeof record_path);
    FILE *record=fopen(record_path,"wx");assert(record);
    assert(fprintf(record,"{\"helper_result\":%d,\"raw_wait_status\":%d,\"safe\":%d,\"fault_errno\":%d,\"good\":%d,\"stdout_bytes\":%zu,\"stderr_bytes\":%zu}\n",rc,captured.status,safe,fault_errno,good,captured.out.kept,captured.err.kept)>0);
    assert(fclose(record)==0);
    return 0;
}
'''


@unittest.skipUnless(os.environ.get("NATIVE_BOOT_RUNNING_EVIDENCE"),
                     "requires admitted actual-main helper scratch fixture")
class RunningBootObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=helpers.RunningBootHelperTests
        if not hasattr(base,"binaries"):
            base.setUpClass()
        cls.base=base
        cls.out=base.out/"observability"
        cls.out.mkdir(mode=0o700,exist_ok=False)
        source=Path(base.binding["collector_variant_path"])
        original=Path(base.binding["collector_original_path"])
        raw=source.read_text()
        if hashlib.sha256(source.read_bytes()).hexdigest()!=base.binding["collector_variant_sha256"]:
            raise RuntimeError("collector source drift")
        if raw!=original.read_text().replace(base.binding["collector_insertion_anchor"],base.binding["collector_insertion"]+base.binding["collector_insertion_anchor"],1):
            raise RuntimeError("collector delta exceeds boot-only bounded log insertion")
        start=raw.index("    static char kernel_log[262144];")
        end=raw.index("    /* Exercise restoration before publication",start)
        finish=raw[start:end]
        original_finish=original.read_text().split("    static char kernel_log[262144];",1)[1].split("    /* Exercise restoration before publication",1)[0]
        if finish!="    static char kernel_log[262144];"+original_finish:
            raise RuntimeError("retained kernel-log publication block changed")
        (cls.out/"exact-finish-publication.c").write_text(finish)
        harness=cls.out/"harness.c"
        harness.write_text(HARNESS.replace("COLLECTOR_SOURCE",str(source)).replace("/* EXACT_FINISH_BLOCK */",finish))
        cls.binary=cls.out/"harness"
        result=base.capture(["/usr/bin/gcc","-std=gnu11","-O2","-Wall","-Wextra","-Werror",
            "-static","-fno-pie","-no-pie","-Wl,-z,noexecstack",str(harness),"-o",str(cls.binary)])
        if result.returncode:
            raise RuntimeError("collector actual-body integration compile failed; evidence retained")

    def run_capture(self,name,status,fault="none"):
        case=self.out/name;case.mkdir(mode=0o700);(case/"case-evidence").mkdir(mode=0o700)
        result=self.base.capture([str(self.binary),str(self.base.binaries["running"]),str(status),str(case),fault])
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stderr,b"")
        private=(case/"case-evidence/boot.stdout").read_bytes()
        self.assertIn(f"NATIVE_BOOT_STATUS x86_64 observed={status} expected=5\n".encode(),private)
        self.assertEqual((case/"case-evidence/boot.stderr").read_bytes(),b"")
        numeric=f"<6>NATIVE_BOOT_STATUS x86_64 observed={status} expected=5\n".encode()
        self.assertIn(numeric,result.stdout)
        self.assertEqual(result.stdout.count(numeric),1)
        self.assertNotIn(b"NATIVE_BOOT_CAPTURE",result.stdout)
        expected_raw=0 if status==5 else 256
        summary=f"<6>NATIVE_BOOT_HELPER raw_wait_status={expected_raw} fault=0 timeout=0 clean=1 child_stage=0 child_errno=0\n".encode()
        if fault=="none":
            self.assertIn(summary,result.stdout)
            self.assertEqual(result.stdout,numeric+summary+b"\n")
        else:
            self.assertEqual(result.stdout,numeric+b"\n")
        self.assertEqual((case/"case-evidence/kernel.log").read_bytes()+b"\n",result.stdout)
        self.assertIn(f"status={expected_raw} fault=0 timeout=0 clean=1 stage=0 errno=0\n".encode(),(case/"case-evidence/boot.status").read_bytes())
        report=json.loads((case/"integration-result.json").read_text())
        self.assertEqual(report["raw_wait_status"],expected_raw)
        self.assertEqual(report["helper_result"],0 if status==5 and fault=="none" else -1)
        self.assertEqual(report["fault_errno"],{"none":0,"open":13,"write":5}[fault])
        (case/"retained-console.stdout").write_bytes(result.stdout)

    def test_running_five_raw_zero_reaches_retained_console(self):self.run_capture("positive-five",5)
    def test_ready_four_raw_256_reaches_retained_console(self):self.run_capture("negative-four",4)
    def test_collector_kmsg_open_failure_rejects_capture(self):self.run_capture("collector-open-fault",5,"open")
    def test_collector_kmsg_write_failure_rejects_capture(self):self.run_capture("collector-write-fault",5,"write")


if __name__=="__main__":
    unittest.main(failfast=True)
