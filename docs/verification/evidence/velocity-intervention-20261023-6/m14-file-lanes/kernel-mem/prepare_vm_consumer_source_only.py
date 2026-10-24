"""Functional OS/Rust only; no security testing. Two actual VM-entry fixture sources only, not executable-ready."""
from pathlib import Path
import hashlib,json,shutil
D=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');N=D/'two-VM-consumer-source-only-1';N.mkdir(exist_ok=False);sha=lambda b:hashlib.sha256(b).hexdigest();C=D/'next-fault-pte-source-1/candidate';rs=(C/'kernel/rust/mem_helpers.rs').read_text();cs=(R/'kernel/mem.c').read_text()
def extract(s,marker):
 a=s.index(marker);start=s.index('{',a);i=start+1;depth=1
 while depth:
  if s[i]=='{':depth+=1
  elif s[i]=='}':depth-=1
  i+=1
 return s[a:i]+'\n'
shutil.copyfile(D/'fixture/actual_abi.rs',N/'actual_abi.rs');shutil.copyfile(D/'fixture/actual_kernel_declarations.h',N/'actual_kernel_declarations.h')
prefix='''#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,ProcessVm,AddressSpace};
use core::{ffi::c_void,mem::offset_of,ptr::null_mut};
type MemLookupPteFn=unsafe extern "C" fn(*mut c_void,*mut c_void,CInt,*mut *mut c_void,*mut usize,*mut CInt)->*mut CULong;
type MemPageFaultProcessVmFn=unsafe extern "C" fn(*mut c_void,*mut c_void,CULong)->CInt;
type MemFaultLogFn=unsafe extern "C" fn(*mut c_void);
type MemPhysToNidFn=unsafe extern "C" fn(CULong)->CInt;
const EINVAL:CInt=22;const ENOENT:CInt=2;const PAGE_SIZE:CULong=4096;
const PTATTR_ACTIVE:CULong=1;const PT_PHYSMASK:CULong=((1u64<<52)-1)&!(PAGE_SIZE-1);
const PF_USER:CULong=1<<2;const PF_POPULATE:CULong=1<<30;
unsafe extern "C" {
 fn ihk_mc_pt_lookup_pte(pt:*mut c_void,virt:*mut c_void,pgshift:CInt,basep:*mut *mut c_void,sizep:*mut usize,p2alignp:*mut CInt)->*mut CULong;
 fn page_fault_process_vm(vm:*mut c_void,virt:*mut c_void,reason:CULong)->CInt;
 fn phys_to_nid(phys:CULong)->CInt;
 fn kprintf(format:*const i8,...)->CInt;
}
'''
markers=['unsafe fn mem_vm_page_table(','pub unsafe extern "C" fn mem_lookup_node_body_result(','pub unsafe extern "C" fn mem_pt_lookup_fault_pte_body_result(','pub unsafe extern "C" fn lookup_node(','unsafe extern "C" fn mem_lookup_fault_log_bridge(','pub unsafe extern "C" fn ihk_mc_pt_lookup_fault_pte('];bindings=[]
for marker in markers:
 body=extract(rs,marker);bindings.append({'marker':marker,'exact_function_sha256':sha(body.encode()),'bytes':len(body.encode())});prefix+=('\n#[no_mangle]\n' if marker.startswith('pub ') else '\n')+body
(N/'actual_VM_closure.rs').write_text(prefix);(N/'EXACT-FUNCTION-EXTRACTIONS.json').write_text(json.dumps(bindings,indent=2)+'\n')
original=''
for marker in ['static pte_t *mem_lookup_fault_pte_bridge(','static int mem_page_fault_process_vm_bridge(','static void mem_lookup_fault_log_bridge(','pte_t *ihk_mc_pt_lookup_fault_pte(','int lookup_node(']:
 body=extract(cs,marker)
 for old,new in [('ihk_mc_pt_lookup_fault_pte(','original_ihk_mc_pt_lookup_fault_pte('),('lookup_node(','original_lookup_node(')]:body=body.replace(old,new,1) if marker.startswith(old.split('(')[0]) else body
 # Explicit public renames, preserving default path and original literal log name.
 if marker.startswith('pte_t *ihk_mc_pt_lookup_fault_pte'):body=body.replace('pte_t *ihk_mc_pt_lookup_fault_pte(','pte_t *original_ihk_mc_pt_lookup_fault_pte(',1)
 if marker.startswith('int lookup_node'):body=body.replace('int lookup_node(','int original_lookup_node(',1)
 original+=body+'\n'
