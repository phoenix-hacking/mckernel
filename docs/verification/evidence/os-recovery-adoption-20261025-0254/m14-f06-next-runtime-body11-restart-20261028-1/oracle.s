	.file	"oracle.c"
	.text
.Ltext0:
	.p2align 4
	.globl	fixture_reset
	.type	fixture_reset, @function
fixture_reset:
.LVL0:
.LFB6:
	.file 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
	.loc 1 12 1 view -0
	.cfi_startproc
	.loc 1 12 1 is_stmt 0 view .LVU1
	endbr64
.L4:
	endbr64
	.loc 1 13 5 is_stmt 1 view .LVU2
.LVL1:
	.loc 1 14 5 view .LVU3
.LBB2:
	.loc 1 14 9 view .LVU4
	.loc 1 14 20 view .LVU5
	leaq	.L4(%rip), %rcx
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L4, %r11
	movabsq	$trace@GOTOFF, %rax
	addq	%r11, %rcx
	addq	%rcx, %rax
	leaq	256(%rax), %rdx
.LVL2:
	.p2align 4,,10
	.p2align 3
.L2:
	.loc 1 14 40 discriminator 3 view .LVU6
	.loc 1 14 48 is_stmt 0 discriminator 3 view .LVU7
	movb	$0, (%rax)
	.loc 1 14 36 is_stmt 1 discriminator 3 view .LVU8
.LVL3:
	.loc 1 14 20 discriminator 3 view .LVU9
	addq	$1, %rax
.LVL4:
	.loc 1 14 5 is_stmt 0 discriminator 3 view .LVU10
	cmpq	%rdx, %rax
	jne	.L2
.LBE2:
	.loc 1 15 5 is_stmt 1 view .LVU11
	.loc 1 15 22 is_stmt 0 view .LVU12
	movabsq	$configured_return@GOTOFF, %rax
.LVL5:
	.loc 1 15 22 view .LVU13
	movl	%edi, (%rcx,%rax)
	.loc 1 16 1 view .LVU14
	ret
	.cfi_endproc
.LFE6:
	.size	fixture_reset, .-fixture_reset
	.p2align 4
	.globl	kprintf
	.type	kprintf, @function
kprintf:
.LVL6:
.LFB7:
	.loc 1 18 1 is_stmt 1 view -0
	.cfi_startproc
	.loc 1 18 1 is_stmt 0 view .LVU16
	endbr64
.L18:
	endbr64
	.loc 1 19 5 is_stmt 1 view .LVU17
	.loc 1 18 1 is_stmt 0 view .LVU18
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rdi, %r10
	.loc 1 19 26 view .LVU19
	xorl	%eax, %eax
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L18, %r11
	.loc 1 18 1 view .LVU20
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	.cfi_offset 15, -24
	leaq	.L18(%rip), %r15
	pushq	%rbx
	addq	%r11, %r15
	subq	$96, %rsp
	.cfi_offset 3, -32
	.loc 1 18 1 view .LVU21
	movq	%rsi, -56(%rbp)
	.loc 1 19 16 view .LVU22
	movabsq	$trace@GOTOFF, %rsi
	.loc 1 18 1 view .LVU23
	movq	%rdx, -48(%rbp)
	movq	%rcx, -40(%rbp)
	movq	%r8, -32(%rbp)
	movq	%r9, -24(%rbp)
	.loc 1 19 16 view .LVU24
	addq	$1, (%rsi,%r15)
	.loc 1 19 19 is_stmt 1 view .LVU25
.LVL7:
	.loc 1 19 35 view .LVU26
	.loc 1 19 40 view .LVU27
	.loc 1 19 47 is_stmt 0 view .LVU28
	movzbl	(%rdi), %edx
	.loc 1 19 40 view .LVU29
	testb	%dl, %dl
	je	.L7
	movabsq	$24+trace@GOTOFF, %rcx
	.loc 1 19 88 view .LVU30
	addq	%r15, %rcx
	jmp	.L8
.LVL8:
	.p2align 4,,10
	.p2align 3
.L20:
	.loc 1 19 55 discriminator 3 view .LVU31
	cmpq	$95, %rax
	je	.L7
.LVL9:
.L8:
	.loc 1 19 68 is_stmt 1 discriminator 5 view .LVU32
	.loc 1 19 88 is_stmt 0 discriminator 5 view .LVU33
	movb	%dl, (%rax,%rcx)
	.loc 1 19 104 is_stmt 1 discriminator 5 view .LVU34
	.loc 1 19 110 is_stmt 0 discriminator 5 view .LVU35
	addq	$1, %rax
.LVL10:
	.loc 1 19 40 is_stmt 1 discriminator 5 view .LVU36
	.loc 1 19 47 is_stmt 0 discriminator 5 view .LVU37
	movzbl	(%r10,%rax), %edx
	.loc 1 19 40 discriminator 5 view .LVU38
	testb	%dl, %dl
	jne	.L20
.LVL11:
.L7:
	.loc 1 19 114 is_stmt 1 discriminator 6 view .LVU39
	.loc 1 19 134 is_stmt 0 discriminator 6 view .LVU40
	addq	%r15, %rax
	.loc 1 20 39 discriminator 6 view .LVU41
	movl	$8, -112(%rbp)
	.loc 1 22 27 discriminator 6 view .LVU42
	leaq	-88(%rbp), %rcx
	.loc 1 21 47 discriminator 6 view .LVU43
	movabsq	$trace@GOTOFF, %rbx
	.loc 1 19 134 discriminator 6 view .LVU44
	movb	$0, 24(%rsi,%rax)
	.loc 1 20 5 is_stmt 1 discriminator 6 view .LVU45
	.loc 1 20 39 discriminator 6 view .LVU46
	leaq	16(%rbp), %rax
	.loc 1 21 14 is_stmt 0 discriminator 6 view .LVU47
	movl	-56(%rbp), %edx
	.loc 1 20 39 discriminator 6 view .LVU48
	movq	%rax, -104(%rbp)
	leaq	-64(%rbp), %rax
	movq	%rax, -96(%rbp)
	.loc 1 20 66 is_stmt 1 discriminator 6 view .LVU49
	movq	-112(%rbp), %rax
	.loc 1 21 48 is_stmt 0 discriminator 6 view .LVU50
	movl	$24, -112(%rbp)
	.loc 1 20 66 discriminator 6 view .LVU51
	movq	%rax, -88(%rbp)
	leaq	16(%rbp), %rax
	movq	%rax, -80(%rbp)
	leaq	-64(%rbp), %rax
	movq	%rax, -72(%rbp)
	.loc 1 21 5 is_stmt 1 discriminator 6 view .LVU52
	.loc 1 21 14 is_stmt 0 discriminator 6 view .LVU53
	movl	%edx, 8(%rsi,%r15)
	.loc 1 21 36 is_stmt 1 discriminator 6 view .LVU54
	.loc 1 21 48 is_stmt 0 discriminator 6 view .LVU55
	movq	-48(%rbp), %rax
	.loc 1 22 27 discriminator 6 view .LVU56
	movq	%r10, %rdx
	movl	$128, %esi
	.loc 1 21 47 discriminator 6 view .LVU57
	movq	%rax, 16(%r15,%rbx)
	.loc 1 22 5 is_stmt 1 discriminator 6 view .LVU58
	.loc 1 22 27 is_stmt 0 discriminator 6 view .LVU59
	movabsq	$120+trace@GOTOFF, %rax
	leaq	(%r15,%rax), %rdi
