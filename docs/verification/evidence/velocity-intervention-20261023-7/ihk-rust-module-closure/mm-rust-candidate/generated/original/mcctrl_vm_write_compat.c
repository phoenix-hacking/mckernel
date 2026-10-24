// SPDX-License-Identifier: GPL-2.0
/* SOURCE-ONLY proposal: link within mcctrl.ko; never bypass Linux MM APIs. */
#include <linux/mm.h>
#include <linux/mmap_lock.h>
#include "mcctrl_vm_write_compat.h"

void mckernel_inherited_mmap_write_lock(struct mm_struct *mm)
{
	mmap_write_lock(mm);
}

void mckernel_inherited_mmap_write_unlock(struct mm_struct *mm)
{
	mmap_write_unlock(mm);
}

void mckernel_inherited_vma_start_write(struct vm_area_struct *vma)
{
	vma_start_write(vma);
}