(N/'original-C-default-wrappers-and-log.inc').write_text(original)
c='''/* Functional OS/Rust only; no security testing. Real VM public entries and existing full Rust bodies; typed controlled providers only. */
#include "actual_kernel_declarations.h"
extern int printf(const char*,...);extern void abort(void);
#define require(c) do{if(!(c)){printf("FAIL VM line=%d\\n",__LINE__);return __LINE__;}}while(0)
extern int mem_lookup_node_body_result(void*,void*,unsigned long,unsigned long,pte_t*(*)(void*,void*,int,void**,size_t*,int*),int(*)(void*,void*,unsigned long),int(*)(unsigned long));
extern pte_t *mem_pt_lookup_fault_pte_body_result(void*,void*,int,void**,size_t*,int*,unsigned long,unsigned long,pte_t*(*)(void*,void*,int,void**,size_t*,int*),int(*)(void*,void*,unsigned long),void(*)(void*));
static struct process_vm vm;static struct address_space aspace;
static pte_t ptes[2];static int states[2],faultret,lookups,node_return;
struct event{unsigned long code,a,b,c,d,e;};static struct event trace[16],saved[16];static unsigned n;
static void event(unsigned long code,unsigned long a,unsigned long b,unsigned long c,unsigned long d,unsigned long e){if(n>=16)abort();trace[n++]=(struct event){code,a,b,c,d,e};}
pte_t *ihk_mc_pt_lookup_pte(page_table_t pt,void *addr,int shift,void **basep,size_t *sizep,int *p2alignp){int i=lookups++;if(i>1)abort();event(1,(unsigned long)pt,(unsigned long)addr,(unsigned long)(long)shift,basep!=0,(sizep!=0)|((p2alignp!=0)<<1));if(basep)*basep=(void*)0x12345000UL;if(sizep)*sizep=8192;if(p2alignp)*p2alignp=5;return states[i]?&ptes[i]:0;}
int page_fault_process_vm(struct process_vm *v,void *addr,unsigned long reason){event(2,(unsigned long)v,(unsigned long)addr,reason,(unsigned long)(long)faultret,0);return faultret;}
int phys_to_nid(unsigned long phys){event(3,phys,(unsigned long)(long)node_return,0,0,0);return node_return;}
int kprintf(const char *format,...){__builtin_va_list ap;__builtin_va_start(ap,format);const char *name=__builtin_va_arg(ap,const char*);unsigned long address=__builtin_va_arg(ap,unsigned long);__builtin_va_end(ap);if(strcmp(format,"%s: successfully faulted 0x%lx\\n")||strcmp(name,"ihk_mc_pt_lookup_fault_pte"))abort();event(4,address,0,0,0,0);return -37;}
#include "original-C-default-wrappers-and-log.inc"
static void reset(void){lookups=n=0;memset(trace,0,sizeof trace);}
int main(void){
 const unsigned long addresses[]={0,4096,~0UL};const int returns[]={-14,0,37};const int shifts[]={-1,0,63};unsigned faultcases=0,nodecases=0;
 for(int geometry=0;geometry<4;geometry++)for(int a=0;a<3;a++)for(int b=0;b<3;b++)for(int r=0;r<3;r++)for(int v=0;v<3;v++)for(int s=0;s<3;s++)for(int output=0;output<2;output++){
  memset(&vm,0,sizeof vm);memset(&aspace,0,sizeof aspace);vm.address_space=geometry==2?0:&aspace;aspace.page_table=geometry==3?0:(void*)0xfeed000UL;struct process_vm *p=geometry==1?0:&vm;
  states[0]=a;states[1]=b;ptes[0]=0xabcde000UL|(a==2);ptes[1]=0xf1234000UL|(b==2);faultret=returns[r];void *base1=0,*base2=0;size_t size1=0,size2=0;int align1=0,align2=0;
  reset();pte_t *x=original_ihk_mc_pt_lookup_fault_pte(p,(void*)addresses[v],shifts[s],output?&base1:0,output?&size1:0,output?&align1:0);unsigned count=n;memcpy(saved,trace,sizeof trace);
  reset();pte_t *y=ihk_mc_pt_lookup_fault_pte(p,(void*)addresses[v],shifts[s],output?&base2:0,output?&size2:0,output?&align2:0);
  require(x==y&&n==count&&!memcmp(saved,trace,sizeof trace)&&base1==base2&&size1==size2&&align1==align2);faultcases++;
 }
 for(int geometry=0;geometry<4;geometry++)for(int state=0;state<3;state++)for(int r=0;r<3;r++)for(int v=0;v<3;v++)for(int node=0;node<3;node++){
  memset(&vm,0,sizeof vm);memset(&aspace,0,sizeof aspace);vm.address_space=geometry==2?0:&aspace;aspace.page_table=geometry==3?0:(void*)0xfeed000UL;struct process_vm *p=geometry==1?0:&vm;
  states[0]=state;states[1]=0;ptes[0]=0xfff00000abcde000UL|(state==2);faultret=returns[r];node_return=returns[node];
  reset();int x=original_lookup_node(p,(void*)addresses[v]);unsigned count=n;memcpy(saved,trace,sizeof trace);
  reset();int y=lookup_node(p,(void*)addresses[v]);require(x==y&&n==count&&!memcmp(saved,trace,sizeof trace));nodecases++;
 }
 require(faultcases==5832&&nodecases==324);printf("PASS VM fault-PTE=%u node=%u exact original-C/default-Rust trace/log/output/error pairs\\n",faultcases,nodecases);return 0;
}
'''
# Only a source fixture: default wrappers require real public prototypes already from actual headers.
(N/'fixture.c').write_text(c)
a={'scope':__doc__,'status':'NEXT_TWO_VM_CONSUMER_SOURCE_ONLY_NOT_EXECUTABLE_READY','candidate':str(C),'source_bindings':[{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(N.iterdir())],'actual':None,'planned_fault_cases':5832,'planned_node_cases':324,'qualification':'Exact full Rust helpers+publicentries+real diagnosticcallback; publicfault/PTE/NUMA/kprintf endpoints controlled. Native synchronization/ISA not exercised. C default wrappers preserve actual existinghelper null/error behavior; no Cfallback invalidpointer execution planned. HeaderABI/defaultfallback consumers and buildrecipe still future, so no second queued executablecohort.','execution_grant':None};(N/'SOURCE-ONLY.NOT-READY.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({'root':str(N),'receipt_sha256':sha((N/'SOURCE-ONLY.NOT-READY.json').read_bytes())},indent=2))
