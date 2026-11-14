/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <sys/types.h>
struct list_head { struct list_head *next,*prev; };
#include "page.h"
_Static_assert(sizeof(struct page)==80 && _Alignof(struct page)==8,"page ABI");
_Static_assert(offsetof(struct page,hash)==16 && offsetof(struct page,phys)==40 && offsetof(struct page,count)==48,"page offsets");
#ifndef FIXTURE_LOCK_WORDS
#define FIXTURE_LOCK_WORDS 3
#endif
/* Controlled lock storage is deliberately opaque to Rust; geometry is C-owned. */
typedef struct { unsigned long opaque[FIXTURE_LOCK_WORDS]; } ihk_spinlock_t;
#define PHYS_PAGE_HASH_SIZE 1024
#define PHYS_PAGE_HASH_MASK (PHYS_PAGE_HASH_SIZE-1)
#define PAGE_SHIFT 12
ihk_spinlock_t page_hash_locks[PHYS_PAGE_HASH_SIZE];
typedef unsigned long (*page_hash_lock_fn_t)(unsigned long);
typedef void (*page_hash_unlock_fn_t)(unsigned long,unsigned long);
typedef int (*page_unmap_orchestrate_fn_t)(struct page *,unsigned long,int,uint64_t,unsigned long,page_hash_lock_fn_t,page_hash_unlock_fn_t);
typedef void (*page_unmap_log_fn_t)(int,struct page *,int);
extern int page_unmap_body_result(struct page *,unsigned long,int,uint64_t,unsigned long,page_hash_lock_fn_t,page_hash_unlock_fn_t,page_unmap_orchestrate_fn_t,page_unmap_log_fn_t);
extern int page_unmap_orchestrate_result(struct page *,unsigned long,int,uint64_t,unsigned long,page_hash_lock_fn_t,page_hash_unlock_fn_t);
static struct page *active;
static int held,initial_count,locks,unlocks,nlog;
static char events[8];
static void event(char c) { if(nlog>=7) abort(); events[nlog++]=c; events[nlog]=0; }
static unsigned long ihk_mc_spinlock_lock(ihk_spinlock_t *lock) {
 if(held || !active || active->count.counter!=initial_count || lock!=&page_hash_locks[(active->phys>>PAGE_SHIFT)&PHYS_PAGE_HASH_MASK]) abort();
 held=1;locks++;event('K');return 0x1234abcUL;
}
static void ihk_mc_spinlock_unlock(ihk_spinlock_t *lock,unsigned long flags) {
 if(!held || flags!=0x1234abcUL || active->count.counter!=initial_count-1 || lock!=&page_hash_locks[(active->phys>>PAGE_SHIFT)&PHYS_PAGE_HASH_MASK]) abort();
 held=0;unlocks++;event('U');
}
#define PAGE_UNMAP_PUBLIC_BRIDGE
#include "public_lock_callbacks.c.inc"
#define PAGE_UNMAP_LOG_ENTER 1
#define PAGE_UNMAP_LOG_STILL_MAPPED 2
#define PAGE_UNMAP_LOG_UNMAPPED 3
static void test_log(const char *fmt,...) {
 if(held) abort();
 event(strstr(fmt,"): 0")?'S':strstr(fmt,"): %d")?'R':'E');
}
#define dkprintf(...) test_log(__VA_ARGS__)
#include "public_log_callback.c.inc"
#include "public_geometry.c.inc"
#define page_unmap original_page_unmap
#include "original_page_unmap.c.inc"
#undef page_unmap
static unsigned invocations;
static int one(int rust,int count,uint64_t phys,unsigned char mode) {
 struct list_head head; struct page page={0};
 head.next=head.prev=&page.hash;page.hash.next=page.hash.prev=&head;
 page.list.next=page.list.prev=&page.list;page.count.counter=count;page.phys=phys;page.mode=mode;page.mapped.counter64=71;page.offset=123;page.pgshift=21;
 active=&page;initial_count=count;held=locks=unlocks=nlog=0;events[0]=0;
 int ret=rust?page_unmap(&page):original_page_unmap(&page);
 if(held || locks!=1 || unlocks!=1 || page.count.counter!=count-1 || ret!=(count==1) || strcmp(events,count==1?"EKUR":"EKUS")) abort();
 if(page.phys!=phys || page.mode!=mode || page.mapped.counter64!=71 || page.offset!=123 || page.pgshift!=21 || page.list.next!=&page.list || page.list.prev!=&page.list) abort();
 if(count==1) {
  if(head.next!=&head || head.prev!=&head || (uintptr_t)page.hash.next!=0x100129 || (uintptr_t)page.hash.prev!=0x200229) abort();
 } else if(head.next!=&page.hash || head.prev!=&page.hash || page.hash.next!=&head || page.hash.prev!=&head) abort();
 ++invocations;return ret;
}
int main(void) {
 int counts[]={1,2,3,INT_MAX};uint64_t phys[]={0,0x1000,0x3ff000,0x400000,UINT64_MAX&~0xfffULL};unsigned char modes[]={0,7};
 for(unsigned i=0;i<4;i++)for(unsigned j=0;j<5;j++)for(unsigned k=0;k<2;k++)if(one(0,counts[i],phys[j],modes[k])!=one(1,counts[i],phys[j],modes[k]))abort();
 active=NULL;held=locks=unlocks=nlog=0;
 if(original_page_unmap(NULL)!=0 || page_unmap(NULL)!=0 || held || locks || unlocks || nlog)abort();
 printf("PASS original C/public Rust actual bodies: %u ownership invocations +2 NULL; lock stride %zu; exact lock/unlock/log order; refcount and unlink preserved\n",invocations,sizeof(page_hash_locks[0]));
 return 0;
}
