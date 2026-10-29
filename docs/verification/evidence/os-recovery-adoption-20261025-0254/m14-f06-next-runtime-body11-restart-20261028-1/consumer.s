	.file	"consumer.c"
	.text
.Ltext0:
	.p2align 4
	.globl	fixture_selected_descriptor
	.type	fixture_selected_descriptor, @function
fixture_selected_descriptor:
.LFB6:
	.file 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/consumer.c"
	.loc 1 18 49 view -0
	.cfi_startproc
	endbr64
.L2:
	endbr64
	.loc 1 18 50 view .LVU1
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L2, %r11
	leaq	.L2(%rip), %rax
	.loc 1 18 57 is_stmt 0 view .LVU2
	movabsq	$mckernel_f06_arch_prctl_debug@GOT, %rdx
	addq	%r11, %rax
	movq	(%rax,%rdx), %rax
	.loc 1 18 79 view .LVU3
	ret
	.cfi_endproc
.LFE6:
	.size	fixture_selected_descriptor, .-fixture_selected_descriptor
	.p2align 4
	.globl	fixture_consumer_set_flags
	.type	fixture_consumer_set_flags, @function
fixture_consumer_set_flags:
.LVL0:
.LFB7:
	.loc 1 19 52 is_stmt 1 view -0
	.cfi_startproc
	.loc 1 19 52 is_stmt 0 view .LVU5
	endbr64
.L5:
	endbr64
	.loc 1 19 53 is_stmt 1 view .LVU6
	leaq	.L5(%rip), %rax
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L5, %r11
	.loc 1 19 79 is_stmt 0 view .LVU7
	movabsq	$mckernel_f06_arch_prctl_debug@GOT, %rdx
	addq	%r11, %rax
	movq	(%rax,%rdx), %rax
	movb	%dil, 27(%rax)
	.loc 1 19 86 view .LVU8
	ret
	.cfi_endproc
.LFE7:
	.size	fixture_consumer_set_flags, .-fixture_consumer_set_flags
	.p2align 4
	.globl	fixture_consumer_read_flags
	.type	fixture_consumer_read_flags, @function
fixture_consumer_read_flags:
.LFB8:
	.loc 1 20 47 is_stmt 1 view -0
	.cfi_startproc
	endbr64
.L7:
	endbr64
	.loc 1 20 48 view .LVU10
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L7, %r11
	leaq	.L7(%rip), %rax
	.loc 1 20 75 is_stmt 0 view .LVU11
	movabsq	$mckernel_f06_arch_prctl_debug@GOT, %rdx
	addq	%r11, %rax
	movq	(%rax,%rdx), %rax
	movzbl	27(%rax), %eax
	.loc 1 20 82 view .LVU12
	ret
	.cfi_endproc
.LFE8:
	.size	fixture_consumer_read_flags, .-fixture_consumer_read_flags
	.p2align 4
	.globl	fixture_consumer_call
	.type	fixture_consumer_call, @function
fixture_consumer_call:
.LVL1:
.LFB9:
	.loc 1 21 66 is_stmt 1 view -0
	.cfi_startproc
	.loc 1 21 66 is_stmt 0 view .LVU14
	endbr64
.L9:
	endbr64
	.loc 1 21 67 is_stmt 1 view .LVU15
	movabsq	$_GLOBAL_OFFSET_TABLE_-.L9, %r11
	.loc 1 21 66 is_stmt 0 view .LVU16
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	.loc 1 21 67 view .LVU17
	movabsq	$arch_prctl_log_bridge@PLTOFF, %rax
	.loc 1 21 66 view .LVU18
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	pushq	%r15
	.cfi_offset 15, -24
	leaq	.L9(%rip), %r15
	addq	%r11, %r15
	.loc 1 21 67 view .LVU19
	addq	%r15, %rax
	.loc 1 21 106 view .LVU20
	popq	%r15
	.cfi_restore 15
	popq	%rbp
	.cfi_restore 6
	.cfi_def_cfa 7, 8
	.loc 1 21 67 view .LVU21
	jmp	*%rax
.LVL2:
	.loc 1 21 67 view .LVU22
	.cfi_endproc
.LFE9:
	.size	fixture_consumer_call, .-fixture_consumer_call
	.comm	f06_prctl_logger_real_header_abi_witness,4,4
.Letext0:
	.file 2 "/home/holden/mckernel/lib/include/ihk/debug.h"
	.section	.debug_info,"",@progbits
