/* Exact selected helper gate; adapters capture diagnostic bytes, no syscall. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "native-boot-status-contract.h"
#define SYS_IOCTL 16
#define OS_STATUS 0x112a03
#define ARCH_LABEL "x86_64"
static long supplied;
static int accepted;
#if NATIVE_BOOT_CALLBACK_ABI2
static char diagnostic[1024];static size_t used;
static void message(const char *s) {size_t n=strlen(s);assert(n<sizeof diagnostic-used);memcpy(diagnostic+used,s,n);used+=n;diagnostic[used]=0;}
static void print_number(unsigned long n) {char s[32];int count=snprintf(s,sizeof s,"%lu",n);assert(count>0 && (size_t)count<sizeof s);message(s);}
#endif
static long call(long nr,long fd,long command,long arg) {assert(nr==SYS_IOCTL && fd==17 && command==OS_STATUS && arg==0);return supplied;}
#define require(condition) do { accepted=!!(condition); } while(0)
static int actual_gate(void) {long os=17;
#include "actual-status-gate.inc"
return accepted;}
int main(void) {
 const long cases[]={5,4,0,9,-5,2};
 for(unsigned i=0;i<sizeof cases/sizeof cases[0];i++) {
  supplied=cases[i];
#if NATIVE_BOOT_CALLBACK_ABI2
  used=0;diagnostic[0]=0;
#endif
  int result=actual_gate();
  assert(result==(supplied==(NATIVE_BOOT_CALLBACK_ABI2?5:4)));
  printf("STATUS_CASE {\"abi2\":%d,\"status\":%ld,\"accepted\":%d,\"diagnostic_hex\":\"",NATIVE_BOOT_CALLBACK_ABI2,supplied,result);
#if NATIVE_BOOT_CALLBACK_ABI2
  for(size_t n=0;n<used;n++)printf("%02x",(unsigned char)diagnostic[n]);
#endif
  puts("\"}");
 }
 return 0;
}
