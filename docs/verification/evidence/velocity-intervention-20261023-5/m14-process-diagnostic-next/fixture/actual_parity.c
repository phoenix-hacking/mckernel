/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Real original C body and headers; actual staged Rust body with test-only symbol.
 */
#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
#include <string.h>
/* Known hosted provider boundary: preserve headers/types; libc owns memset. */
#undef memset

_Static_assert(__builtin_types_compatible_p(__typeof__(((struct vm_range *)0)->flag),unsigned long),"preserve original UL variadic flag, including %x callsite");
extern int printf(const char *,...);
extern void exit(int);
extern void fixture_rust_vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);
extern void fixture_log_layout(unsigned long *);
extern struct ddebug __start___verbose[],__stop___verbose[];

struct trace { int calls,kind; char format[96]; unsigned long args[7]; };
static struct trace trace;
static int logger_return, live;
static unsigned long cases;
static const char overlap_format[]="vm_range_insert(%p,%lx-%lx %x): overlap %lx-%lx %lx\n";
static const char success_format[]="vm_range_insert: %p,%p: %lx-%lx %x\n";
static void need(int ok,int line) {
    if (!ok) { printf("FAIL functional process log fixture line=%d cases=%lu\n",line,cases); exit(1); }
}
#define CHECK(x) need(!!(x),__LINE__)

int kprintf(const char *format,...) {
    __builtin_va_list args;
    CHECK(live && trace.calls==0);
    trace.calls++;
    CHECK(strlen(format)<sizeof(trace.format)); strcpy(trace.format,format);
    __builtin_va_start(args,format);
    trace.args[0]=(unsigned long)__builtin_va_arg(args,void *);
    if (!strcmp(format,overlap_format)) {
        trace.kind=1;
        for (int i=1;i<7;i++) trace.args[i]=__builtin_va_arg(args,unsigned long);
    } else {
        CHECK(!strcmp(format,success_format)); trace.kind=2;
        trace.args[1]=(unsigned long)__builtin_va_arg(args,struct vm_range *);
        for (int i=2;i<5;i++) trace.args[i]=__builtin_va_arg(args,unsigned long);
    }
    __builtin_va_end(args);
    return logger_return;
}

#line 2076 "/src/kernel/process.c"
/* Keep the displaced dynamic-debug selector as declarative C ABI data.
 * Rust owns both event branches, field reads and the existing variadic logger.
 * The source-bound original success callsite remains selectable at line 2086.
 */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_vm_range_insert_debug = {
    .file = __FILE__,
    .func = "vm_range_insert_log_bridge",
    .line = 2086,
    .flags = DDEBUG_DEFAULT,
};

#line 1 "functional-process-log-fixture"

#define PROCESS_SCHED_PUBLIC_BRIDGE
#line 2076 "/src/kernel/process.c"
PROCESS_SCHED_PUBLIC_BRIDGE void vm_range_insert_log_bridge(int event, struct process_vm *vm,
				       struct vm_range *newrange,
				       struct vm_range *range)
{
	if (event == PROCESS_VM_RANGE_INSERT_LOG_OVERLAP) {
		ekprintf("vm_range_insert(%p,%lx-%lx %x): overlap %lx-%lx %lx\n",
				vm, newrange->start, newrange->end, newrange->flag,
				range->start, range->end, range->flag);
	}
	else if (event == PROCESS_VM_RANGE_INSERT_LOG_SUCCESS) {
		dkprintf("vm_range_insert: %p,%p: %lx-%lx %x\n", vm,
				newrange, newrange->start, newrange->end,
				newrange->flag);
	}
}

#line 1 "functional-process-log-fixture"


static void selectors(unsigned int flags) {
    int found=0;
    for (struct ddebug *d=__start___verbose;d<__stop___verbose;d++) {
        CHECK(!strcmp(d->file,"/src/kernel/process.c"));
        CHECK(!strcmp(d->func,"vm_range_insert_log_bridge"));
        CHECK(d->fmt==0 && d->line==2086);
        d->flags=flags; found++;
    }
    CHECK(found==2 && process_vm_range_insert_debug.flags==flags);
}

