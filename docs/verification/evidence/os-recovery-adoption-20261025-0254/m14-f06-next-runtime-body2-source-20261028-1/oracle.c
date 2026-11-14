/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#define IHK_MC_AP_NOWAIT 0x2UL
static _Alignas(64) unsigned char storage[65536+128];
static uint64_t events[96];
static size_t count;
static int configured_value,provided_value,alloc_failure,copy_result,alignment;
static long size_result,validation_result,restore_result;
static const uint64_t mask_value=0x80000000fedcba98UL;
static const unsigned int mxcsr_value=0xfedcba98U;
static void note(uint64_t x) { events[count++]=x; }
int fixture_configured(void) {note(1);note((uint32_t)configured_value);return configured_value;}
long fixture_bytes(int provided,int configured) {note(2);note((uint32_t)provided);note((uint32_t)configured);return size_result;}
long fixture_reset_fp(void) {note(3);return restore_result;}
void *fixture_alloc(size_t bytes) {note(4);note(bytes);return alloc_failure?NULL:storage+alignment;}
int fixture_copy(void *dest,const void *source,size_t bytes) {
 note(5);note((uintptr_t)dest);note((uintptr_t)source);note(bytes);
 for(size_t i=0;i<bytes;i++)((unsigned char*)dest)[i]=(unsigned char)(i*17+3);
 return copy_result;
}
uint64_t fixture_mask(void) {note(6);return mask_value;}
unsigned int fixture_mxcsr(void) {note(7);return mxcsr_value;}
long fixture_validate(const unsigned char *buffer,size_t bytes,int configured,uint64_t mask,unsigned int mxcsr) {
 note(8);note((uintptr_t)buffer);note(bytes);note((uint32_t)configured);note(mask);note(mxcsr);return validation_result;
}
long fixture_restore(const unsigned char *buffer,uint64_t mask) {note(9);note((uintptr_t)buffer);note(mask);return restore_result;}
void fixture_free(void *pointer) {note(10);note((uintptr_t)pointer);}
static void *fixture_tracked_alloc(int bytes,unsigned long flags,char *file,int line) {
 (void)file;(void)line; /* Real ABI/source metadata has a separate genuine-header gate. */
 if(flags!=0x2UL)return NULL;
 return fixture_alloc((size_t)bytes);
}
static void fixture_tracked_free(void *pointer,char *file,int line) {(void)file;(void)line;fixture_free(pointer);}
#define get_xsave_size fixture_configured
#define get_xsave_mask fixture_mask
#define native_xstate_buffer_size_result fixture_bytes
#define arch_native_signal_reset_fp_bridge fixture_reset_fp
#define kmalloc_tracked fixture_tracked_alloc
#define kfree_tracked fixture_tracked_free
#define copy_from_user fixture_copy
#define arch_native_signal_mxcsr_mask_bridge fixture_mxcsr
#define native_xstate_validate_result fixture_validate
#define native_xrstor_checked fixture_restore
#include "original-restore-fp.c.inc"
void fixture_reset(long bytes,int failalloc,int copy,long validate,long restore,int align) {
 memset(storage,0xa5,sizeof(storage));memset(events,0,sizeof(events));count=0;
 configured_value=576;provided_value=512;size_result=bytes;alloc_failure=failalloc;
 copy_result=copy;validation_result=validate;restore_result=restore;alignment=align;
}
long fixture_run_c(unsigned long user) {return arch_native_signal_restore_fp_bridge(user,provided_value);}
struct snapshot { unsigned char storage[65536+128];uint64_t events[96];uint64_t count; };
void fixture_snapshot(struct snapshot *out) {memcpy(out->storage,storage,sizeof(storage));memcpy(out->events,events,sizeof(events));out->count=count;}
