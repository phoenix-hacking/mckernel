/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
#include <string.h>
#undef memset
#ifndef FIXTURE_DEBUG_ENABLED
#error Exact enabled/disabled fixture profile required
#endif
extern int printf(const char *,...);
extern void exit(int);
extern void fixture_rust_vm_range_insert_dump_bridge(struct process_vm *);
extern void fixture_dump_layout(unsigned long *);
const int process_dump_tree_enabled=FIXTURE_DEBUG_ENABLED;
struct event { int kind,width,zero,index; unsigned long first,second; };
struct tape { int count; struct event events[16]; };
static struct process_vm vm;
static struct vm_range ranges[9];
static struct tape tape;
static int live,shape,logger_return,comparisons;
static const unsigned long bases[]={0,0x1000UL,0x100000000UL,0x7fffffffffff0000UL,
    0x8000000000000000UL,0xffff000000000000UL,~0UL-0x20000UL,0xdead000000000000UL};
static void need(int ok,int line) {
    if (!ok) { printf("FAIL functional tree dump line=%d shape=%d comparisons=%d\n",line,shape,comparisons); exit(1); }
}
#define CHECK(x) need(!!(x),__LINE__)
static struct rb_node *node(int index) { return &ranges[index].vm_rb_node; }
static int index_of(struct vm_range *range) {
    CHECK(range>=&ranges[0] && range<&ranges[9]);return range-ranges;
}
int kprintf(const char *fmt,...) {
    __builtin_va_list args;
    CHECK(live && tape.count<16);
    struct event *event=&tape.events[tape.count++];
    __builtin_va_start(args,fmt);
    if (!strcmp(fmt,"dump_tree %p\n")) {
        event->kind=1;event->index=-1;
        struct process_vm *owner=__builtin_va_arg(args,struct process_vm *);
        CHECK(owner==&vm);event->first=(unsigned long)owner;
        if (shape==6) vm.vm_range_tree.rb_node=node(8);
    } else {
        CHECK(!strcmp(fmt,"dtree: %0*d, %p: %lx-%lx\n"));event->kind=2;
        event->width=__builtin_va_arg(args,int);event->zero=__builtin_va_arg(args,int);
        event->index=index_of(__builtin_va_arg(args,struct vm_range *));
        event->first=__builtin_va_arg(args,unsigned long);event->second=__builtin_va_arg(args,unsigned long);
        if (shape==7 && event->index==0) { ranges[1].start+=0x100; ranges[1].end+=0x100; }
        if (shape==8 && event->index==0) ranges[0].vm_rb_node.rb_right=node(1);
    }
    __builtin_va_end(args);return logger_return;
}
#if FIXTURE_DEBUG_ENABLED
#define DEBUG_PRINT_PROCESS
#endif
#ifdef DEBUG_PRINT_PROCESS
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
static void dtree(struct rb_node *node, int l) {
	struct vm_range *range;
	if (!node)
		return;

	range = ((struct vm_range *)((char *)(node) - offsetof(struct vm_range, vm_rb_node)));

	dtree(node->rb_left, l+1);
	kprintf("dtree: %0*d, %p: %lx-%lx\n", l, 0, range, range->start, range->end);
	dtree(node->rb_right, l+1);
}
static void dump_tree(struct process_vm *vm) {
	kprintf("dump_tree %p\n", vm);
	dtree(vm->vm_range_tree.rb_node, 1);
}
#else
static void dump_tree(struct process_vm *vm) {}
#endif


#define PROCESS_SCHED_PUBLIC_BRIDGE
PROCESS_SCHED_PUBLIC_BRIDGE void vm_range_insert_dump_bridge(struct process_vm *vm)
{
	dump_tree(vm);
}


