		if (x86_init_normal_set_large_bridge) {
			x86_rust_stub_pt_set_page_calls = 0;
			require(x86_init_normal_set_large_bridge((void *)0xaaaaUL,
					~0UL, 0xdddd0000UL,
					PTATTR_NO_EXECUTE | PTATTR_WRITABLE) == -5);
			require(x86_rust_stub_pt_set_page_calls == 1);
			require(x86_rust_stub_pt_set_page_pt == (void *)0xaaaaUL);
			require(x86_rust_stub_pt_set_page_virt == ~0UL);
			require(x86_rust_stub_pt_set_page_phys == 0xdddd0000UL);
			require(x86_rust_stub_pt_set_page_attr ==
					(PTATTR_NO_EXECUTE | PTATTR_WRITABLE |
					PTATTR_LARGEPAGE | PTATTR_ACTIVE));
		}