.Ldebug_info0:
	.long	0x1f7
	.value	0x4
	.long	.Ldebug_abbrev0
	.byte	0x8
	.uleb128 0x1
	.long	.LASF20
	.byte	0xc
	.long	.LASF21
	.long	.LASF22
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
	.uleb128 0x3
	.byte	0x4
	.byte	0x5
	.string	"int"
	.uleb128 0x2
	.byte	0x8
	.byte	0x5
	.long	.LASF7
	.uleb128 0x2
	.byte	0x8
	.byte	0x7
	.long	.LASF8
	.uleb128 0x4
	.byte	0x8
	.long	0x80
	.uleb128 0x2
	.byte	0x1
	.byte	0x6
	.long	.LASF9
	.uleb128 0x5
	.long	0x79
	.uleb128 0x6
	.long	.LASF23
	.byte	0x20
	.byte	0x8
	.byte	0x2
	.byte	0xe
	.byte	0x8
	.long	0xdb
	.uleb128 0x7
	.long	.LASF10
	.byte	0x2
	.byte	0xf
	.byte	0xe
	.long	0x73
	.byte	0
	.uleb128 0x7
	.long	.LASF11
	.byte	0x2
	.byte	0x10
	.byte	0xe
	.long	0x73
	.byte	0x8
	.uleb128 0x8
	.string	"fmt"
	.byte	0x2
	.byte	0x11
	.byte	0xe
	.long	0x73
	.byte	0x10
	.uleb128 0x9
	.long	.LASF12
	.byte	0x2
	.byte	0x12
	.byte	0xf
	.long	0x42
	.byte	0x4
	.byte	0x18
	.byte	0x8
	.byte	0x18
	.uleb128 0x9
	.long	.LASF13
	.byte	0x2
	.byte	0x13
	.byte	0xf
	.long	0x42
	.byte	0x4
	.byte	0x8
	.byte	0
	.byte	0x18
	.byte	0
	.uleb128 0xa
	.long	.LASF24
	.byte	0x1
	.byte	0xe
	.byte	0x5
	.long	0x5e
	.uleb128 0x9
	.byte	0x3
	.quad	f06_prctl_logger_real_header_abi_witness
	.uleb128 0xb
	.long	.LASF25
	.byte	0x1
	.byte	0x10
	.byte	0x16
	.long	.LASF26
	.long	0x85
	.uleb128 0xc
	.long	.LASF16
	.byte	0x1
	.byte	0x15
	.byte	0x6
	.quad	.LFB9
	.quad	.LFE9-.LFB9
	.uleb128 0x1
	.byte	0x9c
	.long	0x17f
	.uleb128 0xd
	.long	.LASF14
	.byte	0x1
	.byte	0x15
	.byte	0x20
	.long	0x5e
	.long	.LLST0
	.long	.LVUS0
	.uleb128 0xe
	.string	"cpu"
	.byte	0x1
	.byte	0x15
	.byte	0x2a
	.long	0x5e
	.long	.LLST1
	.long	.LVUS1
	.uleb128 0xd
	.long	.LASF15
	.byte	0x1
	.byte	0x15
	.byte	0x3c
	.long	0x6c
	.long	.LLST2
	.long	.LVUS2
	.uleb128 0xf
	.quad	.LVL2
	.long	0x1ee
	.uleb128 0x10
	.uleb128 0x1
	.byte	0x55
	.uleb128 0x3
	.byte	0xf3
	.uleb128 0x1
	.byte	0x55
	.uleb128 0x10
	.uleb128 0x1
	.byte	0x54
	.uleb128 0x3
	.byte	0xf3
	.uleb128 0x1
	.byte	0x54
	.uleb128 0x10
	.uleb128 0x1
	.byte	0x51
	.uleb128 0x3
	.byte	0xf3
	.uleb128 0x1
	.byte	0x51
	.byte	0
	.byte	0
	.uleb128 0x11
	.long	.LASF18
	.byte	0x1
	.byte	0x14
	.byte	0xe
	.long	0x42
	.quad	.LFB8
	.quad	.LFE8-.LFB8
	.uleb128 0x1
	.byte	0x9c
	.uleb128 0xc
	.long	.LASF17
	.byte	0x1
	.byte	0x13
	.byte	0x6
	.quad	.LFB7
	.quad	.LFE7-.LFB7
	.uleb128 0x1
	.byte	0x9c
	.long	0x1ca
	.uleb128 0x12
	.long	.LASF13
	.byte	0x1
	.byte	0x13
	.byte	0x2e
	.long	0x42
	.uleb128 0x1
	.byte	0x55
	.byte	0
	.uleb128 0x11
	.long	.LASF19
	.byte	0x1
	.byte	0x12
	.byte	0x10
	.long	0x1e8
	.quad	.LFB6
	.quad	.LFE6-.LFB6
	.uleb128 0x1
	.byte	0x9c
	.uleb128 0x4
	.byte	0x8
	.long	0x85
	.uleb128 0x13
	.long	.LASF27
	.long	.LASF27
	.byte	0x1
	.byte	0x7
	.byte	0xd
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
	.uleb128 0x4
	.uleb128 0xf
	.byte	0
	.uleb128 0xb
	.uleb128 0xb
	.uleb128 0x49
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x5
	.uleb128 0x26
	.byte	0
	.uleb128 0x49
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x6
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
	.uleb128 0x7
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
	.uleb128 0x8
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
	.uleb128 0x9
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
	.uleb128 0xa
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
	.uleb128 0x3f
	.uleb128 0x19
	.uleb128 0x2
	.uleb128 0x18
	.byte	0
	.byte	0
	.uleb128 0xb
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
	.uleb128 0xc
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
	.uleb128 0xd
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
	.uleb128 0xe
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
	.uleb128 0xf
	.uleb128 0x4109
	.byte	0x1
	.uleb128 0x11
	.uleb128 0x1
	.uleb128 0x2115
	.uleb128 0x19
	.uleb128 0x31
	.uleb128 0x13
	.byte	0
	.byte	0
	.uleb128 0x10
	.uleb128 0x410a
	.byte	0
	.uleb128 0x2
	.uleb128 0x18
	.uleb128 0x2111
	.uleb128 0x18
	.byte	0
	.byte	0
	.uleb128 0x11
	.uleb128 0x2e
	.byte	0
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
	.byte	0
	.byte	0
	.uleb128 0x12
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
	.uleb128 0x13
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
.LVUS0:
	.uleb128 0
	.uleb128 .LVU22
	.uleb128 .LVU22
	.uleb128 0
