/* bitops.c COPYRIGHT FUJITSU LIMITED 2015-2016 */
#include <bitops.h>

#ifndef MCKERNEL_RUST_BITOPS

#ifdef __x86_64__
int
fls(int x)
{
	int r;

	asm("bsrl %1,%0\n\t"
	    "jnz 1f\n\t"
	    "movl $-1,%0\n"
	    "1:" : "=r" (r) : "rm" (x));

	return r + 1;
}

int
ffs(int x)
{
	int r;

	asm("bsfl %1,%0\n\t"
	    "jnz 1f\n\t"
	    "movl $-1,%0\n"
	    "1:" : "=r" (r) : "rm" (x));
	return r + 1;
}

unsigned long
__ffs(unsigned long word)
{
	asm("bsf %1,%0"
		: "=r" (word)
		: "rm" (word));
	return word;
}

unsigned long
ffz(unsigned long word)
{
	asm("bsf %1,%0"
		: "=r" (word)
		: "r" (~word));
	return word;
}

#define X86_BITOP_ADDR (*(volatile long *)addr)

void
set_bit(int nr, volatile unsigned long *addr)
{
	asm volatile("lock; btsl %1,%0"
		     : "+m" (X86_BITOP_ADDR)
		     : "Ir" (nr)
		     : "memory");
}

void
clear_bit(int nr, volatile unsigned long *addr)
{
	asm volatile("lock; btrl %1,%0"
		     : "+m" (X86_BITOP_ADDR)
		     : "Ir" (nr)
		     : "memory");
}
#else
int
fls(int x)
{
	unsigned int value = (unsigned int)x;
	int r = 32;

	if (!value)
		return 0;

	if (!(value & 0xffff0000u)) {
		value <<= 16;
		r -= 16;
	}
	if (!(value & 0xff000000u)) {
		value <<= 8;
		r -= 8;
	}
	if (!(value & 0xf0000000u)) {
		value <<= 4;
		r -= 4;
	}
	if (!(value & 0xc0000000u)) {
		value <<= 2;
		r -= 2;
	}
	if (!(value & 0x80000000u)) {
		value <<= 1;
		r -= 1;
	}
	return r;
}

unsigned long
__ffs(unsigned long word)
{
	int num = 0;

	if (BITS_PER_LONG == 64) {
		if ((word & 0xffffffff) == 0) {
			num += 32;
			word >>= 32;
		}
	}

	if ((word & 0xffff) == 0) {
		num += 16;
		word >>= 16;
	}
	if ((word & 0xff) == 0) {
		num += 8;
		word >>= 8;
	}
	if ((word & 0xf) == 0) {
		num += 4;
		word >>= 4;
	}
	if ((word & 0x3) == 0) {
		num += 2;
		word >>= 2;
	}
	if ((word & 0x1) == 0)
		num += 1;
	return num;
}

unsigned long
ffz(unsigned long word)
{
	return __ffs(~word);
}

void
set_bit(int nr, volatile unsigned long *addr)
{
	unsigned long mask = (1UL << (nr % BITS_PER_LONG));
	unsigned long *p = ((unsigned long *)addr) + (nr / BITS_PER_LONG);

	*p |= mask;
}

void
clear_bit(int nr, volatile unsigned long *addr)
{
	unsigned long mask = (1UL << (nr % BITS_PER_LONG));
	unsigned long *p = ((unsigned long *)addr) + (nr / BITS_PER_LONG);

	*p &= ~mask;
}
#endif

int
test_bit(int nr, const void *addr)
{
	const uint32_t *p = (const uint32_t *)addr;

	return ((1UL << (nr & 31)) & (p[nr >> 5])) != 0;
}

unsigned long
ihk_bit_word(unsigned long nr)
{
	return nr / BITS_PER_LONG;
}

unsigned long
ihk_align_mask(unsigned long x, unsigned long mask)
{
	return (x + mask) & ~mask;
}

unsigned long
ihk_align(unsigned long x, unsigned long a)
{
	return ihk_align_mask(x, a - 1);
}

int
ihk_is_aligned(unsigned long x, unsigned long a)
{
	return (x & (a - 1)) == 0;
}

#define BITOP_WORD(nr)		((nr) / BITS_PER_LONG)

/*
 * Find the next set bit in a memory region.
 */
unsigned long find_next_bit(const unsigned long *addr, unsigned long size,
		unsigned long offset)
{
	const unsigned long *p = addr + BITOP_WORD(offset);
	unsigned long result = offset & ~(BITS_PER_LONG-1);
	unsigned long tmp;

	if (offset >= size)
		return size;
	size -= result;
	offset %= BITS_PER_LONG;
	if (offset) {
		tmp = *(p++);
		tmp &= (~0UL << offset);
		if (size < BITS_PER_LONG)
			goto found_first;
		if (tmp)
			goto found_middle;
		size -= BITS_PER_LONG;
		result += BITS_PER_LONG;
	}
	while (size & ~(BITS_PER_LONG-1)) {
		if ((tmp = *(p++)))
			goto found_middle;
		result += BITS_PER_LONG;
		size -= BITS_PER_LONG;
	}
	if (!size)
		return result;
	tmp = *p;

found_first:
	tmp &= (~0UL >> (BITS_PER_LONG - size));
	if (tmp == 0UL)		/* Are any bits set? */
		return result + size;	/* Nope. */
found_middle:
	return result + __ffs(tmp);
}

