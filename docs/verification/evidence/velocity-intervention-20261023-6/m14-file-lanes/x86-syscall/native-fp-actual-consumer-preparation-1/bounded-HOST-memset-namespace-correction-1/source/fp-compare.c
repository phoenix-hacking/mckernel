/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Real ABI/original-C/public-Rust orchestration. Hardware XRSTOR/reset, allocation
 * and user-copy endpoints are explicit HOST controls. No raw user/CPU access.
 */
#include <types.h>
#include <kmalloc.h>
#include <errno.h>
#include <memory.h>
extern int printf(const char *,...);
extern void *memcpy(void *,const void *,size_t);
extern void *fixture_host_byte_memset(void *,int,size_t) __asm__("memset");
extern int memcmp(const void *,const void *,size_t);
extern long arch_native_signal_restore_fp_bridge(unsigned long,int);
extern unsigned long fixture_fp_actual_Rust_ABI(unsigned long);
extern long native_xstate_buffer_size_result(int,int);
extern long native_xstate_validate_result(const unsigned char *,size_t,int,uint64_t,unsigned int);
extern long native_xrstor_checked(const unsigned char *,uint64_t);
extern unsigned int arch_native_signal_mxcsr_mask_bridge(void);
extern long arch_native_signal_reset_fp_bridge(void);
extern int get_xsave_size(void);
extern uint64_t get_xsave_mask(void);
_Static_assert(sizeof(long)==8 && sizeof(void *)==8 && sizeof(int)==4,"realLP64");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_native_signal_restore_fp_bridge),long (*)(unsigned long,int)),"actualentryABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kmalloc_tracked),void *(*)(int,ihk_mc_ap_flag,char *,int)),"actualtrackedallocatorABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&copy_from_user),int (*)(void *,const void *,size_t)),"actualusercopyABI");
_Static_assert(IHK_MC_AP_NOWAIT==2,"realNOWAIT");
#define arch_native_signal_restore_fp_bridge original_C_restore_fp
#include "original-C-entry.ACTUAL.inc"
#undef arch_native_signal_restore_fp_bridge

