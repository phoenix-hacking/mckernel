savedcmd_/candidate/modules/ihk-smp-x86_64.mod.o := clang -Wp,-MMD,/candidate/modules/.ihk-smp-x86_64.mod.o.d -nostdinc -I/out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include -I./arch/x86/include/generated -I/out/source/linux-6.12.0-211.44.1.el10_2/include -I./include -I/out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi -I./arch/x86/include/generated/uapi -I/out/source/linux-6.12.0-211.44.1.el10_2/include/uapi -I./include/generated/uapi -include /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/compiler-version.h -include /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kconfig.h -include /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/compiler_types.h -D__KERNEL__ --target=x86_64-linux-gnu -fintegrated-as -Werror=unknown-warning-option -Werror=ignored-optimization-argument -Werror=option-ignored -Werror=unused-command-line-argument -fmacro-prefix-map=/out/source/linux-6.12.0-211.44.1.el10_2/= -std=gnu11 -fshort-wchar -funsigned-char -fno-common -fno-PIE -fno-strict-aliasing -mno-sse -mno-mmx -mno-sse2 -mno-3dnow -mno-avx -fcf-protection=branch -fno-jump-tables -m64 -falign-loops=1 -mno-80387 -mno-fp-ret-in-387 -mstack-alignment=8 -mskip-rax-setup -mtune=generic -mno-red-zone -mcmodel=kernel -Wno-sign-compare -fno-asynchronous-unwind-tables -mretpoline-external-thunk -mindirect-branch-cs-prefix -mfunction-return=thunk-extern -mharden-sls=all -fpatchable-function-entry=16,16 -fno-delete-null-pointer-checks -O2 -fstack-protector-strong -ftrivial-auto-var-init=zero -fno-stack-clash-protection -pg -mfentry -DCC_USING_NOP_MCOUNT -DCC_USING_FENTRY -falign-functions=16 -fstrict-flex-arrays=3 -fno-strict-overflow -fno-stack-check -Wall -Wextra -Wundef -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Werror=strict-prototypes -Wno-format-security -Wno-trigraphs -Wno-frame-address -Wno-address-of-packed-member -Wmissing-declarations -Wmissing-prototypes -Wframe-larger-than=2048 -Wno-gnu -Wno-default-const-init-unsafe -Wvla -Wno-pointer-sign -Wcast-function-type -Wno-unterminated-string-initialization -Wimplicit-fallthrough -Werror=date-time -Werror=incompatible-pointer-types -Wenum-conversion -Wunused -Wno-unused-but-set-variable -Wno-unused-const-variable -Wno-format-overflow -Wno-format-overflow-non-kprintf -Wno-format-truncation-non-kprintf -Wno-override-init -Wno-pointer-to-enum-cast -Wno-tautological-constant-out-of-range-compare -Wno-unaligned-access -Wno-enum-compare-conditional -Wno-enum-enum-conversion -Wno-missing-field-initializers -Wno-type-limits -Wno-shift-negative-value -Wno-sign-compare -Wno-unused-parameter -g -DMODULE -DKBUILD_BASENAME='"ihk_smp_x86_64.mod"' -DKBUILD_MODNAME='"ihk_smp_x86_64"' -D__KBUILD_MODNAME=ihk_smp_x86_64 -c -o /candidate/modules/ihk-smp-x86_64.mod.o /candidate/modules/ihk-smp-x86_64.mod.c

source_/candidate/modules/ihk-smp-x86_64.mod.o := /candidate/modules/ihk-smp-x86_64.mod.c