.LVL12:
	.loc 1 22 27 discriminator 6 view .LVU60
	movabsq	$vsnprintf@PLTOFF, %rax
	addq	%r15, %rax
	call	*%rax
.LVL13:
	.loc 1 22 26 discriminator 6 view .LVU61
	movl	%eax, 248(%rbx,%r15)
	.loc 1 23 4 is_stmt 1 discriminator 6 view .LVU62
	.loc 1 23 29 discriminator 6 view .LVU63
	.loc 1 23 47 discriminator 6 view .LVU64
	.loc 1 23 67 is_stmt 0 discriminator 6 view .LVU65
	movabsq	$configured_return@GOTOFF, %rax
	movl	(%r15,%rax), %eax
	movl	%eax, 12(%r15,%rbx)
	.loc 1 23 86 is_stmt 1 discriminator 6 view .LVU66
	.loc 1 24 1 is_stmt 0 discriminator 6 view .LVU67
	addq	$96, %rsp
	popq	%rbx
	.cfi_restore 3
	popq	%r15
	.cfi_restore 15
	popq	%rbp
	.cfi_restore 6
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE7:
	.size	kprintf, .-kprintf
	.p2align 4
	.globl	fixture_read_trace
	.type	fixture_read_trace, @function
fixture_read_trace:
.LVL14:
.LFB8:
	.loc 1 25 51 is_stmt 1 view -0
	.cfi_startproc
	.loc 1 25 51 is_stmt 0 view .LVU69
	endbr64
.L22:
	endbr64
	.loc 1 25 52 is_stmt 1 view .LVU70
	leaq	.L22(%rip), %rsi
	.loc 1 25 56 is_stmt 0 view .LVU71
	movl	$32, %ecx
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L22, %r11
	movabsq	$trace@GOTOFF, %rdx
	addq	%r11, %rsi
	addq	%rdx, %rsi
	rep movsq
.LVL15:
	.loc 1 25 63 view .LVU72
	ret
	.cfi_endproc
.LFE8:
	.size	fixture_read_trace, .-fixture_read_trace
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align 8
.LC0:
	.string	"[%d] arch_prctl: ARCH_SET_FS: 0x%lX\n"
	.text
	.p2align 4
	.globl	original_arch_prctl_log_bridge
	.type	original_arch_prctl_log_bridge, @function
original_arch_prctl_log_bridge:
.LVL16:
.LFB9:
	.file 2 "/src/arch/x86_64/kernel/syscall.c"
	.loc 2 667 1 is_stmt 1 view -0
	.cfi_startproc
	.loc 2 667 1 is_stmt 0 view .LVU74
	endbr64
.L25:
	endbr64
	.loc 2 668 2 is_stmt 1 view .LVU75
	leaq	.L25(%rip), %rcx
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L25, %r11
	addq	%r11, %rcx
	.loc 2 668 5 is_stmt 0 view .LVU76
	cmpl	$4098, %edi
	je	.L26
.L23:
	.loc 2 671 1 view .LVU77
	ret
	.p2align 4,,10
	.p2align 3
.L26:
	.loc 2 669 3 is_stmt 1 view .LVU78
.LBB3:
	.loc 2 669 8 view .LVU79
	.loc 2 669 199 view .LVU80
	.loc 2 669 209 is_stmt 0 view .LVU81
	movabsq	$ddebug.1270@GOTOFF, %rax
	.loc 2 669 202 view .LVU82
	cmpb	$0, 27(%rcx,%rax)
	je	.L23
	.loc 2 669 217 is_stmt 1 discriminator 1 view .LVU83
	movabsq	$.LC0@GOTOFF, %rax
	movabsq	$kprintf@GOTOFF, %r8
	leaq	(%rcx,%rax), %rdi
.LVL17:
	.loc 2 669 217 is_stmt 0 discriminator 1 view .LVU84
	xorl	%eax, %eax
	addq	%r8, %rcx
	jmp	*%rcx
.LVL18:
	.loc 2 669 217 discriminator 1 view .LVU85
.LBE3:
	.cfi_endproc
.LFE9:
	.size	original_arch_prctl_log_bridge, .-original_arch_prctl_log_bridge
	.p2align 4
	.globl	fixture_original_descriptor
	.type	fixture_original_descriptor, @function
fixture_original_descriptor:
.LFB10:
	.loc 2 675 1 is_stmt 1 view -0
	.cfi_startproc
	endbr64
.L34:
	endbr64
	.loc 2 676 5 view .LVU87
.LVL19:
	.loc 2 677 5 view .LVU88
.LBB4:
	.loc 2 677 9 view .LVU89
	leaq	.L34(%rip), %rcx
.LBE4:
	.loc 2 676 20 is_stmt 0 view .LVU90
	xorl	%r8d, %r8d
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L34, %r11
.LBB6:
	.loc 2 677 23 view .LVU91
	movabsq	$__start___verbose@GOT, %rax
	.loc 2 677 72 view .LVU92
	movabsq	$__stop___verbose@GOT, %rdx
	addq	%r11, %rcx
	.loc 2 677 23 view .LVU93
	movq	(%rcx,%rax), %rax
.LVL20:
	.loc 2 677 64 is_stmt 1 view .LVU94
	.loc 2 677 72 is_stmt 0 view .LVU95
	movq	(%rcx,%rdx), %rdx
	.loc 2 677 5 view .LVU96
	cmpq	%rdx, %rax
	jnb	.L27
	movabsq	$mckernel_f06_arch_prctl_debug@GOT, %rsi
