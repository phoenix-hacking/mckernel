void process_release_final_cleanup_bridge(void *resource_set_arg)
{
	struct resource_set *rset = resource_set_arg;
	struct mcs_rwlock_node_irqsave lock;

	mcs_rwlock_reader_lock(&rset->pid1->children_lock, &lock);
	if (list_empty(&rset->pid1->children_list)) {
#ifdef ENABLE_TOFU
		extern void tof_utofu_finalize(void);

		tof_utofu_finalize();
#endif
		hugefileobj_cleanup();
	}
	mcs_rwlock_reader_unlock(&rset->pid1->children_lock, &lock);
}
