/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * The original entry below is extracted byte-for-byte apart from its symbol.
 * Real process.h/process_helpers.h layouts and full production Rust tree code.
 */
#include <process.h>
#include <process_helpers.h>
#include <string.h>
/* Hosted fixture: retain real declarations/types, use libc memset provider. */
#undef memset

extern int printf(const char *, ...);
extern void exit(int);
extern int vm_range_insert(struct process_vm *, struct vm_range *);
extern void fixture_rust_layout(unsigned long *);

struct event { int kind, value, new_index, old_index, root_index; };
struct outcome { int error, count, root, nodes[16][4]; struct event events[2]; };
static struct process_vm vm;
static struct vm_range ranges[16];
static struct event events[2];
static int event_count, live, failures;

static void need(int ok, int line)
{
	if (!ok) { printf("FAIL functional insertion fixture line=%d\n", line); exit(1); }
}
#define CHECK(x) need(!!(x), __LINE__)

static int index_of(struct vm_range *range)
{
	if (!range) return -1;
	CHECK(range >= &ranges[0] && range < &ranges[16]);
	return range-ranges;
}

static int node_index(struct rb_node *node)
{
	return node ? index_of((struct vm_range *)node) : -1;
}

void vm_range_insert_log_bridge(int event, struct process_vm *owner,
		struct vm_range *newrange, struct vm_range *range)
{
	CHECK(live && owner == &vm && event_count < 2);
	events[event_count++] = (struct event){1,event,index_of(newrange),index_of(range),
		node_index(vm.vm_range_tree.rb_node)};
}

void vm_range_insert_dump_bridge(struct process_vm *owner)
{
	CHECK(live && owner == &vm && event_count == 1);
	events[event_count++] = (struct event){2,0,-1,-1,node_index(vm.vm_range_tree.rb_node)};
}

static int original_vm_range_insert(struct process_vm *vm, struct vm_range *newrange)
{
	return process_vm_range_insert_result(&vm->vm_range_tree, newrange, vm,
			vm_range_insert_log_bridge, vm_range_insert_dump_bridge);
}


static int walk(struct rb_node *node, struct rb_node *parent, int *seen)
{
	int left, right, index;
	if (!node) return 1;
	index = node_index(node);
	CHECK(!seen[index]); seen[index] = 1;
	CHECK((struct rb_node *)(node->__rb_parent_color & ~3UL) == parent);
	if (!(node->__rb_parent_color & 1)) {
		CHECK(!node->rb_left || (node->rb_left->__rb_parent_color & 1));
		CHECK(!node->rb_right || (node->rb_right->__rb_parent_color & 1));
	}
	left = walk(node->rb_left,node,seen);
	right = walk(node->rb_right,node,seen);
	CHECK(left == right);
	return left + !!(node->__rb_parent_color & 1);
}

static void snapshot(struct outcome *out, int error)
{
	int seen[16] = {0};
	memset(out,0,sizeof(*out));
	out->error=error; out->count=event_count;
	out->root=node_index(vm.vm_range_tree.rb_node);
	memcpy(out->events,events,sizeof(events));
	if (vm.vm_range_tree.rb_node) CHECK(vm.vm_range_tree.rb_node->__rb_parent_color & 1);
	walk(vm.vm_range_tree.rb_node,0,seen);
	for (int i=0;i<16;i++) {
		struct rb_node *node=&ranges[i].vm_rb_node;
		out->nodes[i][0]=seen[i];
		out->nodes[i][1]=node_index(node->rb_left);
		out->nodes[i][2]=node_index(node->rb_right);
		out->nodes[i][3]=node_index((struct rb_node *)(node->__rb_parent_color & ~3UL))*2+
			!!(node->__rb_parent_color & 1);
	}
}

static void suite(int variant, int rust, struct outcome results[17])
{
	int accepted[16]={0};
	unsigned long base = variant & 1 ? ~0UL - 0x100000UL : 0x100000000UL;
	memset(&vm,0,sizeof(vm)); memset(ranges,0,sizeof(ranges));
	for (int op=0;op<16;op++) {
		int slot = op < 8 ? ((op*(variant&2 ? 3 : 5)+(variant>>2))&7) : op-8;
		unsigned long start=base+(unsigned long)slot*0x1000;
		unsigned long end=start+0x800;
		int expected=0, before=node_index(vm.vm_range_tree.rb_node), overlap=-1;
		if (op>=8) {
			switch ((variant+op)&3) {
			case 0: start+=0x800; end+=0x1000; break; /* adjacency then overlap */
			case 1: start+=0x100; end+=0x100; break; /* strict overlap */
			case 2: start+=0x800; end=start+0x800; break; /* exact adjacency */
			default: start=base+0x10000+op*0x1000UL; end=start+0x800; break;
			}
		}
		ranges[op].start=start; ranges[op].end=end;
		for (int i=0;i<op;i++) if (accepted[i] &&
			!(end<=ranges[i].start || start>=ranges[i].end)) {
			expected=-14; overlap=i; break;
		}
		memset(events,0,sizeof(events)); event_count=0; live=1;
		int error=rust ? vm_range_insert(&vm,&ranges[op]) : original_vm_range_insert(&vm,&ranges[op]);
		live=0;
		CHECK(error==expected);
		CHECK(event_count==(expected ? 1 : 2));
		CHECK(events[0].kind==1 && events[0].value==(expected ? 1 : 2));
		CHECK(events[0].new_index==op && events[0].root_index==before);
		if (expected) {
			CHECK(events[0].old_index>=0);
			struct vm_range *old=&ranges[events[0].old_index];
			CHECK(overlap>=0 && !(end<=old->start || start>=old->end));
			CHECK(node_index(vm.vm_range_tree.rb_node)==before);
		} else {
			CHECK(events[0].old_index==-1 && events[1].kind==2 && events[1].root_index==before);
			accepted[op]=1;
		}
		snapshot(&results[op],error);
		for (int i=0;i<16;i++) CHECK(results[op].nodes[i][0]==accepted[i]);
	}
	memset(events,0,sizeof(events)); event_count=0; live=1;
	int error=rust ? vm_range_insert(&vm,0) : original_vm_range_insert(&vm,0);
	live=0;
	CHECK(error==-22 && event_count==0);
	snapshot(&results[16],error);
}

int main(void)
{
	unsigned long actual[7];
	unsigned long expected[7]={sizeof(struct process_vm),sizeof(struct vm_range),
		__builtin_offsetof(struct process_vm,vm_range_tree),__builtin_offsetof(struct vm_range,vm_rb_node),
		__builtin_offsetof(struct vm_range,start),__builtin_offsetof(struct vm_range,end),sizeof(int)};
	fixture_rust_layout(actual);
	CHECK(!memcmp(actual,expected,sizeof(actual)));
	for (int variant=0;variant<64;variant++) {
		struct outcome c[17],rust[17];
		suite(variant,0,c); suite(variant,1,rust);
		CHECK(!memcmp(c,rust,sizeof(c)));
	}
	printf("PASS 1088 actual-original-C/Rust entry comparisons; independent interval, red-black, callback-order, errno and real-header ABI checks\n");
	return failures;
}