.LBB5:
	.loc 2 679 11 view .LVU97
	movq	(%rsi,%rcx), %rcx
.LVL21:
	.p2align 4,,10
	.p2align 3
.L30:
	.loc 2 678 9 is_stmt 1 view .LVU98
	.loc 2 679 9 view .LVU99
	.loc 2 679 11 is_stmt 0 view .LVU100
	cmpq	%rcx, %rax
	je	.L29
	.loc 2 680 9 is_stmt 1 view .LVU101
	.loc 2 680 11 is_stmt 0 view .LVU102
	testq	%r8, %r8
	jne	.L32
	movq	%rax, %r8
.LVL22:
.L29:
	.loc 2 680 11 view .LVU103
.LBE5:
	.loc 2 677 104 is_stmt 1 discriminator 2 view .LVU104
	.loc 2 677 111 is_stmt 0 discriminator 2 view .LVU105
	addq	$32, %rax
.LVL23:
	.loc 2 677 64 is_stmt 1 discriminator 2 view .LVU106
	.loc 2 677 5 is_stmt 0 discriminator 2 view .LVU107
	cmpq	%rdx, %rax
	jb	.L30
.LVL24:
.L27:
	.loc 2 677 5 discriminator 2 view .LVU108
.LBE6:
	.loc 2 683 1 view .LVU109
	movq	%r8, %rax
.LVL25:
	.loc 2 683 1 view .LVU110
	ret
.LVL26:
	.p2align 4,,10
	.p2align 3
.L32:
	.loc 2 676 20 view .LVU111
	xorl	%r8d, %r8d
.LVL27:
	.loc 2 683 1 view .LVU112
	movq	%r8, %rax
.LVL28:
	.loc 2 683 1 view .LVU113
	ret
	.cfi_endproc
.LFE10:
	.size	fixture_original_descriptor, .-fixture_original_descriptor
	.p2align 4
	.globl	fixture_descriptor_count
	.type	fixture_descriptor_count, @function
fixture_descriptor_count:
.LFB11:
	.loc 2 684 38 is_stmt 1 view -0
	.cfi_startproc
	endbr64
.L36:
	endbr64
	.loc 2 684 39 view .LVU115
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L36, %r11
	leaq	.L36(%rip), %rdx
	.loc 2 684 78 is_stmt 0 view .LVU116
	movabsq	$__start___verbose@GOT, %rcx
	movabsq	$__stop___verbose@GOT, %rax
	addq	%r11, %rdx
	movq	(%rdx,%rax), %rax
	subq	(%rcx,%rdx), %rax
	.loc 2 684 112 view .LVU117
	shrq	$5, %rax
	.loc 2 684 135 view .LVU118
	ret
	.cfi_endproc
.LFE11:
	.size	fixture_descriptor_count, .-fixture_descriptor_count
	.p2align 4
	.globl	fixture_set_flags
	.type	fixture_set_flags, @function
fixture_set_flags:
.LVL29:
.LFB12:
	.loc 2 685 69 is_stmt 1 view -0
	.cfi_startproc
	.loc 2 685 69 is_stmt 0 view .LVU120
	endbr64
.L38:
	endbr64
	.loc 2 685 70 is_stmt 1 view .LVU121
	.loc 2 685 87 is_stmt 0 view .LVU122
	movb	%sil, 27(%rdi)
	.loc 2 685 94 view .LVU123
	ret
	.cfi_endproc
.LFE12:
	.size	fixture_set_flags, .-fixture_set_flags
	.p2align 4
	.globl	fixture_original_flag_field
	.type	fixture_original_flag_field, @function
fixture_original_flag_field:
.LVL30:
.LFB13:
	.loc 2 686 68 is_stmt 1 view -0
	.cfi_startproc
	.loc 2 686 68 is_stmt 0 view .LVU125
	endbr64
.L40:
	endbr64
	.loc 2 686 69 is_stmt 1 view .LVU126
	.loc 2 686 86 is_stmt 0 view .LVU127
	movzbl	27(%rdi), %eax
	.loc 2 686 94 view .LVU128
	ret
	.cfi_endproc
.LFE13:
	.size	fixture_original_flag_field, .-fixture_original_flag_field
	.section	.rodata
	.align 16
	.type	__func__.1271, @object
	.size	__func__.1271, 22
__func__.1271:
	.string	"arch_prctl_log_bridge"
	.section	.rodata.str1.8
	.align 8
.LC1:
	.string	"/src/arch/x86_64/kernel/syscall.c"
	.section	__verbose,"aw"
	.align 8
	.type	ddebug.1270, @object
	.size	ddebug.1270, 32
ddebug.1270:
	.quad	.LC1
	.quad	__func__.1271
	.zero	8
	.byte	157
	.byte	2
	.byte	0
	.byte	0
	.zero	4
	.local	configured_return
	.comm	configured_return,4,4
	.local	trace
	.comm	trace,256,32
	.text
.Letext0:
	.file 3 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/types.h"
	.file 4 "/home/holden/mckernel/lib/include/ihk/debug.h"
	.file 5 "/usr/lib/gcc/x86_64-linux-gnu/9/include/stdarg.h"
	.file 6 "<built-in>"
	.section	.debug_info,"",@progbits
