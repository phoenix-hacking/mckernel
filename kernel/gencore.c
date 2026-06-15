/* gencore.c COPYRIGHT FUJITSU LIMITED 2015-2019 */
#include <ihk/debug.h>
#include <kmalloc.h>
#include <cls.h>
#include <list.h>
#include <process.h>
#include <string.h>
#include <elfcore.h>
#include <object_helpers.h>

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
#define	align32(x) gencore_align32_result(x)
#define	alignpage(x) gencore_alignpage_result(x)
#else
#define	align32(x) ((((x) + 3) / 4) * 4)
#define	alignpage(x) ((((x) + (PAGE_SIZE) - 1) / (PAGE_SIZE)) * (PAGE_SIZE))
#endif

//#define DEBUG_PRINT_GENCORE

#ifdef DEBUG_PRINT_GENCORE
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif

/* Exclude reserved (mckernel's internal use), device file,
 * hole created by mprotect
 */
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
#define GENCORE_RANGE_IS_INACCESSIBLE(range) \
	gencore_range_inaccessible_result((range)->flag)
#else
#define GENCORE_RANGE_IS_INACCESSIBLE(range) \
	((range->flag & (VR_RESERVED | VR_MEMTYPE_UC | VR_DONTDUMP)))
#endif

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
static void *gencore_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}

static void gencore_free_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

static void gencore_arch_fill_prstatus_bridge(void *prstatus, void *thread,
					      void *regs, int sig)
{
	arch_fill_prstatus(prstatus, thread, regs, sig);
}

static int gencore_pt_virt_to_phys_bridge(void *page_table,
					  unsigned long vaddr,
					  unsigned long *phys)
{
	return ihk_mc_pt_virt_to_phys(page_table, (void *)vaddr, phys);
}

static unsigned long gencore_virt_to_phys_bridge(unsigned long vaddr)
{
	return virt_to_phys((void *)vaddr);
}

static void gencore_coretable_log_bridge(int index, long len,
					 unsigned long addr,
					 unsigned long start)
{
	dkprintf("coretable[%d]: %lx@%lx(%lx)\n", index, len, addr, start);
}

static void *gencore_lookup_range_bridge(void *vm)
{
	return lookup_process_memory_range(vm, 0, -1);
}

static void *gencore_next_range_bridge(void *vm, void *range)
{
	return next_process_memory_range(vm, range);
}

static unsigned long gencore_range_start_bridge(void *range)
{
	return ((struct vm_range *)range)->start;
}

static unsigned long gencore_range_end_bridge(void *range)
{
	return ((struct vm_range *)range)->end;
}

static unsigned long gencore_range_flag_bridge(void *range)
{
	return ((struct vm_range *)range)->flag;
}

static long gencore_range_objoff_bridge(void *range)
{
	return ((struct vm_range *)range)->objoff;
}

static void gencore_range_log_bridge(unsigned long start, unsigned long end,
				     unsigned long flag, long objoff)
{
	dkprintf("start:%lx end:%lx flag:%lx objoff:%lx\n",
		 start, end, flag, objoff);
}

