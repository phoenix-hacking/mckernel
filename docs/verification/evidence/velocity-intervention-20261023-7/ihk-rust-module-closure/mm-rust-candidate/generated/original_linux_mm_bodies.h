/* Exact original: include/linux/seqlock.h :: do_raw_write_seqcount_begin */
static inline void do_raw_write_seqcount_begin(seqcount_t *s)
{
	kcsan_nestable_atomic_begin();
	s->sequence++;
	smp_wmb();
}

/* Exact original: include/linux/seqlock.h :: do_raw_write_seqcount_end */
static inline void do_raw_write_seqcount_end(seqcount_t *s)
{
	smp_wmb();
	s->sequence++;
	kcsan_nestable_atomic_end();
}

/* Exact original: include/linux/mmap_lock.h :: __mmap_lock_trace_start_locking */
static inline void __mmap_lock_trace_start_locking(struct mm_struct *mm,
						   bool write)
{
	if (tracepoint_enabled(mmap_lock_start_locking))
		__mmap_lock_do_trace_start_locking(mm, write);
}

/* Exact original: include/linux/mmap_lock.h :: __mmap_lock_trace_acquire_returned */
static inline void __mmap_lock_trace_acquire_returned(struct mm_struct *mm,
						      bool write, bool success)
{
	if (tracepoint_enabled(mmap_lock_acquire_returned))
		__mmap_lock_do_trace_acquire_returned(mm, write, success);
}

/* Exact original: include/linux/mmap_lock.h :: __mmap_lock_trace_released */
static inline void __mmap_lock_trace_released(struct mm_struct *mm, bool write)
{
	if (tracepoint_enabled(mmap_lock_released))
		__mmap_lock_do_trace_released(mm, write);
}

/* Exact original: include/linux/mmap_lock.h :: mmap_assert_write_locked */
static inline void mmap_assert_write_locked(const struct mm_struct *mm)
{
	rwsem_assert_held_write(&mm->mmap_lock);
}

/* Exact original: include/linux/mmap_lock.h :: mm_lock_seqcount_begin */
static inline void mm_lock_seqcount_begin(struct mm_struct *mm)
{
	do_raw_write_seqcount_begin(&mm->mm_lock_seq);
}

/* Exact original: include/linux/mmap_lock.h :: mm_lock_seqcount_end */
static inline void mm_lock_seqcount_end(struct mm_struct *mm)
{
	ASSERT_EXCLUSIVE_WRITER(mm->mm_lock_seq);
	do_raw_write_seqcount_end(&mm->mm_lock_seq);
}

/* Exact original: include/linux/mmap_lock.h :: mmap_write_lock */
static inline void mmap_write_lock(struct mm_struct *mm)
{
	__mmap_lock_trace_start_locking(mm, true);
	down_write(&mm->mmap_lock);
	mm_lock_seqcount_begin(mm);
	__mmap_lock_trace_acquire_returned(mm, true, true);
}

/* Exact original: include/linux/mmap_lock.h :: vma_end_write_all */
static inline void vma_end_write_all(struct mm_struct *mm)
{
	mmap_assert_write_locked(mm);
	mm_lock_seqcount_end(mm);
}

/* Exact original: include/linux/mmap_lock.h :: mmap_write_unlock */
static inline void mmap_write_unlock(struct mm_struct *mm)
{
	__mmap_lock_trace_released(mm, true);
	vma_end_write_all(mm);
	up_write(&mm->mmap_lock);
}

/* Exact original: include/linux/mm.h :: __is_vma_write_locked */
static bool __is_vma_write_locked(struct vm_area_struct *vma, unsigned int *mm_lock_seq)
{
	mmap_assert_write_locked(vma->vm_mm);

	/*
	 * current task is holding mmap_write_lock, both vma->vm_lock_seq and
	 * mm->mm_lock_seq can't be concurrently modified.
	 */
	*mm_lock_seq = vma->vm_mm->mm_lock_seq.sequence;
	return (vma->vm_lock_seq == *mm_lock_seq);
}

/* Exact original: include/linux/mm.h :: vma_start_write */
static inline void vma_start_write(struct vm_area_struct *vma)
{
	unsigned int mm_lock_seq;

	if (__is_vma_write_locked(vma, &mm_lock_seq))
		return;

	down_write(&vma->vm_lock->lock);
	/*
	 * We should use WRITE_ONCE() here because we can have concurrent reads
	 * from the early lockless pessimistic check in vma_start_read().
	 * We don't really care about the correctness of that early check, but
	 * we should use WRITE_ONCE() for cleanliness and to keep KCSAN happy.
	 */
	WRITE_ONCE(vma->vm_lock_seq, mm_lock_seq);
	up_write(&vma->vm_lock->lock);
}
