#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
void _ihk_mc_free_pages(void*,int,int,char*,int);
extern void x86_clear_free_pages_user_bridge(void*,int);
#include "actual-candidate-data.c.inc"
#define x86_clear_free_pages_user_bridge original_callback
#include "actual-original-callback.c.inc"
#undef x86_clear_free_pages_user_bridge
static void *seen; static int nr,flag,line,calls; static char *file;
void _ihk_mc_free_pages(void *a,int n,int f,char *s,int l) { seen=a; nr=n; flag=f; file=s; line=l; ++calls; }
int main(void) {
 uintptr_t storage[2]={0}; void *ptrs[]={NULL,storage,(void*)(uintptr_t)1,(void*)(uintptr_t)UINTPTR_MAX};
 int nums[]={INT_MIN,-22,-1,0,1,37,INT_MAX}; unsigned vectors=0;
 for(unsigned p=0;p<4;p++) for(unsigned n=0;n<7;n++) {
  calls=0; original_callback(ptrs[p],nums[n]);
  if(calls!=1 || seen!=ptrs[p] || nr!=nums[n] || flag!=1 || line!=1333 || strcmp(file,"/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/page-free-callback-4/preimage/arch/x86_64/kernel/memory.c")) return 1;
  calls=0; x86_clear_free_pages_user_bridge(ptrs[p],nums[n]);
  if(calls!=1 || seen!=ptrs[p] || nr!=nums[n] || flag!=1 || flag!=x86_clear_free_pages_user_flag || line!=x86_clear_free_pages_user_line || line!=1333 || strcmp(file,x86_clear_free_pages_user_file) || strcmp(file,"/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/page-free-callback-4/candidate/arch/x86_64/kernel/memory.c")) return 2;
  ++vectors;
 }
 printf("PASS %u exact callback pointer/signed-count/USER/file/line vectors; original C callsite and Rust C-data descriptor provenance checked separately\n",vectors);
 return 0;
}
