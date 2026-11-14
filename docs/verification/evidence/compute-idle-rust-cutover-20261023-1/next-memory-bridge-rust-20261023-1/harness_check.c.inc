	if (x86_init_text_end_bridge)
		require(x86_init_text_end_bridge() == (unsigned long)_end);
