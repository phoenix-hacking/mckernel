#include <stdint.h>
#include <stddef.h>
#define EINVAL 22
struct mckfd;struct list_head {struct list_head *next,*prev;};
unsigned long perf_event_bit_result(int index)
{
	if (index < 0 || index >= (int)(sizeof(unsigned long) * 8)) {
		return 0;
	}
	return 1UL << index;
}
long c_perf_group(void *event, void *proc, int group_fd,
		int counter_idx, size_t proc_mckfd_offset,
		size_t mckfd_next_offset, size_t mckfd_fd_offset,
		size_t mckfd_data_offset, size_t event_group_leader_offset,
		size_t event_sibling_list_offset,
		size_t event_group_entry_offset,
		size_t event_nr_siblings_offset,
		size_t event_pmc_status_offset)
{
	char *event_base = event;
	void *leader;

	if (!event) {
		return -EINVAL;
	}

	if (group_fd == -1) {
		*(void **)(event_base + event_group_leader_offset) = event;
		*(unsigned long *)(event_base + event_pmc_status_offset) = 0;
		leader = event;
	}
	else {
		struct mckfd *cur;
		char *leader_base;
		struct list_head *entry;
		struct list_head *head;

		if (!proc) {
			return -EINVAL;
		}
		leader = NULL;
		for (cur = *(struct mckfd **)((char *)proc + proc_mckfd_offset);
				cur;
				cur = *(struct mckfd **)((char *)cur + mckfd_next_offset)) {
			if (*(int *)((char *)cur + mckfd_fd_offset) == group_fd) {
				leader = (void *)(uintptr_t)
					*(long *)((char *)cur + mckfd_data_offset);
				break;
			}
		}
		if (!leader) {
			return -EINVAL;
		}

		*(void **)(event_base + event_group_leader_offset) = leader;
		leader_base = leader;
		entry = (struct list_head *)(event_base + event_group_entry_offset);
		head = (struct list_head *)(leader_base + event_sibling_list_offset);
		if (!head->prev) {
			return -EINVAL;
		}
		entry->next = head;
		entry->prev = head->prev;
		head->prev->next = entry;
		head->prev = entry;
		(*(int *)(leader_base + event_nr_siblings_offset))++;
	}

	*(unsigned long *)((char *)leader + event_pmc_status_offset) |=
		perf_event_bit_result(counter_idx);
	return 0;
}