struct scenario {unsigned long address;int provided,configured,offset,alloc_fails,copy_result;uint64_t features;unsigned int mxcsr_mask;long restore_result;int bad_header;long expected;};
struct event {unsigned long kind,a,b,c;};
struct observation {struct event events[12];unsigned long used,getters,allocs,copies,masks,mxcsrs,resets,restores,frees,bytes,payload;long result;};
static struct observation obs,original,rust;
static struct scenario cfg;
static unsigned char arena[65536+256] __attribute__((aligned(64)));
static unsigned char user_bytes[65536] __attribute__((aligned(64)));
static void *owned_base;
static unsigned char *expected_aligned;
static unsigned long expected_bytes,vector;
static int owned;
static void require(int good){if(!good)__builtin_trap();}
static void emit(unsigned long k,unsigned long a,unsigned long b,unsigned long c)
{require(obs.used<12);obs.events[obs.used++]=(struct event){k,a,b,c};}
static unsigned long checksum(const unsigned char *p,unsigned long n)
{unsigned long h=1469598103934665603UL;for(unsigned long i=0;i<n;i++)h=(h^p[i])*1099511628211UL;return h;}
int get_xsave_size(void){obs.getters++;emit(1,(unsigned long)(long)cfg.configured,0,0);return cfg.configured;}
long arch_native_signal_reset_fp_bridge(void)
{require(obs.getters==1 && obs.used==1);obs.resets++;emit(2,0,0,0);return cfg.restore_result;}
void *kmalloc_tracked(int size,ihk_mc_ap_flag flags,char *file,int line)
{
 require(!owned && flags==IHK_MC_AP_NOWAIT && file && file[0] && line>0);
 require(size==(int)(expected_bytes+63));obs.allocs++;emit(3,(unsigned long)size,flags,0);
 if(cfg.alloc_fails)return NULL;
 owned=1;owned_base=arena+64+cfg.offset;expected_aligned=(unsigned char *)(((unsigned long)owned_base+63)&~63UL);
 require(expected_aligned>=(unsigned char *)owned_base && expected_aligned+expected_bytes<=(unsigned char *)owned_base+size);
 return owned_base;
}
int copy_from_user(void *dst,const void *src,size_t size)
{
 require(owned && dst==expected_aligned && src==user_bytes && size==expected_bytes);
 obs.copies++;emit(4,(unsigned long)dst-(unsigned long)owned_base,size,(unsigned long)(long)cfg.copy_result);
 memcpy(dst,src,cfg.copy_result?size/2:size);return cfg.copy_result;
}
uint64_t get_xsave_mask(void)
{require(owned && obs.copies==1 && cfg.copy_result==0);obs.masks++;emit(5,cfg.features,0,0);return cfg.features;}
unsigned int arch_native_signal_mxcsr_mask_bridge(void)
{require(owned && obs.masks==1);obs.mxcsrs++;emit(6,cfg.mxcsr_mask,0,0);return cfg.mxcsr_mask;}
long native_xrstor_checked(const unsigned char *p,uint64_t mask)
{
 require(owned && p==expected_aligned && ((unsigned long)p&63)==0 && mask==cfg.features);
 require(obs.masks==1 && obs.mxcsrs==1 && memcmp(p,user_bytes,expected_bytes)==0);
 obs.restores++;obs.payload=checksum(p,expected_bytes);emit(7,mask,expected_bytes,obs.payload);return cfg.restore_result;
}
void kfree_tracked(void *p,char *file,int line)
{
 require(owned && p==owned_base && file && file[0] && line>0);
 for(unsigned long i=0;i<sizeof arena;i++)
  if(arena+i<expected_aligned || arena+i>=expected_aligned+expected_bytes)require(arena[i]==0xa5);
 obs.frees++;emit(8,(unsigned long)p-(unsigned long)(arena+64),0,0);owned=0;
}
static void prepare(void)
{
 fixture_host_byte_memset(&obs,0,sizeof obs);fixture_host_byte_memset(arena,0xa5,sizeof arena);fixture_host_byte_memset(user_bytes,0,sizeof user_bytes);
 owned=0;owned_base=NULL;expected_aligned=NULL;expected_bytes=cfg.configured>=576 && cfg.configured<=65536?(unsigned long)cfg.configured:0;
 user_bytes[24]=0x80;user_bytes[25]=0x1f;user_bytes[512]=3;
 if(cfg.bad_header==1)user_bytes[26]=1;
 if(cfg.bad_header==2)user_bytes[512]=4;
 if(cfg.bad_header==3)user_bytes[520]=1;
 if(cfg.bad_header==4)user_bytes[528]=1;
}
static int compare(struct scenario s)
{
 cfg=s;prepare();unsigned long address=cfg.address?(unsigned long)user_bytes:0;
 obs.result=original_C_restore_fp(address,cfg.provided);original=obs;require(!owned);
 prepare();obs.result=arch_native_signal_restore_fp_bridge(address,cfg.provided);rust=obs;require(!owned);
 if(memcmp(&original,&rust,sizeof original)!=0 || rust.result!=cfg.expected || rust.getters!=1){
  printf("FAIL native_fp vector=%lu resultC=%ld resultRust=%ld expected=%ld eventsC=%lu eventsRust=%lu\n",vector,original.result,rust.result,cfg.expected,original.used,rust.used);return 1;
 }
 if(cfg.address==0){require(rust.resets==1 && rust.used==2 && rust.allocs==0 && rust.frees==0);}
 else if(rust.allocs==0){require(rust.frees==0 && rust.restores==0);}
 else if(cfg.alloc_fails){require(rust.allocs==1 && rust.copies==0 && rust.frees==0);}
 else {require(rust.allocs==1 && rust.frees==1 && rust.copies==1);if(cfg.copy_result)require(rust.masks==0 && rust.mxcsrs==0 && rust.restores==0);}
 vector++;return 0;
}
int main(void)
{
 unsigned long abi[]={sizeof(int),sizeof(long),sizeof(unsigned long),sizeof(size_t),sizeof(void *),IHK_MC_AP_NOWAIT,65536+63};
 for(unsigned long i=0;i<sizeof abi/sizeof abi[0];i++)if(abi[i]!=fixture_fp_actual_Rust_ABI(i))return 1;
 static const struct scenario base[]={
 {0,576,576,0,0,0,3,0xffbf,0,0,0},
 {0,0,0,0,0,0,3,0xffbf,-95,0,-95},
 {1,-1,576,0,0,0,3,0xffbf,0,0,-22},
 {1,511,511,0,0,0,3,0xffbf,0,0,-22},
 {1,65537,65537,0,0,0,3,0xffbf,0,0,-7},
 {1,576,576,1,1,0,3,0xffbf,0,0,-12},
 {1,576,576,31,0,-14,3,0xffbf,0,0,-14},
 {1,576,576,63,0,3,3,0xffbf,0,0,-14},
 {1,576,576,0,0,0,3,0xffbf,0,0,0},
 {1,576,576,1,0,0,1,0xffbf,0,0,-22},
 {1,576,576,31,0,0,3,0,0,0,-22},
 {1,576,576,63,0,0,3,0x10000,0,0,-22},
 {1,576,576,1,0,0,3,0xffbf,-14,0,-14},
 {1,832,832,31,0,0,3,0xffbf,7,0,7},
 {1,65536,65536,63,0,0,3,0xffbf,0,0,0},
 {1,832,576,0,0,0,3,0xffbf,0,0,-22},
 };
 for(unsigned long i=0;i<sizeof base/sizeof base[0];i++){if(compare(base[i]))return 1;}
 for(int offset=0;offset<64;offset++)for(int header=0;header<5;header++){
  struct scenario s={1,832,832,offset,0,0,3,0xffbf,0,header,header?-22:0};
  if(compare(s))return 1;
 }
 printf("PASS native_fp selected_C_public_Rust=%lu base16=1 allocation_residues64=1 header_variants5=1 actual_ABI7=1 genuine_native_xstate=1 controlled_alloc_copy_reset_XRSTOR=1\n",vector);
 return vector==336?0:1;
}
