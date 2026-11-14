/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-move-pages-source-1/candidate/syscall.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&sys_move_pages),long(*)(int,ihk_mc_user_context_t*)),"complete public entry ABI");
_Static_assert(sizeof(pte_t)==sizeof(unsigned long) && sizeof(pte_t)==8,"selected actual pte alias width");
_Static_assert(sizeof(void*)==8 && sizeof(int)==4 && sizeof(unsigned long)==8,"unchanged allocation geometry");
_Static_assert(sizeof(struct move_pages_smp_req)==104 && __builtin_offsetof(struct move_pages_smp_req,proc)==88 && __builtin_offsetof(struct move_pages_smp_req,phase_done)==96,"actual retained SMP handoff ABI");
_Static_assert(__builtin_offsetof(struct thread,vm)==4200 && __builtin_offsetof(struct thread,cpu_set)==4656 && __builtin_offsetof(struct thread,proc)==4304,"actual current owner fields");
_Static_assert(__builtin_offsetof(struct process_vm,page_table_lock)==176,"actual VM lock field");
extern int move_pages_smp_handler(int,int,void*);
_Static_assert(__builtin_types_compatible_p(__typeof__(&move_pages_smp_handler),int(*)(int,int,void*)),"unchanged architecture callback ABI");
