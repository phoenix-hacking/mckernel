struct option mcexec_options[] = {
#ifndef __aarch64__
	{
		.name =		"disable-vdso",
		.has_arg =	no_argument,
		.flag =		&enable_vdso,
		.val =		0,
	},
	{
		.name =		"enable-vdso",
		.has_arg =	no_argument,
		.flag =		&enable_vdso,
		.val =		1,
	},
#endif /*__aarch64__*/
	{
		.name =		"profile",
		.has_arg =	no_argument,
		.flag =		&profile,
		.val =		1,
	},
	{
		.name =		"mpol-no-heap",
		.has_arg =	no_argument,
		.flag =		&mpol_no_heap,
		.val =		1,
	},
	{
		.name =		"mpol-no-stack",
		.has_arg =	no_argument,
		.flag =		&mpol_no_stack,
		.val =		1,
	},
	{
		.name =		"mpol-no-bss",
		.has_arg =	no_argument,
		.flag =		&mpol_no_bss,
		.val =		1,
	},
	{
		.name =		"mpol-shm-premap",
		.has_arg =	no_argument,
		.flag =		&mpol_shm_premap,
		.val =		1,
	},
	{
		.name =		"no-bind-ikc-map",
		.has_arg =	no_argument,
		.flag =		&no_bind_ikc_map,
		.val =		1,
	},
	{
		.name =		"mpol-threshold",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'M',
	},
	{
		.name =		"enable-straight-map",
		.has_arg =	no_argument,
		.flag =		&straight_map,
		.val =		1,
	},
	{
		.name =		"straight-map-threshold",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'S',
	},
	{
		.name =		"disable-sched-yield",
		.has_arg =	no_argument,
		.flag =		&disable_sched_yield,
		.val =		1,
	},
	{
		.name =		"extend-heap-by",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'h',
	},
	{
		.name =		"stack-premap",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		's',
	},
	{
		.name =		"uti-thread-rank",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'u',
	},
	{
		.name =		"uti-use-last-cpu",
		.has_arg =	no_argument,
		.flag =		&uti_use_last_cpu,
		.val =		1,
	},
	{
		.name =		"enable-uti",
		.has_arg =	no_argument,
		.flag =		&enable_uti,
		.val =		1,
	},
#ifdef ENABLE_TOFU
	{
		.name =		"enable-tofu",
		.has_arg =	no_argument,
		.flag =		&enable_tofu,
		.val =		1,
	},
#endif
	{
		.name =		"debug-mcexec",
		.has_arg =	no_argument,
		.flag =		&debug,
		.val =		1,
	},
	{
		.name =		"flags",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'f',
	},
	/* end */
	{ NULL, 0, NULL, 0, },
};
