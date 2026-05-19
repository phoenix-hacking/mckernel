/* SPDX-License-Identifier: GPL-2.0 */
#ifndef MCKERNEL_PROCESS_HELPERS_H
#define MCKERNEL_PROCESS_HELPERS_H

#include <ihk/types.h>

int process_split_pgshift_result(int pgshift, uintptr_t addr);
int process_add_range_bounds_result(unsigned long user_start,
				    unsigned long user_end,
				    unsigned long start,
				    unsigned long end);
int process_extend_up_result(unsigned long current_end,
			     unsigned long user_end, int has_next,
			     unsigned long next_start,
			     unsigned long newend);
unsigned long process_change_prot_newflag_result(unsigned long oldflag,
						 unsigned long protflag);
void process_attr_delta_result(unsigned long oldattr, unsigned long newattr,
			       unsigned long *clrattrp,
			       unsigned long *setattrp);
unsigned long process_private_file_setattr_result(int has_memobj,
						  unsigned long range_flags,
						  unsigned int memobj_flags,
						  unsigned long setattr);
int process_remove_region_alignment_result(unsigned long start,
					   unsigned long end);
int process_access_initial_result(int has_range, unsigned long range_start,
				  unsigned long addr);
int process_access_adjacent_result(unsigned long range_end, int has_next,
				   unsigned long next_start);
int process_access_permission_result(int verify_type, unsigned long flags);

#endif /* MCKERNEL_PROCESS_HELPERS_H */
