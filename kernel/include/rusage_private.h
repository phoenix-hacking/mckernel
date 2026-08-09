/* Interface toward kernel */

#ifndef RUSAGE_PRIVATE_H_INCLUDED
#define RUSAGE_PRIVATE_H_INCLUDED

#include <config.h>
#include <page.h>
#include <ihk/atomic.h>
#include <memobj.h>
#include <rusage.h>
#include <ihk/ihk_monitor.h>
#include <ihk/debug.h>
#include <memory.h>
#include <mman.h>

#ifdef ENABLE_RUSAGE

#define RUSAGE_OOM_MARGIN (8 * 1024 * 1024) // 8MB

extern void eventfd(int type);

int rusage_pgsize_to_pgtype(size_t pgsize);
void rusage_total_memory_add(unsigned long size);
unsigned long rusage_get_total_memory(void);
unsigned long rusage_get_free_memory(void);
unsigned long rusage_get_usage_memory(void);

void rusage_rss_add(unsigned long size);
void rusage_rss_sub(unsigned long size);

void memory_stat_rss_add(unsigned long size, int pgsize);
void memory_stat_rss_sub(unsigned long size, int pgsize);
void rusage_memory_stat_mapped_file_add(unsigned long size, int pgsize);
void rusage_memory_stat_mapped_file_sub(unsigned long size, int pgsize);

int rusage_memory_stat_add(struct vm_range *range, uintptr_t phys,
			   unsigned long size, int pgsize);
int rusage_memory_stat_add_with_page(struct vm_range *range, uintptr_t phys,
				     unsigned long size, int pgsize,
				     struct page *page);

void rusage_memory_stat_sub(struct memobj *memobj, unsigned long size,
			    int pgsize);

void rusage_kmem_add(unsigned long size);
void rusage_kmem_sub(unsigned long size);

void rusage_numa_add(int numa_id, unsigned long size);
void rusage_numa_sub(int numa_id, unsigned long size);

int rusage_check_oom(int numa_id, unsigned long pages, int is_user);
int rusage_check_overmap(size_t len, int pgshift);
void rusage_page_add(int numa_id, unsigned long pages, int is_user);
void rusage_page_sub(int numa_id, unsigned long pages, int is_user);

void rusage_num_threads_inc(void);
void rusage_num_threads_dec(void);
#else
void rusage_total_memory_add(unsigned long size);

void rusage_rss_add(unsigned long size);

unsigned long rusage_get_total_memory(void);

unsigned long rusage_get_free_memory(void);

unsigned long rusage_get_usage_memory(void);

void rusage_rss_sub(unsigned long size);

void memory_stat_rss_add(unsigned long size, int pgsize);

void memory_stat_rss_sub(unsigned long size, int pgsize);

void rusage_memory_stat_mapped_file_add(unsigned long size, int pgsize);

void rusage_memory_stat_mapped_file_sub(unsigned long size, int pgsize);

int rusage_memory_stat_add_with_page(struct vm_range *range, struct page *page,
				     unsigned long size, int pgsize);
int rusage_memory_stat_add(struct vm_range *range, uintptr_t phys,
			   unsigned long size, int pgsize);

void rusage_memory_stat_sub(struct memobj *memobj, unsigned long size,
			    int pgsize);

void rusage_numa_add(int numa_id, unsigned long size);
void rusage_numa_sub(int numa_id, unsigned long size);

int rusage_check_oom(int numa_id, unsigned long pages, int is_user);
int rusage_check_overmap(size_t len, int pgshift);
void rusage_page_add(int numa_id, unsigned long pages, int is_user);
void rusage_page_sub(int numa_id, unsigned long pages, int is_user);

void rusage_num_threads_inc(void);

void rusage_num_threads_dec(void);
#endif // ENABLE_RUSAGE

extern struct rusage_global rusage;

#endif /* !defined(RUSAGE_PRIVATE_H_INCLUDED) */
