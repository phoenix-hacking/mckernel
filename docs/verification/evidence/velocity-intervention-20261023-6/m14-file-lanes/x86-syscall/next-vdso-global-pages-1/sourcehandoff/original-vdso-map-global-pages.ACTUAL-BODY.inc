int vdso_map_global_pages(void)
{
	int error;
	enum ihk_mc_pt_attribute attr;
	int i;
	void *virt;
	intptr_t phys;

	dkprintf("vdso_map_global_pages()\n");
	if (vdso.vvar_virt && vdso.vvar_is_global) {
		attr = PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE;
		error = ihk_mc_pt_set_page(NULL, vdso.vvar_virt, vdso.vvar_phys, attr);
		if (error) {
			ekprintf("vdso_map_global_pages: mapping vvar failed. %d\n", error);
			goto out;
		}
	}

	if (vdso.hpet_virt && vdso.hpet_is_global) {
		attr = PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE | PTATTR_UNCACHABLE;
		error = ihk_mc_pt_set_page(NULL, vdso.hpet_virt, vdso.hpet_phys, attr);
		if (error) {
			ekprintf("vdso_map_global_pages: mapping hpet failed. %d\n", error);
			goto out;
		}
	}

	if (vdso.pvti_virt && vdso.pvti_is_global) {
		error = arch_setup_pvclock();
		if (error) {
			ekprintf("vdso_map_global_pages: arch_setup_pvclock failed. %d\n", error);
			goto out;
		}

		attr = PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE;
		for (i = 0; i < pvti_npages; ++i) {
			virt = vdso.pvti_virt - (i * PAGE_SIZE);
			phys = virt_to_phys(pvti + (i * PAGE_SIZE));
			error = ihk_mc_pt_set_page(NULL, virt, phys, attr);
			if (error) {
				ekprintf("vdso_map_global_pages: mapping pvti failed. %d\n", error);
				goto out;
			}
		}
	}

	error = 0;
out:
	dkprintf("vdso_map_global_pages(): %d\n", error);
	return error;
}
