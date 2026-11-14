/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Fragment requires real headers/context and errno/AT_* constants. No job/queue.
 * Only the existing full exec lifecycle OS effect is replaced. */
extern int f03_fixture_do_execveat(ihk_mc_user_context_t *,int,const char *,char **,char **,int);
#define do_execveat f03_fixture_do_execveat
#include "../execve_provider.SELECTED-C.inc"
#undef do_execveat
#include "ExecveatFn.EXACT-C.inc"
#undef SYSCALL_POLICY_HELPER_SCOPE
#define SYSCALL_POLICY_HELPER_SCOPE static
#define execveat_policy_result f03_original_execveat_policy_result
#define execveat_body_result f03_original_execveat_body_result
#define execve_body_result f03_original_execve_body_result
#include "execveat_policy_result.ORIGINAL-C.inc"
#include "execveat_body_result.ORIGINAL-C.inc"
#include "execve_body_result.ORIGINAL-C.inc"
#define sys_execve f03_original_sys_execve
#define sys_execveat f03_original_sys_execveat
#include "../sys_execve.ORIGINAL-C.inc"
#include "../sys_execveat.ORIGINAL-C.inc"
#undef sys_execveat
#undef sys_execve
#undef execve_body_result
#undef execveat_body_result
#undef execveat_policy_result
