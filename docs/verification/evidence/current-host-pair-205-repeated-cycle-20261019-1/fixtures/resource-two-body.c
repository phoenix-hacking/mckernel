
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
#include "../candidate/native-resource-release-two.c"
#undef main
/* Matched source 3f7b: ShutdownOnline commits Online/None; memory prepare_release_all
 * clears the OS owner into the reserved map. No CPU release remains necessary. */
static int scenario, call_index, device_memory_released, online_reads;
static int admission_status, admission_cpu, admission_mem, destroy_calls, release_calls;
static int mock_open(const char *path, int flags) {
    assert(flags & O_NOFOLLOW);
    if (!strcmp(path,"/dev/mcd0")) return 10;
    if (!strcmp(path,"/dev/mcos0")) return 11;
    if(!strcmp(path,"/sys/devices/system/cpu/cpu1/online"))return 12;
    assert(!strcmp(path,"/sys/devices/system/cpu/cpu2/online"));return 13;
}
static int mock_close(int fd) {
    assert(fd >= 10 && fd <= 13);
    if (0 && fd == 11) { errno=EIO; return -1; }
    return 0;
}
static long mock_read(int fd, void *buf, unsigned long size) {
    assert((fd == 12 || fd == 13) && size == 3);
    char *s=buf; online_reads++; s[0]=((scenario==9 && online_reads==2)||(scenario==10 && online_reads==4))?'0':'1'; s[1]='\n';
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
    if(!scenario) assert(call_index==11 && online_reads==4 && destroy_calls==1 && release_calls==1);
    if(scenario>=1 && scenario<=6) assert(destroy_calls==0 && release_calls==0);
    return rc;
}