static void *gencore_alloc_bridge(size_t size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

static void gencore_zero_bridge(void *ptr, size_t size)
{
	memset(ptr, 0, size);
}

static void gencore_alloc_error_log_bridge(int stage)
{
	switch (stage) {
	case 0:
		dkprintf("could not alloc a elf header table.\n");
		break;
	case 1:
		kprintf("%s: ERROR: allocating program header\n", "gencore");
		break;
	case 2:
		kprintf("%s: ERROR: allocating NOTE\n", "gencore");
		break;
	case 3:
		kprintf("%s: ERROR: allocating coretable\n", "gencore");
		break;
	default:
		break;
	}
}

static void gencore_pt_error_log_bridge(unsigned long start, int error)
{
	kprintf("%s: error: ihk_mc_pt_virt_to_phys for %lx failed (%d)\n",
		"gencore", start, error);
}
#endif

/* Generate a core file image, which consists of many chunks.
 * Returns an allocated table, an etnry of which is a pair of the address
 * of a chunk and its length.
 */

/**
 * \brief Fill the elf header.
 *
 * \param eh An Elf64_Ehdr structure.
 * \param segs Number of segments of the core file.
 */

void fill_elf_header(Elf64_Ehdr *eh, int segs)
{
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	(void)gencore_fill_elf_header_body_result(eh, segs);
	return;
#else
	eh->e_ident[EI_MAG0] = 0x7f;
	eh->e_ident[EI_MAG1] = 'E';
	eh->e_ident[EI_MAG2] = 'L';
	eh->e_ident[EI_MAG3] = 'F';
	eh->e_ident[EI_CLASS] = ELF_CLASS;
	eh->e_ident[EI_DATA] = ELF_DATA;
	eh->e_ident[EI_VERSION] = El_VERSION;
	eh->e_ident[EI_OSABI] = ELF_OSABI;
	eh->e_ident[EI_ABIVERSION] = ELF_ABIVERSION;

	eh->e_type = ET_CORE;
	eh->e_machine = ELF_ARCH;
	eh->e_version = EV_CURRENT;
	eh->e_entry = 0;	/* Do we really need this? */
	eh->e_phoff = 64;	/* fixed */
	eh->e_shoff = 0;	/* no section header */
	eh->e_flags = 0;
	eh->e_ehsize = 64;	/* fixed */
	eh->e_phentsize = 56;	/* fixed */
	eh->e_phnum = segs;
	eh->e_shentsize = 0;
	eh->e_shnum = 0;
	eh->e_shstrndx = 0;
#endif
}

/**
 * \brief Return the size of the prstatus entry of the NOTE segment.
 *
 */

int get_prstatus_size(void)
{
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	return gencore_prstatus_size_result();
#else
	return sizeof(struct note) + align32(sizeof("CORE"))
		+ align32(sizeof(struct elf_prstatus64));
#endif
}

/**
 * \brief Return the size of the prpsinfo entry of the NOTE segment.
 *
 */

int get_prpsinfo_size(void)
{
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	return gencore_prpsinfo_size_result();
#else
	return sizeof(struct note) + align32(sizeof("CORE"))
		+ align32(sizeof(struct elf_prpsinfo64));
#endif
}

/**
 * \brief Fill a prstatus structure.
 *
 * \param head A pointer to a note structure.
 * \param proc A pointer to the current process structure.
 * \param regs0 A pointer to a ihk_mc_user_context_t structure.
 */
void fill_prstatus(struct note *head, struct thread *thread, int sig)
{
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	(void)gencore_fill_prstatus_body_result(
		head, thread, thread->coredump_regs, sig,
		gencore_arch_fill_prstatus_bridge);
#else
	void *name;
	struct elf_prstatus64 *prstatus;

	head->namesz = sizeof("CORE");
	head->descsz = sizeof(struct elf_prstatus64);
	head->type = NT_PRSTATUS;
	name =  (void *) (head + 1);
	memcpy(name, "CORE", sizeof("CORE"));
	prstatus = (struct elf_prstatus64 *)(name + align32(sizeof("CORE")));

	arch_fill_prstatus(prstatus, thread, thread->coredump_regs, sig);
#endif
}

/**
 * \brief Fill a prpsinfo structure.
 *
 * \param head A pointer to a note structure.
 * \param proc A pointer to the current process structure.
 * \param regs A pointer to a ihk_mc_user_context_t structure.
 */

void fill_prpsinfo(struct note *head, struct process *proc, char *cmdline)
{
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	(void)gencore_fill_prpsinfo_body_result(head, proc->status,
						proc->pid, cmdline);
#else
	void *name;
	struct elf_prpsinfo64 *prpsinfo;

	head->namesz = sizeof("CORE");
	head->descsz = sizeof(struct elf_prpsinfo64);
	head->type = NT_PRPSINFO;
	name =  (void *) (head + 1);
	memcpy(name, "CORE", sizeof("CORE"));
	prpsinfo = (struct elf_prpsinfo64 *)(name + align32(sizeof("CORE")));

	prpsinfo->pr_state = proc->status;
	prpsinfo->pr_pid = proc->pid;

	memcpy(prpsinfo->pr_fname, cmdline, 16);

/* TODO: Fill the following fields:
 *	char pr_sname;
 *	char pr_zomb;
 *	char pr_nice;
 *	a8_uint64_t pr_flag;
 *	unsigned int pr_uid;
 *	unsigned int pr_gid;
 *	int pr_ppid, pr_pgrp, pr_sid;
 *	char pr_fname[16];
 *	char pr_psargs[ELF_PRARGSZ];
 */
#endif
}

/**
 * \brief Return the size of the AUXV entry of the NOTE segment.
 *
 */

int get_auxv_size(void)
{
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	return gencore_auxv_size_result();
#else
	return sizeof(struct note) + align32(sizeof("CORE"))
		+ sizeof(unsigned long) * AUXV_LEN;
#endif
}

/**
 * \brief Fill an AUXV structure.
 *
 * \param head A pointer to a note structure.
 * \param proc A pointer to the current process structure.
 * \param regs A pointer to a ihk_mc_user_context_t structure.
 */

void fill_auxv(struct note *head, struct process *proc)
{
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	(void)gencore_fill_auxv_body_result(head, proc->saved_auxv);
#else
	void *name;
	void *auxv;

	head->namesz = sizeof("CORE");
	head->descsz = sizeof(unsigned long) * AUXV_LEN;
	head->type = NT_AUXV;
	name =  (void *) (head + 1);
	memcpy(name, "CORE", sizeof("CORE"));
	auxv = name + align32(sizeof("CORE"));
	memcpy(auxv, proc->saved_auxv,
	       sizeof(unsigned long) * AUXV_LEN);
#endif
}

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
static void *gencore_first_thread_bridge(void *procp)
{
	struct process *proc = procp;

	if (list_empty(&proc->threads_list)) {
		return NULL;
	}
	return ((struct thread *)((char *)((&proc->threads_list)->next) - offsetof(struct thread, siblings_list)));
}

static void *gencore_next_thread_bridge(void *procp, void *threadp)
{
	struct process *proc = procp;
	struct thread *thread = threadp;
	struct list_head *next = thread->siblings_list.next;

	if (next == &proc->threads_list) {
		return NULL;
	}
	return ((struct thread *)((char *)(next) - offsetof(struct thread, siblings_list)));
}

static int gencore_thread_tid_bridge(void *thread)
{
	return ((struct thread *)thread)->tid;
}

static void *gencore_thread_regs_bridge(void *thread)
{
	return ((struct thread *)thread)->coredump_regs;
}

static int gencore_arch_thread_info_size_bridge(void)
{
	return arch_get_thread_core_info_size();
}

static void gencore_fill_prstatus_note_bridge(void *note, void *thread,
					      int sig)
{
	fill_prstatus(note, thread, sig);
}

static void gencore_arch_fill_thread_info_bridge(void *note, void *thread,
						 void *regs)
{
	arch_fill_thread_core_info(note, thread, regs);
}

static void gencore_fill_prpsinfo_note_bridge(void *note, void *proc,
					      char *cmdline)
{
	fill_prpsinfo(note, proc, cmdline);
}

static void gencore_fill_auxv_note_bridge(void *note, void *proc)
{
	fill_auxv(note, proc);
}
#endif

/**
 * \brief Return the size of the whole NOTE segment.
 *
 */

int get_note_size(struct process *proc)
{
	int note = 0;
#ifndef MCKERNEL_RUST_GENCORE_HELPERS
	struct thread *thread_iter;
#endif
	struct mcs_rwlock_node lock;

	mcs_rwlock_reader_lock_noirq(&proc->threads_lock, &lock);
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	note = gencore_note_size_threads_body_result(
		proc, proc->pid, gencore_first_thread_bridge,
		gencore_next_thread_bridge, gencore_thread_tid_bridge,
		gencore_arch_thread_info_size_bridge);
#else
	for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
		note += get_prstatus_size();
		note += arch_get_thread_core_info_size();
		if (thread_iter->tid == proc->pid) {
			note += get_prpsinfo_size();
			note += get_auxv_size();
		}
	}
#endif
	mcs_rwlock_reader_unlock_noirq(&proc->threads_lock, &lock);


	return note;
}

