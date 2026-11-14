/**
 * \file kmalloc.h
 *  License details are found in the file LICENSE.
 * \brief
 *  kmalloc and kfree functions
 * \author Taku Shimosawa  <shimosawa@is.s.u-tokyo.ac.jp> \par
 * Copyright (C) 2011 - 2012  Taku Shimosawa
 */
/*
 * HISTORY:
 */

#ifndef __HEADER_KMALLOC_H
#define __HEADER_KMALLOC_H

#include "ihk/mm.h"
#include "cls.h"
#include <ihk/debug.h>

void *kmalloc_tracked(int size, ihk_mc_ap_flag flag, char *file, int line);
void kfree_tracked(void *ptr, char *file, int line);
void *kmalloc(int size, ihk_mc_ap_flag flag);
void kfree(void *ptr);
void *_kmalloc(int size, ihk_mc_ap_flag flag, char *file, int line);
void _kfree(void *ptr, char *file, int line);
void *__kmalloc(int size, ihk_mc_ap_flag flag);
void __kfree(void *ptr);

int _memcheck(void *ptr, char *msg, char *file, int line, int free);
int memcheckall(void);
int freecheck(int runcount);
void kmalloc_consolidate_free_list(void);

/*
 * Generic lockless kmalloc cache.
 */
void kmalloc_cache_free(void *elem);
void kmalloc_cache_prealloc(struct kmalloc_cache_header *cache,
		size_t size, int nr_elem);
void *kmalloc_cache_alloc(struct kmalloc_cache_header *cache, size_t size);

#endif