.Ldebug_info0:
	.long	0x570
	.value	0x4
	.long	.Ldebug_abbrev0
	.byte	0x8
	.uleb128 0x1
	.long	.LASF49
	.byte	0xc
	.long	.LASF50
	.long	.LASF51
	.quad	.Ltext0
	.quad	.Letext0-.Ltext0
	.long	.Ldebug_line0
	.uleb128 0x2
	.byte	0x1
	.byte	0x2
	.long	.LASF0
	.uleb128 0x2
	.byte	0x1
	.byte	0x8
	.long	.LASF1
	.uleb128 0x2
	.byte	0x2
	.byte	0x7
	.long	.LASF2
	.uleb128 0x2
	.byte	0x4
	.byte	0x7
	.long	.LASF3
	.uleb128 0x3
	.long	.LASF8
	.byte	0x3
	.byte	0x14
	.byte	0x1c
	.long	0x55
	.uleb128 0x2
	.byte	0x8
	.byte	0x7
	.long	.LASF4
	.uleb128 0x2
	.byte	0x1
	.byte	0x6
	.long	.LASF5
	.uleb128 0x2
	.byte	0x2
	.byte	0x5
	.long	.LASF6
	.uleb128 0x4
	.byte	0x4
	.byte	0x5
	.string	"int"
	.uleb128 0x2
	.byte	0x8
	.byte	0x5
	.long	.LASF7
	.uleb128 0x3
	.long	.LASF9
	.byte	0x3
	.byte	0x1d
	.byte	0x12
	.long	0x49
	.uleb128 0x2
	.byte	0x8
	.byte	0x7
	.long	.LASF10
	.uleb128 0x5
	.byte	0x8
	.long	0x98
	.uleb128 0x2
	.byte	0x1
	.byte	0x6
	.long	.LASF11
	.uleb128 0x6
	.long	0x91
	.uleb128 0x7
	.long	.LASF40
	.byte	0x20
	.byte	0x8
	.byte	0x4
	.byte	0xe
	.byte	0x8
	.long	0xf3
	.uleb128 0x8
	.long	.LASF12
	.byte	0x4
	.byte	0xf
	.byte	0xe
	.long	0x8b
	.byte	0
	.uleb128 0x8
	.long	.LASF13
	.byte	0x4
	.byte	0x10
	.byte	0xe
	.long	0x8b
	.byte	0x8
	.uleb128 0x9
	.string	"fmt"
	.byte	0x4
	.byte	0x11
	.byte	0xe
	.long	0x8b
	.byte	0x10
	.uleb128 0xa
	.long	.LASF14
	.byte	0x4
	.byte	0x12
	.byte	0xf
	.long	0x42
	.byte	0x4
	.byte	0x18
	.byte	0x8
	.byte	0x18
	.uleb128 0xa
	.long	.LASF15
	.byte	0x4
	.byte	0x13
	.byte	0xf
	.long	0x42
	.byte	0x4
	.byte	0x8
	.byte	0
	.byte	0x18
	.byte	0
	.uleb128 0x3
	.long	.LASF16
	.byte	0x5
	.byte	0x28
	.byte	0x1b
	.long	0xff
	.uleb128 0xb
	.long	.LASF52
	.long	0x108
	.uleb128 0xc
	.long	0x118
	.long	0x118
	.uleb128 0xd
	.long	0x84
	.byte	0
	.byte	0
	.uleb128 0xe
	.long	.LASF53
	.byte	0x18
	.byte	0x6
	.byte	0
	.long	0x155
	.uleb128 0xf
	.long	.LASF17
	.byte	0x6
	.byte	0
	.long	0x42
	.byte	0
	.uleb128 0xf
	.long	.LASF18
	.byte	0x6
	.byte	0
	.long	0x42
	.byte	0x4
	.uleb128 0xf
	.long	.LASF19
	.byte	0x6
	.byte	0
	.long	0x155
	.byte	0x8
	.uleb128 0xf
	.long	.LASF20
	.byte	0x6
	.byte	0
	.long	0x155
	.byte	0x10
	.byte	0
	.uleb128 0x10
	.byte	0x8
	.uleb128 0x3
	.long	.LASF21
	.byte	0x5
	.byte	0x63
	.byte	0x18
	.long	0xf3
	.uleb128 0x11
	.long	.LASF54
	.value	0x100
	.byte	0x1
	.byte	0x8
	.byte	0x8
	.long	0x1da
	.uleb128 0x8
	.long	.LASF22
	.byte	0x1
	.byte	0x8
	.byte	0x24
	.long	0x84
	.byte	0
	.uleb128 0x9
	.string	"cpu"
	.byte	0x1
	.byte	0x8
	.byte	0x2e
	.long	0x6a
	.byte	0x8
	.uleb128 0x8
	.long	.LASF23
	.byte	0x1
	.byte	0x8
	.byte	0x32
	.long	0x6a
	.byte	0xc
	.uleb128 0x8
	.long	.LASF24
	.byte	0x1
	.byte	0x8
	.byte	0x4f
	.long	0x84
	.byte	0x10
	.uleb128 0x8
	.long	.LASF25
	.byte	0x1
	.byte	0x8
	.byte	0x5a
	.long	0x1da
	.byte	0x18
	.uleb128 0x8
	.long	.LASF26
	.byte	0x1
	.byte	0x8
	.byte	0x65
	.long	0x1ea
	.byte	0x78
	.uleb128 0x8
	.long	.LASF27
	.byte	0x1
	.byte	0x8
	.byte	0x77
	.long	0x6a
	.byte	0xf8
	.uleb128 0x8
	.long	.LASF28
	.byte	0x1
	.byte	0x8
	.byte	0x87
	.long	0x6a
	.byte	0xfc
	.byte	0
	.uleb128 0xc
	.long	0x91
	.long	0x1ea
	.uleb128 0xd
	.long	0x84
	.byte	0x5f
	.byte	0
	.uleb128 0xc
	.long	0x91
	.long	0x1fa
	.uleb128 0xd
	.long	0x84
	.byte	0x7f
	.byte	0
	.uleb128 0x12
	.long	.LASF29
	.byte	0x1
	.byte	0x9
	.byte	0x1d
	.long	0x163
	.uleb128 0x9
	.byte	0x3
	.quad	trace
	.uleb128 0x12
	.long	.LASF30
	.byte	0x1
	.byte	0xa
	.byte	0xc
	.long	0x6a
	.uleb128 0x9
	.byte	0x3
	.quad	configured_return
	.uleb128 0x13
	.long	.LASF55
	.byte	0x1
	.byte	0x1b
	.byte	0x16
	.long	.LASF56
	.long	0x9d
	.uleb128 0x14
	.long	0x9d
	.byte	0x8
	.long	0x242
	.uleb128 0x15
	.byte	0
	.uleb128 0x16
	.long	.LASF31
	.byte	0x2
	.value	0x2a1
	.byte	0x16
	.long	0x236
	.uleb128 0x16
	.long	.LASF32
	.byte	0x2
	.value	0x2a1
	.byte	0x2a
	.long	0x236
	.uleb128 0x17
	.long	.LASF34
	.byte	0x2
	.value	0x2ae
	.byte	0xe
	.long	0x42
	.quad	.LFB13
	.quad	.LFE13-.LFB13
	.uleb128 0x1
	.byte	0x9c
	.long	0x28f
	.uleb128 0x18
	.long	.LASF33
	.byte	0x2
	.value	0x2ae
	.byte	0x39
	.long	0x28f
	.uleb128 0x1
	.byte	0x55
	.byte	0
	.uleb128 0x5
	.byte	0x8
	.long	0x9d
	.uleb128 0x19
	.long	.LASF41
	.byte	0x2
	.value	0x2ad
	.byte	0x6
	.quad	.LFB12
	.quad	.LFE12-.LFB12
	.uleb128 0x1
	.byte	0x9c
	.long	0x2d3
	.uleb128 0x18
	.long	.LASF33
	.byte	0x2
	.value	0x2ad
	.byte	0x27
	.long	0x28f
	.uleb128 0x1
	.byte	0x55
	.uleb128 0x18
	.long	.LASF15
	.byte	0x2
	.value	0x2ad
	.byte	0x3f
	.long	0x42
	.uleb128 0x1
	.byte	0x54
	.byte	0
	.uleb128 0x1a
	.long	.LASF57
	.byte	0x2
	.value	0x2ac
	.byte	0x8
	.long	0x78
	.quad	.LFB11
	.quad	.LFE11-.LFB11
	.uleb128 0x1
	.byte	0x9c
	.uleb128 0x17
	.long	.LASF35
	.byte	0x2
	.value	0x2a2
	.byte	0x10
	.long	0x28f
	.quad	.LFB10
	.quad	.LFE10-.LFB10
	.uleb128 0x1
	.byte	0x9c
	.long	0x36d
	.uleb128 0x1b
	.long	.LASF36
	.byte	0x2
	.value	0x2a4
	.byte	0x14
	.long	0x28f
	.long	.LLST7
	.long	.LVUS7
	.uleb128 0x1c
	.long	.Ldebug_ranges0+0
	.uleb128 0x1b
	.long	.LASF37
	.byte	0x2
	.value	0x2a5
	.byte	0x17
	.long	0x84
	.long	.LLST8
	.long	.LVUS8
	.uleb128 0x1d
	.quad	.LBB5
	.quad	.LBE5-.LBB5
	.uleb128 0x1e
	.string	"row"
	.byte	0x2
	.value	0x2a6
	.byte	0x18
	.long	0x28f
	.long	.LLST9
	.long	.LVUS9
	.byte	0
	.byte	0
	.byte	0
	.uleb128 0x1f
	.long	.LASF38
	.byte	0x2
	.value	0x29a
	.byte	0x1
	.long	.LASF58
	.quad	.LFB9
	.quad	.LFE9-.LFB9
	.uleb128 0x1
	.byte	0x9c
	.long	0x410
	.uleb128 0x20
	.long	.LASF39
	.byte	0x2
	.value	0x29a
	.byte	0x1b
	.long	0x6a
	.long	.LLST4
	.long	.LVUS4
	.uleb128 0x21
	.string	"cpu"
	.byte	0x2
	.value	0x29a
	.byte	0x26
	.long	0x6a
	.long	.LLST5
	.long	.LVUS5
	.uleb128 0x20
	.long	.LASF24
	.byte	0x2
	.value	0x29a
	.byte	0x39
	.long	0x84
	.long	.LLST6
	.long	.LVUS6
	.uleb128 0x22
	.long	.LASF59
	.long	0x420
	.uleb128 0x1d
	.quad	.LBB3
	.quad	.LBE3-.LBB3
	.uleb128 0x23
	.long	.LASF40
	.byte	0x2
	.value	0x29d
	.byte	0x5f
	.long	0x9d
	.byte	0x8
	.uleb128 0x9
	.byte	0x3
	.quad	ddebug.1270
	.uleb128 0x24
	.quad	.LVL18
	.long	0x45e
	.byte	0
	.byte	0
	.uleb128 0xc
	.long	0x98
	.long	0x420
	.uleb128 0xd
	.long	0x84
	.byte	0x15
	.byte	0
	.uleb128 0x6
	.long	0x410
	.uleb128 0x25
	.long	.LASF42
	.byte	0x1
	.byte	0x19
	.byte	0x6
	.quad	.LFB8
	.quad	.LFE8-.LFB8
	.uleb128 0x1
	.byte	0x9c
	.long	0x458
	.uleb128 0x26
	.string	"out"
	.byte	0x1
	.byte	0x19
	.byte	0x2f
	.long	0x458
	.long	.LLST3
	.long	.LVUS3
	.byte	0
	.uleb128 0x5
	.byte	0x8
	.long	0x163
	.uleb128 0x27
	.long	.LASF43
	.byte	0x1
	.byte	0x11
	.byte	0x5
	.long	0x6a
	.quad	.LFB7
	.quad	.LFE7-.LFB7
	.uleb128 0x1
	.byte	0x9c
	.long	0x4f9
	.uleb128 0x28
	.long	.LASF25
	.byte	0x1
	.byte	0x11
	.byte	0x19
	.long	0x8b
	.long	.LLST1
	.long	.LVUS1
	.uleb128 0x29
	.uleb128 0x2a
	.long	.LASF44
	.byte	0x1
	.byte	0x13
	.byte	0x1a
	.long	0x78
	.long	.LLST2
	.long	.LVUS2
	.uleb128 0x12
	.long	.LASF45
	.byte	0x1
	.byte	0x14
	.byte	0xd
	.long	0x157
	.uleb128 0x3
	.byte	0x91
	.sleb128 -128
	.uleb128 0x12
	.long	.LASF46
	.byte	0x1
	.byte	0x14
	.byte	0x17
	.long	0x157
	.uleb128 0x3
	.byte	0x91
	.sleb128 -104
	.uleb128 0x2b
	.quad	.LVL13
	.long	0x567
	.uleb128 0x2c
	.uleb128 0x1
	.byte	0x55
	.uleb128 0x9
	.byte	0x3
	.quad	trace+120
	.uleb128 0x2c
	.uleb128 0x1
	.byte	0x54
	.uleb128 0x2
	.byte	0x8
	.byte	0x80
	.uleb128 0x2c
	.uleb128 0x1
	.byte	0x51
	.uleb128 0x3
	.byte	0xf3
	.uleb128 0x1
	.byte	0x55
	.uleb128 0x2c
	.uleb128 0x1
	.byte	0x52
	.uleb128 0x3
	.byte	0x76
	.sleb128 -88
	.byte	0
	.byte	0
	.uleb128 0x25
	.long	.LASF47
	.byte	0x1
	.byte	0xb
	.byte	0x6
	.quad	.LFB6
	.quad	.LFE6-.LFB6
	.uleb128 0x1
	.byte	0x9c
	.long	0x561
	.uleb128 0x2d
	.long	.LASF23
	.byte	0x1
	.byte	0xb
	.byte	0x18
	.long	0x6a
	.uleb128 0x1
	.byte	0x55
	.uleb128 0x12
	.long	.LASF48
	.byte	0x1
	.byte	0xd
	.byte	0x14
	.long	0x561
	.uleb128 0xa
	.byte	0x3
	.quad	trace
	.byte	0x9f
	.uleb128 0x1d
	.quad	.LBB2
	.quad	.LBE2-.LBB2
	.uleb128 0x2e
	.string	"i"
	.byte	0x1
	.byte	0xe
	.byte	0x10
	.long	0x78
	.long	.LLST0
	.long	.LVUS0
	.byte	0
	.byte	0
	.uleb128 0x5
	.byte	0x8
	.long	0x34
	.uleb128 0x2f
	.long	.LASF60
	.long	.LASF60
	.byte	0x1
	.byte	0x7
	.byte	0xc
	.byte	0
	.section	.debug_abbrev,"",@progbits