/**
 * \brief Fill the NOTE segment.
 *
 * \param head A pointer to a note structure.
 * \param proc A pointer to the current process structure.
 * \param regs A pointer to a ihk_mc_user_context_t structure.
 */

void fill_note(void *note, struct process *proc, char *cmdline, int sig)
{
#ifndef MCKERNEL_RUST_GENCORE_HELPERS
	struct thread *thread_iter;
#endif
	struct mcs_rwlock_node lock;

	mcs_rwlock_reader_lock_noirq(&proc->threads_lock, &lock);
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	(void)gencore_fill_note_threads_body_result(
		note, proc, cmdline, sig, proc->pid, NULL,
		gencore_first_thread_bridge, gencore_next_thread_bridge,
		gencore_thread_tid_bridge, gencore_thread_regs_bridge,
		gencore_arch_thread_info_size_bridge,
		gencore_fill_prstatus_note_bridge,
		gencore_arch_fill_thread_info_bridge,
		gencore_fill_prpsinfo_note_bridge,
		gencore_fill_auxv_note_bridge);
#else
	for (thread_iter = ((typeof(*thread_iter) *)((char *)((&proc->threads_list)->next) - offsetof(typeof(*thread_iter), siblings_list))); &thread_iter->siblings_list != (&proc->threads_list); thread_iter = ((typeof(*thread_iter) *)((char *)(thread_iter->siblings_list.next) - offsetof(typeof(*thread_iter), siblings_list)))) {
		fill_prstatus(note, thread_iter, sig);
		note += get_prstatus_size();

		arch_fill_thread_core_info(note, thread_iter,
					   thread_iter->coredump_regs);
		note += arch_get_thread_core_info_size();

		if (thread_iter->tid == proc->pid) {
			fill_prpsinfo(note, proc, cmdline);
			note += get_prpsinfo_size();

#if 0
			fill_siginfo(note, proc);
			note += get_siginfo_size();
#endif

			fill_auxv(note, proc);
			note += get_auxv_size();

#if 0
			fill_file(note, proc);
			note += get_file_size();
#endif
		}

#if 0
		fill_fpregset(note, thread);
		note += get_fpregset_size();

		fill_x86_xstate(note, thread);
		note += get_x86_xstate_size();
#endif
	}
#endif
	mcs_rwlock_reader_unlock_noirq(&proc->threads_lock, &lock);

}

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
static int gencore_get_note_size_bridge(void *proc)
{
	return get_note_size(proc);
}

