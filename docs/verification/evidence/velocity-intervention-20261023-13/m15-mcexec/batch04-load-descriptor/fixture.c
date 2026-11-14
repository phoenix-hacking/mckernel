/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "fixture-prelude.h"
int debug;
static int alloc_fail,parse_fail;
void *__real_malloc(size_t);
void *__wrap_malloc(size_t n) {printf("alloc=%zu\n",n);if(alloc_fail){alloc_fail=0;return NULL;}return __real_malloc(n);}
long __wrap_sysconf(int n) {assert(n==_SC_CLK_TCK);puts("clock-tick");return 100;}
int __wrap_getrlimit(__rlimit_resource_t resource,struct rlimit *p) {printf("getrlimit=%d\n",(int)resource);if(resource==RLIMIT_RSS)return -1;p->rlim_cur=1000+resource;p->rlim_max=2000+resource;return 0;}
struct bitmask *numa_parse_nodestring_all(const char *s) {assert(!strcmp(s,"2,63"));printf("parse-nodes=%d\n",parse_fail);return parse_fail?NULL:(void*)0x1234;}
int numa_max_possible_node(void) {return 63;}
int numa_bitmask_isbitset(const struct bitmask *p,unsigned n) {assert(p==(void*)0x1234);return n==2||n==63;}
void mcexec_numa_local_body(unsigned long *cpu,unsigned long *mask,int nonlocal) {assert(cpu[0]==0x55);printf("numa-local=%d\n",nonlocal);mask[0]=nonlocal?0x20:0x10;}
void mcexec_numa_all_body(unsigned long *mask) {puts("numa-all");mask[0]=0x30;}
static void dump(const void *p,size_t n) {const unsigned char *s=p;for(size_t i=0;i<n;i++)printf("%02x",s[i]);puts("");}
int main(void) {
size_t abi[]={sizeof(struct program_load_desc),_Alignof(struct program_load_desc),sizeof(struct program_image_section),_Alignof(struct program_image_section),
offsetof(struct program_load_desc,magic),
offsetof(struct program_load_desc,num_sections),
offsetof(struct program_load_desc,cpu),
offsetof(struct program_load_desc,pid),
offsetof(struct program_load_desc,stack_prot),
offsetof(struct program_load_desc,pgid),
offsetof(struct program_load_desc,cred),
offsetof(struct program_load_desc,reloc),
offsetof(struct program_load_desc,enable_vdso),
offsetof(struct program_load_desc,padding),
offsetof(struct program_load_desc,entry),
offsetof(struct program_load_desc,user_start),
offsetof(struct program_load_desc,user_end),
offsetof(struct program_load_desc,rprocess),
offsetof(struct program_load_desc,rpgtable),
offsetof(struct program_load_desc,at_phdr),
offsetof(struct program_load_desc,at_phent),
offsetof(struct program_load_desc,at_phnum),
offsetof(struct program_load_desc,at_entry),
offsetof(struct program_load_desc,at_clktck),
offsetof(struct program_load_desc,args),
offsetof(struct program_load_desc,args_len),
offsetof(struct program_load_desc,envs),
offsetof(struct program_load_desc,envs_len),
offsetof(struct program_load_desc,rlimit),
offsetof(struct program_load_desc,interp_align),
offsetof(struct program_load_desc,mpol_flags),
offsetof(struct program_load_desc,mpol_threshold),
offsetof(struct program_load_desc,heap_extension),
offsetof(struct program_load_desc,stack_premap),
offsetof(struct program_load_desc,mpol_bind_mask),
offsetof(struct program_load_desc,mpol_mode),
offsetof(struct program_load_desc,mpol_nodemask),
offsetof(struct program_load_desc,thp_disable),
offsetof(struct program_load_desc,enable_uti),
offsetof(struct program_load_desc,uti_thread_rank),
offsetof(struct program_load_desc,uti_use_last_cpu),
offsetof(struct program_load_desc,straight_map),
offsetof(struct program_load_desc,straight_map_threshold),
#ifdef ENABLE_TOFU
offsetof(struct program_load_desc,enable_tofu),
#endif
offsetof(struct program_load_desc,mcexec_flags),
offsetof(struct program_load_desc,nr_processes),
offsetof(struct program_load_desc,process_rank),
offsetof(struct program_load_desc,cpu_set),
offsetof(struct program_load_desc,profile),
offsetof(struct program_load_desc,sections),
offsetof(struct program_image_section,vaddr),
offsetof(struct program_image_section,len),
offsetof(struct program_image_section,remote_pa),
offsetof(struct program_image_section,filesz),
offsetof(struct program_image_section,offset),
offsetof(struct program_image_section,prot),
offsetof(struct program_image_section,interp),
offsetof(struct program_image_section,padding),
offsetof(struct program_image_section,fp),
};

#ifdef RUST_IMPL
 extern size_t mcexec_desc_fixture_abi(size_t *);size_t rustabi[80];size_t count=mcexec_desc_fixture_abi(rustabi);assert(count==sizeof(abi)/sizeof(abi[0])&&!memcmp(abi,rustabi,sizeof abi));
#endif
 printf("abi=");for(size_t i=0;i<sizeof(abi)/sizeof(*abi);i++)printf("%zu,",abi[i]);puts("");
 assert(mcexec_program_load_desc_size_bridge()==sizeof(struct program_load_desc));assert(mcexec_program_image_section_size_bridge()==sizeof(struct program_image_section));
 alloc_fail=1;assert(!mcexec_load_alloc_desc_bridge(2));
 struct program_load_desc *d=mcexec_load_alloc_desc_bridge(2);assert(d&&d->magic==PLD_MAGIC&&d->num_sections==2&&d->stack_prot==7);
 int *cred=mcexec_load_cred_bridge(d);assert(cred==d->cred);for(int i=0;i<8;i++)cred[i]=i+50;
 mcexec_load_publish_main_section_bridge(d,0,0x100,0x20,0x30,0x40,5,(void*)0x1111);
 mcexec_desc_publish_interp_section_bridge(d,1,0x200,0x50,0x60,0x70,6,(void*)0x2222);
 d->sections[0].remote_pa=0x1234;d->rprocess=0xabcd;
 assert(mcexec_desc_section_vaddr_bridge(d,0)==0x100&&mcexec_desc_section_len_bridge(d,1)==0x70&&mcexec_desc_section_filesz_bridge(d,0)==0x20&&mcexec_desc_section_offset_bridge(d,1)==0x60&&mcexec_desc_section_remote_pa_bridge(d,0)==0x1234&&mcexec_desc_section_fp_bridge(d,1)==(void*)0x2222);
 mcexec_load_finalize_desc_bridge(d,21,22,1,0x300,0x400,56,2,0x500,mcexec_load_clk_tck_bridge(),3);
 assert(mcexec_desc_pid_bridge(d)==21&&mcexec_desc_entry_bridge(d)==0x300&&mcexec_desc_rprocess_bridge(d)==0xabcd);
 mcexec_desc_set_num_sections_bridge(d,1);assert(mcexec_desc_num_sections_bridge(d)==1);mcexec_desc_set_num_sections_bridge(d,2);
 mcexec_desc_set_entry_bridge(d,0x999);mcexec_desc_set_interp_align_bridge(d,0x1000);mcexec_desc_set_args_len_bridge(d,77);
 mcexec_partition_publish_cpu_rank_bridge(d,4,5);assert(mcexec_desc_cpu_bridge(d)==4);mcexec_partition_publish_rank_bridge(d,6);
 mcexec_desc_publish_mpol_base_bridge(d,1,3,7,8,9,5);parse_fail=1;mcexec_desc_apply_bind_nodes_bridge(d,"2,63");assert(!d->mpol_bind_mask);parse_fail=0;mcexec_desc_apply_bind_nodes_bridge(d,"2,63");assert(d->mpol_bind_mask==((1UL<<2)|(1UL<<63)));
 d->cpu_set[0]=0x55;for(int i=0;i<5;i++)mcexec_desc_apply_ompi_policy_bridge(d,10+i,i);
 mcexec_desc_publish_runtime_flags_bridge(d,1,2,3,4,5,600,7,0x123);mcexec_desc_publish_runtime_flags_bridge(d,2,3,4,5,6,700,8,0);assert(d->mcexec_flags==0x123);mcexec_desc_clear_flags_bridge(d);assert(!d->mcexec_flags);
 mcexec_desc_snapshot_rlimits_bridge(d);assert(d->rlimit[MCK_RLIMIT_RSS].rlim_cur==0);
 mcexec_desc_set_execve1_runtime_bridge(d,258,41,42,-43);assert(d->enable_vdso==2&&d->rlimit[RLIMIT_STACK].rlim_cur==41);
 debug=1;mcexec_main_stack_publish_bridge(d,51,52,-53);debug=0;assert(d->rlimit[MCK_RLIMIT_STACK].rlim_cur==51);
 mcexec_desc_publish_env_bridge(d,-2,(void*)0x3333);mcexec_desc_publish_args_cpu_bridge(d,88,(void*)0x4444,9,257);assert(d->enable_vdso==1&&d->envs_len==(unsigned long)-2);
 dump(d,sizeof(*d)+2*sizeof(d->sections[0]));free(d);
 puts("descriptor-fixture-complete");return 0;
}
