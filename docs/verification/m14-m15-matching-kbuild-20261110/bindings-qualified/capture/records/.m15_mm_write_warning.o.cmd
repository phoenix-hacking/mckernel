savedcmd_drivers/misc/mckernel/m15_mm_write_warning.o := clang -Wp,-MMD,drivers/misc/mckernel/.m15_mm_write_warning.o.d -nostdinc -I/source/arch/x86/include -I./arch/x86/include/generated -I/source/include -I./include -I/source/arch/x86/include/uapi -I./arch/x86/include/generated/uapi -I/source/include/uapi -I./include/generated/uapi -include /source/include/linux/compiler-version.h -include /source/include/linux/kconfig.h -D__KERNEL__ --target=x86_64-linux-gnu -fintegrated-as -Werror=unknown-warning-option -Werror=ignored-optimization-argument -Werror=option-ignored -Werror=unused-command-line-argument -fmacro-prefix-map=/source/= -Werror -D__ASSEMBLY__ -fno-PIE -m64 -DCC_USING_NOP_MCOUNT -DCC_USING_FENTRY -g -I/source/drivers/misc/mckernel -Idrivers/misc/mckernel  -DMODULE  -DKBUILD_MODNAME='"mcctrl"' -D__KBUILD_MODNAME=mcctrl -c -o drivers/misc/mckernel/m15_mm_write_warning.o /source/drivers/misc/mckernel/m15_mm_write_warning.S 

source_drivers/misc/mckernel/m15_mm_write_warning.o := /source/drivers/misc/mckernel/m15_mm_write_warning.S

deps_drivers/misc/mckernel/m15_mm_write_warning.o := \
    $(wildcard include/config/X86_64) \
    $(wildcard include/config/OBJTOOL) \
    $(wildcard include/config/GENERIC_BUG) \
    $(wildcard include/config/GENERIC_BUG_RELATIVE_POINTERS) \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
    $(wildcard include/config/BUG) \
    $(wildcard include/config/LOCKDEP) \
    $(wildcard include/config/PREEMPT_RT) \
    $(wildcard include/config/NOINSTR_VALIDATION) \
  /source/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /source/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /source/include/linux/linkage.h \
    $(wildcard include/config/FUNCTION_ALIGNMENT) \
    $(wildcard include/config/ARCH_USE_SYM_ANNOTATIONS) \
  /source/include/linux/compiler_types.h \
    $(wildcard include/config/DEBUG_INFO_BTF) \
    $(wildcard include/config/PAHOLE_HAS_BTF_TAG) \
    $(wildcard include/config/CC_HAS_SANE_FUNCTION_ALIGNMENT) \
    $(wildcard include/config/ARM64) \
    $(wildcard include/config/LD_DEAD_CODE_DATA_ELIMINATION) \
    $(wildcard include/config/LTO_CLANG) \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/CC_HAS_MULTIDIMENSIONAL_NONSTRING) \
    $(wildcard include/config/UBSAN_SIGNED_WRAP) \
    $(wildcard include/config/ARCH_USES_CFI_GENERIC_LLVM_PASS) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /source/include/linux/stringify.h \
  /source/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/64BIT) \
  /source/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
  arch/x86/include/generated/asm/rwonce.h \
  /source/include/asm-generic/rwonce.h \
  /source/arch/x86/include/asm/linkage.h \
    $(wildcard include/config/X86_32) \
    $(wildcard include/config/CALL_PADDING) \
    $(wildcard include/config/MITIGATION_RETHUNK) \
    $(wildcard include/config/MITIGATION_RETPOLINE) \
    $(wildcard include/config/MITIGATION_SLS) \
    $(wildcard include/config/FUNCTION_PADDING_BYTES) \
    $(wildcard include/config/UML) \
  /source/arch/x86/include/asm/ibt.h \
    $(wildcard include/config/X86_KERNEL_IBT) \
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
  /source/include/linux/annotate.h \
  /source/include/linux/objtool_types.h \

drivers/misc/mckernel/m15_mm_write_warning.o: $(deps_drivers/misc/mckernel/m15_mm_write_warning.o)

$(deps_drivers/misc/mckernel/m15_mm_write_warning.o):
