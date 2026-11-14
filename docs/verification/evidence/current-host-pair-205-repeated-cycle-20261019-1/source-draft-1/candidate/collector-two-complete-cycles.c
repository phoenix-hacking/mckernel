/* Linux-control-only two complete OS lifecycle cycles, SOURCE PROTOTYPE. */
#define main frozen_FP_main_never_called
#include "/home/holden/mckernel-work/host-preparation/current-host-pair-final-release-20261019-1/collector-typed-avx-final-release.c"
#undef main
static unsigned cycle_index;
static const char *cycle_root,*cycle_pair_prefix;
static char cycle_log_before[262144],cycle_log_after[262144];
static int cycle_log_before_bytes;
static int cycle_log_prefix_valid(const char *log,int size)
{ return size>cycle_log_before_bytes && size<262144 && cycle_log_before_bytes>0 && !memcmp(log,cycle_log_before,(size_t)cycle_log_before_bytes) ? 0 : -1; }
#include "pair_runtime_cycles.inc"
#include "pair_collector_cycles.inc"
static const unsigned char cycle_expected_0[]={0x62,0x61,0x74,0x63,0x68,0x20,0x62,0x65,0x67,0x69,0x6e,0x20,0x63,0x61,0x73,0x65,0x73,0x3d,0x32,0x20,0x6d,0x69,0x78,0x65,0x64,0x5f,0x72,0x6f,0x75,0x6e,0x64,0x73,0x3d,0x33,0x0a,0x72,0x75,0x73,0x74,0x2d,0x66,0x69,0x6c,0x65,0x2d,0x72,0x6f,0x75,0x6e,0x64,0x74,0x72,0x69,0x70,0x20,0x69,0x6e,0x69,0x74,0x69,0x61,0x6c,0x3d,0x31,0x36,0x20,0x6f,0x76,0x65,0x72,0x77,0x72,0x69,0x74,0x65,0x3d,0x34,0x20,0x73,0x68,0x72,0x69,0x6e,0x6b,0x3d,0x31,0x30,0x20,0x67,0x72,0x6f,0x77,0x3d,0x31,0x34,0x20,0x7a,0x65,0x72,0x6f,0x73,0x3d,0x34,0x20,0x74,0x61,0x69,0x6c,0x3d,0x61,0x61,0x62,0x62,0x63,0x63,0x20,0x69,0x6e,0x76,0x61,0x6c,0x69,0x64,0x5f,0x73,0x65,0x65,0x6b,0x3d,0x32,0x32,0x20,0x63,0x75,0x72,0x73,0x6f,0x72,0x3d,0x31,0x34,0x20,0x63,0x68,0x65,0x63,0x6b,0x65,0x64,0x5f,0x63,0x6c,0x6f,0x73,0x65,0x3d,0x31,0x20,0x72,0x65,0x6d,0x6f,0x76,0x65,0x64,0x3d,0x31,0x0a,0x6d,0x69,0x78,0x65,0x64,0x20,0x72,0x6f,0x75,0x6e,0x64,0x73,0x3d,0x33,0x20,0x62,0x79,0x74,0x65,0x73,0x5f,0x65,0x61,0x63,0x68,0x3d,0x38,0x31,0x39,0x33,0x20,0x63,0x68,0x65,0x63,0x6b,0x73,0x75,0x6d,0x5f,0x74,0x6f,0x74,0x61,0x6c,0x3d,0x33,0x30,0x37,0x32,0x32,0x37,0x30,0x0a,0x66,0x69,0x6c,0x65,0x73,0x3d,0x33,0x20,0x63,0x68,0x65,0x63,0x6b,0x65,0x64,0x5f,0x63,0x6c,0x6f,0x73,0x65,0x73,0x3d,0x36,0x20,0x72,0x65,0x6f,0x70,0x65,0x6e,0x65,0x64,0x3d,0x33,0x20,0x65,0x6f,0x66,0x3d,0x33,0x20,0x72,0x65,0x6d,0x6f,0x76,0x65,0x64,0x3d,0x33,0x0a,0x6a,0x6f,0x69,0x6e,0x65,0x64,0x5f,0x74,0x68,0x72,0x65,0x61,0x64,0x73,0x3d,0x36,0x20,0x74,0x75,0x72,0x6e,0x73,0x5f,0x65,0x61,0x63,0x68,0x3d,0x31,0x32,0x38,0x20,0x63,0x6f,0x75,0x6e,0x74,0x65,0x72,0x5f,0x74,0x6f,0x74,0x61,0x6c,0x3d,0x37,0x36,0x38,0x0a,0x62,0x61,0x74,0x63,0x68,0x20,0x70,0x61,0x73,0x73,0x20,0x63,0x61,0x73,0x65,0x73,0x3d,0x32,0x20,0x63,0x68,0x65,0x63,0x6b,0x65,0x64,0x5f,0x63,0x6c,0x6f,0x73,0x65,0x73,0x3d,0x37,0x20,0x72,0x65,0x6d,0x6f,0x76,0x65,0x64,0x3d,0x34,0x20,0x6a,0x6f,0x69,0x6e,0x65,0x64,0x5f,0x74,0x68,0x72,0x65,0x61,0x64,0x73,0x3d,0x36,0x0a};
static const unsigned char cycle_expected_1[]={0x46,0x50,0x54,0x48,0x52,0x45,0x41,0x44,0x20,0x76,0x31,0x20,0x74,0x68,0x72,0x65,0x61,0x64,0x73,0x3d,0x32,0x20,0x73,0x61,0x6d,0x65,0x5f,0x70,0x65,0x72,0x6d,0x69,0x74,0x74,0x65,0x64,0x5f,0x63,0x70,0x75,0x3d,0x31,0x20,0x64,0x69,0x73,0x74,0x69,0x6e,0x63,0x74,0x5f,0x74,0x69,0x64,0x3d,0x31,0x0a,0x74,0x68,0x72,0x65,0x61,0x64,0x30,0x20,0x72,0x6f,0x75,0x6e,0x64,0x73,0x3d,0x36,0x34,0x20,0x79,0x6d,0x6d,0x5f,0x6c,0x61,0x6e,0x65,0x73,0x3d,0x36,0x34,0x20,0x70,0x65,0x65,0x72,0x5f,0x70,0x72,0x6f,0x67,0x72,0x65,0x73,0x73,0x3d,0x36,0x34,0x20,0x79,0x69,0x65,0x6c,0x64,0x5f,0x6d,0x69,0x6e,0x3d,0x36,0x34,0x20,0x63,0x6f,0x6e,0x74,0x72,0x6f,0x6c,0x73,0x3d,0x30,0x37,0x37,0x66,0x2f,0x33,0x66,0x38,0x30,0x20,0x72,0x65,0x73,0x74,0x6f,0x72,0x65,0x64,0x3d,0x31,0x0a,0x74,0x68,0x72,0x65,0x61,0x64,0x31,0x20,0x72,0x6f,0x75,0x6e,0x64,0x73,0x3d,0x36,0x34,0x20,0x79,0x6d,0x6d,0x5f,0x6c,0x61,0x6e,0x65,0x73,0x3d,0x36,0x34,0x20,0x70,0x65,0x65,0x72,0x5f,0x70,0x72,0x6f,0x67,0x72,0x65,0x73,0x73,0x3d,0x36,0x34,0x20,0x79,0x69,0x65,0x6c,0x64,0x5f,0x6d,0x69,0x6e,0x3d,0x36,0x34,0x20,0x63,0x6f,0x6e,0x74,0x72,0x6f,0x6c,0x73,0x3d,0x30,0x62,0x37,0x66,0x2f,0x35,0x66,0x38,0x30,0x20,0x72,0x65,0x73,0x74,0x6f,0x72,0x65,0x64,0x3d,0x31,0x0a,0x46,0x50,0x54,0x48,0x52,0x45,0x41,0x44,0x20,0x50,0x41,0x53,0x53,0x0a};

