savedcmd_drivers/misc/mckernel/mcctrl.mod.o := clang -Wp,-MMD,drivers/misc/mckernel/.mcctrl.mod.o.d -nostdinc -I/source/arch/x86/include -I./arch/x86/include/generated -I/source/include -I./include -I/source/arch/x86/include/uapi -I./arch/x86/include/generated/uapi -I/source/include/uapi -I./include/generated/uapi -include /source/include/linux/compiler-version.h -include /source/include/linux/kconfig.h -include /source/include/linux/compiler_types.h -D__KERNEL__ --target=x86_64-linux-gnu -fintegrated-as -Werror=unknown-warning-option -Werror=ignored-optimization-argument -Werror=option-ignored -Werror=unused-command-line-argument -fmacro-prefix-map=/source/= -Werror -std=gnu11 -fshort-wchar -funsigned-char -fno-common -fno-PIE -fno-strict-aliasing -mno-sse -mno-mmx -mno-sse2 -mno-3dnow -mno-avx -fcf-protection=branch -fno-jump-tables -m64 -falign-loops=1 -mno-80387 -mno-fp-ret-in-387 -mstack-alignment=8 -mskip-rax-setup -mtune=generic -mno-red-zone -mcmodel=kernel -Wno-sign-compare -fno-asynchronous-unwind-tables -mretpoline-external-thunk -mindirect-branch-cs-prefix -mfunction-return=thunk-extern -mharden-sls=all -fpatchable-function-entry=16,16 -fno-delete-null-pointer-checks -O2 -fstack-protector-strong -ftrivial-auto-var-init=zero -fno-stack-clash-protection -pg -mfentry -DCC_USING_NOP_MCOUNT -DCC_USING_FENTRY -falign-functions=16 -fstrict-flex-arrays=3 -fno-strict-overflow -fno-stack-check -Wall -Wextra -Wundef -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Werror=strict-prototypes -Wno-format-security -Wno-trigraphs -Wno-frame-address -Wno-address-of-packed-member -Wmissing-declarations -Wmissing-prototypes -Wframe-larger-than=2048 -Wno-gnu -Wno-default-const-init-unsafe -Wvla -Wno-pointer-sign -Wcast-function-type -Wno-unterminated-string-initialization -Wimplicit-fallthrough -Werror=date-time -Werror=incompatible-pointer-types -Wenum-conversion -Wunused -Wno-unused-but-set-variable -Wno-unused-const-variable -Wno-format-overflow -Wno-format-overflow-non-kprintf -Wno-format-truncation-non-kprintf -Wno-override-init -Wno-pointer-to-enum-cast -Wno-tautological-constant-out-of-range-compare -Wno-unaligned-access -Wno-enum-compare-conditional -Wno-enum-enum-conversion -Wno-missing-field-initializers -Wno-type-limits -Wno-shift-negative-value -Wno-sign-compare -Wno-unused-parameter -g -DMODULE -DKBUILD_BASENAME='"mcctrl.mod"' -DKBUILD_MODNAME='"mcctrl"' -D__KBUILD_MODNAME=mcctrl -c -o drivers/misc/mckernel/mcctrl.mod.o drivers/misc/mckernel/mcctrl.mod.c

source_drivers/misc/mckernel/mcctrl.mod.o := drivers/misc/mckernel/mcctrl.mod.c

