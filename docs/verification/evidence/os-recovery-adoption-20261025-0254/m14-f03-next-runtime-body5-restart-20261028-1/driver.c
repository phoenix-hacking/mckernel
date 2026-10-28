/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Every allocation/map/atomic/hardware callback below is a local HOST mock. */
#include <types.h>
#include <errno.h>
#include <ihk/cpu.h>
#include <ihk/memconst.h>
#include <mc_perf_event.h>
#include "provider-types.C.inc"
#define memset __builtin_memset
#define memcpy __builtin_memcpy
static struct mc_perf_event event,expected_event;
static struct perf_event_attr attribute;
static unsigned char saved_attribute[sizeof attribute];
static char expected_order[32];
static unsigned order_count,invalid,atomic_count;
static int allocation_failure,validation_result,extra_id,initialization_result;
static unsigned long mapped_value,extra_value;
static struct mc_perf_event *published;

static void mark(char operation)
{
    if(order_count>=sizeof expected_order || expected_order[order_count]!=operation)invalid=1;
    ++order_count;
}
static void *perf_event_alloc_kmalloc_bridge(size_t size,unsigned long flags)
{
    mark('A');if(size!=sizeof event || flags!=IHK_MC_AP_NOWAIT)invalid=1;
    return allocation_failure?NULL:&event;
}
static void perf_event_alloc_free_bridge(void *pointer)
{
    mark('F');if(pointer!=&event || published!=(void *)0x1230)invalid=1;
}
static void sync_child_count_set_bridge(void *pointer,long value)
{
    if(atomic_count++==0) { mark('C');if(pointer!=&event.count || value!=0)invalid=1; }
    else { mark('P');if(pointer!=&event.hw.period_left || (unsigned long)value!=(unsigned long)expected_event.hw.period_left.counter64)invalid=1; }
    memcpy(pointer,&value,sizeof value);
}
unsigned long ihk_mc_hw_event_map(unsigned long config)
{ mark('H');if(config!=attribute.config)invalid=1;return mapped_value; }
unsigned long ihk_mc_hw_cache_event_map(unsigned long config)
{ mark('K');if(config!=attribute.config)invalid=1;return mapped_value; }
unsigned long ihk_mc_hw_cache_extra_reg_map(unsigned long config)
{ mark('X');if(config!=attribute.config)invalid=1;return extra_value; }
unsigned long ihk_mc_raw_event_map(unsigned long config)
{ mark('R');if(config!=attribute.config)invalid=1;return mapped_value; }
int ihk_mc_validate_event(unsigned long config)
{ mark('V');if(config!=mapped_value)invalid=1;return validation_result; }
int ihk_mc_get_extra_reg_id(unsigned long config,unsigned long extra)
{ mark('I');if(config!=mapped_value || extra!=(attribute.type==PERF_TYPE_HW_CACHE?extra_value:0))invalid=1;return extra_id; }
unsigned int ihk_mc_get_extra_reg_msr(int id)
{ mark('M');if(id!=extra_id)invalid=1;return 0x80000000U+(unsigned)id; }
int ihk_mc_get_extra_reg_idx(int id)
{ mark('J');if(id!=extra_id)invalid=1;return id^0x40000000; }
static int perf_event_alloc_hw_init_bridge(void *pointer)
{
    mark('N');if(pointer!=&event || published!=(void *)0x1230)invalid=1;
    event.state=(enum perf_event_state)17;return initialization_result;
}

#define perf_event_alloc_init_body_result c_reference_perf_event_alloc_init_body_result
#define perf_event_alloc_map_body_result c_reference_perf_event_alloc_map_body_result
#define perf_event_alloc_body_result c_reference_perf_event_alloc_body_result
#define SYSCALL_POLICY_HELPER_SCOPE static
#include "allocator-original.C.inc"
#define perf_event_open_alloc_event_bridge perf_event_open_alloc_event_bridge_original
#include "entry-original.C.inc"
#undef perf_event_open_alloc_event_bridge
#undef perf_event_alloc_init_body_result
#undef perf_event_alloc_map_body_result
#undef perf_event_alloc_body_result
#include "perf-allocation-binding.C.inc"
#include "abi.C.inc"
extern const unsigned long F03_PERF_ALLOCATION_ABI[];
extern int puts(const char *);

