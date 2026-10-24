"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare one exact full-body extension/COW classification leaf; no execution.
"""
from pathlib import Path
import hashlib,json,re,shutil
P=Path(__file__).resolve().parent;L=P.parent;F=P/'fixture';H=P/'sourcehandoff';O=P/'output-first-candidate-1'
R=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
E=L/'union2-extend-region-source-1';C=L/'union2-cow-classify-source-1'
OLD=L/'next-page-fault-prepare/preexec-lock-binding-correction-1'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def write(p,j):put(p,json.dumps(j,indent=2)+'\n')
def fun(s,m):
 a=s.index(m);b=s.index('{',a);e=b+1;d=1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
def main():
 F.mkdir();H.mkdir()
 cp=E/'candidate/kernel/process.SOURCE-CONTEXT-CORRECTED.c';rp=E/'candidate/kernel/rust/process_helpers.rs'
 assert pin(cp)['sha256']=='42ee6f390724da418d0cc0ac6573200615c1ed2a52cf0f7a10602d6eb9729ef1'
 assert pin(rp)['sha256']=='2e74d8131170630a1930d8f972e2918b8519e929635c5754fafd935009865da1'
 for src,name in [(E/'fixture/extend_region.ACTUAL-RUST.inc','extend_region.ACTUAL-RUST.inc'),(C/'fixture/cow_classify.ACTUAL-RUST.inc','cow_classify.ACTUAL-RUST.inc'),(E/'fixture/extend_process_region.ACTUAL-ORIGINAL-C.inc','extend_process_region.ACTUAL-ORIGINAL-C.inc'),(C/'fixture/original_classify.ACTUAL-C.inc','original_classify.ACTUAL-C.inc')]:
  shutil.copy2(src,F/name)
 c=cp.read_text()
 a=c.index('#ifdef MCKERNEL_RUST_PROCESS_HELPERS\nstatic struct ddebug __aligned(8)')
 e=c.index('\n#else\n#line ',a)
 selected=c[a:e]+'\n#endif\n'
 put(F/'extend_region.ACTUAL-C-SELECTION.inc',selected)
 meta=json.loads((E/'fixture/EXACT-TRACKING-AND-DIAGNOSTIC-SOURCE.json').read_text())
 original=(F/'extend_process_region.ACTUAL-ORIGINAL-C.inc').read_text()
 put(F/'original_lexical_reference.inc','#define extend_process_region fixture_original_extend_process_region\n#define __func__ "extend_process_region"\n#define __FUNCTION__ "extend_process_region"\n#line '+str(meta['original_function_first_line'])+' "held-current-COW-process.c"\n'+original+'\n#undef __FUNCTION__\n#undef __func__\n#undef extend_process_region\n')
 shutil.copy2(R/'kernel/rust/abi.rs',F/'abi.ACTUAL.rs')
 page=(R/'kernel/rust/page_helpers.rs').read_text()
 pfx=page[:page.index('#[inline(always)]\nunsafe fn page_in_memobj_predicate')]
 for marker in ['pub extern "C" fn page_mode_in_memobj_result(','pub extern "C" fn page_multi_mapped_result(','pub unsafe extern "C" fn page_is_in_memobj_body_result(','pub unsafe extern "C" fn page_is_multi_mapped_body_result(','pub unsafe extern "C" fn page_is_in_memobj(','pub unsafe extern "C" fn page_is_multi_mapped(']:
  pfx+='#[no_mangle]\n'+fun(page,marker)+'\n'
 pfx+='''pub fn fixture_layout()->[usize;5] { [
 size_of::<Page>(),align_of::<Page>(),offset_of!(Page,mode),
 offset_of!(Page,count),size_of::<IhkAtomic>() ] }
'''
 put(F/'page_predicates.ACTUAL-RUST.rs',pfx)
 debug=(R/'kernel/rust/debug.rs').read_text()
 struct=debug[debug.index('#[repr(C)]\npub struct Ddebug'):debug.index('#[no_mangle]\npub static mut kmsg_buf')]
 put(F/'debug_type.ACTUAL-RUST.rs',struct)
 provider='''// '''+SCOPE+'''
#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;use core::ptr::null_mut;
use abi::{CInt,CULong,SizeT,ProcessVm,Process,VmRange,Memobj};
const VR_DEMAND_PAGING:CULong=0x1000;const VR_PRIVATE:CULong=0x2000;
const VR_PROT_WRITE:CULong=0x20000;const PF_PATCH:CULong=1<<29;
mod debug { include!("debug_type.ACTUAL-RUST.rs"); }
mod page_helpers { include!("page_predicates.ACTUAL-RUST.rs"); }
extern "C" {
 fn kprintf(format:*const i8,...)->CInt;
 fn lookup_process_memory_range(vm:*mut ProcessVm,start:CULong,end:CULong)->*mut VmRange;
 fn add_process_memory_range(vm:*mut ProcessVm,start:CULong,end:CULong,phys:CULong,
  flag:CULong,obj:*mut c_void,off:abi::OffT,shift:CInt,data:*mut c_void,rp:*mut *mut VmRange)->CInt;
}
mod mem_helpers {
 use super::*;
 extern "C" {
  pub fn _ihk_mc_alloc_aligned_pages_node(n:CInt,a:CInt,f:CULong,node:CInt,user:CInt,
   addr:CULong,file:*mut i8,line:CInt)->*mut c_void;
  pub fn _ihk_mc_free_pages(p:*mut c_void,n:CInt,user:CInt,file:*mut i8,line:CInt);
 }
}
mod x86_memory_helpers {
 use super::*;extern "C" { pub fn virt_to_phys(p:*mut c_void)->CULong; }
}
include!("extend_region.ACTUAL-RUST.inc");
include!("cow_classify.ACTUAL-RUST.inc");
#[no_mangle]pub unsafe extern "C" fn fixture_layout(out:*mut usize) {
 use core::mem::{size_of,align_of,offset_of};
 let p=page_helpers::fixture_layout();
 let x=[size_of::<ProcessVm>(),align_of::<ProcessVm>(),offset_of!(ProcessVm,proc),
 size_of::<Process>(),align_of::<Process>(),offset_of!(Process,mpol_flags),offset_of!(Process,heap_extension),
 size_of::<CULong>(),size_of::<CULong>(),size_of::<debug::Ddebug>(),align_of::<debug::Ddebug>(),
 size_of::<VmRange>(),offset_of!(VmRange,flag),offset_of!(VmRange,memobj),
 size_of::<Memobj>(),offset_of!(Memobj,flags),
 p[0],p[1],p[2],p[3],p[4]];
 core::ptr::copy_nonoverlapping(x.as_ptr(),out,x.len());
}
'''
 put(F/'actual_provider.rs',provider)
 # Actual original function text + exact public selection + real field layout,
 # controlled allocation/range/translation effects, genuine Rust Page predicates.
 parity=r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Original complete C/Rust bodies. These host allocation/range/translation
 * effect adapters do not execute backend/kernel ownership or native mapping. */
#include <process.h>
#include <memobj.h>
#include <page.h>
#include <syscall.h>
#include <memory.h>
#include <ihk/debug.h>
#include <string.h>
#undef memset
extern int printf(const char *,...);extern void exit(int);
extern void fixture_layout(unsigned long *);
extern int process_page_fault_cow_classify_body_result(struct vm_range *,uint64_t,struct page *);
static int fixture_gate(const char *);
#undef dkprintf
#define dkprintf(fmt,args...) do {if(fixture_gate(fmt))kprintf(fmt,##args);}while(0)
#include "original_lexical_reference.inc"
#undef dkprintf
#define extend_process_region fixture_selected_extend_process_region
#line 1 "held-current-COW-process.c"
#include "extend_region.ACTUAL-C-SELECTION.inc"
#undef extend_process_region
#line 1 "extend-cow-functional-fixture"
struct vector {unsigned long end,address,heap,wanted,len;int npages,shift,align;unsigned long align_size,mask;};
static const struct vector vectors[]={
@VECTORS@
};
struct event {int kind,x,y;unsigned long a,b,c,d;};
struct tape {unsigned long result,mpol;int count,allocated,transferred;struct event e[8];};
static struct tape tape;
static struct process_vm vm;static struct process proc;static struct vm_range range;
static struct memobj obj;static struct page page;
static const struct vector *v;
static int action,dbg,mpol,comparisons,extend_comparisons,cow_comparisons;
static void need(int ok,int line) {
 if(!ok){printf("FAIL functional extend/COW line=%d comparisons=%d action=%d vector=%ld debug=%d mpol=%d\n",line,comparisons,action,(long)(v?v-vectors:-1),dbg,mpol);exit(1);}
}
#define CHECK(x) need(!!(x),__LINE__)
static void event(int k,int x,int y,unsigned long a,unsigned long b,unsigned long c,unsigned long d) {
 CHECK(tape.count<8);tape.e[tape.count++]=(struct event){k,x,y,a,b,c,d};
}
static int gate(int which) {
 static const int gates[4][3]={{0,0,0},{1,1,1},{2,0,255},{0,255,0}};
 return gates[dbg][which];
}
static int fixture_gate(const char *fmt) {
 if(!strcmp(fmt,"%s: warning: vm_range for extension already exists\n"))return gate(0);
 if(!strcmp(fmt,"%s: warning: failed to allocate %d contiguous pages  (bytes: %lu, pgshift: %d), enabling demand paging\n"))return gate(1);
 CHECK(!strcmp(fmt,"%s: new_end_allocated: 0x%lx, align_size: %lu, align_mask: %lx\n"));
 return gate(2);
}
static int add_error(void){return action==4||action==5?-12:action==6||action==7?17:0;}
static int demanded(void){return action==1||action==5;}
static int allocation_fails(void){return action==3||action==6;}
struct vm_range *lookup_process_memory_range(struct process_vm *p,uintptr_t start,uintptr_t end) {
 CHECK(p==&vm&&start==v->end&&end==v->wanted);
 event(1,0,0,start,end,0,0);
 if(action==7)proc.mpol_flags^=MPOL_NO_HEAP;
 return action==0?&range:0;
}
void *_ihk_mc_alloc_aligned_pages_node(int n,int align,ihk_mc_ap_flag flag,int node,int user,uintptr_t addr,char *file,int line) {
 CHECK(n==v->npages&&align==v->align&&node==-1&&user==IHK_MC_PG_USER&&addr==v->end);
 CHECK(flag==(IHK_MC_AP_NOWAIT|(!(proc.mpol_flags&MPOL_NO_HEAP)?IHK_MC_AP_USER:0)));
 CHECK(!strcmp(file,"held-current-COW-process.c")&&line==@ALLOC@);
 event(2,n,align,flag,addr,(unsigned long)node,user);
 tape.allocated=!allocation_fails();return allocation_fails()?0:(void *)0x80000000UL;
}
unsigned long virt_to_phys(void *p) {
 CHECK(p==(void *)0x80000000UL&&tape.allocated);
 event(3,0,0,(unsigned long)p,0,0,0);return 0x12345000UL;
}
int add_process_memory_range(struct process_vm *p,unsigned long start,unsigned long end,
 unsigned long phys,unsigned long flag,struct memobj *memobj,off_t offset,int shift,void *data,struct vm_range **rp) {
 CHECK(p==&vm&&start==v->end&&end==v->wanted&&!memobj&&!offset&&shift==v->shift&&!data&&!rp);
 CHECK(phys==(tape.allocated?0x12345000UL:0));
 CHECK(flag==(0x8000000000000000UL|((demanded()||allocation_fails())?VR_DEMAND_PAGING:0)));
 event(4,add_error(),shift,start,end,phys,flag);
 if(!add_error())tape.transferred=tape.allocated;
 return add_error();
}
void _ihk_mc_free_pages(void *p,int n,int user,char *file,int line) {
 CHECK(p==(tape.allocated?(void *)0x80000000UL:0)&&n==v->npages&&user==IHK_MC_PG_USER);
 CHECK(!strcmp(file,"held-current-COW-process.c")&&line==@FREE@&&add_error());
 event(5,n,user,(unsigned long)p,0,0,0);tape.allocated=0;
}
int kprintf(const char *fmt,...) {
 __builtin_va_list ap;__builtin_va_start(ap,fmt);
 CHECK(!strcmp(__builtin_va_arg(ap,const char *),"extend_process_region"));
 if(!strcmp(fmt,"%s: warning: vm_range for extension already exists\n")) {
  CHECK(action==0&&gate(0));event(6,0,0,0,0,0,0);
 }else if(!strcmp(fmt,"%s: warning: failed to allocate %d contiguous pages  (bytes: %lu, pgshift: %d), enabling demand paging\n")) {
  int n=__builtin_va_arg(ap,int);size_t len=__builtin_va_arg(ap,size_t);
  unsigned long align=__builtin_va_arg(ap,unsigned long);
  CHECK(allocation_fails()&&gate(1)&&n==v->npages&&len==v->len&&align==(unsigned long)v->align);
  event(7,n,0,len,align,0,0);
 }else{
  CHECK(!strcmp(fmt,"%s: new_end_allocated: 0x%lx, align_size: %lu, align_mask: %lx\n")&&gate(2)&&!add_error());
  unsigned long end=__builtin_va_arg(ap,unsigned long);size_t size=__builtin_va_arg(ap,size_t);
  unsigned long mask=__builtin_va_arg(ap,unsigned long);
  CHECK(end==v->wanted&&size==v->align_size&&mask==v->mask);event(8,0,0,end,size,mask,0);
 }
 __builtin_va_end(ap);return -77;
}
static struct tape run_extend(int rust) {
 memset(&vm,0,sizeof(vm));memset(&proc,0,sizeof(proc));memset(&range,0,sizeof(range));memset(&tape,0,sizeof(tape));
 vm.proc=&proc;proc.heap_extension=v->heap;proc.mpol_flags=mpol?MPOL_NO_HEAP:0;
 process_extend_region_exists_debug.flags=gate(0);process_extend_region_alloc_debug.flags=gate(1);process_extend_region_success_debug.flags=gate(2);
 unsigned long flag=0x8000000000000000UL|(demanded()?VR_DEMAND_PAGING:0);
 tape.result=rust?fixture_selected_extend_process_region(&vm,v->end,v->address,flag):
  fixture_original_extend_process_region(&vm,v->end,v->address,flag);
 tape.mpol=proc.mpol_flags;
 CHECK(proc.heap_extension==v->heap&&vm.proc==&proc);
 return tape;
}
static void expected_push(struct tape *t,int k,int x,int y,unsigned long a,unsigned long b,unsigned long c,unsigned long d) {
 CHECK(t->count<8);t->e[t->count++]=(struct event){k,x,y,a,b,c,d};
}
static struct tape oracle_extend(void) {
 struct tape t={0};t.mpol=(mpol?MPOL_NO_HEAP:0)^(action==7?MPOL_NO_HEAP:0);
 expected_push(&t,1,0,0,v->end,v->wanted,0,0);
 if(action==0){
  t.result=v->end;if(gate(0))expected_push(&t,6,0,0,0,0,0,0);return t;
 }
 int allocated=!demanded()&&!allocation_fails();
 if(!demanded()){
  unsigned long f=IHK_MC_AP_NOWAIT|(!(t.mpol&MPOL_NO_HEAP)?IHK_MC_AP_USER:0);
  expected_push(&t,2,v->npages,v->align,f,v->end,(unsigned long)-1,IHK_MC_PG_USER);
  if(allocation_fails()&&gate(1))expected_push(&t,7,v->npages,0,v->len,v->align,0,0);
 }
 if(allocated)expected_push(&t,3,0,0,0x80000000UL,0,0,0);
 unsigned long f=0x8000000000000000UL|((demanded()||allocation_fails())?VR_DEMAND_PAGING:0);
 expected_push(&t,4,add_error(),v->shift,v->end,v->wanted,allocated?0x12345000UL:0,f);
 if(add_error()){
  expected_push(&t,5,v->npages,IHK_MC_PG_USER,allocated?0x80000000UL:0,0,0,0);
  t.result=v->end;return t;
 }
 t.allocated=t.transferred=allocated;t.result=v->wanted;
 if(gate(2))expected_push(&t,8,0,0,v->wanted,v->align_size,v->mask,0);
 return t;
}
static int original_cow(struct vm_range *range,uint64_t reason,struct page *page) {
 int private_range,patching_to_rdonly,devfile_or_hugetlbfs_or_premap,regfile_or_shm;
#include "original_classify.ACTUAL-C.inc"
  return 1;
 }
 return 0;
}
int main(void) {
 unsigned long actual[21],wanted[21]={
 sizeof(struct process_vm),__alignof__(struct process_vm),__builtin_offsetof(struct process_vm,proc),
 sizeof(struct process),__alignof__(struct process),__builtin_offsetof(struct process,mpol_flags),__builtin_offsetof(struct process,heap_extension),
 sizeof(proc.mpol_flags),sizeof(proc.heap_extension),sizeof(struct ddebug),__alignof__(struct ddebug),
 sizeof(struct vm_range),__builtin_offsetof(struct vm_range,flag),__builtin_offsetof(struct vm_range,memobj),
 sizeof(struct memobj),__builtin_offsetof(struct memobj,flags),
 sizeof(struct page),__alignof__(struct page),__builtin_offsetof(struct page,mode),__builtin_offsetof(struct page,count),sizeof(ihk_atomic_t)};
 fixture_layout(actual);CHECK(!memcmp(actual,wanted,sizeof(actual)));
 CHECK(!strcmp(process_extend_region_exists_debug.file,"held-current-COW-process.c")&&
 !strcmp(process_extend_region_alloc_debug.func,"extend_process_region")&&
 !strcmp(process_extend_region_success_debug.func,"extend_process_region"));
 CHECK(process_extend_region_exists_debug.line==@EXISTS@&&process_extend_region_alloc_debug.line==@DEBUGALLOC@&&process_extend_region_success_debug.line==@SUCCESS@);
 CHECK(!process_extend_region_exists_debug.fmt&&!process_extend_region_alloc_debug.fmt&&!process_extend_region_success_debug.fmt);
 for(unsigned q=0;q<sizeof(vectors)/sizeof(vectors[0]);q++)for(action=0;action<8;action++)for(dbg=0;dbg<4;dbg++)for(mpol=0;mpol<2;mpol++){
  v=&vectors[q];struct tape c=run_extend(0),r=run_extend(1),e=oracle_extend();
  CHECK(!memcmp(&c,&r,sizeof(c)));CHECK(!memcmp(&c,&e,sizeof(c)));comparisons++;extend_comparisons++;
 }
 unsigned long flags[]={0,VR_PRIVATE,VR_PROT_WRITE,VR_PRIVATE|VR_PROT_WRITE};
 uint64_t reasons[]={0,PF_PATCH,0x8000000000000000ULL,PF_PATCH|0x8000000000000000ULL};
 unsigned char modes[]={0,1,2,3,4,5,6,7,255};int counts[]={(-2147483647-1),-1,0,1,2,2147483647};
 for(int f=0;f<4;f++)for(int z=0;z<4;z++)for(int p=0;p<10;p++)for(int n=0;n<6;n++)for(int m=0;m<4;m++){
  memset(&range,0,sizeof(range));memset(&obj,0,sizeof(obj));memset(&page,0,sizeof(page));
  range.flag=flags[f]|0x8000000000000000UL;range.memobj=m?&obj:0;
  obj.flags=m==2?MF_ZEROOBJ:m==3?0xffffffffU:0;
  page.mode=p?modes[p-1]:255;page.count.counter=counts[n];
  struct page *pp=p?&page:0;struct vm_range before_range=range;struct memobj before_obj=obj;struct page before_page=page;
  int c=original_cow(&range,reasons[z],pp);
  int r=process_page_fault_cow_classify_body_result(&range,reasons[z],pp);
  int in_object=p&&page.mode>=PM_WILL_PAGEIO&&page.mode<=PM_MAPPED;
  int expected=((flags[f]&VR_PRIVATE)||((reasons[z]&PF_PATCH)&&!(flags[f]&VR_PROT_WRITE)))&&p&&(in_object||counts[n]>1);
  CHECK(c==r&&c==!!expected);
  CHECK(!memcmp(&range,&before_range,sizeof(range))&&!memcmp(&obj,&before_obj,sizeof(obj))&&!memcmp(&page,&before_page,sizeof(page)));
  comparisons++;cow_comparisons++;
 }
 CHECK(extend_comparisons==640&&cow_comparisons==3840&&comparisons==4480);
 printf("extend_region_and_cow actual_original_C_Rust_comparisons=4480 extend=640 cow=3840 controlled_host_effects=1\n");return 0;
}
'''
 vectors=[
 (0x10000000,0x10000001,0),(0x10000000,0x10000000,4096),
 (0x10000000,0x10000001,8192),(0x10001000,0x10002000,8192),
 (0x10000000,(1<<64)-1,0),((1<<64)-4096,(1<<64)-1,4096),
 ((1<<64)-4096,(1<<64)-4096,8192),(0,0x80000000000,0),
 (0,0x100000000000,0),(0x10000000,0x10000000,0)]
 formatted=[];u=(1<<64)-1
 for end,addr,heap in vectors:
  size=1<<21 if heap>4096 else 4096;mask=u^(size-1)
  wanted=((addr+4095)&u)&(u^4095)
  if ((wanted-end)&u)<heap:wanted=((end+heap+size-1)&u)&mask
  length=(wanted-end)&u;pages=(length>>12)&0xffffffff
  if pages>=1<<31:pages-=1<<32
  formatted.append(' {0x%xUL,0x%xUL,0x%xUL,0x%xUL,0x%xUL,%d,%d,%d,0x%xUL,0x%xUL},'%(end,addr,heap,wanted,length,pages,21 if heap>4096 else 12,9 if heap>4096 else 0,size,mask))
 parity=parity.replace('@VECTORS@','\n'.join(formatted))
 for key,value in {'ALLOC':meta['allocator_line'],'FREE':meta['free_line'],'EXISTS':meta['debug_lines']['exists'],'DEBUGALLOC':meta['debug_lines']['allocation_failure'],'SUCCESS':meta['debug_lines']['success']}.items():
  parity=parity.replace('@'+key+'@',str(value))
 put(F/'actual_parity.c',parity)
 abi=(E/'fixture/actual_real_header_abi.SOURCE-ONLY.c').read_text()+'''
#include <page.h>
#include <memory.h>
_Static_assert(__builtin_types_compatible_p(__typeof__(&virt_to_phys),unsigned long (*)(void *)),
 "actual physical translation public provider");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_is_in_memobj),int (*)(struct page *))&&
 __builtin_types_compatible_p(__typeof__(&page_is_multi_mapped),int (*)(struct page *)),
 "actual genuine Page predicates");
_Static_assert(PAGE_SIZE==4096&&PAGE_SHIFT==12&&PAGE_P2ALIGN==0&&
 LARGE_PAGE_SIZE==2097152&&LARGE_PAGE_SHIFT==21&&LARGE_PAGE_P2ALIGN==9,
 "ten finite rounding/narrowing vector premises");
_Static_assert(MPOL_NO_HEAP==1&&VR_DEMAND_PAGING==0x1000&&VR_PRIVATE==0x2000&&
 VR_PROT_WRITE==0x20000&&PF_PATCH==(1UL<<29)&&MF_ZEROOBJ==0x20000,
 "actual original flag meanings");
'''
 # These names are not guaranteed through process.h alone.
 abi=abi.replace('#include <process.h>','#include <process.h>\n#include <memobj.h>\n#include <syscall.h>',1)
 put(F/'actual_header_ABI.c',abi)
 old=json.loads((OLD/'sourcehandoff/EXACT-PAGE-FAULT-PREPARE96.NOT-GRANTED.json').read_text())
 rust=old['commands'][0]['argv'];a=rust.index('--crate-name');rust=rust[:a]+['--crate-name','m14_extend_region_cow',str(F/'actual_provider.rs'),'-o',str(O/'actual_provider.o')]
 cbase=old['commands'][1]['argv'][:-2]
 commands=[
 ('00-actual-Rust-extend-COW-body',rust),
 ('01-actual-real-header-ABI',cbase+['-fsyntax-only',str(F/'actual_header_ABI.c')]),
 ('02-actual-original-C-and-independent-oracle',cbase+['-fno-pie','-c',str(F/'actual_parity.c'),'-o',str(O/'actual_parity.o')]),
 ('03-actual-original-C-Rust-link',['/usr/bin/gcc-9','-no-pie','-Wl,--no-undefined',str(O/'actual_parity.o'),str(O/'actual_provider.o'),'-o',str(O/'actual_parity')]),
 ('04-actual-extend-COW4480-execute',[str(O/'actual_parity')]),
 ('05-actual-provider-and-entry-symbols',['/usr/bin/nm','-a','-S',str(O/'actual_parity')])]
 commands=[dict(name=n,argv=a,cwd=str(O),purpose=SCOPE+' '+n+'; exact C/Rust extension + borrowed COW classification, controlled host allocator/range/translation effects, genuine Page predicates, no native effect.') for n,a in commands]
 sourcehandoffs=[E/'sourcehandoff/SOURCE-NEXT-BODY.WITH-ACTUAL-FIELD-ABI.json',C/'sourcehandoff/SOURCE-NEXT-BODY.json']
 canonical={x:pin(R/x) for x in ['kernel/rust/abi.rs','kernel/rust/page_helpers.rs','kernel/rust/debug.rs']}
 inputs=[*F.iterdir(),cp,rp,*sourcehandoffs]
 recipe=dict(scope=SCOPE,status='ONE_EXTEND_COW4480_EXECUTABLE_SOURCE_READY_NO_GRANT',
  commands=commands,input_bindings={str(p):pin(p) for p in inputs},tools=old['tools'],
  actual_header_closure=old['actual_header_closure'],current_canonical_header_preimages=old['current_canonical_header_preimages'],
  current_provider_pins={},current_canonical_source_preimages=canonical,
  accepted_real_C_profile=old['accepted_real_C_profile'],accepted_prior_production=old['accepted_prior_production'],
  profile=old['profile'],expected_comparisons=4480,breakdown=dict(extend=640,cow=3840),
  oracles='Actual original full C entry vs actual Rust through exact selected C wrapper; 21 actual compiler-derived field/layout values, ten frozen arithmetic vectors, eight effect/error/ownership scenarios, independent exact event oracle, exact diagnostics/tracking/metadata, genuine Page predicates, full range/memobj/Page byte preservation.',
  controlled_effect_scope='Host allocator/free/range lookup/add/virt_to_phys effects are explicit modeled boundaries, not executions of real backend/locks/page ownership/native mappings. Genuine Page type + six unchanged predicate bodies are compiled from current real Rust source. Exact new helper bodies compiled verbatim. No prepare96/memobj/anonymous/zeroobj call executes.',
  remaining_provider_debt=['Real backend allocator/free and range ownership must be proved by future current fullcrate/TU/default/native consumer','brk_extend_bridge remains actual C caller','Page-fault COW copy/RSS/PTE-install/out tail and zeroobj ref HOLD excluded'],
  failure_history=dict(prior96='Passed c8802d6c retained, no replay; original runtime lexical-context failure preserved',prior795404='Passed retained, no replay',source_family_attempts=0,rule='First unexpected STOP; root owns one bounded correction only after concrete diagnosis'),
  compiler_jobs=0,CPU_reservations=0,canonical_mutations=0,fullcrate_default_native_credit=False)
 rf=H/'EXACT-EXTEND-COW4480.NOT-GRANTED.json';write(rf,recipe)
 driver=(OLD/'sourcehandoff/run_owned_page_fault_prepare96_once.py').read_text()
 driver=driver.replace('EXACT-PAGE-FAULT-PREPARE96.NOT-GRANTED.json','EXACT-EXTEND-COW4480.NOT-GRANTED.json').replace('EXECUTABLE-READY.PAGE-FAULT-PREPARE96.NOT-GRANTED.json','EXECUTABLE-READY.EXTEND-COW4480.NOT-GRANTED.json').replace('PAGE-FAULT-PREPARE96-FIRST-FAILURE-1.json','EXTEND-COW4480-FIRST-FAILURE-1.json')
 driver=driver.replace('page-fault-prepare96','extend-COW4480').replace('00-actual-Rust-page-fault-prepare','00-actual-Rust-extend-COW-body').replace('04-actual-page-fault-prepare96-execute','04-actual-extend-COW4480-execute').replace('05-actual-provider-and-slice-symbols','05-actual-provider-and-entry-symbols')
 driver=driver.replace("page_fault_prepare actual_original_C_Rust_comparisons=96 exact_lock_retention=1 controlled_host_effects=1\\n","extend_region_and_cow actual_original_C_Rust_comparisons=4480 extend=640 cow=3840 controlled_host_effects=1\\n")
 driver=driver.replace('actual_comparisons=96','actual_comparisons=4480').replace('actual_comparisons==96','actual_comparisons==4480')
 a=driver.index("   for symbol in ['process_page_fault_prepare_body_result'")
 e=driver.index(' assert actual_comparisons==4480',a)
 driver=driver[:a]+'''   for symbol in ['process_extend_region_body_result','process_page_fault_cow_classify_body_result','fixture_selected_extend_process_region','page_is_in_memobj','page_is_multi_mapped','page_mode_in_memobj_result','page_multi_mapped_result','_ihk_mc_alloc_aligned_pages_node','_ihk_mc_free_pages','lookup_process_memory_range','add_process_memory_range','virt_to_phys','kprintf']:
    symbols_witness[symbol]=unique(symbols,symbol,{'T'})
   for symbol in ['process_extend_region_exists_debug','process_extend_region_alloc_debug','process_extend_region_success_debug']:
    found=unique(symbols,symbol,{'d','D'});assert int(found[-3],16)==32;symbols_witness[symbol]=found
'''+driver[e:]
 driver=driver.replace("PASS_ACTUAL_ORIGINAL_C_RUST_PAGE_FAULT_PREPARE96_REAL_ABI_HOST_EFFECTS","PASS_ACTUAL_ORIGINAL_C_RUST_EXTEND640_COW3840_REAL_ABI_HOST_EFFECTS")
 driver=driver.replace('actual_original_C_Rust_comparisons=96','actual_original_C_Rust_comparisons=4480')
 driver=driver.replace('lock_retained_for_original_caller=True,F01_Page_getter_not_executed=True','genuine_Page_predicates=True,controlled_ownership_effects_only=True,zeroobj_ownership_hold_untouched=True')
 df=H/'run_owned_extend_cow4480_once.py';put(df,driver)
 ready=dict(scope=SCOPE,status='ONE_EXTEND_COW4480_EXECUTABLE_READY_NO_GRANT',recipe=pin(rf),driver=pin(df),preparer=pin(Path(__file__)),
  preflight_history_bindings=[pin(p) for p in sourcehandoffs],expected_comparisons=4480,prepared_commands=6,profile=recipe['profile'],
  source_preparation_only=True,compiler_jobs=0,CPU_reservations=0,new_executable_queues=1,
  requires='Root exact scope/CPU6/ordinary_jobs1/ready_sha256 O_EXCL grant; fresh guards and proper CWD; first unexpected STOP/no retry.',
  root_union3_compile_not_replayed=True,prepare96_not_replayed=True,default_native_credit=False)
 readyf=H/'EXECUTABLE-READY.EXTEND-COW4480.NOT-GRANTED.json';write(readyf,ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(readyf),recipe=pin(rf),driver=pin(df),commands=6,planned_comparisons=4480,compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
