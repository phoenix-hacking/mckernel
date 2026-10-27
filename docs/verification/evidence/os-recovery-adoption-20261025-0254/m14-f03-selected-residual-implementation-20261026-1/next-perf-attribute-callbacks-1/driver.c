/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <ihk/lock.h>
#include <process.h>
#include <ihk/debug.h>
#include <mc_perf_event.h>
#include <ihk/memconst.h>
#ifdef __GENKSYMS__
#error "Probe is the selected production runtime ABI, not Linux genksyms projection"
#endif

/* Actual original C callbacks above genuine current runtime headers. */
static int
perf_counter_attr_flags_bridge_C(const void *attr, int *exclude_kernel,
			       int *exclude_user)
{
	const struct perf_event_attr *perf_attr = attr;

	if (!perf_attr || !exclude_kernel || !exclude_user) {
		return -EINVAL;
	}

	*exclude_kernel = perf_attr->exclude_kernel;
	*exclude_user = perf_attr->exclude_user;
	return 0;
}

static int
perf_read_attr_flags_bridge_C(const void *attr, int *exclude_user,
			    int *exclude_kernel, int *inherit)
{
	const struct perf_event_attr *perf_attr = attr;

	if (!perf_attr || !exclude_user || !exclude_kernel || !inherit) {
		return -EINVAL;
	}

	*exclude_user = perf_attr->exclude_user;
	*exclude_kernel = perf_attr->exclude_kernel;
	*inherit = perf_attr->inherit;
	return 0;
}

extern int f03_perf_counter_attr_flags_v1(const void *,int *,int *);
extern int f03_perf_read_attr_flags_v1(const void *,int *,int *,int *);
extern int puts(const char *);
_Static_assert(sizeof(struct perf_event_attr)==104,"retained actual perf attr size");
_Static_assert(__alignof__(struct perf_event_attr)==8,"retained actual perf attr alignment");
_Static_assert(__builtin_offsetof(struct perf_event_attr,read_format)+sizeof(unsigned long)==40,"retained flags word offset");
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8,"selected scalar ABI");
static unsigned pairs;
static int one(unsigned long bits)
{
    struct perf_event_attr attr={0};
    __builtin_memcpy((char *)&attr+40,&bits,sizeof bits);
    int ca[3]={17,19,23},ra[3]={17,19,23};
    int cr=perf_counter_attr_flags_bridge_C(&attr,&ca[0],&ca[1]);
    int rr=f03_perf_counter_attr_flags_v1(&attr,&ra[0],&ra[1]);
    if(cr!=rr || ca[0]!=ra[0] || ca[1]!=ra[1])return 1;
    ++pairs;
    cr=perf_read_attr_flags_bridge_C(&attr,&ca[0],&ca[1],&ca[2]);
    rr=f03_perf_read_attr_flags_v1(&attr,&ra[0],&ra[1],&ra[2]);
    if(cr!=rr || ca[0]!=ra[0] || ca[1]!=ra[1] || ca[2]!=ra[2])return 2;
    ++pairs;
    int c=71,r=71;
    cr=perf_counter_attr_flags_bridge_C(&attr,&c,&c);
    rr=f03_perf_counter_attr_flags_v1(&attr,&r,&r);
    if(cr!=rr || c!=r)return 3;
    ++pairs;
    c=r=71;
    cr=perf_read_attr_flags_bridge_C(&attr,&c,&c,&c);
    rr=f03_perf_read_attr_flags_v1(&attr,&r,&r,&r);
    if(cr!=rr || c!=r)return 4;
    ++pairs;
    return 0;
}
int main(void)
{
    for(unsigned long bits=0;bits<512;++bits)if(one(bits))return 10;
    for(unsigned shift=0;shift<64;++shift)if(one(1UL<<shift))return 11;
    if(one(~0UL))return 12;
    struct perf_event_attr attr={0};attr.exclude_kernel=1;attr.exclude_user=1;attr.inherit=1;
    for(unsigned mask=1;mask<8;++mask){
        int ca[2]={29,31},ra[2]={29,31};
        int cr=perf_counter_attr_flags_bridge_C(mask&1?0:&attr,mask&2?0:&ca[0],mask&4?0:&ca[1]);
        int rr=f03_perf_counter_attr_flags_v1(mask&1?0:&attr,mask&2?0:&ra[0],mask&4?0:&ra[1]);
        if(cr!=-EINVAL || rr!=cr || ca[0]!=ra[0] || ca[1]!=ra[1] || ra[0]!=29 || ra[1]!=31)return 13;
        ++pairs;
    }
    for(unsigned mask=1;mask<16;++mask){
        int ca[3]={29,31,37},ra[3]={29,31,37};
        int cr=perf_read_attr_flags_bridge_C(mask&1?0:&attr,mask&2?0:&ca[0],mask&4?0:&ca[1],mask&8?0:&ca[2]);
        int rr=f03_perf_read_attr_flags_v1(mask&1?0:&attr,mask&2?0:&ra[0],mask&4?0:&ra[1],mask&8?0:&ra[2]);
        if(cr!=-EINVAL || rr!=cr || ca[0]!=ra[0] || ca[1]!=ra[1] || ca[2]!=ra[2] || ra[0]!=29 || ra[1]!=31 || ra[2]!=37)return 14;
        ++pairs;
    }
    if(pairs!=2330)return 15;
    puts("PASS actual-original-C/Rust perf attribute callbacks 2330 pairs including 64 bit images, 512 flag combinations, null/no-write and ordered alias stores; no PMU/kernel/native action");
    return 0;
}
