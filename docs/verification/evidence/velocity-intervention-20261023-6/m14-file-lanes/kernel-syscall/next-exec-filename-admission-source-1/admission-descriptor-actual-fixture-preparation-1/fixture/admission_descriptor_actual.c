/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual C slices/real kernel structures, actual Rust lock/tree/tracker/string bodies.
 * Controlled effects: preemption, backing page/meta allocation, spin backing, log capture.
 * No real exec, physical allocation, interrupts or guest. */
#include <types.h>
#include <process.h>
#include <errno.h>
#include <string.h>
#include <ihk/mm.h>
#include <ihk/debug.h>
#ifndef offsetof
#define offsetof(t,m) __builtin_offsetof(t,m)
#endif
extern int printf(const char*,...);extern void abort(void);
extern int f03_execveat_filename_admission_v1(struct process_vm*,const void*);
extern void *f03_execveat_allocate_descriptor_v1(const char*,int,int*);
extern size_t f03_admission_descriptor_layout(size_t*);
static unsigned long case_id;static int which;
#define CHECK(x) do{if(!(x)){printf("FAIL case=%lu implementation=%d line=%d predicate=%s\n",case_id,which,__LINE__,#x);abort();}}while(0)
static void zero(void*p,size_t n){unsigned char*b=p;for(size_t i=0;i<n;i++)b[i]=0;}
void *__inline_memset(void*p,unsigned long v,size_t n){unsigned char*b=p;for(size_t i=0;i<n;i++)b[i]=(unsigned char)v;return p;}
void *__inline_memcpy(void*d,const void*s,size_t n){for(size_t i=0;i<n;i++)((char*)d)[i]=((const char*)s)[i];return d;}
static unsigned long events[512];static size_t event_count;
static void event(unsigned long e,unsigned long a,unsigned long b){CHECK(event_count+3<=512);events[event_count++]=e;events[event_count++]=a;events[event_count++]=b;}
static struct process_vm vm;static struct vm_range ranges[3];static int initial_readers,preempt_depth;
void preempt_disable(void){CHECK(preempt_depth==0);preempt_depth++;event(1,0,0);}
void preempt_enable(void){CHECK(preempt_depth==1);CHECK(vm.memory_range_lock.v.counter==initial_readers);preempt_depth--;event(2,0,0);}
void cpu_pause(void){CHECK(0);}
void process_range_public_log_bridge(int e,struct process_vm*v,struct vm_range*r,unsigned long s,unsigned long end,int error){CHECK(v==&vm&&preempt_depth==1&&vm.memory_range_lock.v.counter==initial_readers+1&&error==0);event(10+e,s,end);if(e==2)event(20,(unsigned long)r,0);}
static int diagnostic;
int kprintf(const char*format,...){CHECK(preempt_depth==0);if(!strcmp(format,"execve(): ERROR: filename is bad address\n"))diagnostic=1;else if(!strcmp(format,"execve(): ERROR: allocating program descriptor\n"))diagnostic=2;else CHECK(0);event(30,diagnostic,0);return 0;}
/* Full lexical C body below keeps the old function's name for __FUNCTION__/__func__.
 * This slice has no function-name expression; no substituted lexical logger is used. */
static int do_execveat(struct process_vm*vm,const void*filename){struct vm_range*range;
	ihk_rwspinlock_read_lock_noirq(&vm->memory_range_lock);

	range = lookup_process_memory_range(vm, (unsigned long)filename, 
			(unsigned long)filename+1);

	if (range == NULL || !(range->flag & VR_PROT_READ)) {
		ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
		kprintf("execve(): ERROR: filename is bad address\n");
		return -EFAULT;
	}
	
	ihk_rwspinlock_read_unlock_noirq(&vm->memory_range_lock);
return 0;}
/* Genuine C tracker structures copied byte-exact from kernel/mem.c below. */
struct pagealloc_track_addr_entry {
	void *addr;
	int runcount;
	struct list_head list; /* track_entry's list */
	struct pagealloc_track_entry *entry;
	struct list_head hash; /* address hash */
	int npages;
};

struct pagealloc_track_entry {
	char *file;
	int line;
	ihk_atomic_t alloc_count;
	struct list_head hash;
	struct list_head addr_list;
	ihk_spinlock_t addr_list_lock;
};