/*
 * This implementation of find_{first,next}_zero_bit was stolen from
 * Linus' asm-alpha/bitops.h.
 */
unsigned long find_next_zero_bit(const unsigned long *addr,
		unsigned long size, unsigned long offset)
{
	const unsigned long *p = addr + BITOP_WORD(offset);
	unsigned long result = offset & ~(BITS_PER_LONG-1);
	unsigned long tmp;

	if (offset >= size)
		return size;
	size -= result;
	offset %= BITS_PER_LONG;
	if (offset) {
		tmp = *(p++);
		tmp |= ~0UL >> (BITS_PER_LONG - offset);
		if (size < BITS_PER_LONG)
			goto found_first;
		if (~tmp)
			goto found_middle;
		size -= BITS_PER_LONG;
		result += BITS_PER_LONG;
	}
	while (size & ~(BITS_PER_LONG-1)) {
		if (~(tmp = *(p++)))
			goto found_middle;
		result += BITS_PER_LONG;
		size -= BITS_PER_LONG;
	}
	if (!size)
		return result;
	tmp = *p;

found_first:
	tmp |= ~0UL << size;
	if (tmp == ~0UL)	/* Are any bits zero? */
		return result + size;	/* Nope. */
found_middle:
	return result + ffz(tmp);
}

/*
 * Find the first set bit in a memory region.
 */
unsigned long find_first_bit(const unsigned long *addr,
		unsigned long size)
{
	const unsigned long *p = addr;
	unsigned long result = 0;
	unsigned long tmp;

	while (size & ~(BITS_PER_LONG-1)) {
		if ((tmp = *(p++)))
			goto found;
		result += BITS_PER_LONG;
		size -= BITS_PER_LONG;
	}
	if (!size)
		return result;

	tmp = (*p) & (~0UL >> (BITS_PER_LONG - size));
	if (tmp == 0UL)		/* Are any bits set? */
		return result + size;	/* Nope. */
found:
	return result + __ffs(tmp);
}

/*
 * Find the first cleared bit in a memory region.
 */
unsigned long find_first_zero_bit(const unsigned long *addr,
		unsigned long size)
{
	const unsigned long *p = addr;
	unsigned long result = 0;
	unsigned long tmp;

	while (size & ~(BITS_PER_LONG-1)) {
		if (~(tmp = *(p++)))
			goto found;
		result += BITS_PER_LONG;
		size -= BITS_PER_LONG;
	}
	if (!size)
		return result;

	tmp = (*p) | (~0UL << size);
	if (tmp == ~0UL)	/* Are any bits zero? */
		return result + size;	/* Nope. */
found:
	return result + ffz(tmp);
}

/**
 * hweightN - returns the hamming weight of a N-bit word
 * @x: the word to weigh
 *
 * The Hamming Weight of a number is the total number of bits set in it.
 */

unsigned int __sw_hweight32(unsigned int w)
{
#ifdef ARCH_HAS_FAST_MULTIPLIER
	w -= (w >> 1) & 0x55555555;
	w =  (w & 0x33333333) + ((w >> 2) & 0x33333333);
	w =  (w + (w >> 4)) & 0x0f0f0f0f;
	return (w * 0x01010101) >> 24;
#else
	unsigned int res = w - ((w >> 1) & 0x55555555);
	res = (res & 0x33333333) + ((res >> 2) & 0x33333333);
	res = (res + (res >> 4)) & 0x0F0F0F0F;
	res = res + (res >> 8);
	return (res + (res >> 16)) & 0x000000FF;
#endif
}

unsigned int __sw_hweight16(unsigned int w)
{
	unsigned int res = w - ((w >> 1) & 0x5555);
	res = (res & 0x3333) + ((res >> 2) & 0x3333);
	res = (res + (res >> 4)) & 0x0F0F;
	return (res + (res >> 8)) & 0x00FF;
}

unsigned int __sw_hweight8(unsigned int w)
{
	unsigned int res = w - ((w >> 1) & 0x55);
	res = (res & 0x33) + ((res >> 2) & 0x33);
	return (res + (res >> 4)) & 0x0F;
}

unsigned long __sw_hweight64(uint64_t w)
{
#ifdef ARCH_HAS_FAST_MULTIPLIER
	w -= (w >> 1) & 0x5555555555555555ul;
	w =  (w & 0x3333333333333333ul) + ((w >> 2) & 0x3333333333333333ul);
	w =  (w + (w >> 4)) & 0x0f0f0f0f0f0f0f0ful;
	return (w * 0x0101010101010101ul) >> 56;
#else
	uint64_t res = w - ((w >> 1) & 0x5555555555555555ul);
	res = (res & 0x3333333333333333ul) + ((res >> 2) & 0x3333333333333333ul);
	res = (res + (res >> 4)) & 0x0F0F0F0F0F0F0F0Ful;
	res = res + (res >> 8);
	res = res + (res >> 16);
	return (res + (res >> 32)) & 0x00000000000000FFul;
#endif
}

unsigned long hweight_long(unsigned long w)
{
	return sizeof(w) == 4 ? __sw_hweight32(w) : __sw_hweight64(w);
}

#endif /* MCKERNEL_RUST_BITOPS */