static int cycle_pair_ok(void)
{
    const unsigned char *expected[]={cycle_expected_0,cycle_expected_1};
    const size_t lengths[]={sizeof cycle_expected_0,sizeof cycle_expected_1};
    for(int i=0;i<2;i++) {
        const struct result *r=&pair_results[i];
        if(r->pid<=0 || r->status || r->fault || r->timeout || !r->clean ||
           !r->out.eof || !r->err.eof || r->err.observed ||
           r->out.kept!=lengths[i] || r->out.observed!=lengths[i] ||
           memcmp(r->out.data,expected[i],lengths[i]))return -1;
    }
    return 0;
}
static int cycle_life_ok(const struct result *life,int rc)
{
    if(rc || life->status || life->fault || life->timeout || !life->clean ||
       !life->out.eof || !life->err.eof || life->err.observed ||
       life->out.observed!=life->out.kept || life->out.kept>=1024)return -1;
    char text[1025],expected[1025];int descriptor=-1,consumed=0;
    memcpy(text,life->out.data,life->out.kept);text[life->out.kept]=0;
    if(sscanf(text,"{\"operation\":\"open\",\"request\":0,\"return\":%d,%n",&descriptor,&consumed)!=1 || consumed<=0 || descriptor<0)return -1;
    int n=snprintf(expected,sizeof expected,
      "{\"operation\":\"open\",\"request\":0,\"return\":%d,\"errno\":0,\"linux_result\":%d}\n"
      "{\"operation\":\"status_before\",\"request\":1124867,\"return\":5,\"errno\":0,\"linux_result\":5}\n"
      "{\"operation\":\"shutdown\",\"request\":1124866,\"return\":0,\"errno\":0,\"linux_result\":0}\n"
      "{\"operation\":\"status_after\",\"request\":1124867,\"return\":0,\"errno\":0,\"linux_result\":0}\n"
      "{\"operation\":\"close\",\"request\":0,\"return\":0,\"errno\":0,\"linux_result\":0}\n"
      "{\"result\":\"PASS\",\"transition_observed\":true,\"resource_restoration_verified\":false}\n",descriptor,descriptor);
    return n>0 && (size_t)n==life->out.kept && !memcmp(expected,text,(size_t)n) ? 0 : -1;
}
static int cycle_emit_bytes(int console,const char *kind,const char *name,const unsigned char *bytes,size_t size)
{
    if(size>262144)return -1;
    char line[1400];int n=snprintf(line,sizeof line,"ND_CYCLE_STREAM {\"cycle\":%u,\"kind\":\"%s\",\"name\":\"%s\",\"bytes\":%zu}\n",cycle_index,kind,name,size);
    if(n<=0 || (size_t)n>=sizeof line || write_all(console,line,(size_t)n))return -1;
    for(size_t at=0;at<size;) {
        size_t count=size-at;if(count>512)count=512;
        char hex[1025];const char digits[]="0123456789abcdef";
        for(size_t j=0;j<count;j++){hex[2*j]=digits[bytes[at+j]>>4];hex[2*j+1]=digits[bytes[at+j]&15];}hex[2*count]=0;
        n=snprintf(line,sizeof line,"ND_CYCLE_CHUNK {\"cycle\":%u,\"kind\":\"%s\",\"name\":\"%s\",\"offset\":%zu,\"hex\":\"%s\"}\n",cycle_index,kind,name,at,hex);
        if(n<=0 || (size_t)n>=sizeof line || write_all(console,line,(size_t)n))return -1;
        at+=count;
    }
    return 0;
}
static int cycle_publish_control(int console,const char *kind,int rc,const struct result *r)
{
    char line[512];int n=snprintf(line,sizeof line,"ND_CYCLE_CONTROL {\"cycle\":%u,\"kind\":\"%s\",\"helper_rc\":%d,\"raw_wait_status\":%d,\"clean\":%d,\"fault\":%d,\"timeout\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,\"finished_ns\":%llu,\"stdout_observed\":%llu,\"stderr_observed\":%llu,\"stdout_eof\":%d,\"stderr_eof\":%d}\n",cycle_index,kind,rc,r->status,r->clean,r->fault,r->timeout,(unsigned long long)r->started,(unsigned long long)r->reaped,(unsigned long long)r->finished,(unsigned long long)r->out.observed,(unsigned long long)r->err.observed,r->out.eof,r->err.eof);
    return n<=0 || (size_t)n>=sizeof line || write_all(console,line,(size_t)n) ||
       cycle_emit_bytes(console,kind,"stdout",r->out.data,r->out.kept) ||
       cycle_emit_bytes(console,kind,"stderr",r->err.data,r->err.kept) ? -1 : 0;
}
static int cycle_retired(void)
{
    uint64_t start=now_ns(),end=bounded_deadline(start+5000*MS,0);
    while(start && now_ns()<end) {
        int state=retired_at("/proc/mcos0");if(state==1)return 0;if(state<0)return -1;
        struct timespec pause={0,10000000};nanosleep(&pause,NULL);
    }
    return -1;
}
static int run_complete_cycle(int console,int *safe,unsigned long previous_generation,const unsigned long previous_nonce[2])
{
    const char *roots[]={"/case/cycle0","/case/cycle1"};
    const char *prefixes[]={"ND_CYCLE0_PAIR","ND_CYCLE1_PAIR"};
    const char *boot_tags[]={"cycle0-boot","cycle1-boot"};
    const char *stop_tags[]={"cycle0-stop","cycle1-stop"};
    const char *release_tags[]={"cycle0-release","cycle1-release"};
    struct result boot,stop,release;
    if(cycle_index>=2 || !*safe)return -1;
    cycle_root=roots[cycle_index];cycle_pair_prefix=prefixes[cycle_index];
    if(mkdir(cycle_root,0700) || chdir(cycle_root) || mkdir("evidence",0700))return -1;
    cycle_log_before_bytes=klogctl(3,cycle_log_before,sizeof cycle_log_before);
    if(cycle_log_before_bytes<=0 || cycle_log_before_bytes==(int)sizeof cycle_log_before || pair_prepare_challenge())return -1;
    if(cycle_index && pair_nonce[0]==previous_nonce[0] && pair_nonce[1]==previous_nonce[1])return -1;
    int rc=helper_capture(boot_tags[cycle_index],"/bin/native-boot",(char *const[]){"/bin/native-boot",NULL},safe,&boot);
    if(cycle_publish_control(console,"boot",rc,&boot) || rc || !*safe)return -1;
    memset(pair_results,0,sizeof pair_results);
    int cpus[2];
    if(pair_discover(cpus) || (cycle_index && pair_generation==previous_generation))return -1;
    if(pair_run_assigned(cpus,safe) || !*safe || pair_load_results() || cycle_pair_ok() || cycle_retired())return -1;
    int log_n=klogctl(3,cycle_log_after,sizeof cycle_log_after);
    if(cycle_log_prefix_valid(cycle_log_after,log_n))return -1;
    char line[512];int n=snprintf(line,sizeof line,"ND_CYCLE_IDENTITY {\"cycle\":%u,\"os\":%u,\"generation\":%lu,\"challenge\":\"%016lx%016lx\",\"prior_log_bytes\":%d,\"fresh_log_bytes\":%d}\n",cycle_index,pair_os,pair_generation,pair_nonce[0],pair_nonce[1],cycle_log_before_bytes,log_n-cycle_log_before_bytes);
    if(n<=0 || (size_t)n>=sizeof line || write_all(console,line,(size_t)n) ||
       cycle_emit_bytes(console,"pair","kernel_log",(const unsigned char*)cycle_log_after+cycle_log_before_bytes,(size_t)(log_n-cycle_log_before_bytes)) || publish_pair(console,1))return -1;
    rc=helper_capture(stop_tags[cycle_index],"/bin/native-lifecycle-probe",(char *const[]){"/bin/native-lifecycle-probe","0",NULL},safe,&stop);
    if(cycle_publish_control(console,"stop",rc,&stop) || !*safe || cycle_life_ok(&stop,rc))return -1;
    rc=helper_capture(release_tags[cycle_index],"/bin/native-resource-release-probe",(char *const[]){"/bin/native-resource-release-probe",NULL},safe,&release);
    if(cycle_publish_control(console,"release",rc,&release) || rc || !*safe)return -1;
    /* Public inventory is external strictconsumer's obligation; no generation/frame restoration inference. */
    return chdir("/") ? -1 : 0;
}
#ifndef CYCLE_MAIN_NAME
#define CYCLE_MAIN_NAME main
#endif
int CYCLE_MAIN_NAME(void)
{
    (void)pair_run; /* preserved accepted one-pair entrypoint; checked discovery precedes launch here */
    if(getpid()!=1 || geteuid()!=0)return 125;
    uint64_t beginning=now_ns();if(!beginning)remain_pid1();
    collector_deadline=beginning+COLLECTOR_SECONDS*1000ull*MS;
    struct sigaction action;memset(&action,0,sizeof action);action.sa_handler=outer_expired;
    if(sigemptyset(&action.sa_mask) || sigaction(SIGALRM,&action,NULL))remain_pid1();
    alarm(COLLECTOR_SECONDS);
    int good=1,safe=1,console=-1,saved_level=-1,completed=0;
    if(mount_one("proc","/proc") || mount_one("sysfs","/sys") || mount_one("devtmpfs","/dev") || mount_one("debugfs","/sys/kernel/debug"))goto finish;
    console=open("/dev/console",O_WRONLY|O_CLOEXEC|O_NONBLOCK);if(console<0 || mkdir("/case/evidence",0700))goto finish;
    char levels[128];int fd=open("/proc/sys/kernel/printk",O_RDONLY|O_CLOEXEC);ssize_t len=fd<0?-1:read(fd,levels,sizeof levels-1);if(fd>=0 && close(fd))len=-1;
    if(len<=0)goto finish;
    levels[len]=0;
    if(sscanf(levels,"%d",&saved_level)!=1 || saved_level<1 || saved_level>8 || klogctl(6,NULL,0))goto finish;
    if(helper("load-ihk","/sbin/insmod",(char *const[]){"insmod","/modules/ihk.ko",NULL},&safe) || helper("load-smp","/sbin/insmod",(char *const[]){"insmod","/modules/ihk-smp-x86_64.ko","ihk_trampoline=524288",NULL},&safe) || helper("load-mcctrl","/sbin/insmod",(char *const[]){"insmod","/modules/mcctrl.ko",NULL},&safe))goto finish;
    unsigned long previous_generation=0,previous_nonce[2]={0,0};
    for(cycle_index=0;cycle_index<2;cycle_index++) {
        if(run_complete_cycle(console,&safe,previous_generation,previous_nonce)){good=0;break;}
        previous_generation=pair_generation;previous_nonce[0]=pair_nonce[0];previous_nonce[1]=pair_nonce[1];completed++;
    }
finish:
    if(!safe)remain_pid1();
    if(console>=0) {
        char record[200];int n=snprintf(record,sizeof record,"ND_CYCLES_DONE {\"completed\":%d,\"good\":%s,\"logger_seconds\":120,\"full_restoration_verified\":false}\n",completed,(good && completed==2)?"true":"false");
        if(n>0 && (size_t)n<sizeof record)(void)write_all(console,record,(size_t)n);
    }
    if(saved_level>=0 && klogctl(8,NULL,saved_level))remain_pid1();
    poweroff_forever(console);return 125;
}
