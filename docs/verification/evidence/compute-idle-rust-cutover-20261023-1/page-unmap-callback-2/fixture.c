#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <limits.h>
struct page;
int page_unmap(struct page *page);
extern int x86_clear_page_unmap_bridge(void *);
extern int actual_body(struct page *, int);
#define x86_clear_page_unmap_bridge original_callback
#include "original_callback.c.inc"
#undef x86_clear_page_unmap_bridge
static struct page *seen;
static int supplied, calls, body;
int page_unmap(struct page *page) {
    seen=page; ++calls;
    return body ? actual_body(page,supplied) : supplied;
}
int main(void) {
    uintptr_t storage[10]={0};
    void *ptrs[]={NULL, storage, (void *)(uintptr_t)1, (void *)(uintptr_t)UINTPTR_MAX};
    int values[]={0,1,-1,INT_MIN,INT_MAX,37,-22};
    unsigned cases=0;
    for (unsigned p=0;p<4;p++) for(unsigned i=0;i<7;i++) {
        supplied=values[i]; calls=0; int a=original_callback(ptrs[p]);
        if(calls!=1 || seen!=ptrs[p] || a!=supplied) return 1;
        calls=0; int b=x86_clear_page_unmap_bridge(ptrs[p]);
        if(calls!=1 || seen!=ptrs[p] || b!=a) return 2;
        ++cases;
    }
    body=1;
    for(unsigned p=0;p<2;p++) for(unsigned i=0;i<7;i++) {
        supplied=values[i]; calls=0; int a=original_callback(ptrs[p]);
        if(calls!=1 || seen!=ptrs[p]) return 3;
        calls=0; int b=x86_clear_page_unmap_bridge(ptrs[p]);
        if(calls!=1 || seen!=ptrs[p] || b!=a || b!=(p && supplied!=0)) return 4;
        ++cases;
    }
    printf("PASS callback ABI: %u vectors; original C vs Rust; 14 unchanged page_unmap_body_result vectors\n",cases);
    return 0;
}
