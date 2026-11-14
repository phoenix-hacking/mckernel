/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY; host fixture models the existing TLB instruction's effect.
 */
#include <process.h>
#include <process_helpers.h>
#include <memobj.h>
#include <ihk/debug.h>
#include <string.h>
#undef memset
extern int printf(const char *,...);
extern void exit(int);
extern int fixture_rust_sync_one_page(void *,page_table_t,pte_t *,void *,int);
extern void fixture_sync_layout(unsigned long *);
struct ddebug process_sync_one_page_entry_debug;
struct ddebug process_sync_one_page_exit_debug;
static const char entryfmt[]="sync_one_page(%p,%p,%p %#lx,%p,%d)\n";
static const char exitfmt[]="sync_one_page(%p,%p,%p %#lx,%p,%d):%d\n";
static const char errorfmt[]="sync_one_page(%p,%p,%p %#lx,%p,%d):flush failed. %d\n";
struct event { int kind,error; unsigned long pte,phys,size; };
struct result { int error,count; unsigned long pte;struct event events[8]; };
static struct result tape;
static pte_t pte;
static struct memobj object;
static struct memobj_ops operations;
static int shift,mutation,flush_error,active,comparisons;
static void *livearg;
static unsigned long paddr=0x800010002000UL;
static const unsigned long replacement_phys=0x123450000UL;
static const unsigned long dirty_mask=0x40UL,physical_mask=0x000ffffffffff000UL;
static void need(int ok,int line) {
 if (!ok) { printf("FAIL functional sync_one_page line=%d comparisons=%d shift=%d mutation=%d error=%d\n",line,comparisons,shift,mutation,flush_error);exit(1); }
}
#define CHECK(x) need(!!(x),__LINE__)
static void event(int kind,int error,unsigned long phys,unsigned long size) {
 CHECK(active && tape.count<8);tape.events[tape.count++]=(struct event){kind,error,pte,phys,size};
}
void fixture_tlb_effect(unsigned long addr) {
 CHECK(addr==paddr && !(pte&dirty_mask));event(2,0,0,0);
 if (mutation&2) pte=(pte&~physical_mask)|replacement_phys;
}
/* Original C callback resolves the same existing selected architecture boundary;
 * the hosted implementation intentionally calls no invlpg or kernel instruction. */
void flush_tlb_single(unsigned long addr) { fixture_tlb_effect(addr); }
static int flush(struct memobj *obj,unsigned long phys,size_t pgsize) {
 CHECK(obj==&object && phys==(pte&physical_mask) && pgsize==(1UL<<shift));
 event(3,0,phys,pgsize);
 if (mutation&4) pte=0x99887001UL;
 return flush_error;
}
int kprintf(const char *format,...) {
 __builtin_va_list ap;__builtin_va_start(ap,format);
 CHECK(__builtin_va_arg(ap,void *)==livearg);
 CHECK(__builtin_va_arg(ap,page_table_t)==(page_table_t)0x12345000UL);
 CHECK(__builtin_va_arg(ap,pte_t *)==&pte);
 CHECK(__builtin_va_arg(ap,unsigned long)==pte);
 CHECK(__builtin_va_arg(ap,void *)==(void *)paddr);
 CHECK(__builtin_va_arg(ap,int)==shift);
 if (!strcmp(format,entryfmt)) { event(1,0,0,0);if (mutation&1) pte&=~dirty_mask; }
 else if (!strcmp(format,errorfmt)) { CHECK(flush_error!=0);CHECK(__builtin_va_arg(ap,int)==flush_error);event(4,flush_error,0,0);if (mutation&8) pte=0x88776001UL; }
 else { CHECK(!strcmp(format,exitfmt));int result=__builtin_va_arg(ap,int);event(5,result,0,0);if (mutation&16) pte=0x77665001UL; }
 __builtin_va_end(ap);return -77;
}
#undef dkprintf
#define dkprintf(fmt,args...) do { if ((!strcmp((fmt),entryfmt) ? process_sync_one_page_entry_debug.flags : process_sync_one_page_exit_debug.flags)) kprintf(fmt,##args); } while (0)
struct sync_args {
	struct memobj *memobj;
};

int sync_one_page(void *arg0, page_table_t pt, pte_t *ptep,
		  void *pgaddr, int pgshift)
{
	struct sync_args *args = arg0;
	const size_t pgsize = (size_t)1 << pgshift;
	int error;
	uintptr_t phys;

	dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d)\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift);
	if (pte_is_null(ptep) || pte_is_fileoff(ptep, pgsize)
			|| !pte_is_dirty(ptep, pgsize)) {
		error = 0;
		goto out;
	}

	pte_clear_dirty(ptep, pgsize);
	flush_tlb_single((uintptr_t)pgaddr);	/* XXX: TLB flush */

	phys = pte_get_phys(ptep);
	if (args->memobj->flags & MF_ZEROFILL) {
		error = 0;
		goto out;
	}

	error = memobj_flush_page(args->memobj, phys, pgsize);
	if (error) {
		ekprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):"
				"flush failed. %d\n",
				arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
		pte_set_dirty(ptep, pgsize);
		goto out;
	}

	error = 0;
