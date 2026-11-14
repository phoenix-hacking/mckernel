#include "observations.h"
/* All actual headers and typed declarations are already visible above. */
#define ihklib_os_open observation_os_open
#define ihk_os_get_status observation_status
#define ioctl observation_ioctl
#define close observation_close
#define malloc observation_malloc
#define free observation_free
#define access observation_access
#define bfd_init observation_bfd_init
#define bfd_fopen observation_bfd_fopen
#define bfd_close observation_bfd_close
#define dnprintk(fmt, args...) do {  } while (0)
#define dprintf(fmt, args...) do {  } while (0)
#define dprintk(fmt, args...) do {  } while (0)
#define PHYSMEM_NAME_SIZE 32
int ihk_os_makedumpfile(int index, char *dump_file, int dump_level, int interactive)
{
	int ret;
	static char hname[HOST_NAME_MAX+1];
	bfd *abfd = NULL;
	bfd_boolean ok;
	asection *scn;
	dumpargs_t args;
	unsigned long phys_size, phys_offset;
	int error, i;
	size_t bsize;
	void *buf = NULL;
	uintptr_t addr;
	size_t cpsize;
	time_t t;
	struct tm *tm;
	char *date;
	struct passwd *pw;
	dump_mem_chunks_t *mem_chunks = NULL;
	long mem_size;
	char *physmem_name_buf = NULL;
	char physmem_name[PHYSMEM_NAME_SIZE];
	int osfd = -1;
	char *token;
	int dump_nmi_sent = 0;

	dprintk("%s: enter\n", __func__);
	dprintf("%s: index=%d,dump_file=%s,dump_level=%d,interactive=%d\n",
		__func__, index, dump_file, dump_level, interactive);

	if ((osfd = ihklib_os_open(index)) < 0) {
		dprintf("%s: error: ihklib_os_open returned %d\n",
			__func__, osfd);
		ret = osfd;
		goto out;
	}

	ret = ihk_os_get_status(index);
	if (ret < 0) {
		dprintf("%s: ihk_os_get_status returned %d\n",
			__func__, ret);
		goto out;
	}

	if (ret == IHK_STATUS_INACTIVE) {
		ret = -EINVAL;
		goto out;
	}

	t = time(NULL);
	if (t == (time_t)-1) {
		ret = -errno;
		dprintf("%s: error: time returned %d\n",
			__func__, -ret);
		goto out;
	}

	tm = localtime(&t);
	if (!tm) {
		ret = -EINVAL;
		dprintf("%s: error: localtime failed\n",
			__func__);
		goto out;
	}

	error = gethostname(hname, sizeof(hname));
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: gethostname returned %d\n",
			__func__, -ret);
		goto out;
	}

	/* TODO: might be redundant */
	pw = getpwuid(getuid());
	if (pw == NULL) {
		ret = -errno;
		dprintf("%s: error: getpwuid returned %d\n",
			__func__, -ret);
		goto out;
	}

	args.cmd = DUMP_SET_LEVEL;
	args.level = dump_level;
	error = ioctl(osfd, IHK_OS_DUMP, &args);
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: DUMP_SET_LEVEL returned %d\n",
			__func__, -ret);
		goto out;
	}

	args.cmd = DUMP_NMI;
	error = ioctl(osfd, IHK_OS_DUMP, &args);
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: DUMP_NMI returned %d\n",
			__func__, -ret);
		goto out;
	}
	dump_nmi_sent = 1;

	args.cmd = DUMP_QUERY_NUM_MEM_AREAS;
	args.size = 0;
	error = ioctl(osfd, IHK_OS_DUMP, &args);
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: "
			"DUMP_QUERY_NUM_MEM_AREAS returned %d\n",
			__func__, -ret);
		goto out;
	}

	mem_size = args.size;
	mem_chunks = malloc(mem_size);
	if (!mem_chunks) {
		ret = -ENOMEM;
		dprintf("%s: error: alloating mem_chunks\n",
			__func__);
		goto out;
	}

	memset(mem_chunks, 0, args.size);

	args.cmd = DUMP_QUERY_MEM_AREAS;
	args.buf = (void *)mem_chunks;
	error = ioctl(osfd, IHK_OS_DUMP, &args);
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: DUMP_QUERY_MEM_AREAS returned %d\n",
			__func__, -ret);
		goto out;
	}

	phys_size = 0;
	dprintf("%s: nr chunks: %d\n",
		__func__, mem_chunks->nr_chunks);
	for (i = 0; i < mem_chunks->nr_chunks; ++i) {
		dprintf("%s: 0x%lx:%lu\n",
				__FUNCTION__,
				mem_chunks->chunks[i].addr,
				mem_chunks->chunks[i].size);
		phys_size += mem_chunks->chunks[i].size;
	}

	bsize = 0x100000;
	buf = malloc(bsize);
	if (!buf) {
		ret = -ENOMEM;
		dprintf("%s: error: allocating buf\n", __func__);
		goto out;
	}

	bfd_init();

	if (dump_file == NULL) {
		ret = -EFAULT;
		goto out;
	}

	token = strrchr(dump_file, '/');
	if (token) {
		token[0] = 0;
		ret = access(token == dump_file ? "/" : dump_file, W_OK);
		if (ret) {
			ret = -errno;
			dprintf("%s: %s is inaccessible: %d\n",
				__func__, dump_file, -ret);
			token[0] = '/';
			goto out;
		}
		token[0] = '/';
	}

	abfd = bfd_fopen(dump_file, NULL, "w", -1);
	if (!abfd) {
		ret = -EINVAL;
		dprintf("%s: bfd_fopen failed: %s\n",
			__func__, bfd_errmsg(bfd_get_error()));
		goto out;
	}

 abort(); /* harness: only failed bfd_fopen is in this profile */

 out:
	if (dump_nmi_sent) {
		args.cmd = DUMP_NMI_CONT;
		ioctl(osfd, IHK_OS_DUMP, &args);
	}

	if (abfd) {
		ok = bfd_close(abfd);
		if (!ok) {
			ret = -EINVAL;
			dprintf("%s: error: bfd_close: %s\n",
				__func__, bfd_errmsg(bfd_get_error()));
		}
	}
	if (osfd >= 0) {
		error = close(osfd);
		if (error) {
			ret = -errno;
			dprintf("%s: error: close: %s\n",
				__func__, strerror(-ret));
		}
	}
	{
		int saved_errno = errno;

		free(buf);
		free(mem_chunks);
		errno = saved_errno;
	}
	return ret;
}
