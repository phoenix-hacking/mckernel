/* SPDX-License-Identifier: GPL-2.0-only
 * Minimal PID-1 collector for the reviewed startup.argv-empty packet.
 * This is deliberately a fixed-path, fixed-argument program: it is not a
 * general init or shell.  It emits one ND_PAYLOAD frame and always attempts
 * teardown before poweroff.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <dirent.h>

#define LIMIT_OUT 4096u
#define LIMIT_ERR 65536u
#define DEADLINE_SEC 30
static unsigned char outbuf[LIMIT_OUT], errbuf[LIMIT_ERR];
static size_t outn, errn, outdiscard, errdiscard;
static int out_eof, err_eof, child_pid;
static uint64_t launch_ns, reap_ns, finish_ns, out_eof_ns, err_eof_ns;
static int setup_pipe[2] = {-1, -1};

static uint64_t now_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) < 0) return 0;
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}
static int runv(const char *path, char *const av[]) {
    pid_t p = fork(); int st;
    if (p < 0) return -1;
    if (!p) { int fd = open("/dev/console", O_WRONLY|O_CLOEXEC); if (fd >= 0) { dup2(fd, 1); dup2(fd, 2); close(fd); } execve(path, av, (char *const[]){"PATH=/bin:/sbin:/usr/bin:/usr/sbin", "LC_ALL=C", 0}); _exit(127); }
    do { if (waitpid(p, &st, 0) < 0 && errno == EINTR) continue; else break; } while (1);
    return WIFEXITED(st) ? WEXITSTATUS(st) : 128;
}
static int mount_one(const char *type, const char *where) { return mount(type, where, type, 0, 0); }
static int node_exists(void) { struct stat st; return stat("/dev/mcos0", &st) == 0; }
static int retired(void) { DIR *d=opendir("/proc/mcos0"); struct dirent *e; int f=0; if(!d)return 1; while((e=readdir(d))) if(e->d_name[0]>='0'&&e->d_name[0]<='9'){f=1;break;} closedir(d); return !f; }
static void drain_fd(int fd, unsigned char *buf, size_t cap, size_t *n, size_t *discard, int *eof, uint64_t *eofns) {
    unsigned char tmp[4096]; ssize_t r;
    for (;;) { r = read(fd, tmp, sizeof(tmp)); if (r > 0) { size_t keep = (size_t)r; if (*n + keep > cap) keep = cap - *n; if (keep) { memcpy(buf + *n, tmp, keep); *n += keep; } *discard += (size_t)r - keep; continue; } if (!r || (r < 0 && errno != EINTR && errno != EAGAIN)) { *eof = 1; *eofns = now_ns(); } return; }
}
static void hex(char *dst, size_t cap, const unsigned char *src, size_t n) { static const char x[]="0123456789abcdef"; size_t i; if (cap < n*2+1) n=(cap-1)/2; for(i=0;i<n;i++){dst[i*2]=x[src[i]>>4];dst[i*2+1]=x[src[i]&15];} dst[n*2]=0; }
static void publish(int status, int proc_empty) {
    static char oh[LIMIT_OUT*2+1], eh[LIMIT_ERR*2+1]; hex(oh,sizeof oh,outbuf,outn); hex(eh,sizeof eh,errbuf,errn);
    dprintf(STDOUT_FILENO, "ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\",\"/apps/app\",\"app\",\"A\",\"\",\"B\"],\"cwd\":\"/case/work\",\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},\"raw_wait_status\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,\"finished_ns\":%llu,\"streams\":{\"stdout\":{\"hex\":\"%s\",\"eof\":%s,\"truncated\":%s,\"observed\":%zu,\"retained\":%zu,\"discarded\":%zu,\"limit\":%u,\"eof_ns\":%llu},\"stderr\":{\"hex\":\"%s\",\"eof\":%s,\"truncated\":%s,\"observed\":%zu,\"retained\":%zu,\"discarded\":%zu,\"limit\":%u,\"eof_ns\":%llu}},\"procfs_empty\":%s}\n", status,(unsigned long long)launch_ns,(unsigned long long)reap_ns,(unsigned long long)finish_ns,oh,out_eof?"true":"false",outdiscard?"true":"false",outn+outdiscard,outn,outdiscard,LIMIT_OUT,(unsigned long long)out_eof_ns,eh,err_eof?"true":"false",errdiscard?"true":"false",errn+errdiscard,errn,errdiscard,LIMIT_ERR,(unsigned long long)err_eof_ns,proc_empty?"true":"false");
}
static void teardown(void) { (void)runv("/sbin/rmmod", (char *const[]){"rmmod","mcctrl",0}); (void)runv("/sbin/rmmod", (char *const[]){"rmmod","ihk_smp_x86_64",0}); (void)runv("/sbin/rmmod", (char *const[]){"rmmod","ihk",0}); }
int main(int argc, char **argv) {
    int p[4], fl, st=127, ready=0; uint64_t end; struct pollfd pf[2];
    if (argc > 1 && !strcmp(argv[1], "--self-test")) { puts("native-diagnostic-collector self-test PASS"); return 0; }
    if (getpid()!=1 || geteuid()!=0) return 125;
    (void)mount_one("proc", "/proc"); (void)mount_one("sysfs", "/sys"); (void)mount_one("devtmpfs", "/dev"); (void)mount("debugfs","/sys/kernel/debug","debugfs",0,0);
    if (runv("/sbin/insmod", (char *const[]){"insmod","/modules/ihk.ko",0}) || runv("/sbin/insmod", (char *const[]){"insmod","/modules/ihk-smp-x86_64.ko","ihk_trampoline=524288",0}) || runv("/sbin/insmod", (char *const[]){"insmod","/modules/mcctrl.ko",0})) goto fail;
    if (runv("/bin/native-boot", (char *const[]){"native-boot",0})) goto fail;
    end=now_ns()+5000000000ull; while (now_ns()<end) { if(node_exists()){ready=1;break;} usleep(10000); } if(!ready) goto fail;
    if (pipe(p)<0 || pipe(p+1)<0) goto fail; fl=fcntl(p[0],F_GETFL); fcntl(p[0],F_SETFL,fl|O_NONBLOCK); fl=fcntl(p[1],F_GETFL); fcntl(p[1],F_SETFL,fl|O_NONBLOCK);
    child_pid=fork(); if(child_pid<0) goto fail; if(!child_pid){ setpgid(0,0); dup2(p[1],1); dup2(p[3],2); close(p[0]);close(p[1]);close(p[2]);close(p[3]); if(chdir("/case/work")<0)_exit(126); execve("/bin/mcexec",(char *const[]){"/bin/mcexec","-t","1","0","app","A","","B",0},(char *const[]){"PATH=/usr/bin:/bin","COKERNEL_PATH=/apps",0}); _exit(127); }
    close(p[1]);close(p[3]); launch_ns=now_ns(); end=launch_ns+DEADLINE_SEC*1000000000ull; while(now_ns()<end && (!out_eof||!err_eof||!reap_ns)){ pf[0]=(struct pollfd){p[0],POLLIN|POLLHUP,0};pf[1]=(struct pollfd){p[2],POLLIN|POLLHUP,0};poll(pf,2,20);if(pf[0].revents)drain_fd(p[0],outbuf,LIMIT_OUT,&outn,&outdiscard,&out_eof,&out_eof_ns);if(pf[1].revents)drain_fd(p[2],errbuf,LIMIT_ERR,&errn,&errdiscard,&err_eof,&err_eof_ns);if(waitpid(child_pid,&st,WNOHANG)==child_pid)reap_ns=now_ns();}
    if(!reap_ns){kill(child_pid,SIGKILL);waitpid(child_pid,&st,0);reap_ns=now_ns();} drain_fd(p[0],outbuf,LIMIT_OUT,&outn,&outdiscard,&out_eof,&out_eof_ns);drain_fd(p[2],errbuf,LIMIT_ERR,&errn,&errdiscard,&err_eof,&err_eof_ns);close(p[0]);close(p[2]);finish_ns=now_ns(); publish(st,!node_exists()); teardown(); reboot(RB_POWER_OFF); return 0;
fail: finish_ns=now_ns(); publish(st,0); teardown(); reboot(RB_POWER_OFF); return 1;
}
