#define VDSO_MAXPAGES 2
struct vdso {
	long busy;
	int vdso_npages;
	char vvar_is_global;
	char hpet_is_global;
	char pvti_is_global;
	char padding;
	long vdso_physlist[VDSO_MAXPAGES];
	void *vvar_virt;
	long vvar_phys;
	void *hpet_virt;
	long hpet_phys;
	void *pvti_virt;
	long pvti_phys;
	void *vgtod_virt;
};
