/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <assert.h>
struct list_head { struct list_head *next, *prev; };
struct overlay_fd {
 int fd, getdents_fd, linux_fd;
 struct list_head link;
 char linux_path[PATH_MAX],mck_path[PATH_MAX];
 size_t pathlen;
 void *mck_dirents; size_t mck_dirents_size;
 void *linux_dirents; size_t linux_dirents_size;
};
extern struct list_head overlay_fd_list;
extern pthread_spinlock_t overlay_fd_lock;
extern int debug;
#define __dprintf(format, args...) do { if(debug) { printf("%s: " format,__func__,##args); fflush(stdout); } } while(0)
extern void mcexec_overlay_list_add_body(struct list_head *,struct list_head *);
extern void mcexec_overlay_list_del_body(struct list_head *);
#define overlay_list_add mcexec_overlay_list_add_body
#define overlay_list_del mcexec_overlay_list_del_body
extern int mcexec_dirent_rewrite_offsets_result(void *,size_t,size_t,size_t,int);
int mcexec_overlay_addfd_publish_bridge(int,const char *,const char *,size_t);
void mcexec_overlay_delfd_bridge(int);
void *mcexec_overlay_getdents_find_bridge(int);
int mcexec_overlay_getdents_hide_orig_bridge(void *);
const char *mcexec_overlay_getdents_linux_path_bridge(void *);
size_t mcexec_overlay_getdents_pathlen_bridge(void *);
void *mcexec_overlay_getdents_mck_dirents_bridge(void *);
size_t mcexec_overlay_getdents_mck_size_bridge(void *);
void *mcexec_overlay_getdents_linux_dirents_bridge(void *);
size_t mcexec_overlay_getdents_linux_size_bridge(void *);
int mcexec_overlay_getdents_mck_fd_bridge(void *);
int mcexec_overlay_getdents_linux_fd_bridge(void *);
int mcexec_overlay_getdents_append_mck_bridge(void *,const void *,size_t,int);
int mcexec_overlay_getdents_append_linux_bridge(void *,const void *,size_t,int,int);