.Ldebug_abbrev0:
	.uleb128 0x1
	.uleb128 0x11
	.byte	0x1
	.uleb128 0x25
	.uleb128 0xe
	.uleb128 0x13
	.uleb128 0xb
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x1b
	.uleb128 0xe
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x12
	.uleb128 0x7
	.uleb128 0x10
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x2
	.uleb128 0x24
	.byte	0
	.uleb128 0xb
	.uleb128 0xb
	.uleb128 0x3e
	.uleb128 0xb
	.uleb128 0x3
	.uleb128 0xe
	.byte	0
	.byte	0
	.uleb128 0x3
	.uleb128 0x16
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x4
	.uleb128 0x24
	.byte	0
	.uleb128 0xb
	.uleb128 0xb
	.uleb128 0x3e
	.uleb128 0xb
	.uleb128 0x3
	.uleb128 0x8
	.byte	0
	.byte	0
	.uleb128 0x5
	.uleb128 0xf
	.byte	0
	.uleb128 0xb
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x6
	.uleb128 0x26
	.byte	0
	.uleb128 0x49
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x7
	.uleb128 0x13
	.byte	0x1
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0xb
	.uleb128 0xb
	.uleb128 0x88
	.uleb128 0xb
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x8
	.uleb128 0xd
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x38
	.uleb128 0xb
	.byte	0
	.byte	0
	.uleb128 0x9
	.uleb128 0xd
	.byte	0
	.uleb128 0x3
	.uleb128 0x8
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x38
	.uleb128 0xb
	.byte	0
	.byte	0
	.uleb128 0xa
	.uleb128 0xd
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0xb
	.uleb128 0xb
	.uleb128 0xd
	.uleb128 0xb
	.uleb128 0xc
	.uleb128 0xb
	.uleb128 0x38
	.uleb128 0xb
	.byte	0
	.byte	0
	.uleb128 0xb
	.uleb128 0x16
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x49
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0xc
	.uleb128 0x1
	.byte	0x1
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0xd
	.uleb128 0x21
	.byte	0
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2f
	.uleb128 0xb
	.byte	0
	.byte	0
	.uleb128 0xe
	.uleb128 0x13
	.byte	0x1
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0xb
	.uleb128 0xb
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0xf
	.uleb128 0xd
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x38
	.uleb128 0xb
	.byte	0
	.byte	0
	.uleb128 0x10
	.uleb128 0xf
	.byte	0
	.uleb128 0xb
	.uleb128 0xb
	.byte	0
	.byte	0
	.uleb128 0x11
	.uleb128 0x13
	.byte	0x1
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0xb
	.uleb128 0x5
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x12
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x18
	.byte	0
	.byte	0
	.uleb128 0x13
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x6e
	.uleb128 0xe
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3c
	.uleb128 0x19
	.byte	0
	.byte	0
	.uleb128 0x14
	.uleb128 0x1
	.byte	0x1
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x88
	.uleb128 0xb
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x15
	.uleb128 0x21
	.byte	0
	.byte	0
	.byte	0
	.uleb128 0x16
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3c
	.uleb128 0x19
	.byte	0
	.byte	0
	.uleb128 0x17
	.uleb128 0x2e
	.byte	0x1
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x27
	.uleb128 0x19
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x12
	.uleb128 0x7
	.uleb128 0x40
	.uleb128 0x18
	.uleb128 0x2117
	.uleb128 0x19
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x18
	.uleb128 0x5
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x18
	.byte	0
	.byte	0
	.uleb128 0x19
	.uleb128 0x2e
	.byte	0x1
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x27
	.uleb128 0x19
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x12
	.uleb128 0x7
	.uleb128 0x40
	.uleb128 0x18
	.uleb128 0x2117
	.uleb128 0x19
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x1a
	.uleb128 0x2e
	.byte	0
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x27
	.uleb128 0x19
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x12
	.uleb128 0x7
	.uleb128 0x40
	.uleb128 0x18
	.uleb128 0x2117
	.uleb128 0x19
	.byte	0
	.byte	0
	.uleb128 0x1b
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x17
	.uleb128 0x2137
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x1c
	.uleb128 0xb
	.byte	0x1
	.uleb128 0x55
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x1d
	.uleb128 0xb
	.byte	0x1
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x12
	.uleb128 0x7
	.byte	0
	.byte	0
	.uleb128 0x1e
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0x8
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x17
	.uleb128 0x2137
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x1f
	.uleb128 0x2e
	.byte	0x1
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x6e
	.uleb128 0xe
	.uleb128 0x27
	.uleb128 0x19
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x12
	.uleb128 0x7
	.uleb128 0x40
	.uleb128 0x18
	.uleb128 0x2117
	.uleb128 0x19
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x20
	.uleb128 0x5
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x17
	.uleb128 0x2137
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x21
	.uleb128 0x5
	.byte	0
	.uleb128 0x3
	.uleb128 0x8
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x17
	.uleb128 0x2137
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x22
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x34
	.uleb128 0x19
	.byte	0
	.byte	0
	.uleb128 0x23
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0x5
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x88
	.uleb128 0xb
	.uleb128 0x2
	.uleb128 0x18
	.byte	0
	.byte	0
	.uleb128 0x24
	.uleb128 0x4109
	.byte	0
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x2115
	.uleb128 0x19
	.uleb128 0x31
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x25
	.uleb128 0x2e
	.byte	0x1
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x27
	.uleb128 0x19
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x12
	.uleb128 0x7
	.uleb128 0x40
	.uleb128 0x18
	.uleb128 0x2117
	.uleb128 0x19
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x26
	.uleb128 0x5
	.byte	0
	.uleb128 0x3
	.uleb128 0x8
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x17
	.uleb128 0x2137
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x27
	.uleb128 0x2e
	.byte	0x1
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x27
	.uleb128 0x19
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x12
	.uleb128 0x7
	.uleb128 0x40
	.uleb128 0x18
	.uleb128 0x2117
	.uleb128 0x19
	.uleb128 0x1
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x28
	.uleb128 0x5
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x17
	.uleb128 0x2137
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x29
	.uleb128 0x18
	.byte	0
	.byte	0
	.byte	0
	.uleb128 0x2a
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x17
	.uleb128 0x2137
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x2b
	.uleb128 0x4109
	.byte	0x1
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x31
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x2c
	.uleb128 0x410a
	.byte	0
	.uleb128 0x2
	.uleb128 0x18
	.uleb128 0x2111
	.uleb128 0x18
	.byte	0
	.byte	0
	.uleb128 0x2d
	.uleb128 0x5
	.byte	0
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x18
	.byte	0
	.byte	0
	.uleb128 0x2e
	.uleb128 0x34
	.byte	0
	.uleb128 0x3
	.uleb128 0x8
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.uleb128 0x2
	.uleb128 0x17
	.uleb128 0x2137
	.uleb128 0x17
	.byte	0
	.byte	0
	.uleb128 0x2f
	.uleb128 0x2e
	.byte	0
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x3c
	.uleb128 0x19
	.uleb128 0x6e
	.uleb128 0xe
	.uleb128 0x3
	.uleb128 0xe
	.uleb128 0x3a
	.uleb128 0xb
	.uleb128 0x3b
	.uleb128 0xb
	.uleb128 0x39
	.uleb128 0xb
	.byte	0
	.byte	0
	.byte	0
	.section	.debug_loc,"",@progbits