static void append(char value)
{ unsigned i=0;while(expected_order[i])++i;expected_order[i]=value; }
static int prepare(unsigned type,int fail_alloc,int valid,int id,int initialize,int freq,unsigned long sample,int null_kind)
{
    memset(&event,0xa5,sizeof event);memset(&expected_event,0xa5,sizeof expected_event);
    memset(&attribute,0x5a,sizeof attribute);
    attribute.type=type;attribute.config=type==PERF_TYPE_HARDWARE && sample==9?PERF_COUNT_HW_REF_CPU_CYCLES:0x800000000000002aUL;
    attribute.freq=freq;attribute.sample_period=sample;
    memcpy(saved_attribute,&attribute,sizeof attribute);
    memset(expected_order,0,sizeof expected_order);order_count=invalid=atomic_count=0;
    allocation_failure=fail_alloc;validation_result=valid;extra_id=id;initialization_result=initialize;
    mapped_value=0x8000000000000456UL;extra_value=0xfedcba9876543210UL;
    published=(void *)0x1230;
    if(null_kind)return -EINVAL;
    append('A');if(fail_alloc)return -ENOMEM;
    memset(&expected_event,0,sizeof expected_event);memcpy(&expected_event.attr,&attribute,sizeof attribute);
    expected_event.group_entry.next=expected_event.group_entry.prev=&event.group_entry;
    expected_event.sibling_list.next=expected_event.sibling_list.prev=&event.sibling_list;
    expected_event.sample_freq=attribute.sample_freq;
    unsigned long period=freq && attribute.sample_freq?1:attribute.sample_period;
    expected_event.hw.sample_period=expected_event.hw.last_period=period;
    expected_event.hw.period_left.counter64=(long)period;
    append('C');append('P');
    if(type==PERF_TYPE_HARDWARE && attribute.config==PERF_COUNT_HW_REF_CPU_CYCLES) {
        expected_event.use_invariant_tsc=1;return 0;
    }
    if(type==PERF_TYPE_HARDWARE)append('H');
    else if(type==PERF_TYPE_HW_CACHE) { append('K');append('X'); }
    else if(type==PERF_TYPE_RAW)append('R');
    else { append('F');return -EINVAL; }
    append('V');if(!valid) { append('F');return -ENOENT; }
    expected_event.hw_config=mapped_value;
    expected_event.hw_config_ext=type==PERF_TYPE_HW_CACHE?extra_value:0;
    append('I');
    if(id>=0) {
        expected_event.extra_reg.config=expected_event.hw_config_ext;
        expected_event.extra_reg.reg=0x80000000U+(unsigned)id;
        expected_event.extra_reg.idx=id^0x40000000;append('M');append('J');
    }
    append('N');expected_event.state=(enum perf_event_state)17;
    if(initialize)append('F');return initialize;
}

static int one(unsigned type,int fail_alloc,int valid,int id,int initialize,int freq,unsigned long sample,int null_kind,int rust)
{
    int expected_result=prepare(type,fail_alloc,valid,id,initialize,freq,sample,null_kind);
    void **output=null_kind==1?NULL:(void **)&published;
    void *attr=null_kind==2?NULL:&attribute;
    int result=rust?f03_perf_event_allocate_v1(output,attr):perf_event_open_alloc_event_bridge_original(output,attr);
    if(result!=expected_result || invalid || order_count!=__builtin_strlen(expected_order))return 1;
    if(published!=(expected_result? (void *)0x1230:(void *)&event))return 2;
    if(__builtin_memcmp(&event,&expected_event,sizeof event) || __builtin_memcmp(saved_attribute,&attribute,sizeof attribute))return 3;
    return 0;
}
int main(void)
{
    if(__builtin_memcmp(F03_PERF_ALLOCATION_ABI,ABI_C,sizeof ABI_C))return 10;
    const unsigned types[]={PERF_TYPE_HARDWARE,PERF_TYPE_HW_CACHE,PERF_TYPE_RAW,99};
    const int ids[]={-1,0,0x7fffffff},initializers[]={0,-12,17};
    const unsigned long samples[]={0,9,0x8000000000000000UL,~0UL};
    unsigned pairs=0;
    for(unsigned t=0;t<4;t++)for(int a=0;a<2;a++)for(int v=0;v<2;v++)for(unsigned i=0;i<3;i++)for(unsigned n=0;n<3;n++)for(int f=0;f<2;f++)for(unsigned s=0;s<4;s++) {
        for(int rust=0;rust<2;rust++) { int rc=one(types[t],a,v,ids[i],initializers[n],f,samples[s],0,rust);if(rc)return 20+rc; }
        ++pairs;
    }
    for(int kind=1;kind<=2;kind++)for(int rust=0;rust<2;rust++) {
        int rc=one(PERF_TYPE_RAW,0,1,0,0,0,9,kind,rust);if(rc)return 30+rc;
    }
    if(pairs!=1152)return 40;
    puts("PASS perf-allocation genuine-header ABI52; 1152 C/Rust pairs plus 4 null-boundary calls; ordered provider/error/publication/free/full-byte oracles");
    return 0;
}