deps_/candidate/modules/ihk-smp-x86_64.mod.o := \
    $(wildcard include/config/MODULE_UNLOAD) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/compiler_types.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/compiler_attributes.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/compiler-clang.h \
    $(wildcard include/config/ARCH_USE_BUILTIN_BSWAP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/module.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/list.h \
    $(wildcard include/config/LIST_HARDENED) \
    $(wildcard include/config/DEBUG_LIST) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/container_of.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/build_bug.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/OBJTOOL) \
    $(wildcard include/config/64BIT) \
  arch/x86/include/generated/asm/rwonce.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/rwonce.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kasan-checks.h \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KASAN_SW_TAGS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/types.h \
  arch/x86/include/generated/uapi/asm/types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/int-ll64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/int-ll64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/bitsperlong.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitsperlong.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/bitsperlong.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/posix_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/stddef.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/stddef.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/posix_types.h \
    $(wildcard include/config/X86_32) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/posix_types_64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/posix_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kcsan-checks.h \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/KCSAN_WEAK_MEMORY) \
    $(wildcard include/config/KCSAN_IGNORE_ATOMICS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/poison.h \
    $(wildcard include/config/ILLEGAL_POINTER_VALUE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/const.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/const.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/const.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/barrier.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/alternative.h \
    $(wildcard include/config/CALL_THUNKS) \
    $(wildcard include/config/MITIGATION_ITS) \
    $(wildcard include/config/MITIGATION_RETHUNK) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/stringify.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/objtool.h \
    $(wildcard include/config/FRAME_POINTER) \
    $(wildcard include/config/NOINSTR_VALIDATION) \
    $(wildcard include/config/MITIGATION_UNRET_ENTRY) \
    $(wildcard include/config/MITIGATION_SRSO) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/objtool_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/annotate.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/asm.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/extable_fixup_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/nops.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/barrier.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/stat.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/stat.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/stat.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/time.h \
    $(wildcard include/config/POSIX_TIMERS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/cache.h \
    $(wildcard include/config/ARCH_HAS_CACHE_LINE_SIZE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/kernel.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/sysinfo.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/cache.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/cache.h \
    $(wildcard include/config/X86_L1_CACHE_SHIFT) \
    $(wildcard include/config/X86_INTERNODE_CACHE_SHIFT) \
    $(wildcard include/config/X86_VSMP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/linkage.h \
    $(wildcard include/config/ARCH_USE_SYM_ANNOTATIONS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/linkage.h \
    $(wildcard include/config/CALL_PADDING) \
    $(wildcard include/config/MITIGATION_SLS) \
    $(wildcard include/config/FUNCTION_PADDING_BYTES) \
    $(wildcard include/config/UML) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/ibt.h \
    $(wildcard include/config/X86_KERNEL_IBT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/math64.h \
    $(wildcard include/config/ARCH_SUPPORTS_INT128) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/math.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/div64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/div64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/math64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/time64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/time64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/time.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/time_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/time32.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/timex.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/timex.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/param.h \
  arch/x86/include/generated/uapi/asm/param.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/param.h \
    $(wildcard include/config/HZ) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/param.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/timex.h \
    $(wildcard include/config/X86_TSC) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/processor.h \
    $(wildcard include/config/X86_VMX_FEATURE_NAMES) \
    $(wildcard include/config/X86_IOPL_IOPERM) \
    $(wildcard include/config/STACKPROTECTOR) \
    $(wildcard include/config/VM86) \
    $(wildcard include/config/X86_USER_SHADOW_STACK) \
    $(wildcard include/config/USE_X86_SEG_SUPPORT) \
    $(wildcard include/config/PARAVIRT_XXL) \
    $(wildcard include/config/CPU_SUP_AMD) \
    $(wildcard include/config/XEN) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/processor-flags.h \
    $(wildcard include/config/MITIGATION_PAGE_TABLE_ISOLATION) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/processor-flags.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mem_encrypt.h \
    $(wildcard include/config/ARCH_HAS_MEM_ENCRYPT) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/mem_encrypt.h \
    $(wildcard include/config/X86_MEM_ENCRYPT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/init.h \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/cc_platform.h \
    $(wildcard include/config/ARCH_HAS_CC_PLATFORM) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/math_emu.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/ptrace.h \
    $(wildcard include/config/PARAVIRT) \
    $(wildcard include/config/IA32_EMULATION) \
    $(wildcard include/config/X86_DEBUGCTLMSR) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/segment.h \
    $(wildcard include/config/XEN_PV) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/page_types.h \
    $(wildcard include/config/PHYSICAL_START) \
    $(wildcard include/config/PHYSICAL_ALIGN) \
    $(wildcard include/config/DYNAMIC_PHYSICAL_MASK) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/page.h \
    $(wildcard include/config/PAGE_SHIFT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/page_64_types.h \
    $(wildcard include/config/KASAN) \
    $(wildcard include/config/DYNAMIC_MEMORY_LAYOUT) \
    $(wildcard include/config/X86_5LEVEL) \
    $(wildcard include/config/RANDOMIZE_BASE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/kaslr.h \
    $(wildcard include/config/RANDOMIZE_MEMORY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/ptrace.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/ptrace-abi.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/paravirt_types.h \
    $(wildcard include/config/PGTABLE_LEVELS) \
    $(wildcard include/config/ZERO_CALL_USED_REGS) \
    $(wildcard include/config/PARAVIRT_DEBUG) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/desc_defs.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/pgtable_types.h \
    $(wildcard include/config/X86_INTEL_MEMORY_PROTECTION_KEYS) \
    $(wildcard include/config/X86_PAE) \
    $(wildcard include/config/MEM_SOFT_DIRTY) \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_WP) \
    $(wildcard include/config/PROC_FS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/pgtable_64_types.h \
    $(wildcard include/config/KMSAN) \
    $(wildcard include/config/DEBUG_KMAP_LOCAL_FORCE_MAP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/sparsemem.h \
    $(wildcard include/config/SPARSEMEM) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/nospec-branch.h \
    $(wildcard include/config/CALL_THUNKS_DEBUG) \
    $(wildcard include/config/MITIGATION_CALL_DEPTH_TRACKING) \
    $(wildcard include/config/MITIGATION_IBPB_ENTRY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/static_key.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/jump_label.h \
    $(wildcard include/config/HAVE_ARCH_JUMP_LABEL_RELATIVE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/jump_label.h \
    $(wildcard include/config/HAVE_JUMP_LABEL_HACK) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/cpufeatures.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/required-features.h \
    $(wildcard include/config/X86_MINIMUM_CPU_FAMILY) \
    $(wildcard include/config/MATH_EMULATION) \
    $(wildcard include/config/X86_CMPXCHG64) \
    $(wildcard include/config/X86_CMOV) \
    $(wildcard include/config/X86_P6_NOP) \
    $(wildcard include/config/MATOM) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/disabled-features.h \
    $(wildcard include/config/X86_UMIP) \
    $(wildcard include/config/ADDRESS_MASKING) \
    $(wildcard include/config/INTEL_IOMMU_SVM) \
    $(wildcard include/config/X86_SGX) \
    $(wildcard include/config/INTEL_TDX_GUEST) \
    $(wildcard include/config/X86_FRED) \
    $(wildcard include/config/KVM_AMD_SEV) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/msr-index.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/bits.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/bits.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/bits.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/overflow.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/limits.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/limits.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/limits.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/unwind_hints.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/orc_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/byteorder.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/byteorder/little_endian.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/byteorder/little_endian.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/swab.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/swab.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/swab.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/byteorder/generic.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/percpu.h \
    $(wildcard include/config/X86_64_SMP) \
    $(wildcard include/config/CC_HAS_NAMED_AS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/percpu.h \
    $(wildcard include/config/DEBUG_PREEMPT) \
    $(wildcard include/config/HAVE_SETUP_PER_CPU_AREA) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/threads.h \
    $(wildcard include/config/NR_CPUS) \
    $(wildcard include/config/BASE_SMALL) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/percpu-defs.h \
    $(wildcard include/config/DEBUG_FORCE_WEAK_PER_CPU) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/current.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/asm-offsets.h \
  include/generated/asm-offsets.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/GEN-for-each-reg.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/spinlock_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/qspinlock_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/qrwlock_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/proto.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/ldt.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/sigcontext.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/cpuid.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/string.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/string_64.h \
    $(wildcard include/config/ARCH_HAS_UACCESS_FLUSHCACHE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/page.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/page_64.h \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/X86_VSYSCALL_EMULATION) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kmsan-checks.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/range.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/memory_model.h \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/pfn.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/getorder.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/log2.h \
    $(wildcard include/config/ARCH_HAS_ILOG2_U32) \
    $(wildcard include/config/ARCH_HAS_ILOG2_U64) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/bitops.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/typecheck.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitops/generic-non-atomic.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/bitops.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/rmwcc.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/args.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitops/sched.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/arch_hweight.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitops/const_hweight.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitops/instrumented-atomic.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/instrumented.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitops/instrumented-non-atomic.h \
    $(wildcard include/config/KCSAN_ASSUME_PLAIN_WRITES_ATOMIC) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitops/instrumented-lock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitops/le.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bitops/ext2-atomic-setbit.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/special_insns.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/errno.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/errno.h \
  arch/x86/include/generated/uapi/asm/errno.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/errno.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/errno-base.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/irqflags.h \
    $(wildcard include/config/PROVE_LOCKING) \
    $(wildcard include/config/TRACE_IRQFLAGS) \
    $(wildcard include/config/PREEMPT_RT) \
    $(wildcard include/config/IRQSOFF_TRACER) \
    $(wildcard include/config/PREEMPT_TRACER) \
    $(wildcard include/config/DEBUG_IRQFLAGS) \
    $(wildcard include/config/TRACE_IRQFLAGS_SUPPORT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/irqflags_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/cleanup.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/irqflags.h \
    $(wildcard include/config/DEBUG_ENTRY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/fpu/types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/vmxfeatures.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/vdso/processor.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/shstk.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/personality.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/personality.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/err.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/tsc.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/cpufeature.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/msr.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/cpumask.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/cpumask.h \
    $(wildcard include/config/FORCE_NR_CPUS) \
    $(wildcard include/config/HOTPLUG_CPU) \
    $(wildcard include/config/DEBUG_PER_CPU_MAPS) \
    $(wildcard include/config/CPUMASK_OFFSTACK) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kernel.h \
    $(wildcard include/config/PREEMPT_VOLUNTARY_BUILD) \
    $(wildcard include/config/PREEMPT_DYNAMIC) \
    $(wildcard include/config/HAVE_PREEMPT_DYNAMIC_CALL) \
    $(wildcard include/config/HAVE_PREEMPT_DYNAMIC_KEY) \
    $(wildcard include/config/PREEMPT_) \
    $(wildcard include/config/DEBUG_ATOMIC_SLEEP) \
    $(wildcard include/config/MMU) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/stdarg.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/align.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/align.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/array_size.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/hex.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kstrtox.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/minmax.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/panic.h \
    $(wildcard include/config/PANIC_TIMEOUT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/printk.h \
    $(wildcard include/config/MESSAGE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_QUIET) \
    $(wildcard include/config/EARLY_PRINTK) \
    $(wildcard include/config/PRINTK) \
    $(wildcard include/config/DYNAMIC_DEBUG) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kern_levels.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/ratelimit_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/spinlock_types_raw.h \
    $(wildcard include/config/DEBUG_SPINLOCK) \
    $(wildcard include/config/DEBUG_LOCK_ALLOC) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/lockdep_types.h \
    $(wildcard include/config/PROVE_RAW_LOCK_NESTING) \
    $(wildcard include/config/LOCKDEP) \
    $(wildcard include/config/LOCK_STAT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/once_lite.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/dynamic_debug.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sprintf.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/static_call_types.h \
    $(wildcard include/config/HAVE_STATIC_CALL) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/instruction_pointer.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/wordpart.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/bitmap.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/find.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/string.h \
    $(wildcard include/config/BINARY_PRINTF) \
    $(wildcard include/config/FORTIFY_SOURCE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/string.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/fortify-string.h \
    $(wildcard include/config/CC_HAS_KASAN_MEMINTRINSIC_PREFIX) \
    $(wildcard include/config/GENERIC_ENTRY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/bitfield.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/bug.h \
    $(wildcard include/config/BUG_ON_DATA_CORRUPTION) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/bug.h \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/instrumentation.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/bug.h \
    $(wildcard include/config/BUG) \
    $(wildcard include/config/GENERIC_BUG_RELATIVE_POINTERS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/bitmap-str.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/cpumask_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/atomic.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/atomic.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/cmpxchg.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/cmpxchg_64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/atomic64_64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/atomic/atomic-arch-fallback.h \
    $(wildcard include/config/GENERIC_ATOMIC64) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/atomic/atomic-long.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/atomic/atomic-instrumented.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/gfp_types.h \
    $(wildcard include/config/KASAN_HW_TAGS) \
    $(wildcard include/config/SLAB_OBJ_EXT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/numa.h \
    $(wildcard include/config/NUMA_KEEP_MEMINFO) \
    $(wildcard include/config/NUMA) \
    $(wildcard include/config/HAVE_ARCH_NODE_DEV_GROUP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/nodemask.h \
    $(wildcard include/config/HIGHMEM) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/nodemask_types.h \
    $(wildcard include/config/NODES_SHIFT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/random.h \
    $(wildcard include/config/VMGENID) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/random.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/ioctl.h \
  arch/x86/include/generated/uapi/asm/ioctl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/ioctl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/ioctl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/irqnr.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/irqnr.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/prandom.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/once.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/msr.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/shared/msr.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/percpu.h \
    $(wildcard include/config/RANDOM_KMALLOC_CACHES) \
    $(wildcard include/config/PAGE_SIZE_4KB) \
    $(wildcard include/config/NEED_PER_CPU_PAGE_FIRST_CHUNK) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/alloc_tag.h \
    $(wildcard include/config/MEM_ALLOC_PROFILING_DEBUG) \
    $(wildcard include/config/MEM_ALLOC_PROFILING) \
    $(wildcard include/config/MEM_ALLOC_PROFILING_ENABLED_BY_DEFAULT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/codetag.h \
    $(wildcard include/config/CODE_TAGGING) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/preempt.h \
    $(wildcard include/config/PREEMPT_COUNT) \
    $(wildcard include/config/TRACE_PREEMPT_TOGGLE) \
    $(wildcard include/config/PREEMPTION) \
    $(wildcard include/config/PREEMPT_NOTIFIERS) \
    $(wildcard include/config/PREEMPT_NONE) \
    $(wildcard include/config/PREEMPT_VOLUNTARY) \
    $(wildcard include/config/PREEMPT) \
    $(wildcard include/config/PREEMPT_LAZY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/preempt.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/smp.h \
    $(wildcard include/config/UP_LATE_INIT) \
    $(wildcard include/config/CSD_LOCK_WAIT_DEBUG) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/smp_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/llist.h \
    $(wildcard include/config/ARCH_HAVE_NMI_SAFE_CMPXCHG) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/thread_info.h \
    $(wildcard include/config/THREAD_INFO_IN_TASK) \
    $(wildcard include/config/ARCH_HAS_PREEMPT_LAZY) \
    $(wildcard include/config/HAVE_ARCH_WITHIN_STACK_FRAMES) \
    $(wildcard include/config/HARDENED_USERCOPY) \
    $(wildcard include/config/SH) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/restart_block.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/thread_info.h \
    $(wildcard include/config/COMPAT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/smp.h \
    $(wildcard include/config/DEBUG_NMI_SELFTEST) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mmdebug.h \
    $(wildcard include/config/DEBUG_VM) \
    $(wildcard include/config/DEBUG_VM_IRQSOFF) \
    $(wildcard include/config/DEBUG_VM_PGFLAGS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/sched.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rh_kabi.h \
    $(wildcard include/config/RH_KABI_SIZE_ALIGN_CHECKS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/pid_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sem_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/shm.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/shmparam.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kmsan_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mutex_types.h \
    $(wildcard include/config/MUTEX_SPIN_ON_OWNER) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/osq_lock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/spinlock_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rwlock_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/plist_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/hrtimer_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/timerqueue_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rbtree_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/timer_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/seccomp_types.h \
    $(wildcard include/config/SECCOMP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/refcount_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/resource.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/resource.h \
  arch/x86/include/generated/uapi/asm/resource.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/resource.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/resource.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/latencytop.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/prio.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/signal_types.h \
    $(wildcard include/config/OLD_SIGACTION) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/signal.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/signal.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/signal.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/signal-defs.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/siginfo.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/siginfo.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/syscall_user_dispatch_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mm_types_task.h \
    $(wildcard include/config/ARCH_WANT_BATCHED_UNMAP_TLB_FLUSH) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/tlbbatch.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/netdevice_xmit.h \
    $(wildcard include/config/NET_EGRESS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/task_io_accounting.h \
    $(wildcard include/config/TASK_IO_ACCOUNTING) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/posix-timers_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/rseq.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/seqlock_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kcsan.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rv.h \
    $(wildcard include/config/RV_LTL_MONITOR) \
    $(wildcard include/config/RV_REACTORS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/uidgid_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/tracepoint-defs.h \
  arch/x86/include/generated/asm/kmap_size.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/kmap_size.h \
    $(wildcard include/config/DEBUG_KMAP_LOCAL) \
  include/generated/rq-offsets.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/ext.h \
    $(wildcard include/config/EXT_GROUP_SCHED) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rhashtable-types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mutex.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/lockdep.h \
    $(wildcard include/config/DEBUG_LOCKING_API_SELFTESTS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/debug_locks.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/workqueue_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/spinlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/bottom_half.h \
  arch/x86/include/generated/asm/mmiowb.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/mmiowb.h \
    $(wildcard include/config/MMIOWB) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/spinlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/paravirt.h \
    $(wildcard include/config/PARAVIRT_SPINLOCKS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/frame.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/qspinlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/qspinlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/qrwlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/qrwlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rwlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/spinlock_api_smp.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rwlock_api_smp.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/time32.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/time.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/uidgid.h \
    $(wildcard include/config/MULTIUSER) \
    $(wildcard include/config/USER_NS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/highuid.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/buildid.h \
    $(wildcard include/config/VMCORE_INFO) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kmod.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/umh.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/gfp.h \
    $(wildcard include/config/ZONE_DMA) \
    $(wildcard include/config/ZONE_DMA32) \
    $(wildcard include/config/ZONE_DEVICE) \
    $(wildcard include/config/CONTIG_ALLOC) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mmzone.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/list_nulls.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/wait.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/seqlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/pageblock-flags.h \
    $(wildcard include/config/HUGETLB_PAGE_SIZE_VARIABLE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/page-flags-layout.h \
  include/generated/bounds.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mm_types.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/auxvec.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/auxvec.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/auxvec.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kref.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/refcount.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rbtree.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rcupdate.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/context_tracking_irq.h \
    $(wildcard include/config/CONTEXT_TRACKING_IDLE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rcutree.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/maple_tree.h \
    $(wildcard include/config/MAPLE_RCU_DISABLED) \
    $(wildcard include/config/DEBUG_MAPLE_TREE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rwsem.h \
    $(wildcard include/config/RWSEM_SPIN_ON_OWNER) \
    $(wildcard include/config/DEBUG_RWSEMS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/completion.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/swait.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/uprobes.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/uprobes.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/notifier.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/srcu.h \
    $(wildcard include/config/TINY_SRCU) \
    $(wildcard include/config/NEED_SRCU_NMI_SAFE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/workqueue.h \
    $(wildcard include/config/DEBUG_OBJECTS_WORK) \
    $(wildcard include/config/FREEZER) \
    $(wildcard include/config/WQ_WATCHDOG) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/timer.h \
    $(wildcard include/config/DEBUG_OBJECTS_TIMERS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/ktime.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/jiffies.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/jiffies.h \
  include/generated/timeconst.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/vdso/ktime.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/timekeeping.h \
    $(wildcard include/config/GENERIC_CMOS_UPDATE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/clocksource_ids.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/debugobjects.h \
    $(wildcard include/config/DEBUG_OBJECTS) \
    $(wildcard include/config/DEBUG_OBJECTS_FREE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rcu_segcblist.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/srcutree.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rcu_node_tree.h \
    $(wildcard include/config/RCU_FANOUT) \
    $(wildcard include/config/RCU_FANOUT_LEAF) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/percpu_counter.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/mmu.h \
    $(wildcard include/config/MODIFY_LDT_SYSCALL) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/page-flags.h \
    $(wildcard include/config/PAGE_IDLE_FLAG) \
    $(wildcard include/config/ARCH_USES_PG_ARCH_2) \
    $(wildcard include/config/ARCH_USES_PG_ARCH_3) \
    $(wildcard include/config/HUGETLB_PAGE_OPTIMIZE_VMEMMAP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/local_lock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/local_lock_internal.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/zswap.h \
    $(wildcard include/config/ZSWAP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/memory_hotplug.h \
    $(wildcard include/config/ARCH_HAS_ADD_PAGES) \
    $(wildcard include/config/MEMORY_HOTREMOVE) \
  arch/x86/include/generated/asm/mmzone.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/mmzone.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/topology.h \
    $(wildcard include/config/USE_PERCPU_NUMA_NODE_ID) \
    $(wildcard include/config/SCHED_SMT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/arch_topology.h \
    $(wildcard include/config/GENERIC_ARCH_TOPOLOGY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/topology.h \
    $(wildcard include/config/X86_LOCAL_APIC) \
    $(wildcard include/config/SCHED_MC_PRIO) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/mpspec.h \
    $(wildcard include/config/EISA) \
    $(wildcard include/config/X86_MPPARSE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/mpspec_def.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/x86_init.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/apicdef.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/topology.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/cpu_smt.h \
    $(wildcard include/config/HOTPLUG_SMT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sysctl.h \
    $(wildcard include/config/SYSCTL) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/sysctl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/elf.h \
    $(wildcard include/config/ARCH_HAVE_EXTRA_ELF_NOTES) \
    $(wildcard include/config/ARCH_USE_GNU_PROPERTY) \
    $(wildcard include/config/ARCH_HAVE_ELF_PROT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/elf.h \
    $(wildcard include/config/X86_X32_ABI) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/ia32.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/compat.h \
    $(wildcard include/config/ARCH_HAS_SYSCALL_WRAPPER) \
    $(wildcard include/config/COMPAT_OLD_SIGACTION) \
    $(wildcard include/config/ODD_RT_SIGACTION) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sem.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/sem.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/ipc.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/ipc.h \
  arch/x86/include/generated/uapi/asm/ipcbuf.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/ipcbuf.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/sembuf.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/socket.h \
  arch/x86/include/generated/uapi/asm/socket.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/socket.h \
  arch/x86/include/generated/uapi/asm/sockios.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/sockios.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/sockios.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/uio.h \
    $(wildcard include/config/ARCH_HAS_COPY_MC) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/uio.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/socket.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/if.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/libc-compat.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/hdlc/ioctl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/fs.h \
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
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/wait_bit.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kdev_t.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/kdev_t.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/dcache.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rculist.h \
    $(wildcard include/config/PROVE_RCU_LIST) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rculist_bl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/list_bl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/bit_spinlock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/lockref.h \
    $(wildcard include/config/ARCH_USE_CMPXCHG_LOCKREF) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/stringhash.h \
    $(wildcard include/config/DCACHE_WORD_ACCESS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/hash.h \
    $(wildcard include/config/HAVE_ARCH_HASH) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/path.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/list_lru.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/shrinker.h \
    $(wildcard include/config/SHRINKER_DEBUG) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/xarray.h \
    $(wildcard include/config/XARRAY_MULTI) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/mm.h \
    $(wildcard include/config/MMU_LAZY_TLB_REFCOUNT) \
    $(wildcard include/config/ARCH_HAS_MEMBARRIER_CALLBACKS) \
    $(wildcard include/config/ARCH_HAS_SYNC_CORE_BEFORE_USERMODE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sync_core.h \
    $(wildcard include/config/ARCH_HAS_PREPARE_SYNC_CORE_CMD) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/sync_core.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/coredump.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/radix-tree.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/pid.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/capability.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/capability.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/semaphore.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/fcntl.h \
    $(wildcard include/config/ARCH_32BIT_OFF_T) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/fcntl.h \
  arch/x86/include/generated/uapi/asm/fcntl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/asm-generic/fcntl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/openat2.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/migrate_mode.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/percpu-rwsem.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rcuwait.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/signal.h \
    $(wildcard include/config/SCHED_AUTOGROUP) \
    $(wildcard include/config/BSD_PROCESS_ACCT) \
    $(wildcard include/config/TASKSTATS) \
    $(wildcard include/config/STACK_GROWSUP) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/signal.h \
    $(wildcard include/config/DYNAMIC_SIGFRAME) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/jobctl.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/task.h \
    $(wildcard include/config/HAVE_EXIT_THREAD) \
    $(wildcard include/config/ARCH_WANTS_DYNAMIC_TASK_STRUCT) \
    $(wildcard include/config/HAVE_ARCH_THREAD_STRUCT_WHITELIST) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/uaccess.h \
    $(wildcard include/config/ARCH_HAS_SUBPAGE_FAULTS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/fault-inject-usercopy.h \
    $(wildcard include/config/FAULT_INJECTION_USERCOPY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/nospec.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/uaccess.h \
    $(wildcard include/config/CC_HAS_ASM_GOTO_OUTPUT) \
    $(wildcard include/config/CC_HAS_ASM_GOTO_TIED_OUTPUT) \
    $(wildcard include/config/X86_INTEL_USERCOPY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mmap_lock.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/smap.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/extable.h \
    $(wildcard include/config/BPF_JIT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/tlbflush.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mmu_notifier.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/interval_tree.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/invpcid.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/pti.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/pgtable.h \
    $(wildcard include/config/DEBUG_WX) \
    $(wildcard include/config/HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD) \
    $(wildcard include/config/ARCH_HAS_PTE_DEVMAP) \
    $(wildcard include/config/ARCH_SUPPORTS_PMD_PFNMAP) \
    $(wildcard include/config/ARCH_SUPPORTS_PUD_PFNMAP) \
    $(wildcard include/config/HAVE_ARCH_SOFT_DIRTY) \
    $(wildcard include/config/ARCH_ENABLE_THP_MIGRATION) \
    $(wildcard include/config/PAGE_TABLE_CHECK) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/pkru.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/fpu/api.h \
    $(wildcard include/config/X86_DEBUG_FPU) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/coco.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/pgtable_uffd.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/page_table_check.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/pgtable_64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/fixmap.h \
    $(wildcard include/config/PROVIDE_OHCI1394_DMA_INIT) \
    $(wildcard include/config/X86_IO_APIC) \
    $(wildcard include/config/PCI_MMCONFIG) \
    $(wildcard include/config/ACPI_APEI_GHES) \
    $(wildcard include/config/INTEL_TXT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/vsyscall.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/fixmap.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/pgtable-invert.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/uaccess_64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/runtime-const.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/access_ok.h \
    $(wildcard include/config/ALTERNATE_USER_ADDRESS_SPACE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/cred.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/key.h \
    $(wildcard include/config/KEY_NOTIFICATIONS) \
    $(wildcard include/config/NET) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/assoc_array.h \
    $(wildcard include/config/ASSOCIATIVE_ARRAY) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/user.h \
    $(wildcard include/config/VFIO_PCI_ZDEV_KVM) \
    $(wildcard include/config/IOMMUFD) \
    $(wildcard include/config/WATCH_QUEUE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/ratelimit.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/posix-timers.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/alarmtimer.h \
    $(wildcard include/config/RTC_CLASS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/hrtimer.h \
    $(wildcard include/config/HIGH_RES_TIMERS) \
    $(wildcard include/config/TIME_LOW_RES) \
    $(wildcard include/config/TIMERFD) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/hrtimer_defs.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/timerqueue.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rcuref.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rcu_sync.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/delayed_call.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/uuid.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/errseq.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/ioprio.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/rt.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/iocontext.h \
    $(wildcard include/config/BLK_ICQ) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/ioprio.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/fs_types.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mount.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/mnt_idmapping.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/slab.h \
    $(wildcard include/config/FAILSLAB) \
    $(wildcard include/config/KFENCE) \
    $(wildcard include/config/SLUB_TINY) \
    $(wildcard include/config/SLUB_DEBUG) \
    $(wildcard include/config/SLAB_FREELIST_HARDENED) \
    $(wildcard include/config/SLAB_BUCKETS) \
    $(wildcard include/config/KVFREE_RCU_BATCHED) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/percpu-refcount.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kasan.h \
    $(wildcard include/config/KASAN_STACK) \
    $(wildcard include/config/KASAN_VMALLOC) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kasan-enabled.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kasan-tags.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rw_hint.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/file_ref.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/fs.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/quota.h \
    $(wildcard include/config/QUOTA_NETLINK_INTERFACE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/dqblk_xfs.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/dqblk_v1.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/dqblk_v2.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/dqblk_qtree.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/projid.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/quota.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/aio_abi.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/unistd.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/unistd.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/uapi/asm/unistd.h \
  arch/x86/include/generated/uapi/asm/unistd_64.h \
  arch/x86/include/generated/asm/unistd_64_x32.h \
  arch/x86/include/generated/asm/unistd_32_ia32.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/compat.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sched/task_stack.h \
    $(wildcard include/config/DEBUG_STACK_USAGE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/magic.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/user32.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/compat.h \
    $(wildcard include/config/COMPAT_FOR_U64_ALIGNMENT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/syscall_wrapper.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/user.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/user_64.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/fsgsbase.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/vdso.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/elf.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/uapi/linux/elf-em.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kobject.h \
    $(wildcard include/config/UEVENT_HELPER) \
    $(wildcard include/config/DEBUG_KOBJECT_RELEASE) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/sysfs.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kernfs.h \
    $(wildcard include/config/KERNFS) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/idr.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/kobject_ns.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/moduleparam.h \
    $(wildcard include/config/ALPHA) \
    $(wildcard include/config/PPC64) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/rbtree_latch.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/error-injection.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/error-injection.h \
  /out/source/linux-6.12.0-211.44.1.el10_2/arch/x86/include/asm/module.h \
    $(wildcard include/config/UNWINDER_ORC) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/asm-generic/module.h \
    $(wildcard include/config/HAVE_MOD_ARCH_SPECIFIC) \
    $(wildcard include/config/MODULES_USE_ELF_REL) \
    $(wildcard include/config/MODULES_USE_ELF_RELA) \
  /out/source/linux-6.12.0-211.44.1.el10_2/include/linux/export-internal.h \
    $(wildcard include/config/PARISC) \

/candidate/modules/ihk-smp-x86_64.mod.o: $(deps_/candidate/modules/ihk-smp-x86_64.mod.o)

$(deps_/candidate/modules/ihk-smp-x86_64.mod.o):
