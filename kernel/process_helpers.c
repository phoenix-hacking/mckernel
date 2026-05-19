/* SPDX-License-Identifier: GPL-2.0 */
#include <errno.h>
#include <process.h>
#include <process_helpers.h>

#ifndef MCKERNEL_RUST_PROCESS_HELPERS

enum ihk_mc_pt_attribute common_vrflag_to_ptattr(unsigned long flag, uint64_t fault,
						 pte_t *ptep)
{
	enum ihk_mc_pt_attribute attr;

	attr = PTATTR_USER | PTATTR_FOR_USER;

	if (flag & VR_REMOTE) {
		attr |= IHK_PTA_REMOTE;
	}
	else if (flag & VR_IO_NOCACHE) {
		attr |= PTATTR_UNCACHABLE;
	}

	if ((flag & VR_PROT_MASK) != VR_PROT_NONE) {
		attr |= PTATTR_ACTIVE;
	}

	if (flag & VR_PROT_WRITE) {
		attr |= PTATTR_WRITABLE;
	}

	if (!(flag & VR_PROT_EXEC)) {
		attr |= PTATTR_NO_EXECUTE;
	}

	if (flag & VR_WRITE_COMBINED) {
		attr |= PTATTR_WRITE_COMBINED;
	}

	return attr;
}

int process_split_pgshift_result(int pgshift, uintptr_t addr)
{
	if (pgshift > 0 && pgshift < (int)(sizeof(unsigned long) * 8) &&
	    (addr & ((1UL << pgshift) - 1)))
		return 0;

	return pgshift;
}

int process_add_range_bounds_result(unsigned long user_start,
				    unsigned long user_end,
				    unsigned long start,
				    unsigned long end)
{
	return (start < user_start || user_end < end) ? -EINVAL : 0;
}

int process_extend_up_result(unsigned long current_end,
			     unsigned long user_end, int has_next,
			     unsigned long next_start,
			     unsigned long newend)
{
	if (newend <= current_end)
		return -EINVAL;
	if (user_end < newend)
		return -EPERM;
	if (has_next && next_start < newend)
		return -ENOMEM;

	return 0;
}

unsigned long process_change_prot_newflag_result(unsigned long oldflag,
						 unsigned long protflag)
{
	return (oldflag & ~VR_PROT_MASK) | (protflag & VR_PROT_MASK);
}

void process_attr_delta_result(unsigned long oldattr, unsigned long newattr,
			       unsigned long *clrattrp,
			       unsigned long *setattrp)
{
	*clrattrp = oldattr & ~newattr;
	*setattrp = newattr & ~oldattr;
}

unsigned long process_private_file_setattr_result(int has_memobj,
						  unsigned long range_flags,
						  unsigned int memobj_flags,
						  unsigned long setattr)
{
	if (has_memobj && (range_flags & VR_PRIVATE) &&
	    !(memobj_flags & MF_HUGETLBFS))
		setattr &= ~PTATTR_WRITABLE;

	return setattr;
}

int process_remove_region_alignment_result(unsigned long start,
					   unsigned long end)
{
	return ((start & (PAGE_SIZE - 1)) || (end & (PAGE_SIZE - 1))) ?
		-EINVAL : 0;
}

int process_access_initial_result(int has_range, unsigned long range_start,
				  unsigned long addr)
{
	return (!has_range || range_start > addr) ? -EFAULT : 0;
}

int process_access_adjacent_result(unsigned long range_end, int has_next,
				   unsigned long next_start)
{
	return (!has_next || range_end != next_start) ? -EFAULT : 0;
}

int process_access_permission_result(int verify_type, unsigned long flags)
{
	if ((verify_type == VERIFY_WRITE && !(flags & VR_PROT_WRITE)) ||
	    (verify_type == VERIFY_READ && !(flags & VR_PROT_READ)))
		return -EACCES;

	return 0;
}

#endif /* MCKERNEL_RUST_PROCESS_HELPERS */