.Ldebug_loc0:
.LVUS7:
	.uleb128 .LVU88
	.uleb128 .LVU98
	.uleb128 .LVU98
	.uleb128 .LVU108
	.uleb128 .LVU111
	.uleb128 .LVU112
.LLST7:
	.quad	.LVL19-.Ltext0
	.quad	.LVL21-.Ltext0
	.value	0x2
	.byte	0x30
	.byte	0x9f
	.quad	.LVL21-.Ltext0
	.quad	.LVL24-.Ltext0
	.value	0x1
	.byte	0x58
	.quad	.LVL26-.Ltext0
	.quad	.LVL27-.Ltext0
	.value	0x1
	.byte	0x58
	.quad	0
	.quad	0
.LVUS8:
	.uleb128 .LVU94
	.uleb128 .LVU110
	.uleb128 .LVU111
	.uleb128 .LVU113
.LLST8:
	.quad	.LVL20-.Ltext0
	.quad	.LVL25-.Ltext0
	.value	0x1
	.byte	0x50
	.quad	.LVL26-.Ltext0
	.quad	.LVL28-.Ltext0
	.value	0x1
	.byte	0x50
	.quad	0
	.quad	0
.LVUS9:
	.uleb128 .LVU99
	.uleb128 .LVU106
	.uleb128 .LVU106
	.uleb128 .LVU108
	.uleb128 .LVU111
	.uleb128 .LVU113