static void gencore_fill_note_bridge(void *note, void *proc, char *cmdline,
				     int sig)
{
	fill_note(note, proc, cmdline, sig);
}
#endif

/**
 * \brief Generate an image of the core file.
 *
 * \param proc A pointer to the current process structure.
 * \param regs A pointer to a ihk_mc_user_context_t structure.
 * \param coretable(out) An array of core chunks.
 * \param chunks(out) Number of the entires of coretable.
 *
 * A core chunk is represented by a pair of a physical
 * address of memory region and its size. If there are
 * no corresponding physical address for a VM area
 * (an unallocated demand-paging page, e.g.), the address
 * should be zero.
 */

int gencore(struct process *proc, struct coretable **coretable, int *chunks,
	    char *cmdline, int sig)
{
	int error = 0;
	struct coretable *ct = NULL;
	Elf64_Ehdr *eh = NULL;
	Elf64_Phdr *ph = NULL;
	void *note = NULL;
#ifndef MCKERNEL_RUST_GENCORE_HELPERS
	struct vm_range *range, *next;
#endif
	struct process_vm *vm = proc->vm;
	int segs = 1;	/* the first one is for NOTE */
#ifndef MCKERNEL_RUST_GENCORE_HELPERS
	int notesize, phsize, alignednotesize;
	unsigned long offset = 0;
	int i;
#endif

	*chunks = 3; /* Elf header , header table and NOTE segment */

	if (vm == NULL) {
		kprintf("%s: ERROR: vm not found\n", __func__);
		error = -EINVAL;
		goto fail;
	}

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	error = gencore_scan_ranges_for_counts_body_result(
		vm, vm->address_space->page_table, chunks, &segs,
		gencore_lookup_range_bridge, gencore_next_range_bridge,
		gencore_range_start_bridge, gencore_range_end_bridge,
		gencore_range_flag_bridge, gencore_range_objoff_bridge,
		gencore_range_log_bridge, gencore_pt_virt_to_phys_bridge);
	if (error) {
		goto fail;
	}
#else
	next = lookup_process_memory_range(vm, 0, -1);
	while ((range = next)) {
		next = next_process_memory_range(vm, range);

		dkprintf("start:%lx end:%lx flag:%lx objoff:%lx\n",
			 range->start, range->end, range->flag, range->objoff);

		if (GENCORE_RANGE_IS_INACCESSIBLE(range)) {
			continue;
		}
		/* We need a chunk for each page for a demand paging area.
		 * This can be optimized for spacial complexity but we would
		 * lose simplicity instead.
		 */
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
		error = gencore_count_range_chunks_body_result(
			range->start, range->end, range->flag,
			vm->address_space->page_table, chunks,
			gencore_pt_virt_to_phys_bridge);
		if (error) {
			goto fail;
		}
#else
		if (range->flag & VR_DEMAND_PAGING) {
			unsigned long p, phys;
			int prevzero = 0;

			for (p = range->start; p < range->end; p += PAGE_SIZE) {
				if (ihk_mc_pt_virt_to_phys(
						vm->address_space->page_table,
						(void *)p, &phys) != 0) {
					prevzero = 1;
				} else {
					if (prevzero == 1)
						(*chunks)++;
					(*chunks)++;
					prevzero = 0;
				}
			}
			if (prevzero == 1)
				(*chunks)++;
		} else {
			(*chunks)++;
		}
#endif
		segs++;
	}
#endif
	dkprintf("we have %d segs and %d chunks.\n\n", segs, *chunks);

	{
		struct vm_regions region = vm->region;

		dkprintf("text:  %lx-%lx\n", region.text_start,
			 region.text_end);
		dkprintf("data:  %lx-%lx\n", region.data_start,
			 region.data_end);
		dkprintf("brk:   %lx-%lx\n", region.brk_start, region.brk_end);
		dkprintf("map:   %lx-%lx\n", region.map_start, region.map_end);
		dkprintf("stack: %lx-%lx\n", region.stack_start,
			 region.stack_end);
		dkprintf("user:  %lx-%lx\n\n", region.user_start,
			 region.user_end);
	}

	dkprintf("now generate a core file image\n");

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	return gencore_generate_image_body_result(
		proc, vm, vm->address_space->page_table, (void **)coretable,
		chunks, segs, vm->region.user_start, vm->region.user_end,
		cmdline, sig, sizeof(*eh), sizeof(*ph), sizeof(*ct),
		gencore_alloc_bridge, gencore_zero_bridge, gencore_free_bridge,
		gencore_get_note_size_bridge, gencore_fill_note_bridge,
		gencore_virt_to_phys_bridge, gencore_lookup_range_bridge,
		gencore_next_range_bridge, gencore_range_start_bridge,
		gencore_range_end_bridge, gencore_range_flag_bridge,
		gencore_pt_virt_to_phys_bridge, gencore_coretable_log_bridge,
		gencore_alloc_error_log_bridge, gencore_pt_error_log_bridge);
#else
	eh = kmalloc_tracked(sizeof(*eh), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (eh == NULL) {
		dkprintf("could not alloc a elf header table.\n");
		error = -ENOMEM;
		goto fail;
	}
	memset(eh, 0, sizeof(*eh));

	offset += sizeof(*eh);
	fill_elf_header(eh, segs);

	/* program header table */
	phsize = sizeof(Elf64_Phdr) * segs;
	ph = kmalloc_tracked(phsize, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (ph == NULL) {
		kprintf("%s: ERROR: allocating program header\n", __func__);
		error = -ENOMEM;
		goto fail;
	}
	memset(ph, 0, phsize);

	offset += phsize;

	/* NOTE segment
	 * To align the next segment page-sized, we prepare a padded
	 * region for our NOTE segment.
	 */
	notesize = get_note_size(proc);
	alignednotesize = alignpage(notesize + offset) - offset;
	note = kmalloc_tracked(alignednotesize, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (note == NULL) {
		kprintf("%s: ERROR: allocating NOTE\n", __func__);
		error = -ENOMEM;
		goto fail;
	}
	memset(note, 0, alignednotesize);
	fill_note(note, proc, cmdline, sig);

	/* prgram header for NOTE segment is exceptional */
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	(void)gencore_fill_note_phdr_body_result(&ph[0], offset, notesize);
#else
	ph[0].p_type = PT_NOTE;
	ph[0].p_flags = 0;
	ph[0].p_offset = offset;
	ph[0].p_vaddr = 0;
	ph[0].p_paddr = 0;
	ph[0].p_filesz = notesize;
	ph[0].p_memsz = notesize;
	ph[0].p_align = 0;
#endif

	offset += alignednotesize;

	/* program header for each memory chunk */
	i = 1;
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	error = gencore_fill_load_phdrs_body_result(
		vm, ph, &i, &offset,
		gencore_lookup_range_bridge, gencore_next_range_bridge,
		gencore_range_start_bridge, gencore_range_end_bridge,
		gencore_range_flag_bridge);
	if (error) {
		goto fail;
	}
#else
	next = lookup_process_memory_range(vm, 0, -1);
	while ((range = next)) {
		next = next_process_memory_range(vm, range);

		unsigned long flag = range->flag;
		unsigned long size = range->end - range->start;

		if (GENCORE_RANGE_IS_INACCESSIBLE(range)) {
			continue;
		}

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
		(void)gencore_fill_load_phdr_body_result(&ph[i], flag,
							 offset, range->start,
							 size);
#else
		ph[i].p_type = PT_LOAD;
		ph[i].p_flags = ((flag & VR_PROT_READ) ? PF_R : 0)
			| ((flag & VR_PROT_WRITE) ? PF_W : 0)
			| ((flag & VR_PROT_EXEC) ? PF_X : 0);
		ph[i].p_offset = offset;
		ph[i].p_vaddr = range->start;
		ph[i].p_paddr = 0;
		ph[i].p_filesz = size;
		ph[i].p_memsz = size;
		ph[i].p_align = PAGE_SIZE;
#endif
		i++;
		offset += size;
	}
#endif

	/* coretable to send to host */
	ct = kmalloc_tracked(sizeof(struct coretable) * (*chunks), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
	if (!ct) {
		kprintf("%s: ERROR: allocating coretable\n", __func__);
		error = -ENOMEM;
		goto fail;
	}
	memset(ct, 0, sizeof(struct coretable) * (*chunks));

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	(void)gencore_fill_initial_coretable_body_result(
		ct, virt_to_phys(eh), virt_to_phys(ph), virt_to_phys(note),
		phsize, alignednotesize);
#else
	ct[0].addr = virt_to_phys(eh);	/* ELF header */
	ct[0].len = 64;
	ct[1].addr = virt_to_phys(ph);	/* program header table */
	ct[1].len = phsize;
	ct[2].addr = virt_to_phys(note);	/* NOTE segment */
	ct[2].len = alignednotesize;
#endif
	dkprintf("coretable[0]: %lx@%lx(%lx)\n", ct[0].len, ct[0].addr, eh);

	dkprintf("coretable[1]: %lx@%lx(%lx)\n", ct[1].len, ct[1].addr, ph);

	dkprintf("coretable[2]: %lx@%lx(%lx)\n", ct[2].len, ct[2].addr, note);

	i = 3;	/* memory segments */
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	{
		unsigned long error_start = 0;

		error = gencore_emit_coretable_ranges_body_result(
			vm, ct, &i, vm->region.user_start, vm->region.user_end,
			vm->address_space->page_table, &error_start,
			gencore_lookup_range_bridge, gencore_next_range_bridge,
			gencore_range_start_bridge, gencore_range_end_bridge,
			gencore_range_flag_bridge, gencore_pt_virt_to_phys_bridge,
			gencore_virt_to_phys_bridge,
			gencore_coretable_log_bridge);
		if (error) {
			kprintf("%s: error: ihk_mc_pt_virt_to_phys for %lx failed (%d)\n",
				__func__, error_start, error);
			goto fail;
		}
	}
#else
	next = lookup_process_memory_range(vm, 0, -1);
	while ((range = next)) {
		next = next_process_memory_range(vm, range);

		unsigned long phys;

		if (GENCORE_RANGE_IS_INACCESSIBLE(range)) {
			continue;
		}

		if (range->flag & VR_DEMAND_PAGING) {

#ifdef MCKERNEL_RUST_GENCORE_HELPERS
			error = gencore_emit_demand_coretable_body_result(
				ct, &i, range->start, range->end,
				vm->address_space->page_table,
				gencore_pt_virt_to_phys_bridge,
				gencore_coretable_log_bridge);
			if (error) {
				goto fail;
			}
#else
			/* Just an ad hoc kluge. */
			unsigned long p, start, phys;
			int prevzero = 0;
			unsigned long size = 0;

			for (start = p = range->start;
			     p < range->end; p += PAGE_SIZE) {
				if (ihk_mc_pt_virt_to_phys(
						vm->address_space->page_table,
						(void *)p, &phys) != 0) {
					if (prevzero == 0) {
						/* Start a new chunk */
						size = PAGE_SIZE;
						start = p;
					} else {
						/* Extend the previous chunk */
						size += PAGE_SIZE;
					}
					prevzero = 1;
				} else {
					if (prevzero == 1) {
						/* Flush out an empty chunk */
						ct[i].addr = 0;
						ct[i].len = size;
						dkprintf("coretable[%d]: %lx@%lx(%lx)\n",
							 i, ct[i].len,
							 ct[i].addr, start);
						i++;

					}
					ct[i].addr = phys;
					ct[i].len = PAGE_SIZE;
					dkprintf("coretable[%d]: %lx@%lx(%lx)\n",
						 i, ct[i].len, ct[i].addr, p);
					i++;
					prevzero = 0;
				}
			}
			if (prevzero == 1) {
				/* An empty chunk */
				ct[i].addr = 0;
				ct[i].len = size;
				dkprintf("coretable[%d]: %lx@%lx(%lx)\n",
					 i, ct[i].len, ct[i].addr, start);
				i++;
			}
#endif
		} else {
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
			error = gencore_emit_linear_coretable_body_result(
				ct, &i, range->start, range->end,
				vm->region.user_start, vm->region.user_end,
				vm->address_space->page_table,
				gencore_pt_virt_to_phys_bridge,
				gencore_virt_to_phys_bridge,
				gencore_coretable_log_bridge);
			if (error) {
				kprintf("%s: error: ihk_mc_pt_virt_to_phys for %lx failed (%d)\n",
					__func__, range->start, error);
				goto fail;
			}
#else
			if ((vm->region.user_start <= range->start) &&
			    (range->end <= vm->region.user_end)) {
				error = ihk_mc_pt_virt_to_phys(
						vm->address_space->page_table,
						(void *)range->start, &phys);
				if (error) {
					if (error != -EFAULT) {
						kprintf("%s: error: ihk_mc_pt_virt_to_phys for %lx failed (%d)\n",
							__func__, range->start,
							error);
						goto fail;
					}
					/* VR_PROT_NONE range */
					phys = 0;
					error = 0;
				}
			} else {
				phys = virt_to_phys((void *)range->start);
			}
			ct[i].addr = phys;
			ct[i].len = range->end - range->start;
			dkprintf("coretable[%d]: %lx@%lx(%lx)\n", i,
				 ct[i].len, ct[i].addr, range->start);
			i++;
#endif
		}
	}
#endif
	*coretable = ct;

	return error;
#endif

fail:
	kfree_tracked(eh, __FILE__, __LINE__);
	kfree_tracked(ct, __FILE__, __LINE__);
	kfree_tracked(ph, __FILE__, __LINE__);
	kfree_tracked(note, __FILE__, __LINE__);
	return error;
}

/**
 * \brief Free all the allocated spaces for an image of the core file.
 *
 * \param coretable An array of core chunks.
 */

void freecore(struct coretable **coretable)
{
#ifdef MCKERNEL_RUST_GENCORE_HELPERS
	(void)gencore_freecore_body_result(
		(void **)coretable, gencore_phys_to_virt_bridge,
		gencore_free_bridge);
#else
	struct coretable *ct = *coretable;

	kfree_tracked(phys_to_virt(ct[2].addr), __FILE__, __LINE__);	/* NOTE segment */
	kfree_tracked(phys_to_virt(ct[1].addr), __FILE__, __LINE__);	/* ph */
	kfree_tracked(phys_to_virt(ct[0].addr), __FILE__, __LINE__);	/* eh */
	kfree_tracked(*coretable, __FILE__, __LINE__);
#endif
}
