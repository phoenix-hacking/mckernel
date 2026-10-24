			if (error) {
				struct memobj *obj;

				if (zeroobj_create(&obj)) {
					panic("PFPMR: zeroobj_crate");
				}

				if (range->memobj != obj) {
					goto out;
				}
			}