static void setup(int variant) {
    memset(&vm,0,sizeof(vm));memset(ranges,0,sizeof(ranges));memset(&tape,0,sizeof(tape));
    for (int i=0;i<9;i++) { ranges[i].start=bases[variant]+i*0x1000UL;ranges[i].end=ranges[i].start+0x800; }
    switch (shape) {
    case 0: break;
    case 1: vm.vm_range_tree.rb_node=node(0);break;
    case 2:
        vm.vm_range_tree.rb_node=node(3);
        ranges[3].vm_rb_node.rb_left=node(1);ranges[3].vm_rb_node.rb_right=node(5);
        ranges[1].vm_rb_node.rb_left=node(0);ranges[1].vm_rb_node.rb_right=node(2);
        ranges[5].vm_rb_node.rb_left=node(4);ranges[5].vm_rb_node.rb_right=node(6);break;
    case 3:
        vm.vm_range_tree.rb_node=node(8);for (int i=8;i>0;i--) ranges[i].vm_rb_node.rb_left=node(i-1);break;
    case 4:
        vm.vm_range_tree.rb_node=node(0);for (int i=0;i<8;i++) ranges[i].vm_rb_node.rb_right=node(i+1);break;
    case 5:
        vm.vm_range_tree.rb_node=node(4);ranges[4].vm_rb_node.rb_left=node(1);ranges[4].vm_rb_node.rb_right=node(7);
        ranges[1].vm_rb_node.rb_right=node(2);ranges[7].vm_rb_node.rb_left=node(6);ranges[7].vm_rb_node.rb_right=node(8);break;
    case 6: vm.vm_range_tree.rb_node=node(0);break;
    case 7:
        vm.vm_range_tree.rb_node=node(1);ranges[1].vm_rb_node.rb_left=node(0);ranges[1].vm_rb_node.rb_right=node(2);break;
    case 8: vm.vm_range_tree.rb_node=node(0);break;
    default: CHECK(0);
    }
}
static void invoke(int rust,int variant,struct tape *out) {
    setup(variant);live=1;
    if (rust) fixture_rust_vm_range_insert_dump_bridge(&vm);
    else vm_range_insert_dump_bridge(&vm);
    live=0;memcpy(out,&tape,sizeof(tape));
}
static void expected(int variant,struct tape *out) {
    static const int counts[]={0,1,7,9,9,6,1,3,2};
    static const int order[9][9]={{0},{0},{0,1,2,3,4,5,6},{0,1,2,3,4,5,6,7,8},
        {0,1,2,3,4,5,6,7,8},{1,2,4,6,7,8},{8},{0,1,2},{0,1}};
    static const int levels[9][9]={{0},{1},{3,2,3,1,3,2,3},{9,8,7,6,5,4,3,2,1},
        {1,2,3,4,5,6,7,8,9},{2,3,1,3,2,3},{1},{2,1,2},{1,2}};
    memset(out,0,sizeof(*out));
    if (!FIXTURE_DEBUG_ENABLED) return;
    out->count=counts[shape]+1;out->events[0]=(struct event){1,0,0,-1,(unsigned long)&vm,0};
    for (int i=0;i<counts[shape];i++) {
        int index=order[shape][i];unsigned long start=bases[variant]+index*0x1000UL;
        if (shape==7 && index==1) start+=0x100;
        out->events[i+1]=(struct event){2,levels[shape][i],0,index,start,start+0x800};
    }
}
int main(void) {
    unsigned long actual[9],wanted[9]={sizeof(struct vm_range),__builtin_offsetof(struct vm_range,vm_rb_node),
        __builtin_offsetof(struct vm_range,start),__builtin_offsetof(struct vm_range,end),
        __builtin_offsetof(struct process_vm,vm_range_tree),sizeof(struct rb_node),
        __builtin_offsetof(struct rb_node,rb_left),__builtin_offsetof(struct rb_node,rb_right),sizeof(int)};
    static const int returns[]={0,-71,17};
    fixture_dump_layout(actual);CHECK(!memcmp(actual,wanted,sizeof(actual)));
    for (shape=0;shape<9;shape++) for (int variant=0;variant<8;variant++) for (int ret=0;ret<3;ret++) {
        struct tape c,rust,oracle;logger_return=returns[ret];
        invoke(0,variant,&c);invoke(1,variant,&rust);expected(variant,&oracle);
        CHECK(!memcmp(&c,&rust,sizeof(c)) && !memcmp(&c,&oracle,sizeof(c)));comparisons++;
    }
    if (!FIXTURE_DEBUG_ENABLED) {
        memset(&tape,0,sizeof(tape));live=1;
        vm_range_insert_dump_bridge(0);fixture_rust_vm_range_insert_dump_bridge(0);
        live=0;CHECK(tape.count==0);comparisons++;
    }
    CHECK(comparisons==(FIXTURE_DEBUG_ENABLED ? 216 : 217));
    printf("PASS tree_dump_debug=%d actual_original_C_Rust_comparisons=%d independent_order_ABI_formats_lifetime_and_callback_read_order\n",FIXTURE_DEBUG_ENABLED,comparisons);
    return 0;
}
