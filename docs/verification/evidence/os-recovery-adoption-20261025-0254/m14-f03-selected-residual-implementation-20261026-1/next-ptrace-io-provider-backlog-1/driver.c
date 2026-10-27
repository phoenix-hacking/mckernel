/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST-only exact callback forwarding. find_thread/thread_unlock/copy_from_user
 * are explicit identity/normal-buffer mocks. No actual tracee lookup, unlock,
 * usercopy/fault, refcount/current-stack release, IRQ/MSR/CR/FSGS/context switch,
 * syscall, kernel/native action, or ptrace_setsiginfo transaction. */
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
static struct thread threads[3];static struct thread *find_result,*unlock_expected,*unlock_observed;
static int expected_tgid,expected_tid,calls,fault,copy_result,partial;
static unsigned char source[128],dest[128],expected_dest[128],original_dest[128];
static const void *expected_src;static void *expected_dst;static size_t expected_bytes;
struct thread *f03_fixture_find(int tgid,int tid){++calls;if(tgid!=expected_tgid||tid!=expected_tid)fault=1;return find_result;}
void f03_fixture_unlock(struct thread *t){++calls;if(t!=unlock_expected||unlock_observed)fault=1;unlock_observed=t;}
int f03_fixture_copy(void *dst,const void *src,size_t bytes){size_t copied;++calls;if(dst!=expected_dst||src!=expected_src||bytes!=expected_bytes){fault=1;return -EFAULT;}copied=copy_result?(partial?bytes/2:0):bytes;__builtin_memcpy(dst,src,copied);return copy_result;}
#define find_thread f03_fixture_find
#define thread_unlock f03_fixture_unlock
#define copy_from_user f03_fixture_copy
#define ptrace_find_thread_bridge original_ptrace_find_thread_bridge
#include "01-ptrace-find-selected-1/original.C.inc"
#undef ptrace_find_thread_bridge
#include "01-ptrace-find-selected-1/paired-selector.C.inc"
#ifndef ptrace_find_thread_bridge
#error "Actual selected C alias branch required for this callback fixture"
#endif
#define ptrace_thread_unlock_bridge original_ptrace_thread_unlock_bridge
#include "02-ptrace-unlock-selected-1/original.C.inc"
#undef ptrace_thread_unlock_bridge
#include "02-ptrace-unlock-selected-1/paired-selector.C.inc"
#ifndef ptrace_thread_unlock_bridge
#error "Actual selected C alias branch required for this callback fixture"
#endif
#define ptrace_copy_from_user_bridge original_ptrace_copy_from_user_bridge
#include "03-ptrace-copy-from-selected-1/original.C.inc"
#undef ptrace_copy_from_user_bridge
#include "03-ptrace-copy-from-selected-1/paired-selector.C.inc"
#ifndef ptrace_copy_from_user_bridge
#error "Actual selected C alias branch required for this callback fixture"
#endif
extern const unsigned long F03_PTRACE_IO_PROVIDER_ABI[16];
static int check_abi(void){const unsigned long c[16]={sizeof(struct thread),__alignof__(struct thread),sizeof(int),__alignof__(int),sizeof(long),__alignof__(long),sizeof(unsigned long),__alignof__(unsigned long),sizeof(size_t),__alignof__(size_t),sizeof(void *),__alignof__(void *),sizeof(unsigned long (*)(int,int)),sizeof(void (*)(unsigned long)),sizeof(long (*)(void *,unsigned long,size_t)),__builtin_offsetof(struct thread,proc)};unsigned i;for(i=0;i<16;i++)if(c[i]!=F03_PTRACE_IO_PROVIDER_ABI[i]){printf("ABI FAIL %u C=%lu Rust=%lu\n",i,c[i],F03_PTRACE_IO_PROVIDER_ABI[i]);return 0;}return 1;}
static int find_pairs(void){const int tgids[5]={0,1,-1,2147483647,(-2147483647-1)},tids[6]={0,1,2,-1,2147483647,(-2147483647-1)};unsigned i,j,m,n=0;unsigned long a,b;unsigned long (*selected_fn)(int,int)=ptrace_find_thread_bridge;for(i=0;i<5;i++)for(j=0;j<6;j++)for(m=0;m<3;m++){expected_tgid=tgids[i];expected_tid=tids[j];find_result=m?&threads[m-1]:0;calls=fault=0;a=original_ptrace_find_thread_bridge(expected_tgid,expected_tid);if(calls!=1||fault||a!=(unsigned long)find_result)return 0;calls=fault=0;b=selected_fn(expected_tgid,expected_tid);if(calls!=1||fault||b!=a)return 0;++n;}return n==90;}
static int unlock_pairs(void){unsigned i;void (*selected_fn)(unsigned long)=ptrace_thread_unlock_bridge;for(i=0;i<3;i++){unlock_expected=&threads[i];unlock_observed=0;calls=fault=0;original_ptrace_thread_unlock_bridge((unsigned long)unlock_expected);if(calls!=1||fault||unlock_observed!=unlock_expected)return 0;unlock_observed=0;calls=fault=0;selected_fn((unsigned long)unlock_expected);if(calls!=1||fault||unlock_observed!=unlock_expected)return 0;}return 1;}
static int copy_pairs(void){const size_t sizes[6]={0,1,7,8,31,64};const int returns[5]={0,-EFAULT,1,2147483647,(-2147483647-1)};unsigned s,o,e,p,i,n=0;size_t count;long a,b;long (*selected_fn)(void *,unsigned long,size_t)=ptrace_copy_from_user_bridge;if(selected_fn!=syscall_copy_from_user_bridge)return 0;for(s=0;s<6;s++)for(o=0;o<2;o++)for(e=0;e<5;e++)for(p=0;p<2;p++){if(!e&&p)continue;for(i=0;i<128;i++){source[i]=(unsigned char)(i*17+3);dest[i]=expected_dest[i]=0xa5;}expected_src=source+o*3;expected_dst=dest+o*3;expected_bytes=sizes[s];copy_result=returns[e];partial=p;count=copy_result?(partial?expected_bytes/2:0):expected_bytes;__builtin_memcpy(expected_dest+o*3,source+o*3,count);calls=fault=0;a=original_ptrace_copy_from_user_bridge(expected_dst,(unsigned long)expected_src,expected_bytes);if(calls!=1||fault||a!=(long)copy_result||memcmp(dest,expected_dest,sizeof dest))return 0;__builtin_memcpy(original_dest,dest,sizeof dest);__builtin_memset(dest,0xa5,sizeof dest);calls=fault=0;b=selected_fn(expected_dst,(unsigned long)expected_src,expected_bytes);if(calls!=1||fault||b!=a||memcmp(dest,original_dest,sizeof dest)){printf("copy forwarding FAIL %u\n",n);return 0;}for(i=0;i<128;i++)if(source[i]!=(unsigned char)(i*17+3))return 0;++n;}return n==108;}
int main(void){if(!check_abi()||!find_pairs()||!unlock_pairs()||!copy_pairs())return 1;puts("PASS ptrace-IO provider callbacks:90 find pairs +3 unlock identities +108 copy forwarding pairs +16 ABI words; explicit HOST mocks only; real tracee/usercopy/lifetime/setsiginfo ownership OPEN");return 0;}
