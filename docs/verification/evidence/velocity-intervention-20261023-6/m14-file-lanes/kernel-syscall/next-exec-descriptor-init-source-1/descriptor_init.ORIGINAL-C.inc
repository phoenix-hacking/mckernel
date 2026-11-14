	desc = _ihk_mc_alloc_aligned_pages_node(4, PAGE_P2ALIGN, IHK_MC_AP_NOWAIT, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
	if (!desc) {
		kprintf("execve(): ERROR: allocating program descriptor\n");
		return -ENOMEM;
	}

	memset((void*)desc, 0, 4 * PAGE_SIZE);
