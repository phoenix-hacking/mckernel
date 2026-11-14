/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact configured Linux witness, never linked into a production module. */
#include <linux/build_bug.h>
#include <linux/stddef.h>
#include <asm/vdso.h>
#include <asm/vdso/vsyscall.h>
#include <vdso/datapage.h>

#if !defined(CONFIG_X86_64) || !defined(CONFIG_GENERIC_GETTIMEOFDAY) || \
    !defined(CONFIG_GENERIC_VDSO_OVERFLOW_PROTECT) || \
    !defined(CONFIG_GENERIC_VDSO_DATA_STORE) || !defined(CONFIG_VDSO_GETRANDOM)
#error "This witness requires the pinned native x86 vDSO configuration"
#endif
#if defined(CONFIG_ARCH_HAS_VDSO_TIME_DATA) || defined(CONFIG_ARCH_HAS_VDSO_ARCH_DATA)
#error "Architecture-specific data needs a separate reviewed layout"
#endif

#define MEMBER(type, member) offsetof(struct type, member)

const unsigned long native_vdso_layout[]
__attribute__((used, section(".mckernel_native_vdso_layout"))) = {
	PAGE_SIZE, __VDSO_PAGES, VDSO_NR_PAGES, VDSO_NR_VCLOCK_PAGES,
	VDSO_TIME_PAGE_OFFSET, VDSO_TIMENS_PAGE_OFFSET, VDSO_RNG_PAGE_OFFSET,
	VDSO_ARCH_PAGES_START, VDSO_PAGE_PVCLOCK_OFFSET, VDSO_PAGE_HVCLOCK_OFFSET,
	MEMBER(vdso_image, data), MEMBER(vdso_image, size),
	sizeof(struct vdso_timestamp), __alignof__(struct vdso_timestamp),
	MEMBER(vdso_timestamp, sec), MEMBER(vdso_timestamp, nsec),
	sizeof(struct vdso_clock), __alignof__(struct vdso_clock),
	MEMBER(vdso_clock, seq), MEMBER(vdso_clock, clock_mode),
	MEMBER(vdso_clock, cycle_last), MEMBER(vdso_clock, max_cycles),
	MEMBER(vdso_clock, mask), MEMBER(vdso_clock, mult),
	MEMBER(vdso_clock, shift), MEMBER(vdso_clock, basetime),
	VDSO_BASES, CS_BASES, CS_HRES_COARSE, CS_RAW,
	sizeof(struct vdso_time_data), __alignof__(struct vdso_time_data),
	MEMBER(vdso_time_data, clock_data), MEMBER(vdso_time_data, tz_minuteswest),
	MEMBER(vdso_time_data, tz_dsttime), MEMBER(vdso_time_data, hrtimer_res),
	sizeof(struct vdso_rng_data), __alignof__(struct vdso_rng_data),
	MEMBER(vdso_rng_data, generation), MEMBER(vdso_rng_data, is_ready),
	VDSO_CLOCKMODE_NONE, VDSO_CLOCKMODE_TSC,
	VDSO_CLOCKMODE_PVCLOCK, VDSO_CLOCKMODE_HVCLOCK,
};
