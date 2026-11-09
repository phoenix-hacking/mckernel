#define _GNU_SOURCE
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
_Static_assert(sizeof(void *)==8&&sizeof(size_t)==8&&sizeof(int)==4,"selected C ABI LP64 widths");
_Static_assert(__builtin_types_compatible_p(__typeof__(&memset),void *(*)(void *,int,size_t)),"actual C memset prototype");
_Static_assert(__builtin_types_compatible_p(__typeof__(&strnlen),size_t (*)(const char *,size_t)),"actual C strnlen prototype");
static void seed(unsigned char *storage){for(size_t i=0;i<16;i++)((volatile unsigned char *)storage)[i]=0xa5;}
static void fill_case(unsigned char *storage,size_t offset,int value,size_t count){
 seed(storage);void *result=memset(storage+offset,value,count);assert(result==storage+offset);
 for(size_t i=0;i<16;i++){unsigned char expected=i>=offset&&i<offset+count?(unsigned char)value:0xa5;assert(storage[i]==expected);}
 printf("C-ABI memset offset=%zu count=%zu int=%d low-byte=%u return-original=1 owned-prefix-suffix-unchanged=1\n",offset,count,value,(unsigned)(unsigned char)value);
}
int main(void){
 const char empty[]={0};const char abc[]={'a','b','c',0};const char *inputs[]={empty,abc};const size_t limits[]={0,2,3,8};
 for(size_t input=0;input<2;input++)for(size_t i=0;i<4;i++){
  size_t expected=input?(limits[i]<3?limits[i]:3):0;size_t result=strnlen(inputs[input],limits[i]);assert(result==expected);
  /* Every actual condition-read byte is readable, including maxlen==0 and
   * the byte at the limit. Both retained input arrays contain a real NUL. */
  assert(empty[0]==0&&abc[0]=='a'&&abc[1]=='b'&&abc[2]=='c'&&abc[3]==0);
  printf("C-ABI strnlen input=%s limit=%zu result=%zu retained-readable-NUL-input=1\n",input?"abc":"empty",limits[i],result);
 }
 unsigned char *storage=malloc(16);assert(storage);fill_case(storage,4,0x123,0);fill_case(storage,3,0x123,5);fill_case(storage,2,-1,5);free(storage);
 puts("ordinary HOST C-ABI observations complete; genuine kernel roots only; no kernel state/native acceptance");return 0;
}
