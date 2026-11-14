/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY: original selected C orchestration against the complete Rust entry.
 * Real project headers/layout; controlled host-safe mapping/allocation effects.
 */
#include "actual_real_abi.h"
extern int puts(const char *);
extern int printf(const char *,...);
extern int vsnprintf(char *,unsigned long,const char *,__builtin_va_list);
extern void *memset(void *,int,unsigned long);
extern int memcmp(const void *,const void *,unsigned long);
extern unsigned long strlen(const char *);
extern int original_C_vdso_map_global_pages(void);
extern int vdso_map_global_pages(void);
extern int x86_arch_setup_pvclock_body_result(void **,int *,int,unsigned long,
        unsigned long,int,unsigned long,int,char *,int,int (*)(void),
        void *(*)(int,int,unsigned long,int,int,unsigned long,char *,int),void (*)(int));
extern unsigned long x86_virt_to_phys_body_result(unsigned long,unsigned long,
        unsigned long,unsigned long,unsigned long,unsigned long,void (*)(int,unsigned long));
extern int ihk_mc_pt_set_page(void *,void *,unsigned long,enum ihk_mc_pt_attribute);
extern struct ddebug __start___verbose[],__stop___verbose[];
struct vdso vdso;
void *pvti;
int pvti_npages;
static unsigned long container_size;
static long vdso_offset;
static unsigned char pages[3*PAGE_SIZE] __attribute__((aligned(4096)));
static unsigned char scratch_canary[32];
struct config {
 int present,flags,count,setup_error,fail_at,map_error,mutate,address_case;
 int helper_mode,cpus,debug_flags;
};
static struct config cfg;
struct event { unsigned long kind,a,b,c,d; };
struct observation {
 struct event events[64];
 unsigned int events_used,maps,successes,failures,phys_calls,setups,allocs;
 char log[1024];unsigned long log_size;
 struct vdso final_vdso;void *final_pvti;int final_npages,result;
 unsigned char final_pages[sizeof pages];
};
static struct observation obs;
static unsigned long vaddr,source_addr;
static int problem;
#define CHECK(x) do { if (!(x)) {printf("FAIL line=%d vector=%d\n",__LINE__,problem);return 1;} } while(0)
static void event(unsigned long kind,unsigned long a,unsigned long b,unsigned long c,unsigned long d)
{
 if(obs.events_used>=64) __builtin_trap();
 obs.events[obs.events_used++]=(struct event){kind,a,b,c,d};
}
int kprintf(const char *fmt,...)
{
 __builtin_va_list ap;__builtin_va_start(ap,fmt);
 int n=vsnprintf(obs.log+obs.log_size,sizeof obs.log-obs.log_size,fmt,ap);
 __builtin_va_end(ap);
 if(n<0 || (unsigned long)n>=sizeof obs.log-obs.log_size) __builtin_trap();
 obs.log_size+=(unsigned long)n;return n;
}
void arch_vdso_state_bridge(struct vdso **v,unsigned long **s,long **o)
{
 *v=&vdso;*s=&container_size;*o=&vdso_offset;
}
static int available(void) { return cfg.helper_mode==2?0:1; }
static void *allocate_pages(int n,int align,unsigned long flag,int node,int kind,
        unsigned long max,char *file,int line)
{
 (void)file;(void)line;obs.allocs++;
 if(n<0 || n>3 || align!=0 || flag!=2 || node!=-1 || kind!=0 || max!=~0UL) __builtin_trap();
 return cfg.helper_mode==3?NULL:pages;
}
int fixture_setup(void)
{
 obs.setups++;event(2,(unsigned long)(long)cfg.setup_error,0,0,0);
 if(cfg.setup_error) return cfg.setup_error;
 if(cfg.helper_mode) {
  return x86_arch_setup_pvclock_body_result(&pvti,&pvti_npages,cfg.cpus,64,
          PAGE_SIZE,0,2,0,"fixture",0,available,allocate_pages,NULL);
 }
 /* This callback intentionally changes slots AFTER entry: both bodies must reload. */
 pvti=(void *)source_addr;pvti_npages=cfg.count;
 vdso.pvti_virt=(void *)vaddr;
 return 0;
}
int arch_setup_pvclock(void) { return fixture_setup(); }
unsigned long fixture_phys(void *source)
{
 obs.phys_calls++;
 unsigned long physical=x86_virt_to_phys_body_result((unsigned long)source,
       0xffffffff80000000UL,0x12345000UL,0xffff880000000000UL,
       0xffff860000000000UL,0xffff800000000000UL,NULL);
 event(3,(unsigned long)source,physical,0,0);return physical;
}
unsigned long virt_to_phys(void *source) { return fixture_phys(source); }
int x86_pt_set_page_bridge(void *pt,unsigned long virt,unsigned long phys,unsigned long attr)
{
 obs.maps++;event(1,(unsigned long)pt,virt,phys,attr);
 if(pt!=NULL) __builtin_trap();
 if(cfg.fail_at==(int)obs.maps) { obs.failures++;return cfg.map_error; }
 obs.successes++;
 /* Mutations are synchronous callback effects; no foreign thread/invalid lifetime. */
 if(cfg.mutate==1 && obs.maps==1) {
  vdso.hpet_virt=(void *)0xffff860000030000UL;
  vdso.hpet_phys=(long)0x87654000UL;
  vdso.hpet_is_global=1;
 }
 if(cfg.mutate==2 && obs.phys_calls==1) {
  pvti=(void *)(source_addr+0x20000UL);vdso.pvti_virt=(void *)(vaddr+0x30000UL);
  pvti_npages=cfg.count>1?2:cfg.count;
 }
 if(cfg.mutate==3 && obs.phys_calls==1) pvti_npages=0;
 return 0;
}
static void reset(void)
{
 memset(&vdso,0,sizeof vdso);memset(&obs,0,sizeof obs);memset(pages,0xa5,sizeof pages);
 memset(scratch_canary,0x6b,sizeof scratch_canary);
 vaddr=cfg.address_case?0xffffffff80008000UL:0xffff860000080000UL;
 source_addr=cfg.address_case?0xffffffff80012000UL:0xffff800000012000UL;
 vdso.vvar_virt=(cfg.present&1)?(void *)0xffff860000001000UL:NULL;
 vdso.hpet_virt=(cfg.present&2)?(void *)0xffff860000002000UL:NULL;
 vdso.pvti_virt=(cfg.present&4)?(void *)0xffff860000003000UL:NULL;
 vdso.vvar_phys=(long)0xfedcba9876543000UL;vdso.hpet_phys=(long)0x123456789ab000UL;
 vdso.vvar_is_global=(cfg.flags&1)?1:0;vdso.hpet_is_global=(cfg.flags&2)?-1:0;
 vdso.pvti_is_global=(cfg.flags&4)?127:0;
 /* Deliberately stale slots before setup, preserved if setup is skipped/errors. */
 pvti=(void *)0xffff8000000f0000UL;pvti_npages=7;
 container_size=0;vdso_offset=0;
 for(struct ddebug *d=__start___verbose;d<__stop___verbose;d++) d->flags=cfg.debug_flags;
}
static void save(struct observation *out,int result)
{
 obs.final_vdso=vdso;obs.final_pvti=pvti;obs.final_npages=pvti_npages;obs.result=result;
 __builtin_memcpy(obs.final_pages,pages,sizeof pages);*out=obs;
}
static int vector(void)
{
 struct observation old,new;reset();save(&old,original_C_vdso_map_global_pages());
 reset();save(&new,vdso_map_global_pages());
 CHECK(memcmp(&old,&new,sizeof old)==0);
 CHECK(old.successes+old.failures==old.maps);
 CHECK(old.failures<=1);
 CHECK(old.setups<=1 && old.allocs<=1);
 for(unsigned int i=0;i<old.events_used;i++) if(old.events[i].kind==1) {
  unsigned long attr=old.events[i].d;
  CHECK((attr&~PTATTR_UNCACHABLE)==(PTATTR_ACTIVE|PTATTR_USER|PTATTR_NO_EXECUTE));
 }
 for(unsigned int i=0;i<sizeof scratch_canary;i++) CHECK(scratch_canary[i]==0x6b);
 return 0;
}
int main(void)
{
 unsigned long descriptors=(unsigned long)(__stop___verbose-__start___verbose);
 CHECK(descriptors==4);
 const int counts[]={-1,0,1,3};
 /* 64 presence/global combinations x4 counts x3 setup results x6 first failures
  * x4 synchronous mutations x2 addresses =36864 exact whole-entry comparisons. */
 for(int present=0;present<8;present++) for(int flags=0;flags<8;flags++)
 for(int n=0;n<4;n++) for(int error=0;error<3;error++) for(int fail=0;fail<6;fail++)
 for(int mutate=0;mutate<4;mutate++) for(int address=0;address<2;address++) {
  cfg=(struct config){.present=present,.flags=flags,.count=counts[n],
    .setup_error=error==0?0:error==1?-5:17,.fail_at=fail,
    .map_error=(problem&1)?-12:23,.mutate=mutate,.address_case=address,
    .debug_flags=problem%3==0?0:problem%3==1?1:128};
  if(vector())return 1;problem++;
 }
 /* Actual host-safe Rust pvclock body executes allocation/zeroing only on pages[]. */
 const int processors[]={0,1,65,129};
 for(int mode=1;mode<=3;mode++) for(int p=0;p<4;p++) {
  cfg=(struct config){.present=7,.flags=7,.helper_mode=mode,.cpus=processors[p],.debug_flags=1};
  if(vector())return 1;problem++;
 }
 printf("PASS original_C_vs_public_Rust vectors=%d real_headers_vdso88_ddebug32 attr64 pvclock_actual_body12 controlled_map_virt\n",problem);
 return 0;
}
