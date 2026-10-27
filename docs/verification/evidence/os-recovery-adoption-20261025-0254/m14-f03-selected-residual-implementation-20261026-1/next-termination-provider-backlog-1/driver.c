/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST-only genuine atomic storage. Process release is an explicit identity mock.
 * No real process refcount/free/current-stack release, IRQ/MSR/CR/FSGS/context switch,
 * syscall, kernel/native action or concurrent atomic-ordering qualification. */
#include <types.h>
#include <string.h>
#include <arch-memory.h>
#include <registers.h>
#include <signal.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <ihk/lock.h>
#include <process.h>
#include <ihk/debug.h>
extern int puts(const char *);
extern int printf(const char *,...);
static struct process processes[3];static void *expected_release,*observed_release;static int release_calls,release_fault;
void f03_fixture_process_release(struct process *p){++release_calls;if(p!=expected_release||observed_release)release_fault=1;observed_release=p;}
#define release_process f03_fixture_process_release
#define wait_process_release_bridge original_wait_process_release_bridge
#include "01-wait-process-release-selected-1/original.C.inc"
#undef wait_process_release_bridge
#include "01-wait-process-release-selected-1/paired-selector.C.inc"
#ifndef wait_process_release_bridge
#error "This fixture must compile the actual selected C alias branch"
#endif
#define terminate_host_refcount_set_bridge original_terminate_host_refcount_set_bridge
#include "02-terminate-refcount-selected-1/original.C.inc"
#undef terminate_host_refcount_set_bridge
#include "02-terminate-refcount-selected-1/paired-selector.C.inc"
#ifndef terminate_host_refcount_set_bridge
#error "This fixture must compile the actual selected C alias branch"
#endif
#define terminate_mcexec_cmpxchg_bridge original_terminate_mcexec_cmpxchg_bridge
#include "03-terminate-cmpxchg-selected-1/original.C.inc"
#undef terminate_mcexec_cmpxchg_bridge
#include "03-terminate-cmpxchg-selected-1/paired-selector.C.inc"
#ifndef terminate_mcexec_cmpxchg_bridge
#error "This fixture must compile the actual selected C alias branch"
#endif
extern const unsigned long F03_TERMINATION_PROVIDER_ABI[16];
static int check_abi(void){const unsigned long c[16]={sizeof(ihk_atomic_t),__alignof__(ihk_atomic_t),__builtin_offsetof(ihk_atomic_t,counter),sizeof(unsigned long),__alignof__(unsigned long),sizeof(struct process),__alignof__(struct process),sizeof(void (*)(void *)),sizeof(void (*)(void *,int)),sizeof(unsigned long (*)(unsigned long *,unsigned long,unsigned long)),sizeof(int),__alignof__(int),sizeof(ihk_atomic_t),__alignof__(ihk_atomic_t),__builtin_offsetof(ihk_atomic_t,counter),sizeof(void *)};unsigned i;for(i=0;i<16;i++)if(c[i]!=F03_TERMINATION_PROVIDER_ABI[i]){printf("ABI FAIL %u C=%lu Rust=%lu\n",i,c[i],F03_TERMINATION_PROVIDER_ABI[i]);return 0;}return 1;}
struct int_probe {unsigned long before;ihk_atomic_t value[2];unsigned long after;};
struct ulong_probe {unsigned long before,value[2],after;};
static int atomic_set_pairs(void){const int values[8]={0,1,-1,2147483647,(-2147483647-1),0x12345678,0x76543210,-2};struct int_probe original,selected,expected;unsigned i,j,k,n=0;void (*selected_fn)(void *,int)=terminate_host_refcount_set_bridge;for(i=0;i<8;i++)for(j=0;j<8;j++)for(k=0;k<2;k++){__builtin_memset(&original,0,sizeof original);original.before=0x1122334455667788UL;original.after=0x8877665544332211UL;original.value[0].counter=values[i];original.value[1].counter=values[(i+1)%8];selected=expected=original;expected.value[k].counter=values[j];original_terminate_host_refcount_set_bridge(&original.value[k],values[j]);selected_fn(&selected.value[k],values[j]);if(memcmp(&original,&expected,sizeof original)||memcmp(&selected,&expected,sizeof selected)){printf("atomic-set FAIL %u\n",n);return 0;}++n;}return n==128;}
static int cas_pairs(void){const unsigned long values[10]={0,1,~0UL,1UL<<63,(1UL<<63)-1,0xffffffffUL,0x100000000UL,0x1122334455667788UL,0x8877665544332211UL,2};struct ulong_probe original,selected,expected;unsigned i,j,k,p,n=0;unsigned long a,b;unsigned long (*selected_fn)(unsigned long *,unsigned long,unsigned long)=terminate_mcexec_cmpxchg_bridge;if(selected_fn!=atomic_cmpxchg_ulong)return 0;for(i=0;i<10;i++)for(j=0;j<10;j++)for(k=0;k<10;k++)for(p=0;p<2;p++){original.before=0x13579bdf2468ace0UL;original.after=0x02468ace13579bdfUL;original.value[0]=values[i];original.value[1]=values[(i+1)%10];selected=expected=original;if(expected.value[p]==values[j])expected.value[p]=values[k];a=original_terminate_mcexec_cmpxchg_bridge(&original.value[p],values[j],values[k]);b=selected_fn(&selected.value[p],values[j],values[k]);if(a!=(p?values[(i+1)%10]:values[i])||a!=b||memcmp(&original,&expected,sizeof original)||memcmp(&selected,&expected,sizeof selected)){printf("CAS FAIL %u\n",n);return 0;}++n;}return n==2000;}
static int process_release_pairs(void){unsigned i;void (*selected_fn)(void *)=wait_process_release_bridge;for(i=0;i<3;i++){expected_release=&processes[i];observed_release=0;release_calls=release_fault=0;original_wait_process_release_bridge(expected_release);if(release_fault||release_calls!=1||observed_release!=expected_release)return 0;observed_release=0;release_calls=release_fault=0;selected_fn(expected_release);if(release_fault||release_calls!=1||observed_release!=expected_release)return 0;}return 1;}
int main(void){if(!check_abi()||!atomic_set_pairs()||!cas_pairs()||!process_release_pairs())return 1;puts("PASS termination-provider callbacks:128 atomic-set pairs +2000 CAS pairs +3 process-release identity pairs +16 ABI words; HOST atomics/mocked release only; real lifetime/current-stack ownership OPEN");return 0;}
