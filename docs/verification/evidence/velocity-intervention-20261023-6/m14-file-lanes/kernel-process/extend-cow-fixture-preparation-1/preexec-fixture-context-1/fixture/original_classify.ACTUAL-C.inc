	private_range = (range->flag & VR_PRIVATE);
	patching_to_rdonly =
		((reason & PF_PATCH) && !(range->flag & VR_PROT_WRITE));

	/* device file map, hugetlbfs file map, pre-mapped file map */
	devfile_or_hugetlbfs_or_premap =
		(!page &&
		 (range->memobj && !(range->memobj->flags | MF_ZEROOBJ)));

	/* regular file map, Sys V shared memory map */
	regfile_or_shm =
		(page &&
		 (page_is_in_memobj(page) || page_is_multi_mapped(page)));

	if ((private_range || patching_to_rdonly) &&
	    (devfile_or_hugetlbfs_or_premap || regfile_or_shm)) {