.LLST9:
	.quad	.LVL21-.Ltext0
	.quad	.LVL23-.Ltext0
	.value	0x1
	.byte	0x50
	.quad	.LVL23-.Ltext0
	.quad	.LVL24-.Ltext0
	.value	0x3
	.byte	0x70
	.sleb128 -32
	.byte	0x9f
	.quad	.LVL26-.Ltext0
	.quad	.LVL28-.Ltext0
	.value	0x1
	.byte	0x50
	.quad	0
	.quad	0
.LVUS4:
	.uleb128 0
	.uleb128 .LVU84
	.uleb128 .LVU84
	.uleb128 0
.LLST4:
	.quad	.LVL16-.Ltext0
	.quad	.LVL17-.Ltext0
	.value	0x1
	.byte	0x55
	.quad	.LVL17-.Ltext0
	.quad	.LFE9-.Ltext0
	.value	0x4
	.byte	0xf3
	.uleb128 0x1
	.byte	0x55
	.byte	0x9f
	.quad	0
	.quad	0
.LVUS5:
	.uleb128 0
	.uleb128 .LVU85
	.uleb128 .LVU85
	.uleb128 0
.LLST5:
	.quad	.LVL16-.Ltext0
	.quad	.LVL18-1-.Ltext0
	.value	0x1
	.byte	0x54
	.quad	.LVL18-1-.Ltext0
	.quad	.LFE9-.Ltext0
	.value	0x4
	.byte	0xf3
	.uleb128 0x1
	.byte	0x54
	.byte	0x9f
	.quad	0
	.quad	0
.LVUS6:
	.uleb128 0
	.uleb128 .LVU85
	.uleb128 .LVU85
	.uleb128 0
.LLST6:
	.quad	.LVL16-.Ltext0
	.quad	.LVL18-1-.Ltext0
	.value	0x1
	.byte	0x51
	.quad	.LVL18-1-.Ltext0
	.quad	.LFE9-.Ltext0
	.value	0x4
	.byte	0xf3
	.uleb128 0x1
	.byte	0x51
	.byte	0x9f
	.quad	0
	.quad	0
.LVUS3:
	.uleb128 0
	.uleb128 .LVU72
	.uleb128 .LVU72
	.uleb128 0
.LLST3:
	.quad	.LVL14-.Ltext0
	.quad	.LVL15-.Ltext0
	.value	0x1
	.byte	0x55
	.quad	.LVL15-.Ltext0
	.quad	.LFE8-.Ltext0
	.value	0x4
	.byte	0xf3
	.uleb128 0x1
	.byte	0x55
	.byte	0x9f
	.quad	0
	.quad	0
.LVUS1:
	.uleb128 0
	.uleb128 .LVU60
	.uleb128 .LVU60
	.uleb128 .LVU61
	.uleb128 .LVU61
	.uleb128 0
