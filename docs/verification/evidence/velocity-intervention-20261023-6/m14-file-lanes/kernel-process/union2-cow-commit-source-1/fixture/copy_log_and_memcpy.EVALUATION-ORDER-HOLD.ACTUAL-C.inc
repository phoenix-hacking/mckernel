			dkprintf("%s: cow,copying virt:%lx<-%lx,phys:%lx<-%lx,pgsize=%lu\n",
					 __FUNCTION__, virt, phys_to_virt(phys), virt_to_phys(virt), phys, pgsize);
			memcpy(virt, phys_to_virt(phys), pgsize);