struct list_head pagealloc_track_hash[256],pagealloc_addr_hash[256];
ihk_spinlock_t pagealloc_track_hash_locks[256],pagealloc_addr_hash_locks[256];
char *memdebug;int pagealloc_track_initialized,pagealloc_runcount;
static unsigned char pages[4*4096] __attribute__((aligned(4096)));
static unsigned char arena[65536] __attribute__((aligned(64)));static size_t arena_used;
static int base_fail,meta_fail,meta_calls,free_calls,allocation_calls,expected_line;
static const char *expected_file;
static void head_init(struct list_head*h){h->next=h;h->prev=h;}
void *mem_pagealloc_track_base_alloc_bridge(int np,int align,ihk_mc_ap_flag flag,int node,int user,uintptr_t virt){CHECK(np==4&&align==0&&flag==IHK_MC_AP_NOWAIT&&node==-1&&user==IHK_MC_PG_KERNEL&&virt==(uintptr_t)-1);allocation_calls++;event(40,np,virt);return base_fail?0:pages;}
void *mem_pagealloc_track_meta_alloc_bridge(int n,ihk_mc_ap_flag flags){CHECK(n>0&&flags==IHK_MC_AP_NOWAIT);meta_calls++;event(41,n,meta_calls);if(meta_calls==meta_fail)return 0;size_t z=((size_t)n+63)&~63UL;CHECK(arena_used+z<=sizeof(arena));void*r=arena+arena_used;arena_used+=z;return r;}
void mem_pagealloc_track_meta_free_bridge(void*p){CHECK(p>=((void*)arena)&&p<((void*)(arena+sizeof(arena))));free_calls++;event(42,(unsigned long)p,0);}
unsigned long mem_pagealloc_track_lock_bridge(unsigned long addr){CHECK(*(unsigned*)addr==0);*(unsigned*)addr=1;event(43,addr,0);return 0x1357;}
void mem_pagealloc_track_unlock_bridge(unsigned long addr,unsigned long flags){CHECK(flags==0x1357&&*(unsigned*)addr==1);*(unsigned*)addr=0;event(44,addr,flags);}
void mem_pagealloc_track_spin_init_bridge(unsigned long addr){*(unsigned*)addr=0;event(45,addr,0);}
void mem_pagealloc_track_log_bridge(int e,void*p,char*file,int line,int np){CHECK(!strcmp(file,expected_file)&&line==expected_line&&np==4&&p==pages);event(50+e,line,np);}
static int original_descriptor(void**out){void*desc;
/* #line preserves literal __LINE__ allocation-origin data; actual fixture filename
 * remains __FILE__, and the candidate receives the same exact static string. */
#line 7142 "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-exec-filename-admission-source-1/admission-descriptor-actual-fixture-preparation-1/fixture/admission_descriptor_actual.c"
	desc = _ihk_mc_alloc_aligned_pages_node(4, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (!desc) {
		kprintf("execve(): ERROR: allocating program descriptor\n");
		return -ENOMEM;
	}

	memset((void*)desc, 0, 4 * PAGE_SIZE);
*out=desc;return 0;
}
#line 120 "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-exec-filename-admission-source-1/admission-descriptor-actual-fixture-preparation-1/fixture/admission_descriptor_actual.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&f03_execveat_filename_admission_v1),int(*)(struct process_vm*,const void*)),"admission ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&f03_execveat_allocate_descriptor_v1),void*(*)(const char*,int,int*)),"descriptor ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_alloc_aligned_pages_node),void*(*)(int,int,ihk_mc_ap_flag,int,int,uintptr_t,char*,int)),"genuine tracked allocation ABI");
_Static_assert(sizeof(int)==4&&sizeof(long)==8&&sizeof(void*)==8&&PAGE_SIZE==4096&&PAGE_P2ALIGN==0&&IHK_MC_AP_NOWAIT==2&&IHK_MC_PG_KERNEL==0&&VR_PROT_READ==0x10000,"profile widths/flags");
static void layout_check(void){size_t r[32],c[]={sizeof(struct process_vm),_Alignof(struct process_vm),offsetof(struct process_vm,memory_range_lock),offsetof(struct process_vm,vm_range_tree),offsetof(struct process_vm,range_cache),offsetof(struct process_vm,range_cache_ind),sizeof(struct vm_range),_Alignof(struct vm_range),offsetof(struct vm_range,vm_rb_node),offsetof(struct vm_range,start),offsetof(struct vm_range,end),offsetof(struct vm_range,flag),sizeof(ihk_rwspinlock_t),sizeof(ihk_spinlock_t),sizeof(ihk_atomic_t),sizeof(struct list_head)};CHECK(f03_admission_descriptor_layout(r)==sizeof(c)/sizeof(c[0]));for(size_t i=0;i<sizeof(c)/sizeof(c[0]);i++)CHECK(c[i]==r[i]);}
static void admission_init(int tree,int flag,int cache,int readers){zero(&vm,sizeof(vm));zero(ranges,sizeof(ranges));initial_readers=readers;vm.memory_range_lock.v.counter=readers;preempt_depth=0;diagnostic=0;event_count=0;zero(events,sizeof(events));
 ranges[0].start=100;ranges[0].end=200;ranges[1].start=20;ranges[1].end=80;ranges[2].start=300;ranges[2].end=400;
 for(int i=0;i<3;i++)ranges[i].flag=flag==0?0:flag==1?VR_PROT_READ:VR_PROT_READ|0x20;
 if(tree)vm.vm_range_tree.rb_node=&ranges[0].vm_rb_node;
 if(tree>=2)ranges[0].vm_rb_node.rb_left=&ranges[1].vm_rb_node;
 if(tree==3)ranges[0].vm_rb_node.rb_right=&ranges[2].vm_rb_node;
 vm.range_cache_ind=cache;if(cache)vm.range_cache[(cache+1)%VM_RANGE_CACHE_SIZE]=&ranges[cache==1?0:1];
}
struct admission_outcome {long rc;int diagnostic,preempt,readers,cache_ind;unsigned long cache[VM_RANGE_CACHE_SIZE];size_t count;unsigned long events[512];};
static struct admission_outcome ac,ar;
static void admission_save(struct admission_outcome*out,int rc){zero(out,sizeof(*out));out->rc=rc;out->diagnostic=diagnostic;out->preempt=preempt_depth;out->readers=vm.memory_range_lock.v.counter;out->cache_ind=vm.range_cache_ind;for(int i=0;i<VM_RANGE_CACHE_SIZE;i++)out->cache[i]=(unsigned long)vm.range_cache[i];out->count=event_count;__inline_memcpy(out->events,events,sizeof(events));}
static void alloc_init(int debug,int initialized,int failbase,int failmeta,int line){base_fail=failbase;meta_fail=failmeta;meta_calls=free_calls=allocation_calls=diagnostic=preempt_depth=0;arena_used=event_count=0;zero(events,sizeof(events));zero(arena,sizeof(arena));for(size_t i=0;i<sizeof(pages);i++)pages[i]=0xa5;
 memdebug=debug?(char*)"tracking":0;pagealloc_track_initialized=initialized;pagealloc_runcount=7;expected_line=line;expected_file=__FILE__;
 zero(pagealloc_track_hash_locks,sizeof(pagealloc_track_hash_locks));zero(pagealloc_addr_hash_locks,sizeof(pagealloc_addr_hash_locks));for(int i=0;i<256;i++){head_init(&pagealloc_track_hash[i]);head_init(&pagealloc_addr_hash[i]);}
}
struct alloc_outcome {long rc;unsigned long descriptor;int diagnostic,metas,frees,calls;size_t used,count;unsigned long events[512];unsigned char pages[4*4096],arena[65536];};
static struct alloc_outcome dc,dr;
static void alloc_save(struct alloc_outcome*out,int rc,void*desc){zero(out,sizeof(*out));out->rc=rc;out->descriptor=(unsigned long)desc;out->diagnostic=diagnostic;out->metas=meta_calls;out->frees=free_calls;out->calls=allocation_calls;out->used=arena_used;out->count=event_count;__inline_memcpy(out->events,events,sizeof(events));__inline_memcpy(out->pages,pages,sizeof(pages));__inline_memcpy(out->arena,arena,sizeof(arena));}
int main(void){layout_check();unsigned long admission=0,descriptor=0;const unsigned long addresses[]={0,19,20,79,80,100,199,200,300,399,400,~0UL};const int readers[]={0,1,7};
 for(int tree=0;tree<4;tree++)for(int flag=0;flag<3;flag++)for(int address=0;address<12;address++)for(int cache=0;cache<3;cache++)for(int read=0;read<3;read++){
  case_id++;for(which=0;which<2;which++){admission_init(tree,flag,cache,readers[read]);int rc=which?f03_execveat_filename_admission_v1(&vm,(void*)addresses[address]):do_execveat(&vm,(void*)addresses[address]);CHECK((rc==0||rc==-EFAULT)&&preempt_depth==0&&vm.memory_range_lock.v.counter==readers[read]&&diagnostic==(rc?1:0));admission_save(which?&ar:&ac,rc);}CHECK(!memcmp(&ac,&ar,sizeof(ac)));admission++;
 }
 for(int debug=0;debug<2;debug++)for(int initialized=0;initialized<2;initialized++)for(int failbase=0;failbase<2;failbase++)for(int failmeta=0;failmeta<4;failmeta++)for(int repeat=0;repeat<2;repeat++){
  case_id++;for(which=0;which<2;which++){alloc_init(debug,initialized,failbase,failmeta,7142);for(int n=0;n<=repeat;n++){void*desc=0;int error=0x1234;int rc;if(which){desc=f03_execveat_allocate_descriptor_v1(expected_file,expected_line,&error);rc=desc?0:error;CHECK(desc?error==0x1234:error==-ENOMEM);}else rc=original_descriptor(&desc);CHECK(rc==(failbase?-ENOMEM:0)&&desc==(failbase?0:pages));CHECK(diagnostic==(failbase?2:0));if(!failbase)for(size_t k=0;k<sizeof(pages);k++)CHECK(pages[k]==0);}alloc_save(which?&dr:&dc,failbase?-ENOMEM:0,failbase?0:pages);}CHECK(!memcmp(&dc,&dr,sizeof(dc)));descriptor++;
 }
 CHECK(admission==1296&&descriptor==64);printf("PASS_F03_ADMISSION_DESCRIPTOR admission=%lu descriptor=%lu total=%lu real_layout_fields=16 controlled_OS_endpoints=1\n",admission,descriptor,admission+descriptor);return 0;
}