deps_drivers/misc/mckernel/mcctrl.mod.o := \
    $(wildcard include/config/MODULE_UNLOAD) \
  /source/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /source/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /source/include/linux/compiler_types.h \
    $(wildcard include/config/DEBUG_INFO_BTF) \
    $(wildcard include/config/PAHOLE_HAS_BTF_TAG) \
    $(wildcard include/config/FUNCTION_ALIGNMENT) \
    $(wildcard include/config/CC_HAS_SANE_FUNCTION_ALIGNMENT) \
    $(wildcard include/config/X86_64) \
    $(wildcard include/config/ARM64) \
    $(wildcard include/config/LD_DEAD_CODE_DATA_ELIMINATION) \
    $(wildcard include/config/LTO_CLANG) \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/CC_HAS_MULTIDIMENSIONAL_NONSTRING) \
    $(wildcard include/config/UBSAN_SIGNED_WRAP) \
    $(wildcard include/config/ARCH_USES_CFI_GENERIC_LLVM_PASS) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /source/include/linux/compiler_attributes.h \
  /source/include/linux/compiler-clang.h \
    $(wildcard include/config/ARCH_USE_BUILTIN_BSWAP) \
  /source/include/linux/module.h \
    $(wildcard include/config/MODULES) \
    $(wildcard include/config/SYSFS) \
    $(wildcard include/config/MODULES_TREE_LOOKUP) \
    $(wildcard include/config/LIVEPATCH) \
    $(wildcard include/config/STACKTRACE_BUILD_ID) \
    $(wildcard include/config/ARCH_USES_CFI_TRAPS) \
    $(wildcard include/config/MODULE_SIG) \
    $(wildcard include/config/GENERIC_BUG) \
    $(wildcard include/config/KALLSYMS) \
    $(wildcard include/config/SMP) \
    $(wildcard include/config/TRACEPOINTS) \
    $(wildcard include/config/TREE_SRCU) \
    $(wildcard include/config/BPF_EVENTS) \
    $(wildcard include/config/DEBUG_INFO_BTF_MODULES) \
    $(wildcard include/config/JUMP_LABEL) \
    $(wildcard include/config/TRACING) \
    $(wildcard include/config/EVENT_TRACING) \
    $(wildcard include/config/FTRACE_MCOUNT_RECORD) \
    $(wildcard include/config/KPROBES) \
    $(wildcard include/config/HAVE_STATIC_CALL_INLINE) \
    $(wildcard include/config/KUNIT) \
    $(wildcard include/config/PRINTK_INDEX) \
    $(wildcard include/config/CONSTRUCTORS) \
    $(wildcard include/config/FUNCTION_ERROR_INJECTION) \
    $(wildcard include/config/DYNAMIC_DEBUG_CORE) \
    $(wildcard include/config/MITIGATION_RETPOLINE) \
    $(wildcard include/config/RHEL_DIFFERENCES) \
  /source/include/linux/list.h \
    $(wildcard include/config/LIST_HARDENED) \
    $(wildcard include/config/DEBUG_LIST) \
  /source/include/linux/container_of.h \
  /source/include/linux/build_bug.h \
  /source/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/OBJTOOL) \
    $(wildcard include/config/64BIT) \
  arch/x86/include/generated/asm/rwonce.h \
  /source/include/asm-generic/rwonce.h \
  /source/include/linux/kasan-checks.h \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KASAN_SW_TAGS) \
  /source/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /source/include/uapi/linux/types.h \
  arch/x86/include/generated/uapi/asm/types.h \
  /source/include/uapi/asm-generic/types.h \
  /source/include/asm-generic/int-ll64.h \
  /source/include/uapi/asm-generic/int-ll64.h \
  /source/arch/x86/include/uapi/asm/bitsperlong.h \
  /source/include/asm-generic/bitsperlong.h \
  /source/include/uapi/asm-generic/bitsperlong.h \
  /source/include/uapi/linux/posix_types.h \
  /source/include/linux/stddef.h \
  /source/include/uapi/linux/stddef.h \
  /source/arch/x86/include/asm/posix_types.h \
    $(wildcard include/config/X86_32) \
  /source/arch/x86/include/uapi/asm/posix_types_64.h \
  /source/include/uapi/asm-generic/posix_types.h \
  /source/include/linux/kcsan-checks.h \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/KCSAN_WEAK_MEMORY) \
    $(wildcard include/config/KCSAN_IGNORE_ATOMICS) \
  /source/include/linux/poison.h \
    $(wildcard include/config/ILLEGAL_POINTER_VALUE) \
  /source/include/linux/const.h \
  /source/include/vdso/const.h \
  /source/include/uapi/linux/const.h \
  /source/arch/x86/include/asm/barrier.h \
  /source/arch/x86/include/asm/alternative.h \
    $(wildcard include/config/CALL_THUNKS) \
    $(wildcard include/config/MITIGATION_ITS) \
    $(wildcard include/config/MITIGATION_RETHUNK) \
  /source/include/linux/stringify.h \
  /source/include/linux/objtool.h \
    $(wildcard include/config/FRAME_POINTER) \
    $(wildcard include/config/NOINSTR_VALIDATION) \
    $(wildcard include/config/MITIGATION_UNRET_ENTRY) \
    $(wildcard include/config/MITIGATION_SRSO) \
  /source/include/linux/objtool_types.h \
  /source/include/linux/annotate.h \
  /source/arch/x86/include/asm/asm.h \
  /source/arch/x86/include/asm/extable_fixup_types.h \
  /source/arch/x86/include/asm/nops.h \
  /source/include/asm-generic/barrier.h \
  /source/include/linux/stat.h \
  /source/arch/x86/include/uapi/asm/stat.h \
  /source/include/uapi/linux/stat.h \
  /source/include/linux/time.h \
    $(wildcard include/config/POSIX_TIMERS) \
  /source/include/linux/cache.h \
    $(wildcard include/config/ARCH_HAS_CACHE_LINE_SIZE) \
  /source/include/uapi/linux/kernel.h \
  /source/include/uapi/linux/sysinfo.h \
  /source/include/vdso/cache.h \
  /source/arch/x86/include/asm/cache.h \
    $(wildcard include/config/X86_L1_CACHE_SHIFT) \
    $(wildcard include/config/X86_INTERNODE_CACHE_SHIFT) \
    $(wildcard include/config/X86_VSMP) \
  /source/include/linux/linkage.h \
    $(wildcard include/config/ARCH_USE_SYM_ANNOTATIONS) \
  /source/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
  /source/arch/x86/include/asm/linkage.h \
    $(wildcard include/config/CALL_PADDING) \
    $(wildcard include/config/MITIGATION_SLS) \
    $(wildcard include/config/FUNCTION_PADDING_BYTES) \
    $(wildcard include/config/UML) \
  /source/arch/x86/include/asm/ibt.h \
    $(wildcard include/config/X86_KERNEL_IBT) \
  /source/include/linux/math64.h \
    $(wildcard include/config/ARCH_SUPPORTS_INT128) \
  /source/include/linux/math.h \
  /source/arch/x86/include/asm/div64.h \
  /source/include/asm-generic/div64.h \
  /source/include/vdso/math64.h \
  /source/include/linux/time64.h \
  /source/include/vdso/time64.h \
  /source/include/uapi/linux/time.h \
  /source/include/uapi/linux/time_types.h \
  /source/include/linux/time32.h \
  /source/include/linux/timex.h \
  /source/include/uapi/linux/timex.h \
  /source/include/uapi/linux/param.h \
  arch/x86/include/generated/uapi/asm/param.h \
  /source/include/asm-generic/param.h \
    $(wildcard include/config/HZ) \
  /source/include/uapi/asm-generic/param.h \
  /source/arch/x86/include/asm/timex.h \
    $(wildcard include/config/X86_TSC) \
  /source/arch/x86/include/asm/processor.h \
    $(wildcard include/config/X86_VMX_FEATURE_NAMES) \
    $(wildcard include/config/X86_IOPL_IOPERM) \
    $(wildcard include/config/STACKPROTECTOR) \
    $(wildcard include/config/VM86) \
    $(wildcard include/config/X86_USER_SHADOW_STACK) \
    $(wildcard include/config/USE_X86_SEG_SUPPORT) \
    $(wildcard include/config/PARAVIRT_XXL) \
    $(wildcard include/config/CPU_SUP_AMD) \
    $(wildcard include/config/XEN) \
  /source/arch/x86/include/asm/processor-flags.h \
    $(wildcard include/config/MITIGATION_PAGE_TABLE_ISOLATION) \
  /source/arch/x86/include/uapi/asm/processor-flags.h \
  /source/include/linux/mem_encrypt.h \
    $(wildcard include/config/ARCH_HAS_MEM_ENCRYPT) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /source/arch/x86/include/asm/mem_encrypt.h \
    $(wildcard include/config/X86_MEM_ENCRYPT) \
  /source/include/linux/init.h \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
  /source/include/linux/cc_platform.h \
    $(wildcard include/config/ARCH_HAS_CC_PLATFORM) \
  /source/arch/x86/include/asm/math_emu.h \
  /source/arch/x86/include/asm/ptrace.h \
    $(wildcard include/config/PARAVIRT) \
    $(wildcard include/config/IA32_EMULATION) \
    $(wildcard include/config/X86_DEBUGCTLMSR) \
  /source/arch/x86/include/asm/segment.h \
    $(wildcard include/config/XEN_PV) \
  /source/arch/x86/include/asm/page_types.h \
    $(wildcard include/config/PHYSICAL_START) \
    $(wildcard include/config/PHYSICAL_ALIGN) \
    $(wildcard include/config/DYNAMIC_PHYSICAL_MASK) \
  /source/include/vdso/page.h \
    $(wildcard include/config/PAGE_SHIFT) \
  /source/arch/x86/include/asm/page_64_types.h \
    $(wildcard include/config/KASAN) \
    $(wildcard include/config/DYNAMIC_MEMORY_LAYOUT) \
    $(wildcard include/config/X86_5LEVEL) \
    $(wildcard include/config/RANDOMIZE_BASE) \
  /source/arch/x86/include/asm/kaslr.h \
    $(wildcard include/config/RANDOMIZE_MEMORY) \
  /source/arch/x86/include/uapi/asm/ptrace.h \
  /source/arch/x86/include/uapi/asm/ptrace-abi.h \
  /source/arch/x86/include/asm/paravirt_types.h \
    $(wildcard include/config/PGTABLE_LEVELS) \
    $(wildcard include/config/ZERO_CALL_USED_REGS) \
    $(wildcard include/config/PARAVIRT_DEBUG) \
  /source/arch/x86/include/asm/desc_defs.h \
  /source/arch/x86/include/asm/pgtable_types.h \
    $(wildcard include/config/X86_INTEL_MEMORY_PROTECTION_KEYS) \
    $(wildcard include/config/X86_PAE) \
    $(wildcard include/config/MEM_SOFT_DIRTY) \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_WP) \
    $(wildcard include/config/PROC_FS) \
  /source/arch/x86/include/asm/pgtable_64_types.h \
    $(wildcard include/config/KMSAN) \
    $(wildcard include/config/DEBUG_KMAP_LOCAL_FORCE_MAP) \
  /source/arch/x86/include/asm/sparsemem.h \
    $(wildcard include/config/SPARSEMEM) \
  /source/arch/x86/include/asm/nospec-branch.h \
    $(wildcard include/config/CALL_THUNKS_DEBUG) \
    $(wildcard include/config/MITIGATION_CALL_DEPTH_TRACKING) \
    $(wildcard include/config/MITIGATION_IBPB_ENTRY) \
  /source/include/linux/static_key.h \
  /source/include/linux/jump_label.h \
    $(wildcard include/config/HAVE_ARCH_JUMP_LABEL_RELATIVE) \
  /source/arch/x86/include/asm/jump_label.h \
    $(wildcard include/config/HAVE_JUMP_LABEL_HACK) \
  /source/arch/x86/include/asm/cpufeatures.h \
  /source/arch/x86/include/asm/required-features.h \
    $(wildcard include/config/X86_MINIMUM_CPU_FAMILY) \
    $(wildcard include/config/MATH_EMULATION) \
    $(wildcard include/config/X86_CMPXCHG64) \
    $(wildcard include/config/X86_CMOV) \
    $(wildcard include/config/X86_P6_NOP) \
    $(wildcard include/config/MATOM) \
  /source/arch/x86/include/asm/disabled-features.h \
    $(wildcard include/config/X86_UMIP) \
    $(wildcard include/config/ADDRESS_MASKING) \
    $(wildcard include/config/INTEL_IOMMU_SVM) \
    $(wildcard include/config/X86_SGX) \
    $(wildcard include/config/INTEL_TDX_GUEST) \
    $(wildcard include/config/X86_FRED) \
    $(wildcard include/config/KVM_AMD_SEV) \
  /source/arch/x86/include/asm/msr-index.h \
  /source/include/linux/bits.h \
  /source/include/vdso/bits.h \
  /source/include/uapi/linux/bits.h \
  /source/include/linux/overflow.h \
  /source/include/linux/limits.h \
  /source/include/uapi/linux/limits.h \
  /source/include/vdso/limits.h \
  /source/arch/x86/include/asm/unwind_hints.h \
  /source/arch/x86/include/asm/orc_types.h \
  /source/arch/x86/include/uapi/asm/byteorder.h \
  /source/include/linux/byteorder/little_endian.h \
  /source/include/uapi/linux/byteorder/little_endian.h \
  /source/include/linux/swab.h \
  /source/include/uapi/linux/swab.h \
  /source/arch/x86/include/uapi/asm/swab.h \
  /source/include/linux/byteorder/generic.h \
  /source/arch/x86/include/asm/percpu.h \
    $(wildcard include/config/X86_64_SMP) \
    $(wildcard include/config/CC_HAS_NAMED_AS) \
  /source/include/asm-generic/percpu.h \
    $(wildcard include/config/DEBUG_PREEMPT) \
    $(wildcard include/config/HAVE_SETUP_PER_CPU_AREA) \
  /source/include/linux/threads.h \
    $(wildcard include/config/NR_CPUS) \
    $(wildcard include/config/BASE_SMALL) \
  /source/include/linux/percpu-defs.h \
    $(wildcard include/config/DEBUG_FORCE_WEAK_PER_CPU) \
  /source/arch/x86/include/asm/current.h \
  /source/arch/x86/include/asm/asm-offsets.h \
  include/generated/asm-offsets.h \
  /source/arch/x86/include/asm/GEN-for-each-reg.h \
  /source/arch/x86/include/asm/spinlock_types.h \
  /source/include/asm-generic/qspinlock_types.h \
  /source/include/asm-generic/qrwlock_types.h \
  /source/arch/x86/include/asm/proto.h \
  /source/arch/x86/include/uapi/asm/ldt.h \
  /source/arch/x86/include/uapi/asm/sigcontext.h \
  /source/arch/x86/include/asm/cpuid.h \
  /source/arch/x86/include/asm/string.h \
  /source/arch/x86/include/asm/string_64.h \
    $(wildcard include/config/ARCH_HAS_UACCESS_FLUSHCACHE) \
  /source/arch/x86/include/asm/page.h \
  /source/arch/x86/include/asm/page_64.h \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/X86_VSYSCALL_EMULATION) \
  /source/include/linux/kmsan-checks.h \
  /source/include/linux/range.h \
  /source/include/asm-generic/memory_model.h \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
  /source/include/linux/pfn.h \
  /source/include/asm-generic/getorder.h \
  /source/include/linux/log2.h \
    $(wildcard include/config/ARCH_HAS_ILOG2_U32) \
    $(wildcard include/config/ARCH_HAS_ILOG2_U64) \
  /source/include/linux/bitops.h \
  /source/include/linux/typecheck.h \
  /source/include/asm-generic/bitops/generic-non-atomic.h \
  /source/arch/x86/include/asm/bitops.h \
  /source/arch/x86/include/asm/rmwcc.h \
  /source/include/linux/args.h \
  /source/include/asm-generic/bitops/sched.h \
  /source/arch/x86/include/asm/arch_hweight.h \
  /source/include/asm-generic/bitops/const_hweight.h \
  /source/include/asm-generic/bitops/instrumented-atomic.h \
  /source/include/linux/instrumented.h \
  /source/include/asm-generic/bitops/instrumented-non-atomic.h \
    $(wildcard include/config/KCSAN_ASSUME_PLAIN_WRITES_ATOMIC) \
  /source/include/asm-generic/bitops/instrumented-lock.h \
  /source/include/asm-generic/bitops/le.h \
  /source/include/asm-generic/bitops/ext2-atomic-setbit.h \
  /source/arch/x86/include/asm/special_insns.h \
  /source/include/linux/errno.h \
  /source/include/uapi/linux/errno.h \
  arch/x86/include/generated/uapi/asm/errno.h \
  /source/include/uapi/asm-generic/errno.h \
  /source/include/uapi/asm-generic/errno-base.h \
  /source/include/linux/irqflags.h \
    $(wildcard include/config/PROVE_LOCKING) \
    $(wildcard include/config/TRACE_IRQFLAGS) \
    $(wildcard include/config/PREEMPT_RT) \
    $(wildcard include/config/IRQSOFF_TRACER) \
    $(wildcard include/config/PREEMPT_TRACER) \
    $(wildcard include/config/DEBUG_IRQFLAGS) \
    $(wildcard include/config/TRACE_IRQFLAGS_SUPPORT) \
  /source/include/linux/irqflags_types.h \
  /source/include/linux/cleanup.h \
  /source/arch/x86/include/asm/irqflags.h \
    $(wildcard include/config/DEBUG_ENTRY) \
  /source/arch/x86/include/asm/fpu/types.h \
  /source/arch/x86/include/asm/vmxfeatures.h \
  /source/arch/x86/include/asm/vdso/processor.h \
  /source/arch/x86/include/asm/shstk.h \
  /source/include/linux/personality.h \
  /source/include/uapi/linux/personality.h \
  /source/include/linux/err.h \
  /source/arch/x86/include/asm/tsc.h \
  /source/arch/x86/include/asm/cpufeature.h \
  /source/arch/x86/include/asm/msr.h \
  /source/arch/x86/include/asm/cpumask.h \
  /source/include/linux/cpumask.h \
    $(wildcard include/config/FORCE_NR_CPUS) \
    $(wildcard include/config/HOTPLUG_CPU) \
    $(wildcard include/config/DEBUG_PER_CPU_MAPS) \
    $(wildcard include/config/CPUMASK_OFFSTACK) \
  /source/include/linux/kernel.h \
    $(wildcard include/config/PREEMPT_VOLUNTARY_BUILD) \
    $(wildcard include/config/PREEMPT_DYNAMIC) \
    $(wildcard include/config/HAVE_PREEMPT_DYNAMIC_CALL) \
    $(wildcard include/config/HAVE_PREEMPT_DYNAMIC_KEY) \
    $(wildcard include/config/PREEMPT_) \
    $(wildcard include/config/DEBUG_ATOMIC_SLEEP) \
    $(wildcard include/config/MMU) \
  /source/include/linux/stdarg.h \
  /source/include/linux/align.h \
  /source/include/vdso/align.h \
  /source/include/linux/array_size.h \
  /source/include/linux/hex.h \
  /source/include/linux/kstrtox.h \
  /source/include/linux/minmax.h \
  /source/include/linux/panic.h \
    $(wildcard include/config/PANIC_TIMEOUT) \
  /source/include/linux/printk.h \
    $(wildcard include/config/MESSAGE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_QUIET) \
    $(wildcard include/config/EARLY_PRINTK) \
    $(wildcard include/config/PRINTK) \
    $(wildcard include/config/DYNAMIC_DEBUG) \
  /source/include/linux/kern_levels.h \
  /source/include/linux/ratelimit_types.h \
  /source/include/linux/spinlock_types_raw.h \
    $(wildcard include/config/DEBUG_SPINLOCK) \
    $(wildcard include/config/DEBUG_LOCK_ALLOC) \
  /source/include/linux/lockdep_types.h \
    $(wildcard include/config/PROVE_RAW_LOCK_NESTING) \
    $(wildcard include/config/LOCKDEP) \
    $(wildcard include/config/LOCK_STAT) \
  /source/include/linux/once_lite.h \
  /source/include/linux/dynamic_debug.h \
  /source/include/linux/sprintf.h \
  /source/include/linux/static_call_types.h \
    $(wildcard include/config/HAVE_STATIC_CALL) \
  /source/include/linux/instruction_pointer.h \
  /source/include/linux/wordpart.h \
  /source/include/linux/bitmap.h \
  /source/include/linux/find.h \
  /source/include/linux/string.h \
    $(wildcard include/config/BINARY_PRINTF) \
    $(wildcard include/config/FORTIFY_SOURCE) \
  /source/include/uapi/linux/string.h \
  /source/include/linux/fortify-string.h \
    $(wildcard include/config/CC_HAS_KASAN_MEMINTRINSIC_PREFIX) \
    $(wildcard include/config/GENERIC_ENTRY) \
  /source/include/linux/bitfield.h \
  /source/include/linux/bug.h \
    $(wildcard include/config/BUG_ON_DATA_CORRUPTION) \
  /source/arch/x86/include/asm/bug.h \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
  /source/include/linux/instrumentation.h \
  /source/include/asm-generic/bug.h \
    $(wildcard include/config/BUG) \
    $(wildcard include/config/GENERIC_BUG_RELATIVE_POINTERS) \
  /source/include/linux/bitmap-str.h \
  /source/include/linux/cpumask_types.h \
  /source/include/linux/atomic.h \
  /source/arch/x86/include/asm/atomic.h \
  /source/arch/x86/include/asm/cmpxchg.h \
  /source/arch/x86/include/asm/cmpxchg_64.h \
  /source/arch/x86/include/asm/atomic64_64.h \
  /source/include/linux/atomic/atomic-arch-fallback.h \
    $(wildcard include/config/GENERIC_ATOMIC64) \
  /source/include/linux/atomic/atomic-long.h \
  /source/include/linux/atomic/atomic-instrumented.h \
  /source/include/linux/gfp_types.h \
    $(wildcard include/config/KASAN_HW_TAGS) \
    $(wildcard include/config/SLAB_OBJ_EXT) \
  /source/include/linux/numa.h \
    $(wildcard include/config/NUMA_KEEP_MEMINFO) \
    $(wildcard include/config/NUMA) \
    $(wildcard include/config/HAVE_ARCH_NODE_DEV_GROUP) \
  /source/include/linux/nodemask.h \
    $(wildcard include/config/HIGHMEM) \
  /source/include/linux/nodemask_types.h \
    $(wildcard include/config/NODES_SHIFT) \
  /source/include/linux/random.h \
    $(wildcard include/config/VMGENID) \
  /source/include/uapi/linux/random.h \
  /source/include/uapi/linux/ioctl.h \
  arch/x86/include/generated/uapi/asm/ioctl.h \
  /source/include/asm-generic/ioctl.h \
  /source/include/uapi/asm-generic/ioctl.h \
  /source/include/linux/irqnr.h \
  /source/include/uapi/linux/irqnr.h \
  /source/include/linux/prandom.h \
  /source/include/linux/once.h \
  /source/arch/x86/include/uapi/asm/msr.h \
  /source/arch/x86/include/asm/shared/msr.h \
  /source/include/linux/percpu.h \
    $(wildcard include/config/RANDOM_KMALLOC_CACHES) \
    $(wildcard include/config/PAGE_SIZE_4KB) \
    $(wildcard include/config/NEED_PER_CPU_PAGE_FIRST_CHUNK) \
  /source/include/linux/alloc_tag.h \
    $(wildcard include/config/MEM_ALLOC_PROFILING_DEBUG) \
    $(wildcard include/config/MEM_ALLOC_PROFILING) \
    $(wildcard include/config/MEM_ALLOC_PROFILING_ENABLED_BY_DEFAULT) \
  /source/include/linux/codetag.h \
    $(wildcard include/config/CODE_TAGGING) \
  /source/include/linux/preempt.h \
    $(wildcard include/config/PREEMPT_COUNT) \
    $(wildcard include/config/TRACE_PREEMPT_TOGGLE) \
    $(wildcard include/config/PREEMPTION) \
    $(wildcard include/config/PREEMPT_NOTIFIERS) \
    $(wildcard include/config/PREEMPT_NONE) \
    $(wildcard include/config/PREEMPT_VOLUNTARY) \
    $(wildcard include/config/PREEMPT) \
    $(wildcard include/config/PREEMPT_LAZY) \
  /source/arch/x86/include/asm/preempt.h \
  /source/include/linux/smp.h \
    $(wildcard include/config/UP_LATE_INIT) \
    $(wildcard include/config/CSD_LOCK_WAIT_DEBUG) \
  /source/include/linux/smp_types.h \
  /source/include/linux/llist.h \
    $(wildcard include/config/ARCH_HAVE_NMI_SAFE_CMPXCHG) \
  /source/include/linux/thread_info.h \
    $(wildcard include/config/THREAD_INFO_IN_TASK) \
    $(wildcard include/config/ARCH_HAS_PREEMPT_LAZY) \
    $(wildcard include/config/HAVE_ARCH_WITHIN_STACK_FRAMES) \
    $(wildcard include/config/HARDENED_USERCOPY) \
    $(wildcard include/config/SH) \
  /source/include/linux/restart_block.h \
  /source/arch/x86/include/asm/thread_info.h \
    $(wildcard include/config/COMPAT) \
  /source/arch/x86/include/asm/smp.h \
    $(wildcard include/config/DEBUG_NMI_SELFTEST) \
  /source/include/linux/mmdebug.h \
    $(wildcard include/config/DEBUG_VM) \
    $(wildcard include/config/DEBUG_VM_IRQSOFF) \
    $(wildcard include/config/DEBUG_VM_PGFLAGS) \
  /source/include/linux/sched.h \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_NATIVE) \
    $(wildcard include/config/SCHED_INFO) \
    $(wildcard include/config/SCHEDSTATS) \
    $(wildcard include/config/SCHED_CORE) \
    $(wildcard include/config/FAIR_GROUP_SCHED) \
    $(wildcard include/config/RT_GROUP_SCHED) \
    $(wildcard include/config/RT_MUTEXES) \
    $(wildcard include/config/UCLAMP_TASK) \
    $(wildcard include/config/UCLAMP_BUCKETS_COUNT) \
    $(wildcard include/config/KMAP_LOCAL) \
    $(wildcard include/config/SCHED_CLASS_EXT) \
    $(wildcard include/config/CGROUP_SCHED) \
    $(wildcard include/config/CFS_BANDWIDTH) \
    $(wildcard include/config/BLK_DEV_IO_TRACE) \
    $(wildcard include/config/PREEMPT_RCU) \
    $(wildcard include/config/TASKS_RCU) \
    $(wildcard include/config/TASKS_TRACE_RCU) \
    $(wildcard include/config/MEMCG_V1) \
    $(wildcard include/config/LRU_GEN) \
    $(wildcard include/config/COMPAT_BRK) \
    $(wildcard include/config/CGROUPS) \
    $(wildcard include/config/BLK_CGROUP) \
    $(wildcard include/config/PSI) \
    $(wildcard include/config/PAGE_OWNER) \
    $(wildcard include/config/EVENTFD) \
    $(wildcard include/config/ARCH_HAS_CPU_PASID) \
    $(wildcard include/config/X86_BUS_LOCK_DETECT) \
    $(wildcard include/config/TASK_DELAY_ACCT) \
    $(wildcard include/config/ARCH_HAS_SCALED_CPUTIME) \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_GEN) \
    $(wildcard include/config/NO_HZ_FULL) \
    $(wildcard include/config/POSIX_CPUTIMERS) \
    $(wildcard include/config/POSIX_CPU_TIMERS_TASK_WORK) \
    $(wildcard include/config/KEYS) \
    $(wildcard include/config/SYSVIPC) \
    $(wildcard include/config/DETECT_HUNG_TASK) \
    $(wildcard include/config/IO_URING) \
    $(wildcard include/config/AUDIT) \
    $(wildcard include/config/AUDITSYSCALL) \
    $(wildcard include/config/DEBUG_MUTEXES) \
    $(wildcard include/config/UBSAN) \
    $(wildcard include/config/UBSAN_TRAP) \
    $(wildcard include/config/COMPACTION) \
    $(wildcard include/config/TASK_XACCT) \
    $(wildcard include/config/CPUSETS) \
    $(wildcard include/config/X86_CPU_RESCTRL) \
    $(wildcard include/config/FUTEX) \
    $(wildcard include/config/PERF_EVENTS) \
    $(wildcard include/config/NUMA_BALANCING) \
    $(wildcard include/config/RSEQ) \
    $(wildcard include/config/DEBUG_RSEQ) \
    $(wildcard include/config/SCHED_MM_CID) \
    $(wildcard include/config/FAULT_INJECTION) \
    $(wildcard include/config/LATENCYTOP) \
    $(wildcard include/config/FUNCTION_GRAPH_TRACER) \
    $(wildcard include/config/KCOV) \
    $(wildcard include/config/MEMCG) \
    $(wildcard include/config/UPROBES) \
    $(wildcard include/config/BCACHE) \
    $(wildcard include/config/VMAP_STACK) \
    $(wildcard include/config/SECURITY) \
    $(wildcard include/config/BPF_SYSCALL) \
    $(wildcard include/config/GCC_PLUGIN_STACKLEAK) \
    $(wildcard include/config/X86_MCE) \
    $(wildcard include/config/KRETPROBES) \
    $(wildcard include/config/RETHOOK) \
    $(wildcard include/config/ARCH_HAS_PARANOID_L1D_FLUSH) \
    $(wildcard include/config/RV) \
    $(wildcard include/config/RV_PER_TASK_MONITORS) \
    $(wildcard include/config/USER_EVENTS) \
  /source/include/uapi/linux/sched.h \
  /source/include/linux/rh_kabi.h \
    $(wildcard include/config/RH_KABI_SIZE_ALIGN_CHECKS) \
  /source/include/linux/pid_types.h \
  /source/include/linux/sem_types.h \
  /source/include/linux/shm.h \
  /source/arch/x86/include/asm/shmparam.h \
  /source/include/linux/kmsan_types.h \
  /source/include/linux/mutex_types.h \
    $(wildcard include/config/MUTEX_SPIN_ON_OWNER) \
  /source/include/linux/osq_lock.h \
  /source/include/linux/spinlock_types.h \
  /source/include/linux/rwlock_types.h \
  /source/include/linux/plist_types.h \
  /source/include/linux/hrtimer_types.h \
  /source/include/linux/timerqueue_types.h \
  /source/include/linux/rbtree_types.h \
  /source/include/linux/timer_types.h \
  /source/include/linux/seccomp_types.h \
    $(wildcard include/config/SECCOMP) \
  /source/include/linux/refcount_types.h \
  /source/include/linux/resource.h \
  /source/include/uapi/linux/resource.h \
  arch/x86/include/generated/uapi/asm/resource.h \
  /source/include/asm-generic/resource.h \
  /source/include/uapi/asm-generic/resource.h \
  /source/include/linux/latencytop.h \
  /source/include/linux/sched/prio.h \
  /source/include/linux/sched/types.h \
  /source/include/linux/signal_types.h \
    $(wildcard include/config/OLD_SIGACTION) \
  /source/include/uapi/linux/signal.h \
  /source/arch/x86/include/asm/signal.h \
  /source/arch/x86/include/uapi/asm/signal.h \
  /source/include/uapi/asm-generic/signal-defs.h \
  /source/arch/x86/include/uapi/asm/siginfo.h \
  /source/include/uapi/asm-generic/siginfo.h \
  /source/include/linux/syscall_user_dispatch_types.h \
  /source/include/linux/mm_types_task.h \
    $(wildcard include/config/ARCH_WANT_BATCHED_UNMAP_TLB_FLUSH) \
  /source/arch/x86/include/asm/tlbbatch.h \
  /source/include/linux/netdevice_xmit.h \
    $(wildcard include/config/NET_EGRESS) \
  /source/include/linux/task_io_accounting.h \
    $(wildcard include/config/TASK_IO_ACCOUNTING) \
  /source/include/linux/posix-timers_types.h \
  /source/include/uapi/linux/rseq.h \
  /source/include/linux/seqlock_types.h \
  /source/include/linux/kcsan.h \
  /source/include/linux/rv.h \
    $(wildcard include/config/RV_LTL_MONITOR) \
    $(wildcard include/config/RV_REACTORS) \
  /source/include/linux/uidgid_types.h \
  /source/include/linux/tracepoint-defs.h \
  arch/x86/include/generated/asm/kmap_size.h \
  /source/include/asm-generic/kmap_size.h \
    $(wildcard include/config/DEBUG_KMAP_LOCAL) \
  include/generated/rq-offsets.h \
  /source/include/linux/sched/ext.h \
    $(wildcard include/config/EXT_GROUP_SCHED) \
  /source/include/linux/rhashtable-types.h \
  /source/include/linux/mutex.h \
  /source/include/linux/lockdep.h \
    $(wildcard include/config/DEBUG_LOCKING_API_SELFTESTS) \
  /source/include/linux/debug_locks.h \
  /source/include/linux/workqueue_types.h \
  /source/include/linux/spinlock.h \
  /source/include/linux/bottom_half.h \
  arch/x86/include/generated/asm/mmiowb.h \
  /source/include/asm-generic/mmiowb.h \
    $(wildcard include/config/MMIOWB) \
  /source/arch/x86/include/asm/spinlock.h \
  /source/arch/x86/include/asm/paravirt.h \
    $(wildcard include/config/PARAVIRT_SPINLOCKS) \
  /source/arch/x86/include/asm/frame.h \
  /source/arch/x86/include/asm/qspinlock.h \
  /source/include/asm-generic/qspinlock.h \
  /source/arch/x86/include/asm/qrwlock.h \
  /source/include/asm-generic/qrwlock.h \
  /source/include/linux/rwlock.h \
  /source/include/linux/spinlock_api_smp.h \
    $(wildcard include/config/INLINE_SPIN_LOCK) \
    $(wildcard include/config/INLINE_SPIN_LOCK_BH) \
    $(wildcard include/config/INLINE_SPIN_LOCK_IRQ) \
    $(wildcard include/config/INLINE_SPIN_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_SPIN_TRYLOCK) \
    $(wildcard include/config/INLINE_SPIN_TRYLOCK_BH) \
    $(wildcard include/config/UNINLINE_SPIN_UNLOCK) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_BH) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_IRQRESTORE) \
    $(wildcard include/config/GENERIC_LOCKBREAK) \
  /source/include/linux/rwlock_api_smp.h \
    $(wildcard include/config/INLINE_READ_LOCK) \
    $(wildcard include/config/INLINE_WRITE_LOCK) \
    $(wildcard include/config/INLINE_READ_LOCK_BH) \
    $(wildcard include/config/INLINE_WRITE_LOCK_BH) \
    $(wildcard include/config/INLINE_READ_LOCK_IRQ) \
    $(wildcard include/config/INLINE_WRITE_LOCK_IRQ) \
    $(wildcard include/config/INLINE_READ_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_WRITE_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_READ_TRYLOCK) \
    $(wildcard include/config/INLINE_WRITE_TRYLOCK) \
    $(wildcard include/config/INLINE_READ_UNLOCK) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK) \
    $(wildcard include/config/INLINE_READ_UNLOCK_BH) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_BH) \
    $(wildcard include/config/INLINE_READ_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_READ_UNLOCK_IRQRESTORE) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_IRQRESTORE) \
  /source/include/vdso/time32.h \
  /source/include/vdso/time.h \
  /source/include/linux/uidgid.h \
    $(wildcard include/config/MULTIUSER) \
    $(wildcard include/config/USER_NS) \
  /source/include/linux/highuid.h \
  /source/include/linux/buildid.h \
    $(wildcard include/config/VMCORE_INFO) \
  /source/include/linux/kmod.h \
  /source/include/linux/umh.h \
  /source/include/linux/gfp.h \
    $(wildcard include/config/ZONE_DMA) \
    $(wildcard include/config/ZONE_DMA32) \
    $(wildcard include/config/ZONE_DEVICE) \
    $(wildcard include/config/CONTIG_ALLOC) \
  /source/include/linux/mmzone.h \
    $(wildcard include/config/ARCH_FORCE_MAX_ORDER) \
    $(wildcard include/config/CMA) \
    $(wildcard include/config/MEMORY_ISOLATION) \
    $(wildcard include/config/ZSMALLOC) \
    $(wildcard include/config/UNACCEPTED_MEMORY) \
    $(wildcard include/config/SHADOW_CALL_STACK) \
    $(wildcard include/config/IOMMU_SUPPORT) \
    $(wildcard include/config/SWAP) \
    $(wildcard include/config/HUGETLB_PAGE) \
    $(wildcard include/config/TRANSPARENT_HUGEPAGE) \
    $(wildcard include/config/LRU_GEN_STATS) \
    $(wildcard include/config/LRU_GEN_WALKS_MMU) \
    $(wildcard include/config/MEMORY_FAILURE) \
    $(wildcard include/config/PAGE_EXTENSION) \
    $(wildcard include/config/DEFERRED_STRUCT_PAGE_INIT) \
    $(wildcard include/config/HAVE_MEMORYLESS_NODES) \
    $(wildcard include/config/SPARSEMEM_EXTREME) \
    $(wildcard include/config/HAVE_ARCH_PFN_VALID) \
  /source/include/linux/list_nulls.h \
  /source/include/linux/wait.h \
  /source/include/linux/seqlock.h \
  /source/include/linux/pageblock-flags.h \
    $(wildcard include/config/HUGETLB_PAGE_SIZE_VARIABLE) \
  /source/include/linux/page-flags-layout.h \
  include/generated/bounds.h \
  /source/include/linux/mm_types.h \
    $(wildcard include/config/HAVE_ALIGNED_STRUCT_PAGE) \
    $(wildcard include/config/HUGETLB_PMD_PAGE_TABLE_SHARING) \
    $(wildcard include/config/USERFAULTFD) \
    $(wildcard include/config/ANON_VMA_NAME) \
    $(wildcard include/config/PER_VMA_LOCK) \
    $(wildcard include/config/HAVE_ARCH_COMPAT_MMAP_BASES) \
    $(wildcard include/config/MEMBARRIER) \
    $(wildcard include/config/FUTEX_PRIVATE_HASH) \
    $(wildcard include/config/AIO) \
    $(wildcard include/config/MMU_NOTIFIER) \
    $(wildcard include/config/SPLIT_PMD_PTLOCKS) \
    $(wildcard include/config/IOMMU_MM_DATA) \
    $(wildcard include/config/KSM) \
    $(wildcard include/config/CORE_DUMP_DEFAULT_ELF_HEADERS) \
  /source/include/linux/auxvec.h \
  /source/include/uapi/linux/auxvec.h \
  /source/arch/x86/include/uapi/asm/auxvec.h \
  /source/include/linux/kref.h \
  /source/include/linux/refcount.h \
  /source/include/linux/rbtree.h \
  /source/include/linux/rcupdate.h \
    $(wildcard include/config/TINY_RCU) \
    $(wildcard include/config/RCU_STRICT_GRACE_PERIOD) \
    $(wildcard include/config/RCU_LAZY) \
    $(wildcard include/config/RCU_STALL_COMMON) \
    $(wildcard include/config/VIRT_XFER_TO_GUEST_WORK) \
    $(wildcard include/config/RCU_NOCB_CPU) \
    $(wildcard include/config/TASKS_RCU_GENERIC) \
    $(wildcard include/config/TASKS_RUDE_RCU) \
    $(wildcard include/config/TREE_RCU) \
    $(wildcard include/config/DEBUG_OBJECTS_RCU_HEAD) \
    $(wildcard include/config/PROVE_RCU) \
    $(wildcard include/config/ARCH_WEAK_RELEASE_ACQUIRE) \
  /source/include/linux/context_tracking_irq.h \
    $(wildcard include/config/CONTEXT_TRACKING_IDLE) \
  /source/include/linux/rcutree.h \
  /source/include/linux/maple_tree.h \
    $(wildcard include/config/MAPLE_RCU_DISABLED) \
    $(wildcard include/config/DEBUG_MAPLE_TREE) \
  /source/include/linux/rwsem.h \
    $(wildcard include/config/RWSEM_SPIN_ON_OWNER) \
    $(wildcard include/config/DEBUG_RWSEMS) \
  /source/include/linux/completion.h \
  /source/include/linux/swait.h \
  /source/include/linux/uprobes.h \
  /source/arch/x86/include/asm/uprobes.h \
  /source/include/linux/notifier.h \
  /source/include/linux/srcu.h \
    $(wildcard include/config/TINY_SRCU) \
    $(wildcard include/config/NEED_SRCU_NMI_SAFE) \
  /source/include/linux/workqueue.h \
    $(wildcard include/config/DEBUG_OBJECTS_WORK) \
    $(wildcard include/config/FREEZER) \
    $(wildcard include/config/WQ_WATCHDOG) \
  /source/include/linux/timer.h \
    $(wildcard include/config/DEBUG_OBJECTS_TIMERS) \
  /source/include/linux/ktime.h \
  /source/include/linux/jiffies.h \
  /source/include/vdso/jiffies.h \
  include/generated/timeconst.h \
  /source/include/vdso/ktime.h \
  /source/include/linux/timekeeping.h \
    $(wildcard include/config/GENERIC_CMOS_UPDATE) \
  /source/include/linux/clocksource_ids.h \
  /source/include/linux/debugobjects.h \
    $(wildcard include/config/DEBUG_OBJECTS) \
    $(wildcard include/config/DEBUG_OBJECTS_FREE) \
  /source/include/linux/rcu_segcblist.h \
  /source/include/linux/srcutree.h \
  /source/include/linux/rcu_node_tree.h \
    $(wildcard include/config/RCU_FANOUT) \
    $(wildcard include/config/RCU_FANOUT_LEAF) \
  /source/include/linux/percpu_counter.h \
  /source/arch/x86/include/asm/mmu.h \
    $(wildcard include/config/MODIFY_LDT_SYSCALL) \
  /source/include/linux/page-flags.h \
    $(wildcard include/config/PAGE_IDLE_FLAG) \
    $(wildcard include/config/ARCH_USES_PG_ARCH_2) \
    $(wildcard include/config/ARCH_USES_PG_ARCH_3) \
    $(wildcard include/config/HUGETLB_PAGE_OPTIMIZE_VMEMMAP) \
  /source/include/linux/local_lock.h \
  /source/include/linux/local_lock_internal.h \
  /source/include/linux/zswap.h \
    $(wildcard include/config/ZSWAP) \
  /source/include/linux/memory_hotplug.h \
    $(wildcard include/config/ARCH_HAS_ADD_PAGES) \
    $(wildcard include/config/MEMORY_HOTREMOVE) \
  arch/x86/include/generated/asm/mmzone.h \
  /source/include/asm-generic/mmzone.h \
  /source/include/linux/topology.h \
    $(wildcard include/config/USE_PERCPU_NUMA_NODE_ID) \
    $(wildcard include/config/SCHED_SMT) \
  /source/include/linux/arch_topology.h \
    $(wildcard include/config/GENERIC_ARCH_TOPOLOGY) \
  /source/arch/x86/include/asm/topology.h \
    $(wildcard include/config/X86_LOCAL_APIC) \
    $(wildcard include/config/SCHED_MC_PRIO) \
  /source/arch/x86/include/asm/mpspec.h \
    $(wildcard include/config/EISA) \
    $(wildcard include/config/X86_MPPARSE) \
  /source/arch/x86/include/asm/mpspec_def.h \
  /source/arch/x86/include/asm/x86_init.h \
  /source/arch/x86/include/asm/apicdef.h \
  /source/include/asm-generic/topology.h \
  /source/include/linux/cpu_smt.h \
    $(wildcard include/config/HOTPLUG_SMT) \
  /source/include/linux/sysctl.h \
    $(wildcard include/config/SYSCTL) \
  /source/include/uapi/linux/sysctl.h \
  /source/include/linux/elf.h \
    $(wildcard include/config/ARCH_HAVE_EXTRA_ELF_NOTES) \
    $(wildcard include/config/ARCH_USE_GNU_PROPERTY) \
    $(wildcard include/config/ARCH_HAVE_ELF_PROT) \
  /source/arch/x86/include/asm/elf.h \
    $(wildcard include/config/X86_X32_ABI) \
  /source/arch/x86/include/asm/ia32.h \
  /source/include/linux/compat.h \
    $(wildcard include/config/ARCH_HAS_SYSCALL_WRAPPER) \
    $(wildcard include/config/COMPAT_OLD_SIGACTION) \
    $(wildcard include/config/ODD_RT_SIGACTION) \
  /source/include/linux/sem.h \
  /source/include/uapi/linux/sem.h \
  /source/include/linux/ipc.h \
  /source/include/uapi/linux/ipc.h \
  arch/x86/include/generated/uapi/asm/ipcbuf.h \
  /source/include/uapi/asm-generic/ipcbuf.h \
  /source/arch/x86/include/uapi/asm/sembuf.h \
  /source/include/linux/socket.h \
  arch/x86/include/generated/uapi/asm/socket.h \
  /source/include/uapi/asm-generic/socket.h \
  arch/x86/include/generated/uapi/asm/sockios.h \
  /source/include/uapi/asm-generic/sockios.h \
  /source/include/uapi/linux/sockios.h \
  /source/include/linux/uio.h \
    $(wildcard include/config/ARCH_HAS_COPY_MC) \
  /source/include/uapi/linux/uio.h \
  /source/include/uapi/linux/socket.h \
  /source/include/uapi/linux/if.h \
  /source/include/uapi/linux/libc-compat.h \
  /source/include/uapi/linux/hdlc/ioctl.h \
  /source/include/linux/fs.h \
    $(wildcard include/config/READ_ONLY_THP_FOR_FS) \
    $(wildcard include/config/FS_POSIX_ACL) \
    $(wildcard include/config/CGROUP_WRITEBACK) \
    $(wildcard include/config/IMA) \
    $(wildcard include/config/FILE_LOCKING) \
    $(wildcard include/config/FSNOTIFY) \
    $(wildcard include/config/FS_ENCRYPTION) \
    $(wildcard include/config/FS_VERITY) \
    $(wildcard include/config/EPOLL) \
    $(wildcard include/config/UNICODE) \
    $(wildcard include/config/QUOTA) \
    $(wildcard include/config/FS_DAX) \
    $(wildcard include/config/BLOCK) \
  /source/include/linux/wait_bit.h \
  /source/include/linux/kdev_t.h \
  /source/include/uapi/linux/kdev_t.h \
  /source/include/linux/dcache.h \
  /source/include/linux/rculist.h \
    $(wildcard include/config/PROVE_RCU_LIST) \
  /source/include/linux/rculist_bl.h \
  /source/include/linux/list_bl.h \
  /source/include/linux/bit_spinlock.h \
  /source/include/linux/lockref.h \
    $(wildcard include/config/ARCH_USE_CMPXCHG_LOCKREF) \
  /source/include/linux/stringhash.h \
    $(wildcard include/config/DCACHE_WORD_ACCESS) \
  /source/include/linux/hash.h \
    $(wildcard include/config/HAVE_ARCH_HASH) \
  /source/include/linux/path.h \
  /source/include/linux/list_lru.h \
  /source/include/linux/shrinker.h \
    $(wildcard include/config/SHRINKER_DEBUG) \
  /source/include/linux/xarray.h \
    $(wildcard include/config/XARRAY_MULTI) \
  /source/include/linux/sched/mm.h \
    $(wildcard include/config/MMU_LAZY_TLB_REFCOUNT) \
    $(wildcard include/config/ARCH_HAS_MEMBARRIER_CALLBACKS) \
    $(wildcard include/config/ARCH_HAS_SYNC_CORE_BEFORE_USERMODE) \
  /source/include/linux/sync_core.h \
    $(wildcard include/config/ARCH_HAS_PREPARE_SYNC_CORE_CMD) \
  /source/arch/x86/include/asm/sync_core.h \
  /source/include/linux/sched/coredump.h \
  /source/include/linux/radix-tree.h \
  /source/include/linux/pid.h \
  /source/include/linux/capability.h \
  /source/include/uapi/linux/capability.h \
  /source/include/linux/semaphore.h \
  /source/include/linux/fcntl.h \
    $(wildcard include/config/ARCH_32BIT_OFF_T) \
  /source/include/uapi/linux/fcntl.h \
  arch/x86/include/generated/uapi/asm/fcntl.h \
  /source/include/uapi/asm-generic/fcntl.h \
  /source/include/uapi/linux/openat2.h \
  /source/include/linux/migrate_mode.h \
  /source/include/linux/percpu-rwsem.h \
  /source/include/linux/rcuwait.h \
  /source/include/linux/sched/signal.h \
    $(wildcard include/config/SCHED_AUTOGROUP) \
    $(wildcard include/config/BSD_PROCESS_ACCT) \
    $(wildcard include/config/TASKSTATS) \
    $(wildcard include/config/STACK_GROWSUP) \
  /source/include/linux/signal.h \
    $(wildcard include/config/DYNAMIC_SIGFRAME) \
  /source/include/linux/sched/jobctl.h \
  /source/include/linux/sched/task.h \
    $(wildcard include/config/HAVE_EXIT_THREAD) \
    $(wildcard include/config/ARCH_WANTS_DYNAMIC_TASK_STRUCT) \
    $(wildcard include/config/HAVE_ARCH_THREAD_STRUCT_WHITELIST) \
  /source/include/linux/uaccess.h \
    $(wildcard include/config/ARCH_HAS_SUBPAGE_FAULTS) \
  /source/include/linux/fault-inject-usercopy.h \
    $(wildcard include/config/FAULT_INJECTION_USERCOPY) \
  /source/include/linux/nospec.h \
  /source/arch/x86/include/asm/uaccess.h \
    $(wildcard include/config/CC_HAS_ASM_GOTO_OUTPUT) \
    $(wildcard include/config/CC_HAS_ASM_GOTO_TIED_OUTPUT) \
    $(wildcard include/config/X86_INTEL_USERCOPY) \
  /source/include/linux/mmap_lock.h \
  /source/arch/x86/include/asm/smap.h \
  /source/arch/x86/include/asm/extable.h \
    $(wildcard include/config/BPF_JIT) \
  /source/arch/x86/include/asm/tlbflush.h \
  /source/include/linux/mmu_notifier.h \
  /source/include/linux/interval_tree.h \
  /source/arch/x86/include/asm/invpcid.h \
  /source/arch/x86/include/asm/pti.h \
  /source/arch/x86/include/asm/pgtable.h \
    $(wildcard include/config/DEBUG_WX) \
    $(wildcard include/config/HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD) \
    $(wildcard include/config/ARCH_HAS_PTE_DEVMAP) \
    $(wildcard include/config/ARCH_SUPPORTS_PMD_PFNMAP) \
    $(wildcard include/config/ARCH_SUPPORTS_PUD_PFNMAP) \
    $(wildcard include/config/HAVE_ARCH_SOFT_DIRTY) \
    $(wildcard include/config/ARCH_ENABLE_THP_MIGRATION) \
    $(wildcard include/config/PAGE_TABLE_CHECK) \
  /source/arch/x86/include/asm/pkru.h \
  /source/arch/x86/include/asm/fpu/api.h \
    $(wildcard include/config/X86_DEBUG_FPU) \
  /source/arch/x86/include/asm/coco.h \
  /source/include/asm-generic/pgtable_uffd.h \
  /source/include/linux/page_table_check.h \
  /source/arch/x86/include/asm/pgtable_64.h \
  /source/arch/x86/include/asm/fixmap.h \
    $(wildcard include/config/PROVIDE_OHCI1394_DMA_INIT) \
    $(wildcard include/config/X86_IO_APIC) \
    $(wildcard include/config/PCI_MMCONFIG) \
    $(wildcard include/config/ACPI_APEI_GHES) \
    $(wildcard include/config/INTEL_TXT) \
  /source/arch/x86/include/uapi/asm/vsyscall.h \
  /source/include/asm-generic/fixmap.h \
  /source/arch/x86/include/asm/pgtable-invert.h \
  /source/arch/x86/include/asm/uaccess_64.h \
  /source/arch/x86/include/asm/runtime-const.h \
  /source/include/asm-generic/access_ok.h \
    $(wildcard include/config/ALTERNATE_USER_ADDRESS_SPACE) \
  /source/include/linux/cred.h \
  /source/include/linux/key.h \
    $(wildcard include/config/KEY_NOTIFICATIONS) \
    $(wildcard include/config/NET) \
  /source/include/linux/assoc_array.h \
    $(wildcard include/config/ASSOCIATIVE_ARRAY) \
  /source/include/linux/sched/user.h \
    $(wildcard include/config/VFIO_PCI_ZDEV_KVM) \
    $(wildcard include/config/IOMMUFD) \
    $(wildcard include/config/WATCH_QUEUE) \
  /source/include/linux/ratelimit.h \
  /source/include/linux/posix-timers.h \
  /source/include/linux/alarmtimer.h \
    $(wildcard include/config/RTC_CLASS) \
  /source/include/linux/hrtimer.h \
    $(wildcard include/config/HIGH_RES_TIMERS) \
    $(wildcard include/config/TIME_LOW_RES) \
    $(wildcard include/config/TIMERFD) \
  /source/include/linux/hrtimer_defs.h \
  /source/include/linux/timerqueue.h \
  /source/include/linux/rcuref.h \
  /source/include/linux/rcu_sync.h \
  /source/include/linux/delayed_call.h \
  /source/include/linux/uuid.h \
  /source/include/linux/errseq.h \
  /source/include/linux/ioprio.h \
  /source/include/linux/sched/rt.h \
  /source/include/linux/iocontext.h \
    $(wildcard include/config/BLK_ICQ) \
  /source/include/uapi/linux/ioprio.h \
  /source/include/linux/fs_types.h \
  /source/include/linux/mount.h \
  /source/include/linux/mnt_idmapping.h \
  /source/include/linux/slab.h \
    $(wildcard include/config/FAILSLAB) \
    $(wildcard include/config/KFENCE) \
    $(wildcard include/config/SLUB_TINY) \
    $(wildcard include/config/SLUB_DEBUG) \
    $(wildcard include/config/SLAB_FREELIST_HARDENED) \
    $(wildcard include/config/SLAB_BUCKETS) \
    $(wildcard include/config/KVFREE_RCU_BATCHED) \
  /source/include/linux/percpu-refcount.h \
  /source/include/linux/kasan.h \
    $(wildcard include/config/KASAN_STACK) \
    $(wildcard include/config/KASAN_VMALLOC) \
  /source/include/linux/kasan-enabled.h \
  /source/include/linux/kasan-tags.h \
  /source/include/linux/rw_hint.h \
  /source/include/linux/file_ref.h \
  /source/include/uapi/linux/fs.h \
  /source/include/linux/quota.h \
    $(wildcard include/config/QUOTA_NETLINK_INTERFACE) \
  /source/include/uapi/linux/dqblk_xfs.h \
  /source/include/linux/dqblk_v1.h \
  /source/include/linux/dqblk_v2.h \
  /source/include/linux/dqblk_qtree.h \
  /source/include/linux/projid.h \
  /source/include/uapi/linux/quota.h \
  /source/include/uapi/linux/aio_abi.h \
  /source/include/uapi/linux/unistd.h \
  /source/arch/x86/include/asm/unistd.h \
  /source/arch/x86/include/uapi/asm/unistd.h \
  arch/x86/include/generated/uapi/asm/unistd_64.h \
  arch/x86/include/generated/asm/unistd_64_x32.h \
  arch/x86/include/generated/asm/unistd_32_ia32.h \
  /source/arch/x86/include/asm/compat.h \
  /source/include/linux/sched/task_stack.h \
    $(wildcard include/config/DEBUG_STACK_USAGE) \
  /source/include/uapi/linux/magic.h \
  /source/arch/x86/include/asm/user32.h \
  /source/include/asm-generic/compat.h \
    $(wildcard include/config/COMPAT_FOR_U64_ALIGNMENT) \
  /source/arch/x86/include/asm/syscall_wrapper.h \
  /source/arch/x86/include/asm/user.h \
  /source/arch/x86/include/asm/user_64.h \
  /source/arch/x86/include/asm/fsgsbase.h \
  /source/arch/x86/include/asm/vdso.h \
  /source/include/uapi/linux/elf.h \
  /source/include/uapi/linux/elf-em.h \
  /source/include/linux/kobject.h \
    $(wildcard include/config/UEVENT_HELPER) \
    $(wildcard include/config/DEBUG_KOBJECT_RELEASE) \
  /source/include/linux/sysfs.h \
  /source/include/linux/kernfs.h \
    $(wildcard include/config/KERNFS) \
  /source/include/linux/idr.h \
  /source/include/linux/kobject_ns.h \
  /source/include/linux/moduleparam.h \
    $(wildcard include/config/ALPHA) \
    $(wildcard include/config/PPC64) \
  /source/include/linux/rbtree_latch.h \
  /source/include/linux/error-injection.h \
  /source/include/asm-generic/error-injection.h \
  /source/arch/x86/include/asm/module.h \
    $(wildcard include/config/UNWINDER_ORC) \
  /source/include/asm-generic/module.h \
    $(wildcard include/config/HAVE_MOD_ARCH_SPECIFIC) \
    $(wildcard include/config/MODULES_USE_ELF_REL) \
    $(wildcard include/config/MODULES_USE_ELF_RELA) \
  /source/include/linux/export-internal.h \
    $(wildcard include/config/PARISC) \

drivers/misc/mckernel/mcctrl.mod.o: $(deps_drivers/misc/mckernel/mcctrl.mod.o)

$(deps_drivers/misc/mckernel/mcctrl.mod.o):
