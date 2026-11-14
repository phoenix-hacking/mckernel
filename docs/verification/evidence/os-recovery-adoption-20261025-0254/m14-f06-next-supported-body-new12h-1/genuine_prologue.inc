/* syscall.c COPYRIGHT FUJITSU LIMITED 2018 */
/**
 * \file syscall.c
 *  License details are found in the file LICENSE.
 * \brief
 *  archtecture depended system call handlers
 * \author Gou Nakamura  <go.nakamura.yw@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 * \author Masamichi Takagi  <m-takagi@ab.jp.nec.com> \par
 * 	Copyright (C) 2013  NEC Corporation
 * \author Tomoki Shirasawa  <tomoki.shirasawa.kk@hitachi-solutions.com> \par
 * 	Copyright (C) 2013  Hitachi, Ltd.
 */
/*
 * HISTORY:
 */

#include <ihk/cpu.h>
#include <cls.h>
#include <cpulocal.h>
#include <syscall.h>
#include <process.h>
#include <string.h>
#include <errno.h>
#include <kmalloc.h>
#include <uio.h>
#include <mman.h>
#include <shm.h>
#include <prctl.h>
#include <ihk/ikc.h>
#include <page.h>
#include <limits.h>
#include <syscall.h>
#include <bitops.h>
#include <rusage_private.h>
#include <memory.h>
#include <arch-memory-helpers.h>
#include <ihk/debug.h>
#include <elfcore.h>

