/**
 * \file futex.h
 * Licence details are found in the file LICENSE.
 *  
 * \brief
 * Futex adaptation to McKernel
 *
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * Copyright (C) 2012  RIKEN AICS
 *
 *
 * HISTORY:
 *
 */
#ifndef _ARCH_FUTEX_H
#define _ARCH_FUTEX_H

int futex_atomic_cmpxchg_inatomic(int __user *uaddr, int oldval, int newval);
int futex_atomic_op_inuser(int encoded_op, int __user *uaddr);

#endif