.LLST1:
	.quad	.LVL6-.Ltext0
	.quad	.LVL12-.Ltext0
	.value	0x1
	.byte	0x55
	.quad	.LVL12-.Ltext0
	.quad	.LVL13-1-.Ltext0
	.value	0x1
	.byte	0x5a
	.quad	.LVL13-1-.Ltext0
	.quad	.LFE7-.Ltext0
	.value	0x4
	.byte	0xf3
	.uleb128 0x1
	.byte	0x55
	.byte	0x9f
	.quad	0
	.quad	0
.LVUS2:
	.uleb128 .LVU26
	.uleb128 .LVU31
	.uleb128 .LVU31
	.uleb128 .LVU39
.LLST2:
	.quad	.LVL7-.Ltext0
	.quad	.LVL8-.Ltext0
	.value	0x2
	.byte	0x30
	.byte	0x9f
	.quad	.LVL8-.Ltext0
	.quad	.LVL11-.Ltext0
	.value	0x1
	.byte	0x50
	.quad	0
	.quad	0
.LVUS0:
	.uleb128 .LVU5
	.uleb128 .LVU6
	.uleb128 .LVU6
	.uleb128 .LVU9
	.uleb128 .LVU9
	.uleb128 .LVU10
	.uleb128 .LVU10
	.uleb128 .LVU13
.LLST0:
	.quad	.LVL1-.Ltext0
	.quad	.LVL2-.Ltext0
	.value	0x2
	.byte	0x30
	.byte	0x9f
	.quad	.LVL2-.Ltext0
	.quad	.LVL3-.Ltext0
	.value	0xd
	.byte	0x70
	.sleb128 0
	.byte	0x3
	.quad	trace
	.byte	0x1c
	.byte	0x9f
	.quad	.LVL3-.Ltext0
	.quad	.LVL4-.Ltext0
	.value	0xd
	.byte	0x70
	.sleb128 0
	.byte	0x3
	.quad	trace-1
	.byte	0x1c
	.byte	0x9f
	.quad	.LVL4-.Ltext0
	.quad	.LVL5-.Ltext0
	.value	0xd
	.byte	0x70
	.sleb128 0
	.byte	0x3
	.quad	trace
	.byte	0x1c
	.byte	0x9f
	.quad	0
	.quad	0
	.section	.debug_aranges,"",@progbits
	.long	0x2c
	.value	0x2
	.long	.Ldebug_info0
	.byte	0x8
	.byte	0
	.value	0
	.value	0
	.quad	.Ltext0
	.quad	.Letext0-.Ltext0
	.quad	0
	.quad	0
	.section	.debug_ranges,"",@progbits
.Ldebug_ranges0:
	.quad	.LBB4-.Ltext0
	.quad	.LBE4-.Ltext0
	.quad	.LBB6-.Ltext0
	.quad	.LBE6-.Ltext0
	.quad	0
	.quad	0
	.section	.debug_line,"",@progbits
.Ldebug_line0:
	.section	.debug_str,"MS",@progbits,1
.LASF41:
	.string	"fixture_set_flags"
.LASF54:
	.string	"fixture_trace"
.LASF9:
	.string	"size_t"
.LASF52:
	.string	"__builtin_va_list"
.LASF26:
	.string	"rendered"
.LASF24:
	.string	"value"
.LASF40:
	.string	"ddebug"
.LASF60:
	.string	"vsnprintf"
.LASF45:
	.string	"arguments"
.LASF31:
	.string	"__start___verbose"
.LASF47:
	.string	"fixture_reset"
.LASF8:
	.string	"uint64_t"
.LASF43:
	.string	"kprintf"
.LASF59:
	.string	"__func__"
.LASF58:
	.string	"original_arch_prctl_log_bridge"
.LASF12:
	.string	"file"
.LASF1:
	.string	"unsigned char"
.LASF30:
	.string	"configured_return"
.LASF51:
	.string	"/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1"
.LASF37:
	.string	"address"
.LASF10:
	.string	"long unsigned int"
.LASF2:
	.string	"short unsigned int"
.LASF38:
	.string	"arch_prctl_log_bridge"
.LASF20:
	.string	"reg_save_area"
.LASF21:
	.string	"va_list"
.LASF35:
	.string	"fixture_original_descriptor"
.LASF13:
	.string	"func"
.LASF16:
	.string	"__gnuc_va_list"
.LASF27:
	.string	"rendered_length"
.LASF17:
	.string	"gp_offset"
.LASF25:
	.string	"format"
.LASF39:
	.string	"event"
.LASF50:
	.string	"/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
.LASF3:
	.string	"unsigned int"
.LASF15:
	.string	"flags"
.LASF34:
	.string	"fixture_original_flag_field"
.LASF4:
	.string	"long long unsigned int"
.LASF14:
	.string	"line"
.LASF28:
	.string	"padding"
.LASF49:
	.string	"GNU C11 9.4.0 -mcmodel=large -mno-red-zone -mno-sse -mtune=generic -march=x86-64 -g -O2 -std=gnu11 -ffreestanding -fno-omit-frame-pointer -fno-builtin -fasynchronous-unwind-tables -fstack-clash-protection -fcf-protection"
.LASF23:
	.string	"printer_return"
.LASF7:
	.string	"long long int"
.LASF11:
	.string	"char"
.LASF46:
	.string	"render_arguments"
.LASF32:
	.string	"__stop___verbose"
.LASF57:
	.string	"fixture_descriptor_count"
.LASF19:
	.string	"overflow_arg_area"
.LASF6:
	.string	"short int"
.LASF33:
	.string	"descriptor"
.LASF36:
	.string	"found"
.LASF22:
	.string	"calls"
.LASF42:
	.string	"fixture_read_trace"
.LASF44:
	.string	"length"
.LASF48:
	.string	"bytes"
.LASF5:
	.string	"signed char"
.LASF29:
	.string	"trace"
.LASF53:
	.string	"__va_list_tag"
.LASF55:
	.string	"arch_prctl_log_debug"
.LASF0:
	.string	"_Bool"
.LASF18:
	.string	"fp_offset"
.LASF56:
	.string	"mckernel_f06_arch_prctl_debug"
	.ident	"GCC: (Ubuntu 9.4.0-1ubuntu1~20.04.2) 9.4.0"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align 8
	.long	 1f - 0f
	.long	 4f - 1f
	.long	 5
0:
	.string	 "GNU"
1:
	.align 8
	.long	 0xc0000002
	.long	 3f - 2f
2:
	.long	 0x3
3:
	.align 8
4:
