#ifndef __UIO_H
#define __UIO_H

struct iovec
{
	void *iov_base;	/* BSD uses caddr_t (1003.1g requires void *) */
	size_t iov_len; /* Must be size_t (1003.1g) */
};

/*
 * Total number of bytes covered by an iovec.
 *
 * NOTE that it is not safe to use this function until all the iovec's
 * segment lengths have been validated.  Because the individual lengths can
 * overflow a size_t when added together.
 */
size_t iov_length(const struct iovec *iov, unsigned long nr_segs);

#endif
