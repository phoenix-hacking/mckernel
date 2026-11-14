/* Source-only ABI data witness; include the genuine unmodified public contract. */
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/resource.h>
#include "uprotocol.h"
#ifdef ENABLE_TOFU
#error "This witness is bound only to the qualified ENABLE_TOFU=OFF profile"
#endif
_Static_assert(sizeof(unsigned long)==8 && sizeof(void*)==8 && sizeof(int)==4, "qualified Linux x86_64 LP64 only");
_Static_assert(MCK_RLIM_MAX==20 && PLD_CPU_SET_SIZE==16, "genuine selected descriptor dimensions");
__attribute__((used)) const unsigned long m15_f02_descriptor_cpuset_abi[78] = {
    1UL, /* 0 witness_version */
    sizeof(unsigned long), /* 1 sizeof(unsigned long) */
    sizeof(int), /* 2 sizeof(int) */
    sizeof(pid_t), /* 3 sizeof(pid_t) */
    sizeof(size_t), /* 4 sizeof(size_t) */
    sizeof(void*), /* 5 sizeof(void*) */
    sizeof(struct program_load_desc), /* 6 sizeof(program_load_desc) */
    _Alignof(struct program_load_desc), /* 7 alignof(program_load_desc) */
    offsetof(struct program_load_desc, magic), /* 8 program_load_desc::magic */
    offsetof(struct program_load_desc, num_sections), /* 9 program_load_desc::num_sections */
    offsetof(struct program_load_desc, cpu), /* 10 program_load_desc::cpu */
    offsetof(struct program_load_desc, pid), /* 11 program_load_desc::pid */
    offsetof(struct program_load_desc, stack_prot), /* 12 program_load_desc::stack_prot */
    offsetof(struct program_load_desc, pgid), /* 13 program_load_desc::pgid */
    offsetof(struct program_load_desc, cred), /* 14 program_load_desc::cred */
    offsetof(struct program_load_desc, reloc), /* 15 program_load_desc::reloc */
    offsetof(struct program_load_desc, enable_vdso), /* 16 program_load_desc::enable_vdso */
    offsetof(struct program_load_desc, padding), /* 17 program_load_desc::padding */
    offsetof(struct program_load_desc, entry), /* 18 program_load_desc::entry */
    offsetof(struct program_load_desc, user_start), /* 19 program_load_desc::user_start */
    offsetof(struct program_load_desc, user_end), /* 20 program_load_desc::user_end */
    offsetof(struct program_load_desc, rprocess), /* 21 program_load_desc::rprocess */
    offsetof(struct program_load_desc, rpgtable), /* 22 program_load_desc::rpgtable */
    offsetof(struct program_load_desc, at_phdr), /* 23 program_load_desc::at_phdr */
    offsetof(struct program_load_desc, at_phent), /* 24 program_load_desc::at_phent */
    offsetof(struct program_load_desc, at_phnum), /* 25 program_load_desc::at_phnum */
    offsetof(struct program_load_desc, at_entry), /* 26 program_load_desc::at_entry */
    offsetof(struct program_load_desc, at_clktck), /* 27 program_load_desc::at_clktck */
    offsetof(struct program_load_desc, args), /* 28 program_load_desc::args */
    offsetof(struct program_load_desc, args_len), /* 29 program_load_desc::args_len */
    offsetof(struct program_load_desc, envs), /* 30 program_load_desc::envs */
    offsetof(struct program_load_desc, envs_len), /* 31 program_load_desc::envs_len */
    offsetof(struct program_load_desc, rlimit), /* 32 program_load_desc::rlimit */
    offsetof(struct program_load_desc, interp_align), /* 33 program_load_desc::interp_align */
    offsetof(struct program_load_desc, mpol_flags), /* 34 program_load_desc::mpol_flags */
    offsetof(struct program_load_desc, mpol_threshold), /* 35 program_load_desc::mpol_threshold */
    offsetof(struct program_load_desc, heap_extension), /* 36 program_load_desc::heap_extension */
    offsetof(struct program_load_desc, stack_premap), /* 37 program_load_desc::stack_premap */
    offsetof(struct program_load_desc, mpol_bind_mask), /* 38 program_load_desc::mpol_bind_mask */
    offsetof(struct program_load_desc, mpol_mode), /* 39 program_load_desc::mpol_mode */
    offsetof(struct program_load_desc, mpol_nodemask), /* 40 program_load_desc::mpol_nodemask */
    offsetof(struct program_load_desc, thp_disable), /* 41 program_load_desc::thp_disable */
    offsetof(struct program_load_desc, enable_uti), /* 42 program_load_desc::enable_uti */
    offsetof(struct program_load_desc, uti_thread_rank), /* 43 program_load_desc::uti_thread_rank */
    offsetof(struct program_load_desc, uti_use_last_cpu), /* 44 program_load_desc::uti_use_last_cpu */
    offsetof(struct program_load_desc, straight_map), /* 45 program_load_desc::straight_map */
    offsetof(struct program_load_desc, straight_map_threshold), /* 46 program_load_desc::straight_map_threshold */
    offsetof(struct program_load_desc, mcexec_flags), /* 47 program_load_desc::mcexec_flags */
    offsetof(struct program_load_desc, nr_processes), /* 48 program_load_desc::nr_processes */
    offsetof(struct program_load_desc, process_rank), /* 49 program_load_desc::process_rank */
    offsetof(struct program_load_desc, cpu_set), /* 50 program_load_desc::cpu_set */
    offsetof(struct program_load_desc, profile), /* 51 program_load_desc::profile */
    offsetof(struct program_load_desc, sections), /* 52 program_load_desc::sections */
    sizeof(struct program_image_section), /* 53 sizeof(program_image_section) */
    _Alignof(struct program_image_section), /* 54 alignof(program_image_section) */
    offsetof(struct program_image_section, vaddr), /* 55 program_image_section::vaddr */
    offsetof(struct program_image_section, len), /* 56 program_image_section::len */
    offsetof(struct program_image_section, remote_pa), /* 57 program_image_section::remote_pa */
    offsetof(struct program_image_section, filesz), /* 58 program_image_section::filesz */
    offsetof(struct program_image_section, offset), /* 59 program_image_section::offset */
    offsetof(struct program_image_section, prot), /* 60 program_image_section::prot */
    offsetof(struct program_image_section, interp), /* 61 program_image_section::interp */
    offsetof(struct program_image_section, padding), /* 62 program_image_section::padding */
    offsetof(struct program_image_section, fp), /* 63 program_image_section::fp */
    sizeof(struct get_cpu_set_arg), /* 64 sizeof(get_cpu_set_arg) */
    _Alignof(struct get_cpu_set_arg), /* 65 alignof(get_cpu_set_arg) */
    offsetof(struct get_cpu_set_arg, nr_processes), /* 66 get_cpu_set_arg::nr_processes */
    offsetof(struct get_cpu_set_arg, req_cpu_list), /* 67 get_cpu_set_arg::req_cpu_list */
    offsetof(struct get_cpu_set_arg, req_cpu_list_len), /* 68 get_cpu_set_arg::req_cpu_list_len */
    offsetof(struct get_cpu_set_arg, process_rank), /* 69 get_cpu_set_arg::process_rank */
    offsetof(struct get_cpu_set_arg, ppid), /* 70 get_cpu_set_arg::ppid */
    offsetof(struct get_cpu_set_arg, cpu_set), /* 71 get_cpu_set_arg::cpu_set */
    offsetof(struct get_cpu_set_arg, cpu_set_size), /* 72 get_cpu_set_arg::cpu_set_size */
    offsetof(struct get_cpu_set_arg, target_core), /* 73 get_cpu_set_arg::target_core */
    offsetof(struct get_cpu_set_arg, mcexec_linux_numa), /* 74 get_cpu_set_arg::mcexec_linux_numa */
    offsetof(struct get_cpu_set_arg, mcexec_cpu_set), /* 75 get_cpu_set_arg::mcexec_cpu_set */
    offsetof(struct get_cpu_set_arg, mcexec_cpu_set_size), /* 76 get_cpu_set_arg::mcexec_cpu_set_size */
    offsetof(struct get_cpu_set_arg, ikc_mapped), /* 77 get_cpu_set_arg::ikc_mapped */
};
