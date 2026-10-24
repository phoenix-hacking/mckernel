int mcexec_overlay_addfd_publish_bridge(int fd, const char *linux_path,
		const char *mck_path, size_t pathlen)
{
	struct overlay_fd *ofd;

	ofd = malloc(sizeof(*ofd));
	if (!ofd) {
		fprintf(stderr, "%s: out of memory\n", "overlay_addfd");
		return -ENOMEM;
	}

	ofd->fd = fd;
	ofd->getdents_fd = -1;
	ofd->linux_fd = -1;
	ofd->mck_dirents = NULL;
	ofd->mck_dirents_size = 0;
	ofd->linux_dirents = NULL;
	ofd->linux_dirents_size = 0;
	ofd->pathlen = pathlen;
	strncpy(ofd->linux_path, linux_path, PATH_MAX);
	strncpy(ofd->mck_path, mck_path, PATH_MAX);

	pthread_spin_lock(&overlay_fd_lock);
	overlay_list_add(&ofd->link, &overlay_fd_list);
	pthread_spin_unlock(&overlay_fd_lock);

	return 0;
}

void mcexec_overlay_delfd_bridge(int fd)
{
	struct overlay_fd *ofd;

	pthread_spin_lock(&overlay_fd_lock);
	for (ofd = ((typeof(*ofd) *)((char *)((&overlay_fd_list)->next) - offsetof(typeof(*ofd), link))); &ofd->link != (&overlay_fd_list); ofd = ((typeof(*ofd) *)((char *)(ofd->link.next) - offsetof(typeof(*ofd), link)))) {
		if (ofd->fd == fd) {
			overlay_list_del(&ofd->link);
			if (ofd->getdents_fd != -1)
				close(ofd->getdents_fd);
			if (ofd->linux_fd != -1)
				close(ofd->linux_fd);
			free(ofd->mck_dirents);
			free(ofd->linux_dirents);
			free(ofd);
			break;
		}
	}
	pthread_spin_unlock(&overlay_fd_lock);
}

void *mcexec_overlay_getdents_find_bridge(int fd)
{
	struct overlay_fd *ofd_iter;

	pthread_spin_lock(&overlay_fd_lock);
	for (ofd_iter = ((typeof(*ofd_iter) *)((char *)((&overlay_fd_list)->next) - offsetof(typeof(*ofd_iter), link))); &ofd_iter->link != (&overlay_fd_list); ofd_iter = ((typeof(*ofd_iter) *)((char *)(ofd_iter->link.next) - offsetof(typeof(*ofd_iter), link)))) {
		if (ofd_iter->fd == fd) {
			__dprintf("found overlay cache entry (%s)\n",
					ofd_iter->linux_path);
			pthread_spin_unlock(&overlay_fd_lock);
			return ofd_iter;
		}
	}
	pthread_spin_unlock(&overlay_fd_lock);

	return NULL;
}

int mcexec_overlay_getdents_hide_orig_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;
	size_t len;

	if (!ofd || strncmp(ofd->linux_path, "/proc", 5))
		return 0;

	len = strlen(ofd->linux_path);
	return len >= 4 && !strncmp(ofd->linux_path + len - 4, "task", 4);
}

const char *mcexec_overlay_getdents_linux_path_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->linux_path;
}

size_t mcexec_overlay_getdents_pathlen_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->pathlen;
}

void *mcexec_overlay_getdents_mck_dirents_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->mck_dirents;
}

size_t mcexec_overlay_getdents_mck_size_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->mck_dirents_size;
}

void *mcexec_overlay_getdents_linux_dirents_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->linux_dirents;
}

size_t mcexec_overlay_getdents_linux_size_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	return ofd->linux_dirents_size;
}

int mcexec_overlay_getdents_mck_fd_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	if (ofd->getdents_fd == -1) {
		ofd->getdents_fd = open(ofd->mck_path, O_RDONLY | O_DIRECTORY);
		if (ofd->getdents_fd < 0) {
			int error = errno;

			if (error != ENOENT) {
				fprintf(stderr, "%s: could not open %s: %d\n",
					"overlay_getdents", ofd->mck_path,
					error);
			}
			return -error;
		}
	}

	return ofd->getdents_fd;
}

int mcexec_overlay_getdents_linux_fd_bridge(void *opaque)
{
	struct overlay_fd *ofd = opaque;

	if (ofd->linux_fd == -1) {
		ofd->linux_fd = open(ofd->linux_path, O_RDONLY | O_DIRECTORY);
		if (ofd->linux_fd < 0) {
			int error = errno;

			if (error != ENOENT) {
				fprintf(stderr, "%s: could not open %s: %d\n",
					"overlay_getdents", ofd->linux_path,
					error);
			}
			return -error;
		}
	}

	return ofd->linux_fd;
}

int mcexec_overlay_getdents_append_mck_bridge(void *opaque,
		const void *dirp, size_t len, int is64)
{
	struct overlay_fd *ofd = opaque;
	void *newbuf;
	int rc;

	newbuf = realloc(ofd->mck_dirents, ofd->mck_dirents_size + len);
	if (!newbuf) {
		fprintf(stderr, "%s: not enough memory (%zd)",
			"overlay_getdents", ofd->mck_dirents_size + len);
		return -ENOMEM;
	}
	ofd->mck_dirents = newbuf;
	memcpy(ofd->mck_dirents + ofd->mck_dirents_size, dirp, len);

	rc = mcexec_dirent_rewrite_offsets_result(ofd->mck_dirents,
			ofd->mck_dirents_size, ofd->mck_dirents_size + len,
			0, is64);
	if (rc < 0)
		return rc;

	ofd->mck_dirents_size += len;
	return 0;
}

int mcexec_overlay_getdents_append_linux_bridge(void *opaque,
		const void *dirp, size_t len, int is64, int old_ret)
{
	struct overlay_fd *ofd = opaque;
	void *newbuf;
	int rc;

	newbuf = realloc(ofd->linux_dirents, ofd->linux_dirents_size + len);
	if (!newbuf) {
		fprintf(stderr, "%s: not enough memory (%zd)",
			"overlay_getdents", ofd->linux_dirents_size + len);
		return old_ret;
	}
	ofd->linux_dirents = newbuf;
	memcpy(ofd->linux_dirents + ofd->linux_dirents_size, dirp, len);
	ofd->linux_dirents_size += len;

	rc = mcexec_dirent_rewrite_offsets_result(ofd->linux_dirents, 0,
			ofd->linux_dirents_size, ofd->mck_dirents_size,
			is64);
	if (rc < 0)
		return rc;

	return 0;
}