out:
	dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):%d\n",
			arg0, pt, ptep, *ptep, pgaddr, pgshift, error);
	return error;
}

static void setup(unsigned long value,unsigned int zerofill,int op,int entry,int leave,int nullargs) {
 memset(&tape,0,sizeof(tape));memset(&object,0,sizeof(object));memset(&operations,0,sizeof(operations));
 pte=value;object.flags=zerofill;object.ops=&operations;operations.flush_page=op?flush:0;
 process_sync_one_page_entry_debug.flags=entry;process_sync_one_page_exit_debug.flags=leave;
 process_sync_one_page_entry_debug.line=0x123456;process_sync_one_page_exit_debug.line=0x654321;
 static struct sync_args args;args.memobj=&object;livearg=nullargs?0:&args;
}
static void invoke(int rust,unsigned long value,unsigned int zerofill,int op,int entry,int leave,int nullargs,struct result *out) {
 setup(value,zerofill,op,entry,leave,nullargs);active=1;
 int result=rust?fixture_rust_sync_one_page(livearg,(page_table_t)0x12345000UL,&pte,(void *)paddr,shift):sync_one_page(livearg,(page_table_t)0x12345000UL,&pte,(void *)paddr,shift);
 active=0;tape.error=result;tape.pte=pte;memcpy(out,&tape,sizeof(tape));
}
static void add_expected(struct result *out,int kind,int error,unsigned long value,unsigned long phys,unsigned long size) {
 CHECK(out->count<8);out->events[out->count++]=(struct event){kind,error,value,phys,size};
}
static void oracle(unsigned long value,unsigned int zerofill,int op,int entry,int leave,struct result *out) {
 memset(out,0,sizeof(*out));unsigned long current=value;
 if (entry) { add_expected(out,1,0,current,0,0);if (mutation&1)current&=~0x40UL; }
 int visit=current!=0 && !(current&0x800UL) && !!(current&0x40UL);
 if (visit) {
  current&=~0x40UL;add_expected(out,2,0,current,0,0);
  if (mutation&2)current=(current&~physical_mask)|replacement_phys;
  if (!(zerofill&0x10U) && op) {
   add_expected(out,3,0,current,current&physical_mask,1UL<<shift);
   if (mutation&4)current=0x99887001UL;
   out->error=flush_error;
   if (flush_error) { add_expected(out,4,flush_error,current,0,0);if(mutation&8)current=0x88776001UL;current|=0x40UL; }
  }
 }
 if (leave) { add_expected(out,5,out->error,current,0,0);if (mutation&16)current=0x77665001UL; }
 out->pte=current;
}
static void compare(unsigned long value,unsigned int zerofill,int op,int entry,int leave,int nullargs) {
 struct result c,r,wanted;invoke(0,value,zerofill,op,entry,leave,nullargs,&c);invoke(1,value,zerofill,op,entry,leave,nullargs,&r);oracle(value,zerofill,op,entry,leave,&wanted);
 CHECK(!memcmp(&c,&r,sizeof(c)));CHECK(!memcmp(&c,&wanted,sizeof(c)));comparisons++;
}
int main(void) {
 unsigned long got[11],want[11]={sizeof(struct sync_args),__alignof__(struct sync_args),__builtin_offsetof(struct sync_args,memobj),sizeof(struct memobj),__builtin_offsetof(struct memobj,flags),__builtin_offsetof(struct memobj,ops),sizeof(struct memobj_ops),__builtin_offsetof(struct memobj_ops,flush_page),sizeof(struct ddebug),24,sizeof(pte_t)};
 fixture_sync_layout(got);CHECK(!memcmp(got,want,sizeof(got)));
 const unsigned long values[]={0,1,0x41,0x841,0xc1,0x000fedcba9876041UL};
 const int shifts[]={12,21,30};const int errors[]={0,-5,7,(-2147483647-1)};
 const unsigned int flags[][2]={{0,0},{1,0},{0,128},{255,1}};
 mutation=0;
 for (int a=0;a<6;a++)for(int b=0;b<3;b++)for(int zero=0;zero<2;zero++)for(int op=0;op<5;op++)for(int debug=0;debug<4;debug++) {
  shift=shifts[b];flush_error=op?errors[op-1]:0;compare(values[a],zero?0x80000010U:0x80000000U,op,flags[debug][0],flags[debug][1],0);
 }
 const int mutations[]={1,2,4,8,16,31};
 for(int m=0;m<6;m++)for(int b=0;b<3;b++)for(int e=0;e<4;e++) {
  mutation=mutations[m];shift=shifts[b];flush_error=errors[e];compare(0x12345041UL,0,1,255,128,0);
 }
 mutation=0;shift=12;flush_error=-99;compare(0,0,1,0,0,1);compare(1,0,1,0,0,1);compare(0x841,0,1,0,0,1);
 printf("sync_one_page actual_original_C_Rust_comparisons=%d real_PTE_memobj_dispatch=1 controlled_TLB=1\n",comparisons);return 0;
}