.LLST0:
	.quad	.LVL1-.Ltext0
	.quad	.LVL2-1-.Ltext0
	.value	0x1
	.byte	0x55
	.quad	.LVL2-1-.Ltext0
	.quad	.LFE9-.Ltext0
	.value	0x4
	.byte	0xf3
	.uleb128 0x1
	.byte	0x55
	.byte	0x9f
	.quad	0
	.quad	0
.LVUS1:
	.uleb128 0
	.uleb128 .LVU22
	.uleb128 .LVU22
	.uleb128 0
.LLST1:
	.quad	.LVL1-.Ltext0
	.quad	.LVL2-1-.Ltext0
	.value	0x1
	.byte	0x54
	.quad	.LVL2-1-.Ltext0
	.quad	.LFE9-.Ltext0
	.value	0x4
	.byte	0xf3
	.uleb128 0x1
	.byte	0x54
	.byte	0x9f
	.quad	0
	.quad	0
.LVUS2:
	.uleb128 0
	.uleb128 .LVU22
	.uleb128 .LVU22
	.uleb128 0
.LLST2:
	.quad	.LVL1-.Ltext0
	.quad	.LVL2-1-.Ltext0
	.value	0x1
	.byte	0x51
	.quad	.LVL2-1-.Ltext0
	.quad	.LFE9-.Ltext0
	.value	0x4
	.byte	0xf3
	.uleb128 0x1
	.byte	0x51
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
	.section	.debug_line,"",@progbits
.Ldebug_line0:
	.section	.debug_str,"MS",@progbits,1
.LASF15:
	.string	"value"
.LASF23:
	.string	"ddebug"
.LASF10:
	.string	"file"
.LASF1:
	.string	"unsigned char"
.LASF22:
	.string	"/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1"
.LASF8:
	.string	"long unsigned int"
.LASF2:
	.string	"short unsigned int"
.LASF27:
	.string	"arch_prctl_log_bridge"
.LASF17:
	.string	"fixture_consumer_set_flags"
.LASF19:
	.string	"fixture_selected_descriptor"
.LASF11:
	.string	"func"
.LASF24:
	.string	"f06_prctl_logger_real_header_abi_witness"
.LASF16:
	.string	"fixture_consumer_call"
.LASF14:
	.string	"event"
.LASF18:
	.string	"fixture_consumer_read_flags"
.LASF3:
	.string	"unsigned int"
.LASF13:
	.string	"flags"
.LASF4:
	.string	"long long unsigned int"
.LASF12:
	.string	"line"
.LASF20:
	.string	"GNU C11 9.4.0 -mcmodel=large -mno-red-zone -mno-sse -mtune=generic -march=x86-64 -g -O2 -std=gnu11 -ffreestanding -fno-omit-frame-pointer -fno-builtin -fasynchronous-unwind-tables -fstack-clash-protection -fcf-protection"
.LASF7:
	.string	"long long int"
.LASF9:
	.string	"char"
.LASF6:
	.string	"short int"
.LASF21:
	.string	"/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/consumer.c"
.LASF26:
	.string	"mckernel_f06_arch_prctl_debug"
.LASF5:
	.string	"signed char"
.LASF25:
	.string	"arch_prctl_log_debug"
.LASF0:
	.string	"_Bool"
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
