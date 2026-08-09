#ifndef _MC_JHASH_H
#define _MC_JHASH_H
/**
 * \file mc_jhash.h
 * Licence details are found in the file LICENSE.
 *
 * \brief
 * Adaptation to McKernel
 *
 * \author Balazs Gerofi  <bgerofi@riken.jp> \par
 * Copyright (C) 2012  RIKEN AICS
 *
 *
 * HISTORY:
 */

/*
 * jhash.h: Jenkins hash support.
 *
 * Copyright (C) 1996 Bob Jenkins (bob_jenkins@burtleburtle.net)
 *
 * http://burtleburtle.net/bob/hash/
 *
 * These are the credits from Bob's sources:
 *
 * lookup2.c, by Bob Jenkins, December 1996, Public Domain.
 * hash(), hash2(), hash3, and mix() are externally useful functions.
 * Routines to test the hash are included if SELF_TEST is defined.
 * You can use this free for any purpose.  It has no warranty.
 *
 * Copyright (C) 2003 David S. Miller (davem@redhat.com)
 *
 * I've modified Bob's hash to be useful in the Linux kernel, and
 * any bugs present are surely my fault.  -DaveM
 *
 */

/* The golden ration: an arbitrary value */
#define JHASH_GOLDEN_RATIO	0x9e3779b9

/* A special optimized version that handles 1 or more of uint32_ts.
 * The length parameter here is the number of uint32_ts in the key.
 */
uint32_t mc_jhash2(const uint32_t *k, uint32_t length, uint32_t initval);

#endif /* _MC_JHASH_H */
