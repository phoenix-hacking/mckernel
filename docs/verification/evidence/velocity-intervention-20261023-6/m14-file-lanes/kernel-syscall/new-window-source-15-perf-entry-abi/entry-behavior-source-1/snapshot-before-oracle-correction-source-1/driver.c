/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-15-perf-entry-abi/entry-behavior-source-1/reference.c"
extern long sys_perf_event_open(int,ihk_mc_user_context_t *);
extern const unsigned long f03_perf_entry_fixture_Rust_ABI[56];
extern int printf(const char *,...);
extern void abort(void);
extern int dprintf(int,const char *,...);
#define require(value) do { if(!(value)){ dprintf(2,"FAIL perf entry assertion line=%d expr=%s\n",__LINE__,#value); abort(); } } while(0)
static struct cpu_local_var cpu_state;
static struct thread task;
static struct process process_state;
static struct mc_perf_event event_state,leader_state;
static struct mckfd old_descriptor,new_descriptor;
static ihk_mc_user_context_t context_state;
static struct perf_event_attr user_attribute;
static int scenario,counter_value,mutate_context,expected_pid;
static long linux_result;
static unsigned long original_flags;
struct observations {
 int events[16],event_count,copy_calls,freq_calls,event_calls,counter_calls;
 int syscall_calls,descriptor_calls,lock_calls,unlock_calls,callback_calls;
 unsigned long copied_size,copied_source,descriptor_size,descriptor_flags;
 struct perf_event_attr copied_attribute;
 struct syscall_request prepared_request;
 int delivered_linux_cpu,event_pid,counter_id,descriptor_fd,signal_number;
 unsigned long map,event_status,leader_status,leader_siblings,group_owner;
 unsigned long process_head,descriptor_next,descriptor_data,callback_mask;
 unsigned long group_next,group_prev,leader_next,leader_prev;
 ihk_mc_user_context_t context_after;
};
static struct observations observed;
static void note(int event){require(observed.event_count<16);observed.events[observed.event_count++]=event;}
struct cpu_local_var *get_this_cpu_local_var(void){note(1);return &cpu_state;}
int ihk_mc_get_processor_id(void){note(2);return 3;}
long fixture_copy(void *destination,unsigned long source,size_t size)
{
 note(3);observed.copy_calls++;observed.copied_size=size;observed.copied_source=source;
 require(source==(unsigned long)&user_attribute);require(size==sizeof(user_attribute));
 if(mutate_context){context_state.gpr.rsi=0x55555555;context_state.gpr.rdx=0x77777777;context_state.gpr.r8=~0UL;}
 if(scenario==1)return 1;
 __builtin_memcpy(destination,(void *)source,size);
 __builtin_memcpy(&observed.copied_attribute,destination,size);
 return 0;
}
int fixture_frequency(const void *attribute)
{
 note(4);observed.freq_calls++;
 require(!memcmp(attribute,&user_attribute,sizeof(user_attribute)));
 return ((const struct perf_event_attr *)attribute)->freq;
}
int fixture_event(void **output,void *attribute)
{
 note(5);observed.event_calls++;
 require(!memcmp(attribute,&user_attribute,sizeof(user_attribute)));
 if(scenario==8)return -12;
 __builtin_memcpy(&event_state.attr,attribute,sizeof(user_attribute));
 *output=&event_state;return 0;
}
int fixture_counter(void *thread,void *event)
{
 note(6);observed.counter_calls++;require(thread==&task&&event==&event_state);
 require(event_state.pid==expected_pid);
 if(scenario==9)return -28;
 return counter_value;
}
long fixture_syscall(struct syscall_request *request,int cpu)
{
 note(7);observed.syscall_calls++;observed.delivered_linux_cpu=cpu;
 require(cpu==3);require(request->number==__NR_perf_event_open);
 for(unsigned i=0;i<6;i++)require(request->args[i]==0);
 /* IDs/valid are deliberately initialized by their controlled provider owner.
  * Their incoming bytes are not read: the real existing helper leaves these
  * fields to actual do_syscall preparation, outside this controlled fixture. */
 request->rtid=task.tid;request->ttid=process_state.pid;request->valid=0x123456789abcdef0UL;
 observed.prepared_request=*request;
 if(scenario==12)return -9;
 return linux_result;
}
void *fixture_descriptor(size_t size,unsigned long flags)
{
 note(8);observed.descriptor_calls++;observed.descriptor_size=size;observed.descriptor_flags=flags;
 require(size==sizeof(struct mckfd)&&flags==IHK_MC_AP_NOWAIT);
 if(scenario==13)return NULL;
 return &new_descriptor;
}
long fixture_read(struct mckfd *fd,ihk_mc_user_context_t *context){observed.callback_calls++;require(fd==&new_descriptor&&context==&context_state);return 31;}
int fixture_ioctl(struct mckfd *fd,ihk_mc_user_context_t *context){observed.callback_calls++;require(fd==&new_descriptor&&context==&context_state);return 32;}
long fixture_mmap(struct mckfd *fd,ihk_mc_user_context_t *context){observed.callback_calls++;require(fd==&new_descriptor&&context==&context_state);return 33;}
int fixture_close(struct mckfd *fd,ihk_mc_user_context_t *context){observed.callback_calls++;require(fd==&new_descriptor&&context==&context_state);return 34;}
int fixture_fcntl(struct mckfd *fd,ihk_mc_user_context_t *context){observed.callback_calls++;require(fd==&new_descriptor&&context==&context_state);return 35;}
long fixture_lock(void *lock)
{
 note(9);observed.lock_calls++;require(lock==&process_state.mckfd_lock);
 require(new_descriptor.fd==(int)linux_result&&new_descriptor.sig_no==-1);
 require(new_descriptor.data==(long)&event_state);return 0x12345678;
}
void fixture_unlock(void *lock,long irqstate)
{
 note(10);observed.unlock_calls++;require(lock==&process_state.mckfd_lock&&irqstate==0x12345678);
 require(process_state.mckfd==&new_descriptor);
}
static void reset(unsigned long pid,long fd,int counter,int mutation,int selected_scenario)
{
 __builtin_memset(&observed,0,sizeof(observed));
 __builtin_memset(&cpu_state,0,sizeof(cpu_state));__builtin_memset(&task,0,sizeof(task));
 __builtin_memset(&process_state,0,sizeof(process_state));
 __builtin_memset(&event_state,0,sizeof(event_state));__builtin_memset(&leader_state,0,sizeof(leader_state));
 __builtin_memset(&old_descriptor,0,sizeof(old_descriptor));__builtin_memset(&new_descriptor,0,sizeof(new_descriptor));
 __builtin_memset(&context_state,0,sizeof(context_state));__builtin_memset(&user_attribute,0,sizeof(user_attribute));
 scenario=selected_scenario;counter_value=counter;linux_result=fd;mutate_context=mutation;expected_pid=(int)pid;
 cpu_state.current=&task;task.proc=&process_state;task.tid=-77;process_state.pid=314;
 task.pmc_alloc_map=0x200;event_state.counter_id=-99;
 event_state.sibling_list.next=event_state.sibling_list.prev=&event_state.sibling_list;
 event_state.group_entry.next=event_state.group_entry.prev=&event_state.group_entry;
 leader_state.sibling_list.next=leader_state.sibling_list.prev=&leader_state.sibling_list;
 leader_state.nr_siblings=3;leader_state.pmc_status=0x80;
 user_attribute.type=PERF_TYPE_RAW;user_attribute.size=sizeof(user_attribute);
 user_attribute.config=0x1122334455667788UL;user_attribute.sample_period=17;
 user_attribute.sample_type=0xfedcba9876543210UL;user_attribute.config1=0x1020304050607080UL;
 context_state.gpr.rdi=(unsigned long)&user_attribute;context_state.gpr.rsi=pid;
 context_state.gpr.rdx=-1UL;context_state.gpr.r10=-1UL;context_state.gpr.r8=0;
 context_state.gpr.rax=0xabcdef0123456789UL;
 if(scenario==2)context_state.gpr.rdx=1;
 if(scenario==3)context_state.gpr.r8=0x100000000UL;
 if(scenario==4)user_attribute.type=0xffffffffU;
 if(scenario==5)user_attribute.read_format=PERF_FORMAT_ID;
 if(scenario==6){user_attribute.freq=1;user_attribute.sample_period=1UL<<63;context_state.gpr.rdx=1;}
 if(scenario==7){user_attribute.sample_period=1UL<<63;context_state.gpr.rdx=1;context_state.gpr.r8=1;}
 if(scenario==10)context_state.gpr.r10=55;
 if(scenario==11||scenario==14){
  context_state.gpr.r10=55;old_descriptor.fd=55;old_descriptor.data=(long)&leader_state;
  process_state.mckfd=&old_descriptor;
  if(scenario==11)leader_state.sibling_list.prev=NULL;
 }
 if(scenario==15){context_state.gpr.rdx=0x100000000UL;context_state.gpr.r10=0x1ffffffffUL;}
 if(scenario==16){user_attribute.type=PERF_TYPE_HARDWARE;user_attribute.read_format=PERF_FORMAT_GROUP;}
 if(scenario==17){user_attribute.type=PERF_TYPE_HW_CACHE;context_state.gpr.rdx=0xffffffff80000000UL;}
 original_flags=context_state.gpr.r8;
}
static void snapshot(void)
{
 observed.event_pid=event_state.pid;observed.counter_id=event_state.counter_id;
 observed.map=task.pmc_alloc_map;observed.event_status=event_state.pmc_status;
 observed.leader_status=leader_state.pmc_status;observed.leader_siblings=leader_state.nr_siblings;
 observed.group_owner=(unsigned long)event_state.group_leader;
 observed.process_head=(unsigned long)process_state.mckfd;
 observed.descriptor_next=(unsigned long)new_descriptor.next;observed.descriptor_fd=new_descriptor.fd;
 observed.signal_number=new_descriptor.sig_no;observed.descriptor_data=new_descriptor.data;
 observed.group_next=(unsigned long)event_state.group_entry.next;observed.group_prev=(unsigned long)event_state.group_entry.prev;
 observed.leader_next=(unsigned long)leader_state.sibling_list.next;observed.leader_prev=(unsigned long)leader_state.sibling_list.prev;
 observed.callback_mask=(new_descriptor.read_cb==fixture_read)|((new_descriptor.ioctl_cb==fixture_ioctl)<<1)|((new_descriptor.mmap_cb==fixture_mmap)<<2)|((new_descriptor.close_cb==fixture_close)<<3)|((new_descriptor.fcntl_cb==fixture_fcntl)<<4);
 observed.context_after=context_state;
}
static long expected_return(void)
{
 switch(scenario){case 1:return -14;case 2:case 3:case 4:case 5:case 6:return -2;
 case 7:case 10:case 11:return -22;case 8:case 13:return -12;case 9:return -28;case 12:return -9;
 default:return (int)linux_result;}
}
static unsigned long counter_bit(void){return counter_value>=0&&counter_value<64?1UL<<counter_value:0;}
static void independent_oracles(long result)
{
 require(result==expected_return());require(observed.callback_calls==0);
 require(observed.event_count>=3&&observed.events[0]==1&&observed.events[1]==2&&observed.events[2]==3);
 require(observed.copy_calls==1);require(observed.freq_calls==(scenario!=1));
 int valid=scenario==0||scenario>=8;require(observed.event_calls==valid);
 require(observed.counter_calls==(valid&&scenario!=8));
 int delegated=valid&&scenario!=8&&scenario!=9&&scenario!=10&&scenario!=11;
 require(observed.syscall_calls==delegated);
 require(observed.descriptor_calls==(delegated&&scenario!=12));
 int published=delegated&&scenario!=12&&scenario!=13;
 require(observed.lock_calls==published&&observed.unlock_calls==published);
 require(observed.event_count==(scenario==1?3:4+observed.event_calls+observed.counter_calls+observed.syscall_calls+observed.descriptor_calls+observed.lock_calls+observed.unlock_calls));
 for(int i=1;i<observed.event_count;i++)require(observed.events[i]>observed.events[i-1]);
 require(observed.map==(0x200UL|((delegated&&scenario!=12)?counter_bit():0)));
 if(observed.counter_calls)require(event_state.pid==expected_pid);
 if(published){
  require(process_state.mckfd==&new_descriptor&&observed.callback_mask==31);
  require(new_descriptor.fd==(int)linux_result&&new_descriptor.sig_no==-1);
  require(new_descriptor.next==(scenario==14?&old_descriptor:NULL));
  require(new_descriptor.data==(long)&event_state);
 }else require(process_state.mckfd==((scenario==11||scenario==14)?&old_descriptor:NULL));
 if(scenario==14){require(leader_state.nr_siblings==4);require(leader_state.pmc_status==(0x80UL|counter_bit()));}
 if(scenario==11){require(event_state.group_leader==&leader_state&&leader_state.nr_siblings==3);}
 if(observed.syscall_calls){require(observed.prepared_request.rtid==-77&&observed.prepared_request.ttid==314);require(observed.prepared_request.valid==0x123456789abcdef0UL);}
 if(mutate_context){require(context_state.gpr.rsi==0x55555555&&context_state.gpr.rdx==0x77777777&&context_state.gpr.r8==~0UL);}
 else require(context_state.gpr.r8==original_flags);
}
int main(void)
{
 require(!memcmp(f03_perf_entry_fixture_C_ABI,f03_perf_entry_fixture_Rust_ABI,sizeof(f03_perf_entry_fixture_C_ABI)));
 const unsigned long pids[]={0,1,0xffffffffUL,0x80000000UL,0x100000001UL};
 const long descriptors[]={0,17,2147483647L,2147483648L,0x100000005L};
 const int counters[]={0,1,63,64};unsigned tested=0;
 for(int selected=0;selected<18;selected++)for(unsigned p=0;p<5;p++)for(unsigned f=0;f<5;f++)for(unsigned k=0;k<4;k++)for(int mutation=0;mutation<2;mutation++){
  reset(pids[p],descriptors[f],counters[k],mutation,selected);
  long old=original_sys_perf_event_open(-77,&context_state);snapshot();independent_oracles(old);struct observations baseline=observed;
  reset(pids[p],descriptors[f],counters[k],mutation,selected);
  long new=sys_perf_event_open(298,&context_state);snapshot();independent_oracles(new);
  require(old==new);require(!memcmp(&baseline,&observed,sizeof(observed)));tested++;
 }
 require(tested==3600);
 printf("PASS perf entry genuine-C/Rust cases=3600 ABI56 scenarios18 providers13 copy/error/order/identity/request/flags/publication controlled-only\n");
 return 0;
}