static struct trace invoke(int rust,int event,struct process_vm *vm,
        struct vm_range *newrange,struct vm_range *oldrange) {
    struct trace result;
    memset(&trace,0,sizeof(trace));live=1;
    if (rust) fixture_rust_vm_range_insert_log_bridge(event,vm,newrange,oldrange);
    else vm_range_insert_log_bridge(event,vm,newrange,oldrange);
    live=0;result=trace;return result;
}

static void one(int event,unsigned int flags,struct process_vm *vm,
        struct vm_range *newrange,struct vm_range *oldrange) {
    struct trace c,rust,expected={0};
    selectors(flags);
    c=invoke(0,event,vm,newrange,oldrange);rust=invoke(1,event,vm,newrange,oldrange);
    CHECK(!memcmp(&c,&rust,sizeof(c)));
    if (event==1 || (event==2 && flags)) {
        expected.calls=1;expected.kind=event;expected.args[0]=(unsigned long)vm;
        strcpy(expected.format,event==1 ? overlap_format : success_format);
        if (event==1) {
            expected.args[1]=newrange->start;expected.args[2]=newrange->end;
            expected.args[3]=newrange->flag;expected.args[4]=oldrange->start;
            expected.args[5]=oldrange->end;expected.args[6]=oldrange->flag;
        } else {
            expected.args[1]=(unsigned long)newrange;expected.args[2]=newrange->start;
            expected.args[3]=newrange->end;expected.args[4]=newrange->flag;
        }
    }
    CHECK(!memcmp(&c,&expected,sizeof(c)));cases++;
}

int main(void) {
    static const unsigned long values[]={0,1,0xffffffffUL,0x100000000UL,
        0x8000000000000000UL,0x7fffffffffffffffUL,~0UL,0xdeadbeefc001d00dUL};
    static const unsigned int flags[]={0,1,2,0x7f,0x80,0xff};
    static const int events[]={1,2,0,3,-1,(-2147483647-1),2147483647};
    static const int returns[]={0,-71,17};
    struct process_vm vm={0};struct vm_range newrange={0},oldrange={0};
    unsigned long actual[8],expected[8]={sizeof(struct vm_range),
        __builtin_offsetof(struct vm_range,start),__builtin_offsetof(struct vm_range,end),
        __builtin_offsetof(struct vm_range,flag),sizeof(struct ddebug),__alignof__(struct ddebug),
        3*sizeof(void *),sizeof(int)};
    fixture_log_layout(actual);CHECK(!memcmp(actual,expected,sizeof(actual)));
    for (int f=0;f<6;f++) {
        unsigned int packed=0;
        selectors(flags[f]);memcpy(&packed,(char *)&process_vm_range_insert_debug+actual[6],4);
        CHECK(packed==((flags[f]<<24)|2086U));
    }
    for (int v=0;v<8;v++) {
        newrange.start=values[v];newrange.end=values[(v+1)&7];newrange.flag=values[(v+2)&7];
        oldrange.start=values[(v+3)&7];oldrange.end=values[(v+4)&7];oldrange.flag=values[(v+5)&7];
        for (int f=0;f<6;f++) for (int r=0;r<3;r++) for (int e=0;e<7;e++) {
            logger_return=returns[r];one(events[e],flags[f],&vm,&newrange,&oldrange);
        }
    }
    for (int f=0;f<6;f++) for (int r=0;r<3;r++) for (int e=1;e<7;e++) {
        if (events[e]==2 && flags[f]) continue;
        logger_return=returns[r];one(events[e],flags[f],0,0,0);
    }
    CHECK(cases==1101);
    printf("PASS 1101 actual-original-C/Rust process log comparisons; exact variadic format/UL arguments/event gates/debug metadata/real-header ABI/lifetime cases\n");
    return 0;
}
