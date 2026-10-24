/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Literal old C entries/fallback helpers, genuine Rust helpers/getters/real context.
 * Only do_execveat lifecycle effect controlled; no exec/syscall/kernel execution. */
#include <types.h>
#include <process.h>
#include <syscall.h>
#include <errno.h>
#include <string.h>
#ifndef offsetof
#define offsetof(t,m) __builtin_offsetof(t,m)
#endif
extern int printf(const char*,...);extern void abort(void);
extern long sys_execve(int,ihk_mc_user_context_t*);
extern long sys_execveat(int,ihk_mc_user_context_t*);
extern size_t f03_exec_fixture_layout(size_t*);
static unsigned long case_id;static int which;
#define CHECK(x) do{if(!(x)){printf("FAIL case=%lu implementation=%d line=%d predicate=%s\n",case_id,which,__LINE__,#x);abort();}}while(0)
static void zero(void*p,size_t n){unsigned char*b=p;for(size_t i=0;i<n;i++)b[i]=0;}
static void copy(void*d0,const void*s0,size_t n){unsigned char*d=d0;const unsigned char*s=s0;for(size_t i=0;i<n;i++)d[i]=s[i];}
/* Known hosted-only kernelstring macro linkage, not production compute code. */
void *__inline_memset(void*p,unsigned long v,size_t n){unsigned char*b=p;for(size_t i=0;i<n;i++)b[i]=(unsigned char)v;return p;}
void *__inline_memcpy(void*d,const void*s,size_t n){copy(d,s,n);return d;}
static ihk_mc_user_context_t ctx;
static char names[4][5]={{'/',0},{'r','e','l',0},{0},{(char)0xff,0}};
static char *argv_values[2],*envp_values[2];
static char **expected_argv,**expected_envp;static const char *expected_filename;
static int expected_dirfd,expected_flags,provider_result;static unsigned long called;
struct observed {unsigned long ctx,dirfd,filename,argv,envp,flags,return_bits;};
static struct observed observed;
int f03_fixture_do_execveat(ihk_mc_user_context_t*passed,int dirfd,const char*filename,char**argv,char**envp,int flags){
 CHECK(passed==&ctx&&dirfd==expected_dirfd&&filename==expected_filename&&argv==expected_argv&&envp==expected_envp&&flags==expected_flags&&called==0);
 called++;observed=(struct observed){(unsigned long)passed,(unsigned long)dirfd,(unsigned long)filename,(unsigned long)argv,(unsigned long)envp,(unsigned long)flags,(unsigned long)(long)provider_result};
 /* Model observable lifecycle writes only after argument admission and capture. */
 passed->gpr.rax^=0x5a5a5a5aUL;passed->gpr.r10^=0x1357UL;
 if(argv)argv[0]=names[1];if(envp)envp[0]=names[2];return provider_result;
}
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-exec-entries-source-1/fixture-fragments-only/exec_entries_actual.C-FIXTURE-FRAGMENT.inc"
_Static_assert(__builtin_types_compatible_p(__typeof__(&sys_execve),long(*)(int,ihk_mc_user_context_t*)),"actual execve entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&sys_execveat),long(*)(int,ihk_mc_user_context_t*)),"actual execveat entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_execveat_bridge),int(*)(void*,int,const char*,char**,char**,int)),"actual retained provider ABI");
_Static_assert(sizeof(int)==4&&sizeof(long)==8&&sizeof(void*)==8&&(char)0xff<0,"actual x86_64 widths/promotion");
static void abi_check(void){size_t r[16],c[]={sizeof(ihk_mc_user_context_t),_Alignof(ihk_mc_user_context_t),offsetof(ihk_mc_user_context_t,gpr),offsetof(ihk_mc_user_context_t,sr),sizeof(struct x86_basic_regs),_Alignof(struct x86_basic_regs),offsetof(struct x86_basic_regs,rdi),offsetof(struct x86_basic_regs,rsi),offsetof(struct x86_basic_regs,rdx),offsetof(struct x86_basic_regs,r10),offsetof(struct x86_basic_regs,r8),offsetof(struct x86_basic_regs,r9),offsetof(struct x86_basic_regs,rax),offsetof(struct x86_basic_regs,orig_rax)};CHECK(f03_exec_fixture_layout(r)==sizeof(c)/sizeof(c[0]));for(size_t i=0;i<sizeof(c)/sizeof(c[0]);i++)if(c[i]!=r[i]){printf("ABI_MISMATCH index=%lu C=%lu Rust=%lu\n",i,c[i],r[i]);abort();}}
static void init(int is_at,int filename_index,int fd,int flags,int alias,int result){
 zero(&ctx,sizeof(ctx));zero(&observed,sizeof(observed));called=0;provider_result=result;
 argv_values[0]=names[0];argv_values[1]=0;envp_values[0]=names[3];envp_values[1]=0;
 expected_argv=alias==2?0:argv_values;expected_envp=alias==2?0:alias==1?argv_values:envp_values;
 expected_filename=names[filename_index];expected_dirfd=is_at?fd:AT_FDCWD;expected_flags=is_at?flags:0;
 ctx.gpr.rdi=is_at?(unsigned long)fd:(unsigned long)expected_filename;
 ctx.gpr.rsi=is_at?(unsigned long)expected_filename:(unsigned long)expected_argv;
 ctx.gpr.rdx=is_at?(unsigned long)expected_argv:(unsigned long)expected_envp;
 ctx.gpr.r10=is_at?(unsigned long)expected_envp:0x123456789abcdef0UL;
 ctx.gpr.r8=is_at?(unsigned long)flags:0xaaaaffffUL;ctx.gpr.r9=0xcccc5555UL;ctx.gpr.rax=0x76543210UL;ctx.gpr.orig_rax=0x10203040UL;
 ctx.gpr.rip=0x23456789UL;ctx.gpr.rsp=0x34567890UL;
}
struct outcome {unsigned long result,called;struct observed args;unsigned long rdi,rsi,rdx,r10,r8,r9,rax,orig_rax,rip,rsp,argv0,argv1,envp0,envp1;};
static struct outcome baseline,candidate;
static void save(struct outcome*out,long result){*out=(struct outcome){(unsigned long)result,called,observed,ctx.gpr.rdi,ctx.gpr.rsi,ctx.gpr.rdx,ctx.gpr.r10,ctx.gpr.r8,ctx.gpr.r9,ctx.gpr.rax,ctx.gpr.orig_rax,ctx.gpr.rip,ctx.gpr.rsp,(unsigned long)argv_values[0],(unsigned long)argv_values[1],(unsigned long)envp_values[0],(unsigned long)envp_values[1]};}
static void same(void){if(memcmp(&baseline,&candidate,sizeof(baseline))){printf("MISMATCH case=%lu C_rc=%ld Rust_rc=%ld C_calls=%lu Rust_calls=%lu\n",case_id,(long)baseline.result,(long)candidate.result,baseline.called,candidate.called);for(size_t i=0;i<sizeof(baseline)/sizeof(unsigned long);i++)if(((unsigned long*)&baseline)[i]!=((unsigned long*)&candidate)[i])printf("outcome%lu C=%lx Rust=%lx\n",i,((unsigned long*)&baseline)[i],((unsigned long*)&candidate)[i]);abort();}}
int main(void){
 abi_check();const int results[]={(-2147483647-1),-12,-14,-1,0,1,2147483647};const int fds[]={AT_FDCWD,-1,-101,0,1,(-2147483647-1),2147483647};const int flags[]={0,AT_EMPTY_PATH,AT_SYMLINK_NOFOLLOW,AT_EMPTY_PATH|AT_SYMLINK_NOFOLLOW,1,AT_EMPTY_PATH|1,(-2147483647-1),2147483647};unsigned long exec=0,at=0;
 for(int filename=0;filename<4;filename++)for(int result=0;result<7;result++)for(int alias=0;alias<3;alias++){
  case_id++;for(which=0;which<2;which++){init(0,filename,0,0,alias,results[result]);int n=case_id%3==0?(-2147483647-1):case_id%3==1?0:2147483647;long rc=which?sys_execve(n,&ctx):f03_original_sys_execve(n,&ctx);CHECK(rc==(long)results[result]&&called==1);save(which?&candidate:&baseline,rc);}same();exec++;
 }
 for(int filename=0;filename<4;filename++)for(int fd=0;fd<7;fd++)for(int fl=0;fl<8;fl++)for(int result=0;result<7;result++)for(int alias=0;alias<3;alias++){
  case_id++;for(which=0;which<2;which++){init(1,filename,fds[fd],flags[fl],alias,results[result]);int n=case_id%3==0?(-2147483647-1):case_id%3==1?0:2147483647;long rc=which?sys_execveat(n,&ctx):f03_original_sys_execveat(n,&ctx);int policy=(flags[fl]&~(AT_EMPTY_PATH|AT_SYMLINK_NOFOLLOW))?-EINVAL:(names[filename][0]!='/'&&fds[fd]!=AT_FDCWD&&fds[fd]<0)?-EBADF:0;CHECK(rc==(policy?policy:(long)results[result])&&called==(policy?0:1));if(policy)CHECK(ctx.gpr.rax==0x76543210UL&&argv_values[0]==names[0]&&envp_values[0]==names[3]);save(which?&candidate:&baseline,rc);}same();at++;
 }
 CHECK(exec==84&&at==4704);printf("PASS_F03_ACTUAL_C_RUST_EXEC_ENTRIES execve=%lu execveat=%lu total=%lu real_layout_fields=14 lifecycle_effect_controlled=1\n",exec,at,exec+at);return 0;
}
