/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/proc_fs.h>
#include <linux/stddef.h>
const unsigned long mckernel_procfs_layout[]
__attribute__((section(".mckernel_procfs_layout"), used)) = {
    sizeof(struct proc_ops), __alignof__(struct proc_ops),
    offsetof(struct proc_ops, proc_flags), offsetof(struct proc_ops, proc_open),
    offsetof(struct proc_ops, proc_read), offsetof(struct proc_ops, proc_read_iter),
    offsetof(struct proc_ops, proc_write), offsetof(struct proc_ops, proc_lseek),
    offsetof(struct proc_ops, proc_release), offsetof(struct proc_ops, proc_poll),
    offsetof(struct proc_ops, proc_ioctl), offsetof(struct proc_ops, proc_compat_ioctl),
    offsetof(struct proc_ops, proc_mmap), offsetof(struct proc_ops, proc_get_unmapped_area),
    sizeof(struct inode), __alignof__(struct inode), offsetof(struct inode, i_private),
    sizeof(struct file), __alignof__(struct file), offsetof(struct file, private_data),
    offsetof(struct file, f_pos), offsetof(struct file, f_mode),
    sizeof(kuid_t), offsetof(kuid_t, val), sizeof(kgid_t), offsetof(kgid_t, val),
    IS_ENABLED(CONFIG_COMPAT),
};
