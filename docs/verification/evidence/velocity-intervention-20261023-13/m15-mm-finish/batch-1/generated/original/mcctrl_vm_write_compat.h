/* SPDX-License-Identifier: GPL-2.0 */
#ifndef MCKERNEL_MCCTRL_VM_WRITE_COMPAT_H
#define MCKERNEL_MCCTRL_VM_WRITE_COMPAT_H
struct mm_struct;
struct vm_area_struct;
void mckernel_inherited_mmap_write_lock(struct mm_struct *mm);
void mckernel_inherited_mmap_write_unlock(struct mm_struct *mm);
void mckernel_inherited_vma_start_write(struct vm_area_struct *vma);
#endif
