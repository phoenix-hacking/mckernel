/* Functional OS/Rust only; no security testing. Actual public/fallback VM ABI witness. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/coherent-TLB13-VM-source-only-1/candidate/kernel/mem.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&lookup_node),int(*)(struct process_vm*,void*)),"completeNUMA lookup ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_lookup_fault_pte),pte_t*(*)(struct process_vm*,void*,int,void**,size_t*,int*)),"completefaultPTE ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_pt_lookup_pte),pte_t*(*)(page_table_t,void*,int,void**,size_t*,int*)),"publicPTEprovider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_fault_process_vm),int(*)(struct process_vm*,void*,uint64_t)),"publicVMfaultprovider ABI");
_Static_assert(sizeof(pte_t)==8&&sizeof(unsigned long)==8&&sizeof(size_t)==8&&sizeof(int)==4,"actualscalarABI");

_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_dec_bridge),void(*)(unsigned long)),"preserved actualTLBcompletion ABI");
