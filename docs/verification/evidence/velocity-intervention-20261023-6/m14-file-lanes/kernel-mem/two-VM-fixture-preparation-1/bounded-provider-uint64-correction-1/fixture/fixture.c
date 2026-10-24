/* Functional OS/Rust only; no security testing. Real VM public entries and existing full Rust bodies; typed controlled providers only. */
#include "actual_kernel_declarations.h"
#include <memory.h>
#include <errno.h>
extern int printf(const char*,...);extern void abort(void);
#define require(c) do{if(!(c)){printf("FAIL VM line=%d\n",__LINE__);return __LINE__;}}while(0)
extern int mem_lookup_node_body_result(struct process_vm*,void*,unsigned long,unsigned long,pte_t*(*)(page_table_t,void*,int,void**,size_t*,int*),int(*)(struct process_vm*,void*,unsigned long),int(*)(unsigned long));
extern pte_t *mem_pt_lookup_fault_pte_body_result(struct process_vm*,void*,int,void**,size_t*,int*,unsigned long,unsigned long,pte_t*(*)(page_table_t,void*,int,void**,size_t*,int*),int(*)(struct process_vm*,void*,unsigned long),void(*)(void*));
static struct process_vm vm;static struct address_space aspace;
static pte_t ptes[2];static int states[2],faultret,lookups,node_return;
struct event{unsigned long code,a,b,c,d,e;};static struct event trace[16],saved[16];static unsigned n;
static void event(unsigned long code,unsigned long a,unsigned long b,unsigned long c,unsigned long d,unsigned long e){if(n>=16)abort();trace[n++]=(struct event){code,a,b,c,d,e};}
pte_t *ihk_mc_pt_lookup_pte(page_table_t pt,void *addr,int shift,void **basep,size_t *sizep,int *p2alignp){int i=lookups++;if(i>1)abort();event(1,(unsigned long)pt,(unsigned long)addr,(unsigned long)(long)shift,basep!=0,(sizep!=0)|((p2alignp!=0)<<1));if(basep)*basep=(void*)0x12345000UL;if(sizep)*sizep=8192;if(p2alignp)*p2alignp=5;return states[i]?&ptes[i]:0;}
int page_fault_process_vm(struct process_vm *v,void *addr,uint64_t reason){event(2,(unsigned long)v,(unsigned long)addr,reason,(unsigned long)(long)faultret,0);return faultret;}
int phys_to_nid(unsigned long phys){event(3,phys,(unsigned long)(long)node_return,0,0,0);return node_return;}
int kprintf(const char *format,...){__builtin_va_list ap;__builtin_va_start(ap,format);const char *name=__builtin_va_arg(ap,const char*);unsigned long address=__builtin_va_arg(ap,unsigned long);__builtin_va_end(ap);if(strcmp(format,"%s: successfully faulted 0x%lx\n")||strcmp(name,"ihk_mc_pt_lookup_fault_pte"))abort();event(4,address,0,0,0,0);return -37;}
#include "original-C-default-wrappers-and-log.inc"
static void reset(void){lookups=n=0;memset(trace,0,sizeof trace);}
extern const unsigned long F01_VM_ACTUAL_LAYOUT[8];
int main(void){
 const unsigned long actual_layout[8]={__builtin_offsetof(struct process_vm,address_space),__builtin_offsetof(struct address_space,page_table),sizeof(unsigned long),sizeof(int),PTATTR_ACTIVE,PT_PHYSMASK,PF_USER,PF_POPULATE};
 require(!memcmp(actual_layout,F01_VM_ACTUAL_LAYOUT,sizeof actual_layout));
 const unsigned long addresses[]={0,4096,~0UL};const int returns[]={-14,0,37};const int shifts[]={-1,0,63};unsigned faultcases=0,nodecases=0;
 for(int geometry=0;geometry<4;geometry++)for(int a=0;a<3;a++)for(int b=0;b<3;b++)for(int r=0;r<3;r++)for(int v=0;v<3;v++)for(int s=0;s<3;s++)for(int output=0;output<2;output++){
  memset(&vm,0,sizeof vm);memset(&aspace,0,sizeof aspace);vm.address_space=geometry==2?0:&aspace;aspace.page_table=geometry==3?0:(void*)0xfeed000UL;struct process_vm *p=geometry==1?0:&vm;
  states[0]=a;states[1]=b;ptes[0]=0xabcde000UL|(a==2);ptes[1]=0xf1234000UL|(b==2);faultret=returns[r];void *base1=0,*base2=0;size_t size1=0,size2=0;int align1=0,align2=0;
  reset();pte_t *x=original_ihk_mc_pt_lookup_fault_pte(p,(void*)addresses[v],shifts[s],output?&base1:0,output?&size1:0,output?&align1:0);unsigned count=n;memcpy(saved,trace,sizeof trace);
  reset();pte_t *y=ihk_mc_pt_lookup_fault_pte(p,(void*)addresses[v],shifts[s],output?&base2:0,output?&size2:0,output?&align2:0);
  require(x==y&&n==count&&!memcmp(saved,trace,sizeof trace)&&base1==base2&&size1==size2&&align1==align2);
  if(geometry){require(y==0&&n==0&&lookups==0);}
  else if(a==2){require(y==&ptes[0]&&n==1&&lookups==1&&trace[0].code==1);}
  else{require(lookups==2&&n==(unsigned)(3+(b==2))&&trace[0].code==1&&trace[1].code==2&&trace[1].c==(PF_POPULATE|PF_USER)&&trace[2].code==1&&y==(b?&ptes[1]:0));if(b==2)require(trace[3].code==4&&trace[3].a==addresses[v]);}
  faultcases++;
 }
 for(int geometry=0;geometry<4;geometry++)for(int state=0;state<3;state++)for(int r=0;r<3;r++)for(int v=0;v<3;v++)for(int node=0;node<3;node++){
  memset(&vm,0,sizeof vm);memset(&aspace,0,sizeof aspace);vm.address_space=geometry==2?0:&aspace;aspace.page_table=geometry==3?0:(void*)0xfeed000UL;struct process_vm *p=geometry==1?0:&vm;
  states[0]=state;states[1]=0;ptes[0]=0xfff00000abcde000UL|(state==2);faultret=returns[r];node_return=returns[node];
  reset();int x=original_lookup_node(p,(void*)addresses[v]);unsigned count=n;memcpy(saved,trace,sizeof trace);
  reset();int y=lookup_node(p,(void*)addresses[v]);require(x==y&&n==count&&!memcmp(saved,trace,sizeof trace));
  require(trace[0].code==2&&trace[0].c==(PF_POPULATE|PF_USER));
  if(faultret){require(n==1&&lookups==0&&y==faultret);}
  else if(geometry){require(n==1&&lookups==0&&y==-ENOENT);}
  else if(state!=2){require(n==2&&lookups==1&&y==-ENOENT&&trace[1].code==1);}
  else{require(n==3&&lookups==1&&y==node_return&&trace[2].code==3&&trace[2].a==(ptes[0]&PT_PHYSMASK));}
  nodecases++;
 }
 require(faultcases==1944&&nodecases==324);printf("PASS VM fault-PTE=%u node=%u exact original-C/default-Rust trace/log/output/error pairs\n",faultcases,nodecases);return 0;
}
