
typedef unsigned char __u_char;
typedef unsigned short int __u_short;
typedef unsigned int __u_int;
typedef unsigned long int __u_long;
typedef signed char __int8_t;
typedef unsigned char __uint8_t;
typedef signed short int __int16_t;
typedef unsigned short int __uint16_t;
typedef signed int __int32_t;
typedef unsigned int __uint32_t;
typedef signed long int __int64_t;
typedef unsigned long int __uint64_t;
typedef __int8_t __int_least8_t;
typedef __uint8_t __uint_least8_t;
typedef __int16_t __int_least16_t;
typedef __uint16_t __uint_least16_t;
typedef __int32_t __int_least32_t;
typedef __uint32_t __uint_least32_t;
typedef __int64_t __int_least64_t;
typedef __uint64_t __uint_least64_t;
typedef long int __quad_t;
typedef unsigned long int __u_quad_t;
typedef long int __intmax_t;
typedef unsigned long int __uintmax_t;
typedef unsigned long int __dev_t;
typedef unsigned int __uid_t;
typedef unsigned int __gid_t;
typedef unsigned long int __ino_t;
typedef unsigned long int __ino64_t;
typedef unsigned int __mode_t;
typedef unsigned long int __nlink_t;
typedef long int __off_t;
typedef long int __off64_t;
typedef int __pid_t;
typedef struct { int __val[2]; } __fsid_t;
typedef long int __clock_t;
typedef unsigned long int __rlim_t;
typedef unsigned long int __rlim64_t;
typedef unsigned int __id_t;
typedef long int __time_t;
typedef unsigned int __useconds_t;
typedef long int __suseconds_t;
typedef int __daddr_t;
typedef int __key_t;
typedef int __clockid_t;
typedef void * __timer_t;
typedef long int __blksize_t;
typedef long int __blkcnt_t;
typedef long int __blkcnt64_t;
typedef unsigned long int __fsblkcnt_t;
typedef unsigned long int __fsblkcnt64_t;
typedef unsigned long int __fsfilcnt_t;
typedef unsigned long int __fsfilcnt64_t;
typedef long int __fsword_t;
typedef long int __ssize_t;
typedef long int __syscall_slong_t;
typedef unsigned long int __syscall_ulong_t;
typedef __off64_t __loff_t;
typedef char *__caddr_t;
typedef long int __intptr_t;
typedef unsigned int __socklen_t;
typedef int __sig_atomic_t;
typedef __ino_t ino_t;
typedef __ino64_t ino64_t;
struct dirent
  {
    __ino_t d_ino;
    __off_t d_off;
    unsigned short int d_reclen;
    unsigned char d_type;
    char d_name[256];
  };
struct dirent64
  {
    __ino64_t d_ino;
    __off64_t d_off;
    unsigned short int d_reclen;
    unsigned char d_type;
    char d_name[256];
  };
enum
  {
    DT_UNKNOWN = 0,
    DT_FIFO = 1,
    DT_CHR = 2,
    DT_DIR = 4,
    DT_BLK = 6,
    DT_REG = 8,
    DT_LNK = 10,
    DT_SOCK = 12,
    DT_WHT = 14
  };
typedef struct __dirstream DIR;
extern DIR *opendir (const char *__name) __attribute__ ((__nonnull__ (1)));
extern DIR *fdopendir (int __fd);
extern int closedir (DIR *__dirp) __attribute__ ((__nonnull__ (1)));
extern struct dirent *readdir (DIR *__dirp) __attribute__ ((__nonnull__ (1)));
extern struct dirent64 *readdir64 (DIR *__dirp) __attribute__ ((__nonnull__ (1)));
extern int readdir_r (DIR *__restrict __dirp,
        struct dirent *__restrict __entry,
        struct dirent **__restrict __result)
     __attribute__ ((__nonnull__ (1, 2, 3))) __attribute__ ((__deprecated__));
extern int readdir64_r (DIR *__restrict __dirp,
   struct dirent64 *__restrict __entry,
   struct dirent64 **__restrict __result)
  __attribute__ ((__nonnull__ (1, 2, 3))) __attribute__ ((__deprecated__));
extern void rewinddir (DIR *__dirp) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern void seekdir (DIR *__dirp, long int __pos) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern long int telldir (DIR *__dirp) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int dirfd (DIR *__dirp) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
typedef long unsigned int size_t;
extern int scandir (const char *__restrict __dir,
      struct dirent ***__restrict __namelist,
      int (*__selector) (const struct dirent *),
      int (*__cmp) (const struct dirent **,
      const struct dirent **))
     __attribute__ ((__nonnull__ (1, 2)));
extern int scandir64 (const char *__restrict __dir,
        struct dirent64 ***__restrict __namelist,
        int (*__selector) (const struct dirent64 *),
        int (*__cmp) (const struct dirent64 **,
        const struct dirent64 **))
     __attribute__ ((__nonnull__ (1, 2)));
extern int scandirat (int __dfd, const char *__restrict __dir,
        struct dirent ***__restrict __namelist,
        int (*__selector) (const struct dirent *),
        int (*__cmp) (const struct dirent **,
        const struct dirent **))
     __attribute__ ((__nonnull__ (2, 3)));
extern int scandirat64 (int __dfd, const char *__restrict __dir,
   struct dirent64 ***__restrict __namelist,
   int (*__selector) (const struct dirent64 *),
   int (*__cmp) (const struct dirent64 **,
          const struct dirent64 **))
     __attribute__ ((__nonnull__ (2, 3)));
extern int alphasort (const struct dirent **__e1,
        const struct dirent **__e2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int alphasort64 (const struct dirent64 **__e1,
   const struct dirent64 **__e2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern __ssize_t getdirentries (int __fd, char *__restrict __buf,
    size_t __nbytes,
    __off_t *__restrict __basep)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 4)));
extern __ssize_t getdirentries64 (int __fd, char *__restrict __buf,
      size_t __nbytes,
      __off64_t *__restrict __basep)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 4)));
extern int versionsort (const struct dirent **__e1,
   const struct dirent **__e2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int versionsort64 (const struct dirent64 **__e1,
     const struct dirent64 **__e2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));


extern __ssize_t getdents64 (int __fd, void *__buffer, size_t __length)
  __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));


extern int *__errno_location (void) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern char *program_invocation_name;
extern char *program_invocation_short_name;
typedef int error_t;


struct flock
  {
    short int l_type;
    short int l_whence;
    __off_t l_start;
    __off_t l_len;
    __pid_t l_pid;
  };
struct flock64
  {
    short int l_type;
    short int l_whence;
    __off64_t l_start;
    __off64_t l_len;
    __pid_t l_pid;
  };
struct iovec
  {
    void *iov_base;
    size_t iov_len;
  };
enum __pid_type
  {
    F_OWNER_TID = 0,
    F_OWNER_PID,
    F_OWNER_PGRP,
    F_OWNER_GID = F_OWNER_PGRP
  };
struct f_owner_ex
  {
    enum __pid_type type;
    __pid_t pid;
  };
struct file_handle
{
  unsigned int handle_bytes;
  int handle_type;
  unsigned char f_handle[0];
};

extern __ssize_t readahead (int __fd, __off64_t __offset, size_t __count)
    __attribute__ ((__nothrow__ , __leaf__));
extern int sync_file_range (int __fd, __off64_t __offset, __off64_t __count,
       unsigned int __flags);
extern __ssize_t vmsplice (int __fdout, const struct iovec *__iov,
      size_t __count, unsigned int __flags);
extern __ssize_t splice (int __fdin, __off64_t *__offin, int __fdout,
    __off64_t *__offout, size_t __len,
    unsigned int __flags);
extern __ssize_t tee (int __fdin, int __fdout, size_t __len,
        unsigned int __flags);
extern int fallocate (int __fd, int __mode, __off_t __offset, __off_t __len);
extern int fallocate64 (int __fd, int __mode, __off64_t __offset,
   __off64_t __len);
extern int name_to_handle_at (int __dfd, const char *__name,
         struct file_handle *__handle, int *__mnt_id,
         int __flags) __attribute__ ((__nothrow__ , __leaf__));
extern int open_by_handle_at (int __mountdirfd, struct file_handle *__handle,
         int __flags);

typedef __mode_t mode_t;
typedef __off_t off_t;
typedef __off64_t off64_t;
typedef __pid_t pid_t;
struct timespec
{
  __time_t tv_sec;
  __syscall_slong_t tv_nsec;
};
struct stat
  {
    __dev_t st_dev;
    __ino_t st_ino;
    __nlink_t st_nlink;
    __mode_t st_mode;
    __uid_t st_uid;
    __gid_t st_gid;
    int __pad0;
    __dev_t st_rdev;
    __off_t st_size;
    __blksize_t st_blksize;
    __blkcnt_t st_blocks;
    struct timespec st_atim;
    struct timespec st_mtim;
    struct timespec st_ctim;
    __syscall_slong_t __glibc_reserved[3];
  };
struct stat64
  {
    __dev_t st_dev;
    __ino64_t st_ino;
    __nlink_t st_nlink;
    __mode_t st_mode;
    __uid_t st_uid;
    __gid_t st_gid;
    int __pad0;
    __dev_t st_rdev;
    __off_t st_size;
    __blksize_t st_blksize;
    __blkcnt64_t st_blocks;
    struct timespec st_atim;
    struct timespec st_mtim;
    struct timespec st_ctim;
    __syscall_slong_t __glibc_reserved[3];
  };
extern int fcntl (int __fd, int __cmd, ...);
extern int fcntl64 (int __fd, int __cmd, ...);
extern int open (const char *__file, int __oflag, ...) __attribute__ ((__nonnull__ (1)));
extern int open64 (const char *__file, int __oflag, ...) __attribute__ ((__nonnull__ (1)));
extern int openat (int __fd, const char *__file, int __oflag, ...)
     __attribute__ ((__nonnull__ (2)));
extern int openat64 (int __fd, const char *__file, int __oflag, ...)
     __attribute__ ((__nonnull__ (2)));
extern int creat (const char *__file, mode_t __mode) __attribute__ ((__nonnull__ (1)));
extern int creat64 (const char *__file, mode_t __mode) __attribute__ ((__nonnull__ (1)));
extern int lockf (int __fd, int __cmd, off_t __len);
extern int lockf64 (int __fd, int __cmd, off64_t __len);
extern int posix_fadvise (int __fd, off_t __offset, off_t __len,
     int __advise) __attribute__ ((__nothrow__ , __leaf__));
extern int posix_fadvise64 (int __fd, off64_t __offset, off64_t __len,
       int __advise) __attribute__ ((__nothrow__ , __leaf__));
extern int posix_fallocate (int __fd, off_t __offset, off_t __len);
extern int posix_fallocate64 (int __fd, off64_t __offset, off64_t __len);
extern int __open_2 (const char *__path, int __oflag) __attribute__ ((__nonnull__ (1)));
extern int __open_alias (const char *__path, int __oflag, ...) __asm__ ("" "open") __attribute__ ((__nonnull__ (1)));
extern void __open_too_many_args (void) __attribute__((__error__ ("open can be called either with 2 or 3 arguments, not more")));
extern void __open_missing_mode (void) __attribute__((__error__ ("open with O_CREAT or O_TMPFILE in second argument needs 3 arguments")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
open (const char *__path, int __oflag, ...)
{
  if (__builtin_va_arg_pack_len () > 1)
    __open_too_many_args ();
  if (__builtin_constant_p (__oflag))
    {
      if ((((__oflag) & 0100) != 0 || ((__oflag) & (020000000 | 0200000)) == (020000000 | 0200000)) && __builtin_va_arg_pack_len () < 1)
 {
   __open_missing_mode ();
   return __open_2 (__path, __oflag);
 }
      return __open_alias (__path, __oflag, __builtin_va_arg_pack ());
    }
  if (__builtin_va_arg_pack_len () < 1)
    return __open_2 (__path, __oflag);
  return __open_alias (__path, __oflag, __builtin_va_arg_pack ());
}
extern int __open64_2 (const char *__path, int __oflag) __attribute__ ((__nonnull__ (1)));
extern int __open64_alias (const char *__path, int __oflag, ...) __asm__ ("" "open64") __attribute__ ((__nonnull__ (1)));
extern void __open64_too_many_args (void) __attribute__((__error__ ("open64 can be called either with 2 or 3 arguments, not more")));
extern void __open64_missing_mode (void) __attribute__((__error__ ("open64 with O_CREAT or O_TMPFILE in second argument needs 3 arguments")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
open64 (const char *__path, int __oflag, ...)
{
  if (__builtin_va_arg_pack_len () > 1)
    __open64_too_many_args ();
  if (__builtin_constant_p (__oflag))
    {
      if ((((__oflag) & 0100) != 0 || ((__oflag) & (020000000 | 0200000)) == (020000000 | 0200000)) && __builtin_va_arg_pack_len () < 1)
 {
   __open64_missing_mode ();
   return __open64_2 (__path, __oflag);
 }
      return __open64_alias (__path, __oflag, __builtin_va_arg_pack ());
    }
  if (__builtin_va_arg_pack_len () < 1)
    return __open64_2 (__path, __oflag);
  return __open64_alias (__path, __oflag, __builtin_va_arg_pack ());
}
extern int __openat_2 (int __fd, const char *__path, int __oflag)
     __attribute__ ((__nonnull__ (2)));
extern int __openat_alias (int __fd, const char *__path, int __oflag, ...) __asm__ ("" "openat")
     __attribute__ ((__nonnull__ (2)));
extern void __openat_too_many_args (void) __attribute__((__error__ ("openat can be called either with 3 or 4 arguments, not more")));
extern void __openat_missing_mode (void) __attribute__((__error__ ("openat with O_CREAT or O_TMPFILE in third argument needs 4 arguments")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
openat (int __fd, const char *__path, int __oflag, ...)
{
  if (__builtin_va_arg_pack_len () > 1)
    __openat_too_many_args ();
  if (__builtin_constant_p (__oflag))
    {
      if ((((__oflag) & 0100) != 0 || ((__oflag) & (020000000 | 0200000)) == (020000000 | 0200000)) && __builtin_va_arg_pack_len () < 1)
 {
   __openat_missing_mode ();
   return __openat_2 (__fd, __path, __oflag);
 }
      return __openat_alias (__fd, __path, __oflag, __builtin_va_arg_pack ());
    }
  if (__builtin_va_arg_pack_len () < 1)
    return __openat_2 (__fd, __path, __oflag);
  return __openat_alias (__fd, __path, __oflag, __builtin_va_arg_pack ());
}
extern int __openat64_2 (int __fd, const char *__path, int __oflag)
     __attribute__ ((__nonnull__ (2)));
extern int __openat64_alias (int __fd, const char *__path, int __oflag, ...) __asm__ ("" "openat64")
     __attribute__ ((__nonnull__ (2)));
extern void __openat64_too_many_args (void) __attribute__((__error__ ("openat64 can be called either with 3 or 4 arguments, not more")));
extern void __openat64_missing_mode (void) __attribute__((__error__ ("openat64 with O_CREAT or O_TMPFILE in third argument needs 4 arguments")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
openat64 (int __fd, const char *__path, int __oflag, ...)
{
  if (__builtin_va_arg_pack_len () > 1)
    __openat64_too_many_args ();
  if (__builtin_constant_p (__oflag))
    {
      if ((((__oflag) & 0100) != 0 || ((__oflag) & (020000000 | 0200000)) == (020000000 | 0200000)) && __builtin_va_arg_pack_len () < 1)
 {
   __openat64_missing_mode ();
   return __openat64_2 (__fd, __path, __oflag);
 }
      return __openat64_alias (__fd, __path, __oflag, __builtin_va_arg_pack ());
    }
  if (__builtin_va_arg_pack_len () < 1)
    return __openat64_2 (__fd, __path, __oflag);
  return __openat64_alias (__fd, __path, __oflag, __builtin_va_arg_pack ());
}

typedef struct
{
  unsigned long int __val[(1024 / (8 * sizeof (unsigned long int)))];
} __sigset_t;
typedef unsigned long int nfds_t;
struct pollfd
  {
    int fd;
    short int events;
    short int revents;
  };

extern int poll (struct pollfd *__fds, nfds_t __nfds, int __timeout);
extern int ppoll (struct pollfd *__fds, nfds_t __nfds,
    const struct timespec *__timeout,
    const __sigset_t *__ss);


extern int __poll_alias (struct pollfd *__fds, nfds_t __nfds, int __timeout) __asm__ ("" "poll");
extern int __poll_chk (struct pollfd *__fds, nfds_t __nfds, int __timeout,
         long unsigned int __fdslen);
extern int __poll_chk_warn (struct pollfd *__fds, nfds_t __nfds, int __timeout, long unsigned int __fdslen) __asm__ ("" "__poll_chk")
  __attribute__((__warning__ ("poll called with fds buffer too small file nfds entries")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
poll (struct pollfd *__fds, nfds_t __nfds, int __timeout)
{
  if (__builtin_object_size (__fds, 2 > 1) != (long unsigned int) -1)
    {
      if (! __builtin_constant_p (__nfds))
 return __poll_chk (__fds, __nfds, __timeout, __builtin_object_size (__fds, 2 > 1));
      else if (__builtin_object_size (__fds, 2 > 1) / sizeof (*__fds) < __nfds)
 return __poll_chk_warn (__fds, __nfds, __timeout, __builtin_object_size (__fds, 2 > 1));
    }
  return __poll_alias (__fds, __nfds, __timeout);
}
extern int __ppoll_alias (struct pollfd *__fds, nfds_t __nfds, const struct timespec *__timeout, const __sigset_t *__ss) __asm__ ("" "ppoll");
extern int __ppoll_chk (struct pollfd *__fds, nfds_t __nfds,
   const struct timespec *__timeout,
   const __sigset_t *__ss, long unsigned int __fdslen);
extern int __ppoll_chk_warn (struct pollfd *__fds, nfds_t __nfds, const struct timespec *__timeout, const __sigset_t *__ss, long unsigned int __fdslen) __asm__ ("" "__ppoll_chk")
  __attribute__((__warning__ ("ppoll called with fds buffer too small file nfds entries")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
ppoll (struct pollfd *__fds, nfds_t __nfds, const struct timespec *__timeout,
       const __sigset_t *__ss)
{
  if (__builtin_object_size (__fds, 2 > 1) != (long unsigned int) -1)
    {
      if (! __builtin_constant_p (__nfds))
 return __ppoll_chk (__fds, __nfds, __timeout, __ss, __builtin_object_size (__fds, 2 > 1));
      else if (__builtin_object_size (__fds, 2 > 1) / sizeof (*__fds) < __nfds)
 return __ppoll_chk_warn (__fds, __nfds, __timeout, __ss,
     __builtin_object_size (__fds, 2 > 1));
    }
  return __ppoll_alias (__fds, __nfds, __timeout, __ss);
}


typedef __sig_atomic_t sig_atomic_t;
typedef __sigset_t sigset_t;
typedef __uid_t uid_t;
union sigval
{
  int sival_int;
  void *sival_ptr;
};
typedef union sigval __sigval_t;
typedef struct
  {
    int si_signo;
    int si_errno;
    int si_code;
    int __pad0;
    union
      {
 int _pad[((128 / sizeof (int)) - 4)];
 struct
   {
     __pid_t si_pid;
     __uid_t si_uid;
   } _kill;
 struct
   {
     int si_tid;
     int si_overrun;
     __sigval_t si_sigval;
   } _timer;
 struct
   {
     __pid_t si_pid;
     __uid_t si_uid;
     __sigval_t si_sigval;
   } _rt;
 struct
   {
     __pid_t si_pid;
     __uid_t si_uid;
     int si_status;
     __clock_t si_utime;
     __clock_t si_stime;
   } _sigchld;
 struct
   {
     void *si_addr;
    
     short int si_addr_lsb;
     union
       {
  struct
    {
      void *_lower;
      void *_upper;
    } _addr_bnd;
  __uint32_t _pkey;
       } _bounds;
   } _sigfault;
 struct
   {
     long int si_band;
     int si_fd;
   } _sigpoll;
 struct
   {
     void *_call_addr;
     int _syscall;
     unsigned int _arch;
   } _sigsys;
      } _sifields;
  } siginfo_t ;
enum
{
  SI_ASYNCNL = -60,
  SI_DETHREAD = -7,
  SI_TKILL,
  SI_SIGIO,
  SI_ASYNCIO,
  SI_MESGQ,
  SI_TIMER,
  SI_QUEUE,
  SI_USER,
  SI_KERNEL = 0x80
};
enum
{
  ILL_ILLOPC = 1,
  ILL_ILLOPN,
  ILL_ILLADR,
  ILL_ILLTRP,
  ILL_PRVOPC,
  ILL_PRVREG,
  ILL_COPROC,
  ILL_BADSTK,
  ILL_BADIADDR
};
enum
{
  FPE_INTDIV = 1,
  FPE_INTOVF,
  FPE_FLTDIV,
  FPE_FLTOVF,
  FPE_FLTUND,
  FPE_FLTRES,
  FPE_FLTINV,
  FPE_FLTSUB,
  FPE_FLTUNK = 14,
  FPE_CONDTRAP
};
enum
{
  SEGV_MAPERR = 1,
  SEGV_ACCERR,
  SEGV_BNDERR,
  SEGV_PKUERR,
  SEGV_ACCADI,
  SEGV_ADIDERR,
  SEGV_ADIPERR
};
enum
{
  BUS_ADRALN = 1,
  BUS_ADRERR,
  BUS_OBJERR,
  BUS_MCEERR_AR,
  BUS_MCEERR_AO
};
enum
{
  TRAP_BRKPT = 1,
  TRAP_TRACE,
  TRAP_BRANCH,
  TRAP_HWBKPT,
  TRAP_UNK
};
enum
{
  CLD_EXITED = 1,
  CLD_KILLED,
  CLD_DUMPED,
  CLD_TRAPPED,
  CLD_STOPPED,
  CLD_CONTINUED
};
enum
{
  POLL_IN = 1,
  POLL_OUT,
  POLL_MSG,
  POLL_ERR,
  POLL_PRI,
  POLL_HUP
};
typedef __sigval_t sigval_t;
typedef union pthread_attr_t pthread_attr_t;
typedef struct sigevent
  {
    __sigval_t sigev_value;
    int sigev_signo;
    int sigev_notify;
    union
      {
 int _pad[((64 / sizeof (int)) - 4)];
 __pid_t _tid;
 struct
   {
     void (*_function) (__sigval_t);
     pthread_attr_t *_attribute;
   } _sigev_thread;
      } _sigev_un;
  } sigevent_t;
enum
{
  SIGEV_SIGNAL = 0,
  SIGEV_NONE,
  SIGEV_THREAD,
  SIGEV_THREAD_ID = 4
};
typedef void (*__sighandler_t) (int);
extern __sighandler_t __sysv_signal (int __sig, __sighandler_t __handler)
     __attribute__ ((__nothrow__ , __leaf__));
extern __sighandler_t sysv_signal (int __sig, __sighandler_t __handler)
     __attribute__ ((__nothrow__ , __leaf__));
extern __sighandler_t signal (int __sig, __sighandler_t __handler)
     __attribute__ ((__nothrow__ , __leaf__));
extern int kill (__pid_t __pid, int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern int killpg (__pid_t __pgrp, int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern int raise (int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern __sighandler_t ssignal (int __sig, __sighandler_t __handler)
     __attribute__ ((__nothrow__ , __leaf__));
extern int gsignal (int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern void psignal (int __sig, const char *__s);
extern void psiginfo (const siginfo_t *__pinfo, const char *__s);
extern int sigpause (int __sig) __asm__ ("__xpg_sigpause");
extern int sigblock (int __mask) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__deprecated__));
extern int sigsetmask (int __mask) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__deprecated__));
extern int siggetmask (void) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__deprecated__));
typedef __sighandler_t sighandler_t;
typedef __sighandler_t sig_t;
extern int sigemptyset (sigset_t *__set) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int sigfillset (sigset_t *__set) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int sigaddset (sigset_t *__set, int __signo) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int sigdelset (sigset_t *__set, int __signo) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int sigismember (const sigset_t *__set, int __signo)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int sigisemptyset (const sigset_t *__set) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int sigandset (sigset_t *__set, const sigset_t *__left,
        const sigset_t *__right) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2, 3)));
extern int sigorset (sigset_t *__set, const sigset_t *__left,
       const sigset_t *__right) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2, 3)));
struct sigaction
  {
    union
      {
 __sighandler_t sa_handler;
 void (*sa_sigaction) (int, siginfo_t *, void *);
      }
    __sigaction_handler;
    __sigset_t sa_mask;
    int sa_flags;
    void (*sa_restorer) (void);
  };
extern int sigprocmask (int __how, const sigset_t *__restrict __set,
   sigset_t *__restrict __oset) __attribute__ ((__nothrow__ , __leaf__));
extern int sigsuspend (const sigset_t *__set) __attribute__ ((__nonnull__ (1)));
extern int sigaction (int __sig, const struct sigaction *__restrict __act,
        struct sigaction *__restrict __oact) __attribute__ ((__nothrow__ , __leaf__));
extern int sigpending (sigset_t *__set) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int sigwait (const sigset_t *__restrict __set, int *__restrict __sig)
     __attribute__ ((__nonnull__ (1, 2)));
extern int sigwaitinfo (const sigset_t *__restrict __set,
   siginfo_t *__restrict __info) __attribute__ ((__nonnull__ (1)));
extern int sigtimedwait (const sigset_t *__restrict __set,
    siginfo_t *__restrict __info,
    const struct timespec *__restrict __timeout)
     __attribute__ ((__nonnull__ (1)));
extern int sigqueue (__pid_t __pid, int __sig, const union sigval __val)
     __attribute__ ((__nothrow__ , __leaf__));
extern const char *const _sys_siglist[(64 + 1)];
extern const char *const sys_siglist[(64 + 1)];
struct _fpx_sw_bytes
{
  __uint32_t magic1;
  __uint32_t extended_size;
  __uint64_t xstate_bv;
  __uint32_t xstate_size;
  __uint32_t __glibc_reserved1[7];
};
struct _fpreg
{
  unsigned short significand[4];
  unsigned short exponent;
};
struct _fpxreg
{
  unsigned short significand[4];
  unsigned short exponent;
  unsigned short __glibc_reserved1[3];
};
struct _xmmreg
{
  __uint32_t element[4];
};
struct _fpstate
{
  __uint16_t cwd;
  __uint16_t swd;
  __uint16_t ftw;
  __uint16_t fop;
  __uint64_t rip;
  __uint64_t rdp;
  __uint32_t mxcsr;
  __uint32_t mxcr_mask;
  struct _fpxreg _st[8];
  struct _xmmreg _xmm[16];
  __uint32_t __glibc_reserved1[24];
};
struct sigcontext
{
  __uint64_t r8;
  __uint64_t r9;
  __uint64_t r10;
  __uint64_t r11;
  __uint64_t r12;
  __uint64_t r13;
  __uint64_t r14;
  __uint64_t r15;
  __uint64_t rdi;
  __uint64_t rsi;
  __uint64_t rbp;
  __uint64_t rbx;
  __uint64_t rdx;
  __uint64_t rax;
  __uint64_t rcx;
  __uint64_t rsp;
  __uint64_t rip;
  __uint64_t eflags;
  unsigned short cs;
  unsigned short gs;
  unsigned short fs;
  unsigned short __pad0;
  __uint64_t err;
  __uint64_t trapno;
  __uint64_t oldmask;
  __uint64_t cr2;
  __extension__ union
    {
      struct _fpstate * fpstate;
      __uint64_t __fpstate_word;
    };
  __uint64_t __reserved1 [8];
};
struct _xsave_hdr
{
  __uint64_t xstate_bv;
  __uint64_t __glibc_reserved1[2];
  __uint64_t __glibc_reserved2[5];
};
struct _ymmh_state
{
  __uint32_t ymmh_space[64];
};
struct _xstate
{
  struct _fpstate fpstate;
  struct _xsave_hdr xstate_hdr;
  struct _ymmh_state ymmh;
};
extern int sigreturn (struct sigcontext *__scp) __attribute__ ((__nothrow__ , __leaf__));
typedef struct
  {
    void *ss_sp;
    int ss_flags;
    size_t ss_size;
  } stack_t;
__extension__ typedef long long int greg_t;
typedef greg_t gregset_t[23];
enum
{
  REG_R8 = 0,
  REG_R9,
  REG_R10,
  REG_R11,
  REG_R12,
  REG_R13,
  REG_R14,
  REG_R15,
  REG_RDI,
  REG_RSI,
  REG_RBP,
  REG_RBX,
  REG_RDX,
  REG_RAX,
  REG_RCX,
  REG_RSP,
  REG_RIP,
  REG_EFL,
  REG_CSGSFS,
  REG_ERR,
  REG_TRAPNO,
  REG_OLDMASK,
  REG_CR2
};
struct _libc_fpxreg
{
  unsigned short int significand[4];
  unsigned short int exponent;
  unsigned short int __glibc_reserved1[3];
};
struct _libc_xmmreg
{
  __uint32_t element[4];
};
struct _libc_fpstate
{
  __uint16_t cwd;
  __uint16_t swd;
  __uint16_t ftw;
  __uint16_t fop;
  __uint64_t rip;
  __uint64_t rdp;
  __uint32_t mxcsr;
  __uint32_t mxcr_mask;
  struct _libc_fpxreg _st[8];
  struct _libc_xmmreg _xmm[16];
  __uint32_t __glibc_reserved1[24];
};
typedef struct _libc_fpstate *fpregset_t;
typedef struct
  {
    gregset_t gregs;
    fpregset_t fpregs;
    __extension__ unsigned long long __reserved1 [8];
} mcontext_t;
typedef struct ucontext_t
  {
    unsigned long int uc_flags;
    struct ucontext_t *uc_link;
    stack_t uc_stack;
    mcontext_t uc_mcontext;
    sigset_t uc_sigmask;
    struct _libc_fpstate __fpregs_mem;
    __extension__ unsigned long long int __ssp[4];
  } ucontext_t;
extern int siginterrupt (int __sig, int __interrupt) __attribute__ ((__nothrow__ , __leaf__));
enum
{
  SS_ONSTACK = 1,
  SS_DISABLE
};
extern int sigaltstack (const stack_t *__restrict __ss,
   stack_t *__restrict __oss) __attribute__ ((__nothrow__ , __leaf__));
struct sigstack
  {
    void *ss_sp;
    int ss_onstack;
  };
extern int sigstack (struct sigstack *__ss, struct sigstack *__oss)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__deprecated__));
extern int sighold (int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern int sigrelse (int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern int sigignore (int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern __sighandler_t sigset (int __sig, __sighandler_t __disp) __attribute__ ((__nothrow__ , __leaf__));
typedef struct __pthread_internal_list
{
  struct __pthread_internal_list *__prev;
  struct __pthread_internal_list *__next;
} __pthread_list_t;
typedef struct __pthread_internal_slist
{
  struct __pthread_internal_slist *__next;
} __pthread_slist_t;
struct __pthread_mutex_s
{
  int __lock;
  unsigned int __count;
  int __owner;
  unsigned int __nusers;
  int __kind;
  short __spins;
  short __elision;
  __pthread_list_t __list;
};
struct __pthread_rwlock_arch_t
{
  unsigned int __readers;
  unsigned int __writers;
  unsigned int __wrphase_futex;
  unsigned int __writers_futex;
  unsigned int __pad3;
  unsigned int __pad4;
  int __cur_writer;
  int __shared;
  signed char __rwelision;
  unsigned char __pad1[7];
  unsigned long int __pad2;
  unsigned int __flags;
};
struct __pthread_cond_s
{
  __extension__ union
  {
    __extension__ unsigned long long int __wseq;
    struct
    {
      unsigned int __low;
      unsigned int __high;
    } __wseq32;
  };
  __extension__ union
  {
    __extension__ unsigned long long int __g1_start;
    struct
    {
      unsigned int __low;
      unsigned int __high;
    } __g1_start32;
  };
  unsigned int __g_refs[2] ;
  unsigned int __g_size[2];
  unsigned int __g1_orig_size;
  unsigned int __wrefs;
  unsigned int __g_signals[2];
};
typedef unsigned long int pthread_t;
typedef union
{
  char __size[4];
  int __align;
} pthread_mutexattr_t;
typedef union
{
  char __size[4];
  int __align;
} pthread_condattr_t;
typedef unsigned int pthread_key_t;
typedef int pthread_once_t;
union pthread_attr_t
{
  char __size[56];
  long int __align;
};
typedef union
{
  struct __pthread_mutex_s __data;
  char __size[40];
  long int __align;
} pthread_mutex_t;
typedef union
{
  struct __pthread_cond_s __data;
  char __size[48];
  __extension__ long long int __align;
} pthread_cond_t;
typedef union
{
  struct __pthread_rwlock_arch_t __data;
  char __size[56];
  long int __align;
} pthread_rwlock_t;
typedef union
{
  char __size[8];
  long int __align;
} pthread_rwlockattr_t;
typedef volatile int pthread_spinlock_t;
typedef union
{
  char __size[32];
  long int __align;
} pthread_barrier_t;
typedef union
{
  char __size[4];
  int __align;
} pthread_barrierattr_t;
extern int pthread_sigmask (int __how,
       const __sigset_t *__restrict __newmask,
       __sigset_t *__restrict __oldmask)__attribute__ ((__nothrow__ , __leaf__));
extern int pthread_kill (pthread_t __threadid, int __signo) __attribute__ ((__nothrow__ , __leaf__));
extern int pthread_sigqueue (pthread_t __threadid, int __signo,
        const union sigval __value) __attribute__ ((__nothrow__ , __leaf__));
extern int __libc_current_sigrtmin (void) __attribute__ ((__nothrow__ , __leaf__));
extern int __libc_current_sigrtmax (void) __attribute__ ((__nothrow__ , __leaf__));
extern int tgkill (__pid_t __tgid, __pid_t __tid, int __signal);

typedef __builtin_va_list __gnuc_va_list;
typedef __gnuc_va_list va_list;
typedef __int8_t int8_t;
typedef __int16_t int16_t;
typedef __int32_t int32_t;
typedef __int64_t int64_t;
typedef __uint8_t uint8_t;
typedef __uint16_t uint16_t;
typedef __uint32_t uint32_t;
typedef __uint64_t uint64_t;
typedef __int_least8_t int_least8_t;
typedef __int_least16_t int_least16_t;
typedef __int_least32_t int_least32_t;
typedef __int_least64_t int_least64_t;
typedef __uint_least8_t uint_least8_t;
typedef __uint_least16_t uint_least16_t;
typedef __uint_least32_t uint_least32_t;
typedef __uint_least64_t uint_least64_t;
typedef signed char int_fast8_t;
typedef long int int_fast16_t;
typedef long int int_fast32_t;
typedef long int int_fast64_t;
typedef unsigned char uint_fast8_t;
typedef unsigned long int uint_fast16_t;
typedef unsigned long int uint_fast32_t;
typedef unsigned long int uint_fast64_t;
typedef long int intptr_t;
typedef unsigned long int uintptr_t;
typedef __intmax_t intmax_t;
typedef __uintmax_t uintmax_t;

typedef struct
{
  int __count;
  union
  {
    unsigned int __wch;
    char __wchb[4];
  } __value;
} __mbstate_t;
typedef struct _G_fpos_t
{
  __off_t __pos;
  __mbstate_t __state;
} __fpos_t;
typedef struct _G_fpos64_t
{
  __off64_t __pos;
  __mbstate_t __state;
} __fpos64_t;
struct _IO_FILE;
typedef struct _IO_FILE __FILE;
struct _IO_FILE;
typedef struct _IO_FILE FILE;
struct _IO_FILE;
struct _IO_marker;
struct _IO_codecvt;
struct _IO_wide_data;
typedef void _IO_lock_t;
struct _IO_FILE
{
  int _flags;
  char *_IO_read_ptr;
  char *_IO_read_end;
  char *_IO_read_base;
  char *_IO_write_base;
  char *_IO_write_ptr;
  char *_IO_write_end;
  char *_IO_buf_base;
  char *_IO_buf_end;
  char *_IO_save_base;
  char *_IO_backup_base;
  char *_IO_save_end;
  struct _IO_marker *_markers;
  struct _IO_FILE *_chain;
  int _fileno;
  int _flags2;
  __off_t _old_offset;
  unsigned short _cur_column;
  signed char _vtable_offset;
  char _shortbuf[1];
  _IO_lock_t *_lock;
  __off64_t _offset;
  struct _IO_codecvt *_codecvt;
  struct _IO_wide_data *_wide_data;
  struct _IO_FILE *_freeres_list;
  void *_freeres_buf;
  size_t __pad5;
  int _mode;
  char _unused2[15 * sizeof (int) - 4 * sizeof (void *) - sizeof (size_t)];
};
typedef __ssize_t cookie_read_function_t (void *__cookie, char *__buf,
                                          size_t __nbytes);
typedef __ssize_t cookie_write_function_t (void *__cookie, const char *__buf,
                                           size_t __nbytes);
typedef int cookie_seek_function_t (void *__cookie, __off64_t *__pos, int __w);
typedef int cookie_close_function_t (void *__cookie);
typedef struct _IO_cookie_io_functions_t
{
  cookie_read_function_t *read;
  cookie_write_function_t *write;
  cookie_seek_function_t *seek;
  cookie_close_function_t *close;
} cookie_io_functions_t;
typedef __ssize_t ssize_t;
typedef __fpos_t fpos_t;
typedef __fpos64_t fpos64_t;
extern FILE *stdin;
extern FILE *stdout;
extern FILE *stderr;
extern int remove (const char *__filename) __attribute__ ((__nothrow__ , __leaf__));
extern int rename (const char *__old, const char *__new) __attribute__ ((__nothrow__ , __leaf__));
extern int renameat (int __oldfd, const char *__old, int __newfd,
       const char *__new) __attribute__ ((__nothrow__ , __leaf__));
extern int renameat2 (int __oldfd, const char *__old, int __newfd,
        const char *__new, unsigned int __flags) __attribute__ ((__nothrow__ , __leaf__));
extern FILE *tmpfile (void) __attribute__ ((__warn_unused_result__));
extern FILE *tmpfile64 (void) __attribute__ ((__warn_unused_result__));
extern char *tmpnam (char *__s) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern char *tmpnam_r (char *__s) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern char *tempnam (const char *__dir, const char *__pfx)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__malloc__)) __attribute__ ((__warn_unused_result__));
extern int fclose (FILE *__stream);
extern int fflush (FILE *__stream);
extern int fflush_unlocked (FILE *__stream);
extern int fcloseall (void);
extern FILE *fopen (const char *__restrict __filename,
      const char *__restrict __modes) __attribute__ ((__warn_unused_result__));
extern FILE *freopen (const char *__restrict __filename,
        const char *__restrict __modes,
        FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern FILE *fopen64 (const char *__restrict __filename,
        const char *__restrict __modes) __attribute__ ((__warn_unused_result__));
extern FILE *freopen64 (const char *__restrict __filename,
   const char *__restrict __modes,
   FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern FILE *fdopen (int __fd, const char *__modes) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern FILE *fopencookie (void *__restrict __magic_cookie,
     const char *__restrict __modes,
     cookie_io_functions_t __io_funcs) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern FILE *fmemopen (void *__s, size_t __len, const char *__modes)
  __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern FILE *open_memstream (char **__bufloc, size_t *__sizeloc) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern void setbuf (FILE *__restrict __stream, char *__restrict __buf) __attribute__ ((__nothrow__ , __leaf__));
extern int setvbuf (FILE *__restrict __stream, char *__restrict __buf,
      int __modes, size_t __n) __attribute__ ((__nothrow__ , __leaf__));
extern void setbuffer (FILE *__restrict __stream, char *__restrict __buf,
         size_t __size) __attribute__ ((__nothrow__ , __leaf__));
extern void setlinebuf (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int fprintf (FILE *__restrict __stream,
      const char *__restrict __format, ...);
extern int printf (const char *__restrict __format, ...);
extern int sprintf (char *__restrict __s,
      const char *__restrict __format, ...) __attribute__ ((__nothrow__));
extern int vfprintf (FILE *__restrict __s, const char *__restrict __format,
       __gnuc_va_list __arg);
extern int vprintf (const char *__restrict __format, __gnuc_va_list __arg);
extern int vsprintf (char *__restrict __s, const char *__restrict __format,
       __gnuc_va_list __arg) __attribute__ ((__nothrow__));
extern int snprintf (char *__restrict __s, size_t __maxlen,
       const char *__restrict __format, ...)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 3, 4)));
extern int vsnprintf (char *__restrict __s, size_t __maxlen,
        const char *__restrict __format, __gnuc_va_list __arg)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 3, 0)));
extern int vasprintf (char **__restrict __ptr, const char *__restrict __f,
        __gnuc_va_list __arg)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 2, 0))) __attribute__ ((__warn_unused_result__));
extern int __asprintf (char **__restrict __ptr,
         const char *__restrict __fmt, ...)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 2, 3))) __attribute__ ((__warn_unused_result__));
extern int asprintf (char **__restrict __ptr,
       const char *__restrict __fmt, ...)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 2, 3))) __attribute__ ((__warn_unused_result__));
extern int vdprintf (int __fd, const char *__restrict __fmt,
       __gnuc_va_list __arg)
     __attribute__ ((__format__ (__printf__, 2, 0)));
extern int dprintf (int __fd, const char *__restrict __fmt, ...)
     __attribute__ ((__format__ (__printf__, 2, 3)));
extern int fscanf (FILE *__restrict __stream,
     const char *__restrict __format, ...) __attribute__ ((__warn_unused_result__));
extern int scanf (const char *__restrict __format, ...) __attribute__ ((__warn_unused_result__));
extern int sscanf (const char *__restrict __s,
     const char *__restrict __format, ...) __attribute__ ((__nothrow__ , __leaf__));
extern int fscanf (FILE *__restrict __stream, const char *__restrict __format, ...) __asm__ ("" "__isoc99_fscanf") __attribute__ ((__warn_unused_result__));
extern int scanf (const char *__restrict __format, ...) __asm__ ("" "__isoc99_scanf") __attribute__ ((__warn_unused_result__));
extern int sscanf (const char *__restrict __s, const char *__restrict __format, ...) __asm__ ("" "__isoc99_sscanf") __attribute__ ((__nothrow__ , __leaf__));
extern int vfscanf (FILE *__restrict __s, const char *__restrict __format,
      __gnuc_va_list __arg)
     __attribute__ ((__format__ (__scanf__, 2, 0))) __attribute__ ((__warn_unused_result__));
extern int vscanf (const char *__restrict __format, __gnuc_va_list __arg)
     __attribute__ ((__format__ (__scanf__, 1, 0))) __attribute__ ((__warn_unused_result__));
extern int vsscanf (const char *__restrict __s,
      const char *__restrict __format, __gnuc_va_list __arg)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__format__ (__scanf__, 2, 0)));
extern int vfscanf (FILE *__restrict __s, const char *__restrict __format, __gnuc_va_list __arg) __asm__ ("" "__isoc99_vfscanf")
     __attribute__ ((__format__ (__scanf__, 2, 0))) __attribute__ ((__warn_unused_result__));
extern int vscanf (const char *__restrict __format, __gnuc_va_list __arg) __asm__ ("" "__isoc99_vscanf")
     __attribute__ ((__format__ (__scanf__, 1, 0))) __attribute__ ((__warn_unused_result__));
extern int vsscanf (const char *__restrict __s, const char *__restrict __format, __gnuc_va_list __arg) __asm__ ("" "__isoc99_vsscanf") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__format__ (__scanf__, 2, 0)));
extern int fgetc (FILE *__stream);
extern int getc (FILE *__stream);
extern int getchar (void);
extern int getc_unlocked (FILE *__stream);
extern int getchar_unlocked (void);
extern int fgetc_unlocked (FILE *__stream);
extern int fputc (int __c, FILE *__stream);
extern int putc (int __c, FILE *__stream);
extern int putchar (int __c);
extern int fputc_unlocked (int __c, FILE *__stream);
extern int putc_unlocked (int __c, FILE *__stream);
extern int putchar_unlocked (int __c);
extern int getw (FILE *__stream);
extern int putw (int __w, FILE *__stream);
extern char *fgets (char *__restrict __s, int __n, FILE *__restrict __stream)
     __attribute__ ((__warn_unused_result__));
extern char *fgets_unlocked (char *__restrict __s, int __n,
        FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern __ssize_t __getdelim (char **__restrict __lineptr,
                             size_t *__restrict __n, int __delimiter,
                             FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern __ssize_t getdelim (char **__restrict __lineptr,
                           size_t *__restrict __n, int __delimiter,
                           FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern __ssize_t getline (char **__restrict __lineptr,
                          size_t *__restrict __n,
                          FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern int fputs (const char *__restrict __s, FILE *__restrict __stream);
extern int puts (const char *__s);
extern int ungetc (int __c, FILE *__stream);
extern size_t fread (void *__restrict __ptr, size_t __size,
       size_t __n, FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern size_t fwrite (const void *__restrict __ptr, size_t __size,
        size_t __n, FILE *__restrict __s);
extern int fputs_unlocked (const char *__restrict __s,
      FILE *__restrict __stream);
extern size_t fread_unlocked (void *__restrict __ptr, size_t __size,
         size_t __n, FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern size_t fwrite_unlocked (const void *__restrict __ptr, size_t __size,
          size_t __n, FILE *__restrict __stream);
extern int fseek (FILE *__stream, long int __off, int __whence);
extern long int ftell (FILE *__stream) __attribute__ ((__warn_unused_result__));
extern void rewind (FILE *__stream);
extern int fseeko (FILE *__stream, __off_t __off, int __whence);
extern __off_t ftello (FILE *__stream) __attribute__ ((__warn_unused_result__));
extern int fgetpos (FILE *__restrict __stream, fpos_t *__restrict __pos);
extern int fsetpos (FILE *__stream, const fpos_t *__pos);
extern int fseeko64 (FILE *__stream, __off64_t __off, int __whence);
extern __off64_t ftello64 (FILE *__stream) __attribute__ ((__warn_unused_result__));
extern int fgetpos64 (FILE *__restrict __stream, fpos64_t *__restrict __pos);
extern int fsetpos64 (FILE *__stream, const fpos64_t *__pos);
extern void clearerr (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int feof (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int ferror (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern void clearerr_unlocked (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int feof_unlocked (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int ferror_unlocked (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern void perror (const char *__s);
extern int sys_nerr;
extern const char *const sys_errlist[];
extern int _sys_nerr;
extern const char *const _sys_errlist[];
extern int fileno (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int fileno_unlocked (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern FILE *popen (const char *__command, const char *__modes) __attribute__ ((__warn_unused_result__));
extern int pclose (FILE *__stream);
extern char *ctermid (char *__s) __attribute__ ((__nothrow__ , __leaf__));
extern char *cuserid (char *__s);
struct obstack;
extern int obstack_printf (struct obstack *__restrict __obstack,
      const char *__restrict __format, ...)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 2, 3)));
extern int obstack_vprintf (struct obstack *__restrict __obstack,
       const char *__restrict __format,
       __gnuc_va_list __args)
     __attribute__ ((__nothrow__)) __attribute__ ((__format__ (__printf__, 2, 0)));
extern void flockfile (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int ftrylockfile (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern void funlockfile (FILE *__stream) __attribute__ ((__nothrow__ , __leaf__));
extern int __uflow (FILE *);
extern int __overflow (FILE *, int);
extern __inline __attribute__ ((__gnu_inline__)) int
getchar (void)
{
  return getc (stdin);
}
extern __inline __attribute__ ((__gnu_inline__)) int
fgetc_unlocked (FILE *__fp)
{
  return (__builtin_expect (((__fp)->_IO_read_ptr >= (__fp)->_IO_read_end), 0) ? __uflow (__fp) : *(unsigned char *) (__fp)->_IO_read_ptr++);
}
extern __inline __attribute__ ((__gnu_inline__)) int
getc_unlocked (FILE *__fp)
{
  return (__builtin_expect (((__fp)->_IO_read_ptr >= (__fp)->_IO_read_end), 0) ? __uflow (__fp) : *(unsigned char *) (__fp)->_IO_read_ptr++);
}
extern __inline __attribute__ ((__gnu_inline__)) int
getchar_unlocked (void)
{
  return (__builtin_expect (((stdin)->_IO_read_ptr >= (stdin)->_IO_read_end), 0) ? __uflow (stdin) : *(unsigned char *) (stdin)->_IO_read_ptr++);
}
extern __inline __attribute__ ((__gnu_inline__)) int
putchar (int __c)
{
  return putc (__c, stdout);
}
extern __inline __attribute__ ((__gnu_inline__)) int
fputc_unlocked (int __c, FILE *__stream)
{
  return (__builtin_expect (((__stream)->_IO_write_ptr >= (__stream)->_IO_write_end), 0) ? __overflow (__stream, (unsigned char) (__c)) : (unsigned char) (*(__stream)->_IO_write_ptr++ = (__c)));
}
extern __inline __attribute__ ((__gnu_inline__)) int
putc_unlocked (int __c, FILE *__stream)
{
  return (__builtin_expect (((__stream)->_IO_write_ptr >= (__stream)->_IO_write_end), 0) ? __overflow (__stream, (unsigned char) (__c)) : (unsigned char) (*(__stream)->_IO_write_ptr++ = (__c)));
}
extern __inline __attribute__ ((__gnu_inline__)) int
putchar_unlocked (int __c)
{
  return (__builtin_expect (((stdout)->_IO_write_ptr >= (stdout)->_IO_write_end), 0) ? __overflow (stdout, (unsigned char) (__c)) : (unsigned char) (*(stdout)->_IO_write_ptr++ = (__c)));
}
extern __inline __attribute__ ((__gnu_inline__)) __ssize_t
getline (char **__lineptr, size_t *__n, FILE *__stream)
{
  return __getdelim (__lineptr, __n, '\n', __stream);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) feof_unlocked (FILE *__stream)
{
  return (((__stream)->_flags & 0x0010) != 0);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) ferror_unlocked (FILE *__stream)
{
  return (((__stream)->_flags & 0x0020) != 0);
}
extern int __sprintf_chk (char *__restrict __s, int __flag, size_t __slen,
     const char *__restrict __format, ...) __attribute__ ((__nothrow__ , __leaf__));
extern int __vsprintf_chk (char *__restrict __s, int __flag, size_t __slen,
      const char *__restrict __format,
      __gnuc_va_list __ap) __attribute__ ((__nothrow__ , __leaf__));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) sprintf (char *__restrict __s, const char *__restrict __fmt, ...)
{
  return __builtin___sprintf_chk (__s, 2 - 1,
      __builtin_object_size (__s, 2 > 1), __fmt, __builtin_va_arg_pack ());
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) vsprintf (char *__restrict __s, const char *__restrict __fmt, __gnuc_va_list __ap)
{
  return __builtin___vsprintf_chk (__s, 2 - 1,
       __builtin_object_size (__s, 2 > 1), __fmt, __ap);
}
extern int __snprintf_chk (char *__restrict __s, size_t __n, int __flag,
      size_t __slen, const char *__restrict __format,
      ...) __attribute__ ((__nothrow__ , __leaf__));
extern int __vsnprintf_chk (char *__restrict __s, size_t __n, int __flag,
       size_t __slen, const char *__restrict __format,
       __gnuc_va_list __ap) __attribute__ ((__nothrow__ , __leaf__));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) snprintf (char *__restrict __s, size_t __n, const char *__restrict __fmt, ...)
{
  return __builtin___snprintf_chk (__s, __n, 2 - 1,
       __builtin_object_size (__s, 2 > 1), __fmt, __builtin_va_arg_pack ());
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) vsnprintf (char *__restrict __s, size_t __n, const char *__restrict __fmt, __gnuc_va_list __ap)
{
  return __builtin___vsnprintf_chk (__s, __n, 2 - 1,
        __builtin_object_size (__s, 2 > 1), __fmt, __ap);
}
extern int __fprintf_chk (FILE *__restrict __stream, int __flag,
     const char *__restrict __format, ...);
extern int __printf_chk (int __flag, const char *__restrict __format, ...);
extern int __vfprintf_chk (FILE *__restrict __stream, int __flag,
      const char *__restrict __format, __gnuc_va_list __ap);
extern int __vprintf_chk (int __flag, const char *__restrict __format,
     __gnuc_va_list __ap);
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
fprintf (FILE *__restrict __stream, const char *__restrict __fmt, ...)
{
  return __fprintf_chk (__stream, 2 - 1, __fmt,
   __builtin_va_arg_pack ());
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
printf (const char *__restrict __fmt, ...)
{
  return __printf_chk (2 - 1, __fmt, __builtin_va_arg_pack ());
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
vprintf (const char *__restrict __fmt, __gnuc_va_list __ap)
{
  return __vfprintf_chk (stdout, 2 - 1, __fmt, __ap);
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
vfprintf (FILE *__restrict __stream,
   const char *__restrict __fmt, __gnuc_va_list __ap)
{
  return __vfprintf_chk (__stream, 2 - 1, __fmt, __ap);
}
extern int __dprintf_chk (int __fd, int __flag, const char *__restrict __fmt,
     ...) __attribute__ ((__format__ (__printf__, 3, 4)));
extern int __vdprintf_chk (int __fd, int __flag,
      const char *__restrict __fmt, __gnuc_va_list __arg)
     __attribute__ ((__format__ (__printf__, 3, 0)));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
dprintf (int __fd, const char *__restrict __fmt, ...)
{
  return __dprintf_chk (__fd, 2 - 1, __fmt,
   __builtin_va_arg_pack ());
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
vdprintf (int __fd, const char *__restrict __fmt, __gnuc_va_list __ap)
{
  return __vdprintf_chk (__fd, 2 - 1, __fmt, __ap);
}
extern int __asprintf_chk (char **__restrict __ptr, int __flag,
      const char *__restrict __fmt, ...)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__format__ (__printf__, 3, 4))) __attribute__ ((__warn_unused_result__));
extern int __vasprintf_chk (char **__restrict __ptr, int __flag,
       const char *__restrict __fmt, __gnuc_va_list __arg)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__format__ (__printf__, 3, 0))) __attribute__ ((__warn_unused_result__));
extern int __obstack_printf_chk (struct obstack *__restrict __obstack,
     int __flag, const char *__restrict __format,
     ...)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__format__ (__printf__, 3, 4)));
extern int __obstack_vprintf_chk (struct obstack *__restrict __obstack,
      int __flag,
      const char *__restrict __format,
      __gnuc_va_list __args)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__format__ (__printf__, 3, 0)));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) asprintf (char **__restrict __ptr, const char *__restrict __fmt, ...)
{
  return __asprintf_chk (__ptr, 2 - 1, __fmt,
    __builtin_va_arg_pack ());
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) __asprintf (char **__restrict __ptr, const char *__restrict __fmt, ...)
{
  return __asprintf_chk (__ptr, 2 - 1, __fmt,
    __builtin_va_arg_pack ());
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) obstack_printf (struct obstack *__restrict __obstack, const char *__restrict __fmt, ...)
{
  return __obstack_printf_chk (__obstack, 2 - 1, __fmt,
          __builtin_va_arg_pack ());
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) vasprintf (char **__restrict __ptr, const char *__restrict __fmt, __gnuc_va_list __ap)
{
  return __vasprintf_chk (__ptr, 2 - 1, __fmt, __ap);
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) obstack_vprintf (struct obstack *__restrict __obstack, const char *__restrict __fmt, __gnuc_va_list __ap)
{
  return __obstack_vprintf_chk (__obstack, 2 - 1, __fmt,
    __ap);
}
extern char *__fgets_chk (char *__restrict __s, size_t __size, int __n,
     FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern char *__fgets_alias (char *__restrict __s, int __n, FILE *__restrict __stream) __asm__ ("" "fgets") __attribute__ ((__warn_unused_result__));
extern char *__fgets_chk_warn (char *__restrict __s, size_t __size, int __n, FILE *__restrict __stream) __asm__ ("" "__fgets_chk")
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("fgets called with bigger size than length " "of destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__warn_unused_result__)) char *
fgets (char *__restrict __s, int __n, FILE *__restrict __stream)
{
  if (__builtin_object_size (__s, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__n) || __n <= 0)
 return __fgets_chk (__s, __builtin_object_size (__s, 2 > 1), __n, __stream);
      if ((size_t) __n > __builtin_object_size (__s, 2 > 1))
 return __fgets_chk_warn (__s, __builtin_object_size (__s, 2 > 1), __n, __stream);
    }
  return __fgets_alias (__s, __n, __stream);
}
extern size_t __fread_chk (void *__restrict __ptr, size_t __ptrlen,
      size_t __size, size_t __n,
      FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern size_t __fread_alias (void *__restrict __ptr, size_t __size, size_t __n, FILE *__restrict __stream) __asm__ ("" "fread") __attribute__ ((__warn_unused_result__));
extern size_t __fread_chk_warn (void *__restrict __ptr, size_t __ptrlen, size_t __size, size_t __n, FILE *__restrict __stream) __asm__ ("" "__fread_chk")
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("fread called with bigger size * nmemb than length " "of destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__warn_unused_result__)) size_t
fread (void *__restrict __ptr, size_t __size, size_t __n,
       FILE *__restrict __stream)
{
  if (__builtin_object_size (__ptr, 0) != (size_t) -1)
    {
      if (!__builtin_constant_p (__size)
   || !__builtin_constant_p (__n)
   || (__size | __n) >= (((size_t) 1) << (8 * sizeof (size_t) / 2)))
 return __fread_chk (__ptr, __builtin_object_size (__ptr, 0), __size, __n, __stream);
      if (__size * __n > __builtin_object_size (__ptr, 0))
 return __fread_chk_warn (__ptr, __builtin_object_size (__ptr, 0), __size, __n, __stream);
    }
  return __fread_alias (__ptr, __size, __n, __stream);
}
extern char *__fgets_unlocked_chk (char *__restrict __s, size_t __size,
       int __n, FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern char *__fgets_unlocked_alias (char *__restrict __s, int __n, FILE *__restrict __stream) __asm__ ("" "fgets_unlocked") __attribute__ ((__warn_unused_result__));
extern char *__fgets_unlocked_chk_warn (char *__restrict __s, size_t __size, int __n, FILE *__restrict __stream) __asm__ ("" "__fgets_unlocked_chk")
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("fgets_unlocked called with bigger size than length " "of destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__warn_unused_result__)) char *
fgets_unlocked (char *__restrict __s, int __n, FILE *__restrict __stream)
{
  if (__builtin_object_size (__s, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__n) || __n <= 0)
 return __fgets_unlocked_chk (__s, __builtin_object_size (__s, 2 > 1), __n, __stream);
      if ((size_t) __n > __builtin_object_size (__s, 2 > 1))
 return __fgets_unlocked_chk_warn (__s, __builtin_object_size (__s, 2 > 1), __n, __stream);
    }
  return __fgets_unlocked_alias (__s, __n, __stream);
}
extern size_t __fread_unlocked_chk (void *__restrict __ptr, size_t __ptrlen,
        size_t __size, size_t __n,
        FILE *__restrict __stream) __attribute__ ((__warn_unused_result__));
extern size_t __fread_unlocked_alias (void *__restrict __ptr, size_t __size, size_t __n, FILE *__restrict __stream) __asm__ ("" "fread_unlocked") __attribute__ ((__warn_unused_result__));
extern size_t __fread_unlocked_chk_warn (void *__restrict __ptr, size_t __ptrlen, size_t __size, size_t __n, FILE *__restrict __stream) __asm__ ("" "__fread_unlocked_chk")
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("fread_unlocked called with bigger size * nmemb than " "length of destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__warn_unused_result__)) size_t
fread_unlocked (void *__restrict __ptr, size_t __size, size_t __n,
  FILE *__restrict __stream)
{
  if (__builtin_object_size (__ptr, 0) != (size_t) -1)
    {
      if (!__builtin_constant_p (__size)
   || !__builtin_constant_p (__n)
   || (__size | __n) >= (((size_t) 1) << (8 * sizeof (size_t) / 2)))
 return __fread_unlocked_chk (__ptr, __builtin_object_size (__ptr, 0), __size, __n,
         __stream);
      if (__size * __n > __builtin_object_size (__ptr, 0))
 return __fread_unlocked_chk_warn (__ptr, __builtin_object_size (__ptr, 0), __size, __n,
       __stream);
    }
  if (__builtin_constant_p (__size)
      && __builtin_constant_p (__n)
      && (__size | __n) < (((size_t) 1) << (8 * sizeof (size_t) / 2))
      && __size * __n <= 8)
    {
      size_t __cnt = __size * __n;
      char *__cptr = (char *) __ptr;
      if (__cnt == 0)
 return 0;
      for (; __cnt > 0; --__cnt)
 {
   int __c = getc_unlocked (__stream);
   if (__c == (-1))
     break;
   *__cptr++ = __c;
 }
      return (__cptr - (char *) __ptr) / __size;
    }
  return __fread_unlocked_alias (__ptr, __size, __n, __stream);
}


extern void *memcpy (void *__restrict __dest, const void *__restrict __src,
       size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *memmove (void *__dest, const void *__src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *memccpy (void *__restrict __dest, const void *__restrict __src,
        int __c, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *memset (void *__s, int __c, size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int memcmp (const void *__s1, const void *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *memchr (const void *__s, int __c, size_t __n)
      __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern void *rawmemchr (const void *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern void *memrchr (const void *__s, int __c, size_t __n)
      __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *strcpy (char *__restrict __dest, const char *__restrict __src)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strncpy (char *__restrict __dest,
        const char *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strcat (char *__restrict __dest, const char *__restrict __src)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strncat (char *__restrict __dest, const char *__restrict __src,
        size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strcmp (const char *__s1, const char *__s2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strncmp (const char *__s1, const char *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strcoll (const char *__s1, const char *__s2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern size_t strxfrm (char *__restrict __dest,
         const char *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
struct __locale_struct
{
  struct __locale_data *__locales[13];
  const unsigned short int *__ctype_b;
  const int *__ctype_tolower;
  const int *__ctype_toupper;
  const char *__names[13];
};
typedef struct __locale_struct *__locale_t;
typedef __locale_t locale_t;
extern int strcoll_l (const char *__s1, const char *__s2, locale_t __l)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2, 3)));
extern size_t strxfrm_l (char *__dest, const char *__src, size_t __n,
    locale_t __l) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 4)));
extern char *strdup (const char *__s)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__malloc__)) __attribute__ ((__nonnull__ (1)));
extern char *strndup (const char *__string, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__malloc__)) __attribute__ ((__nonnull__ (1)));
extern char *strchr (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *strrchr (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *strchrnul (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern size_t strcspn (const char *__s, const char *__reject)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern size_t strspn (const char *__s, const char *__accept)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strpbrk (const char *__s, const char *__accept)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strstr (const char *__haystack, const char *__needle)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strtok (char *__restrict __s, const char *__restrict __delim)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern char *__strtok_r (char *__restrict __s,
    const char *__restrict __delim,
    char **__restrict __save_ptr)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern char *strtok_r (char *__restrict __s, const char *__restrict __delim,
         char **__restrict __save_ptr)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern char *strcasestr (const char *__haystack, const char *__needle)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *memmem (const void *__haystack, size_t __haystacklen,
       const void *__needle, size_t __needlelen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 3)));
extern void *__mempcpy (void *__restrict __dest,
   const void *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void *mempcpy (void *__restrict __dest,
        const void *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern size_t strlen (const char *__s)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern size_t strnlen (const char *__string, size_t __maxlen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *strerror (int __errnum) __attribute__ ((__nothrow__ , __leaf__));
extern char *strerror_r (int __errnum, char *__buf, size_t __buflen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2))) __attribute__ ((__warn_unused_result__));
extern char *strerror_l (int __errnum, locale_t __l) __attribute__ ((__nothrow__ , __leaf__));

extern int bcmp (const void *__s1, const void *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern void bcopy (const void *__src, void *__dest, size_t __n)
  __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void bzero (void *__s, size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern char *index (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern char *rindex (const char *__s, int __c)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern int ffs (int __i) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern int ffsl (long int __l) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
__extension__ extern int ffsll (long long int __ll)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern int strcasecmp (const char *__s1, const char *__s2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strncasecmp (const char *__s1, const char *__s2, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strcasecmp_l (const char *__s1, const char *__s2, locale_t __loc)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2, 3)));
extern int strncasecmp_l (const char *__s1, const char *__s2,
     size_t __n, locale_t __loc)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2, 4)));

extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) void
__attribute__ ((__nothrow__ , __leaf__)) bcopy (const void *__src, void *__dest, size_t __len)
{
  (void) __builtin___memmove_chk (__dest, __src, __len, __builtin_object_size (__dest, 0));
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) void
__attribute__ ((__nothrow__ , __leaf__)) bzero (void *__dest, size_t __len)
{
  (void) __builtin___memset_chk (__dest, '\0', __len, __builtin_object_size (__dest, 0));
}
extern void explicit_bzero (void *__s, size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern char *strsep (char **__restrict __stringp,
       const char *__restrict __delim)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strsignal (int __sig) __attribute__ ((__nothrow__ , __leaf__));
extern char *__stpcpy (char *__restrict __dest, const char *__restrict __src)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *stpcpy (char *__restrict __dest, const char *__restrict __src)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *__stpncpy (char *__restrict __dest,
   const char *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *stpncpy (char *__restrict __dest,
        const char *__restrict __src, size_t __n)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int strverscmp (const char *__s1, const char *__s2)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1, 2)));
extern char *strfry (char *__string) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern void *memfrob (void *__s, size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern char *basename (const char *__filename) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) void *
__attribute__ ((__nothrow__ , __leaf__)) memcpy (void *__restrict __dest, const void *__restrict __src, size_t __len)
{
  return __builtin___memcpy_chk (__dest, __src, __len, __builtin_object_size (__dest, 0));
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) void *
__attribute__ ((__nothrow__ , __leaf__)) memmove (void *__dest, const void *__src, size_t __len)
{
  return __builtin___memmove_chk (__dest, __src, __len, __builtin_object_size (__dest, 0));
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) void *
__attribute__ ((__nothrow__ , __leaf__)) mempcpy (void *__restrict __dest, const void *__restrict __src, size_t __len)
{
  return __builtin___mempcpy_chk (__dest, __src, __len, __builtin_object_size (__dest, 0));
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) void *
__attribute__ ((__nothrow__ , __leaf__)) memset (void *__dest, int __ch, size_t __len)
{
  return __builtin___memset_chk (__dest, __ch, __len, __builtin_object_size (__dest, 0));
}
void __explicit_bzero_chk (void *__dest, size_t __len, size_t __destlen)
  __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) void
__attribute__ ((__nothrow__ , __leaf__)) explicit_bzero (void *__dest, size_t __len)
{
  __explicit_bzero_chk (__dest, __len, __builtin_object_size (__dest, 0));
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) char *
__attribute__ ((__nothrow__ , __leaf__)) strcpy (char *__restrict __dest, const char *__restrict __src)
{
  return __builtin___strcpy_chk (__dest, __src, __builtin_object_size (__dest, 2 > 1));
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) char *
__attribute__ ((__nothrow__ , __leaf__)) stpcpy (char *__restrict __dest, const char *__restrict __src)
{
  return __builtin___stpcpy_chk (__dest, __src, __builtin_object_size (__dest, 2 > 1));
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) char *
__attribute__ ((__nothrow__ , __leaf__)) strncpy (char *__restrict __dest, const char *__restrict __src, size_t __len)
{
  return __builtin___strncpy_chk (__dest, __src, __len, __builtin_object_size (__dest, 2 > 1));
}
extern char *__stpncpy_chk (char *__dest, const char *__src, size_t __n,
       size_t __destlen) __attribute__ ((__nothrow__ , __leaf__));
extern char *__stpncpy_alias (char *__dest, const char *__src, size_t __n) __asm__ ("" "stpncpy") __attribute__ ((__nothrow__ , __leaf__));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) char *
__attribute__ ((__nothrow__ , __leaf__)) stpncpy (char *__dest, const char *__src, size_t __n)
{
  if (__builtin_object_size (__dest, 2 > 1) != (size_t) -1
      && (!__builtin_constant_p (__n) || __n > __builtin_object_size (__dest, 2 > 1)))
    return __stpncpy_chk (__dest, __src, __n, __builtin_object_size (__dest, 2 > 1));
  return __stpncpy_alias (__dest, __src, __n);
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) char *
__attribute__ ((__nothrow__ , __leaf__)) strcat (char *__restrict __dest, const char *__restrict __src)
{
  return __builtin___strcat_chk (__dest, __src, __builtin_object_size (__dest, 2 > 1));
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) char *
__attribute__ ((__nothrow__ , __leaf__)) strncat (char *__restrict __dest, const char *__restrict __src, size_t __len)
{
  return __builtin___strncat_chk (__dest, __src, __len, __builtin_object_size (__dest, 2 > 1));
}


extern int klogctl (int __type, char *__bufp, int __len) __attribute__ ((__nothrow__ , __leaf__));


struct winsize
  {
    unsigned short int ws_row;
    unsigned short int ws_col;
    unsigned short int ws_xpixel;
    unsigned short int ws_ypixel;
  };
struct termio
  {
    unsigned short int c_iflag;
    unsigned short int c_oflag;
    unsigned short int c_cflag;
    unsigned short int c_lflag;
    unsigned char c_line;
    unsigned char c_cc[8];
};
extern int ioctl (int __fd, unsigned long int __request, ...) __attribute__ ((__nothrow__ , __leaf__));

enum
{
  MS_RDONLY = 1,
  MS_NOSUID = 2,
  MS_NODEV = 4,
  MS_NOEXEC = 8,
  MS_SYNCHRONOUS = 16,
  MS_REMOUNT = 32,
  MS_MANDLOCK = 64,
  MS_DIRSYNC = 128,
  MS_NOATIME = 1024,
  MS_NODIRATIME = 2048,
  MS_BIND = 4096,
  MS_MOVE = 8192,
  MS_REC = 16384,
  MS_SILENT = 32768,
  MS_POSIXACL = 1 << 16,
  MS_UNBINDABLE = 1 << 17,
  MS_PRIVATE = 1 << 18,
  MS_SLAVE = 1 << 19,
  MS_SHARED = 1 << 20,
  MS_RELATIME = 1 << 21,
  MS_KERNMOUNT = 1 << 22,
  MS_I_VERSION = 1 << 23,
  MS_STRICTATIME = 1 << 24,
  MS_LAZYTIME = 1 << 25,
  MS_ACTIVE = 1 << 30,
  MS_NOUSER = 1 << 31
};
enum
{
  MNT_FORCE = 1,
  MNT_DETACH = 2,
  MNT_EXPIRE = 4,
  UMOUNT_NOFOLLOW = 8
};

extern int mount (const char *__special_file, const char *__dir,
    const char *__fstype, unsigned long int __rwflag,
    const void *__data) __attribute__ ((__nothrow__ , __leaf__));
extern int umount (const char *__special_file) __attribute__ ((__nothrow__ , __leaf__));
extern int umount2 (const char *__special_file, int __flags) __attribute__ ((__nothrow__ , __leaf__));

typedef __signed__ char __s8;
typedef unsigned char __u8;
typedef __signed__ short __s16;
typedef unsigned short __u16;
typedef __signed__ int __s32;
typedef unsigned int __u32;
__extension__ typedef __signed__ long long __s64;
__extension__ typedef unsigned long long __u64;
typedef struct {
 unsigned long fds_bits[1024 / (8 * sizeof(long))];
} __kernel_fd_set;
typedef void (*__kernel_sighandler_t)(int);
typedef int __kernel_key_t;
typedef int __kernel_mqd_t;
typedef unsigned short __kernel_old_uid_t;
typedef unsigned short __kernel_old_gid_t;
typedef unsigned long __kernel_old_dev_t;
typedef long __kernel_long_t;
typedef unsigned long __kernel_ulong_t;
typedef __kernel_ulong_t __kernel_ino_t;
typedef unsigned int __kernel_mode_t;
typedef int __kernel_pid_t;
typedef int __kernel_ipc_pid_t;
typedef unsigned int __kernel_uid_t;
typedef unsigned int __kernel_gid_t;
typedef __kernel_long_t __kernel_suseconds_t;
typedef int __kernel_daddr_t;
typedef unsigned int __kernel_uid32_t;
typedef unsigned int __kernel_gid32_t;
typedef __kernel_ulong_t __kernel_size_t;
typedef __kernel_long_t __kernel_ssize_t;
typedef __kernel_long_t __kernel_ptrdiff_t;
typedef struct {
 int val[2];
} __kernel_fsid_t;
typedef __kernel_long_t __kernel_off_t;
typedef long long __kernel_loff_t;
typedef __kernel_long_t __kernel_time_t;
typedef long long __kernel_time64_t;
typedef __kernel_long_t __kernel_clock_t;
typedef int __kernel_timer_t;
typedef int __kernel_clockid_t;
typedef char * __kernel_caddr_t;
typedef unsigned short __kernel_uid16_t;
typedef unsigned short __kernel_gid16_t;
typedef __u16 __le16;
typedef __u16 __be16;
typedef __u32 __le32;
typedef __u32 __be32;
typedef __u64 __le64;
typedef __u64 __be64;
typedef __u16 __sum16;
typedef __u32 __wsum;
typedef unsigned __poll_t;
struct prctl_mm_map {
 __u64 start_code;
 __u64 end_code;
 __u64 start_data;
 __u64 end_data;
 __u64 start_brk;
 __u64 brk;
 __u64 start_stack;
 __u64 arg_start;
 __u64 arg_end;
 __u64 env_start;
 __u64 env_end;
 __u64 *auxv;
 __u32 auxv_size;
 __u32 exe_fd;
};

extern int prctl (int __option, ...) __attribute__ ((__nothrow__ , __leaf__));


extern int reboot (int __howto) __attribute__ ((__nothrow__ , __leaf__));

typedef __time_t time_t;
typedef __dev_t dev_t;
typedef __gid_t gid_t;
typedef __nlink_t nlink_t;
typedef __blkcnt_t blkcnt_t;
typedef __blksize_t blksize_t;

extern int stat (const char *__restrict __file,
   struct stat *__restrict __buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int fstat (int __fd, struct stat *__buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int stat64 (const char *__restrict __file,
     struct stat64 *__restrict __buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int fstat64 (int __fd, struct stat64 *__buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int fstatat (int __fd, const char *__restrict __file,
      struct stat *__restrict __buf, int __flag)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern int fstatat64 (int __fd, const char *__restrict __file,
        struct stat64 *__restrict __buf, int __flag)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern int lstat (const char *__restrict __file,
    struct stat *__restrict __buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int lstat64 (const char *__restrict __file,
      struct stat64 *__restrict __buf)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int chmod (const char *__file, __mode_t __mode)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int lchmod (const char *__file, __mode_t __mode)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int fchmod (int __fd, __mode_t __mode) __attribute__ ((__nothrow__ , __leaf__));
extern int fchmodat (int __fd, const char *__file, __mode_t __mode,
       int __flag)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2))) __attribute__ ((__warn_unused_result__));
extern __mode_t umask (__mode_t __mask) __attribute__ ((__nothrow__ , __leaf__));
extern __mode_t getumask (void) __attribute__ ((__nothrow__ , __leaf__));
extern int mkdir (const char *__path, __mode_t __mode)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int mkdirat (int __fd, const char *__path, __mode_t __mode)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int mknod (const char *__path, __mode_t __mode, __dev_t __dev)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int mknodat (int __fd, const char *__path, __mode_t __mode,
      __dev_t __dev) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int mkfifo (const char *__path, __mode_t __mode)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int mkfifoat (int __fd, const char *__path, __mode_t __mode)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int utimensat (int __fd, const char *__path,
        const struct timespec __times[2],
        int __flags)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int futimens (int __fd, const struct timespec __times[2]) __attribute__ ((__nothrow__ , __leaf__));
extern int __fxstat (int __ver, int __fildes, struct stat *__stat_buf)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (3)));
extern int __xstat (int __ver, const char *__filename,
      struct stat *__stat_buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern int __lxstat (int __ver, const char *__filename,
       struct stat *__stat_buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern int __fxstatat (int __ver, int __fildes, const char *__filename,
         struct stat *__stat_buf, int __flag)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (3, 4)));
extern int __fxstat64 (int __ver, int __fildes, struct stat64 *__stat_buf)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (3)));
extern int __xstat64 (int __ver, const char *__filename,
        struct stat64 *__stat_buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern int __lxstat64 (int __ver, const char *__filename,
         struct stat64 *__stat_buf) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));
extern int __fxstatat64 (int __ver, int __fildes, const char *__filename,
    struct stat64 *__stat_buf, int __flag)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (3, 4)));
extern int __xmknod (int __ver, const char *__path, __mode_t __mode,
       __dev_t *__dev) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 4)));
extern int __xmknodat (int __ver, int __fd, const char *__path,
         __mode_t __mode, __dev_t *__dev)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (3, 5)));
struct statx_timestamp {
 __s64 tv_sec;
 __u32 tv_nsec;
 __s32 __reserved;
};
struct statx {
 __u32 stx_mask;
 __u32 stx_blksize;
 __u64 stx_attributes;
 __u32 stx_nlink;
 __u32 stx_uid;
 __u32 stx_gid;
 __u16 stx_mode;
 __u16 __spare0[1];
 __u64 stx_ino;
 __u64 stx_size;
 __u64 stx_blocks;
 __u64 stx_attributes_mask;
 struct statx_timestamp stx_atime;
 struct statx_timestamp stx_btime;
 struct statx_timestamp stx_ctime;
 struct statx_timestamp stx_mtime;
 __u32 stx_rdev_major;
 __u32 stx_rdev_minor;
 __u32 stx_dev_major;
 __u32 stx_dev_minor;
 __u64 __spare2[14];
};

int statx (int __dirfd, const char *__restrict __path, int __flags,
           unsigned int __mask, struct statx *__restrict __buf)
  __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 5)));

extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) stat (const char *__path, struct stat *__statbuf)
{
  return __xstat (1, __path, __statbuf);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) lstat (const char *__path, struct stat *__statbuf)
{
  return __lxstat (1, __path, __statbuf);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) fstat (int __fd, struct stat *__statbuf)
{
  return __fxstat (1, __fd, __statbuf);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) fstatat (int __fd, const char *__filename, struct stat *__statbuf, int __flag)
{
  return __fxstatat (1, __fd, __filename, __statbuf, __flag);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) mknod (const char *__path, __mode_t __mode, __dev_t __dev)
{
  return __xmknod (0, __path, __mode, &__dev);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) mknodat (int __fd, const char *__path, __mode_t __mode, __dev_t __dev)
{
  return __xmknodat (0, __fd, __path, __mode, &__dev);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) stat64 (const char *__path, struct stat64 *__statbuf)
{
  return __xstat64 (1, __path, __statbuf);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) lstat64 (const char *__path, struct stat64 *__statbuf)
{
  return __lxstat64 (1, __path, __statbuf);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) fstat64 (int __fd, struct stat64 *__statbuf)
{
  return __fxstat64 (1, __fd, __statbuf);
}
extern __inline __attribute__ ((__gnu_inline__)) int
__attribute__ ((__nothrow__ , __leaf__)) fstatat64 (int __fd, const char *__filename, struct stat64 *__statbuf, int __flag)
{
  return __fxstatat64 (1, __fd, __filename, __statbuf, __flag);
}


typedef __u_char u_char;
typedef __u_short u_short;
typedef __u_int u_int;
typedef __u_long u_long;
typedef __quad_t quad_t;
typedef __u_quad_t u_quad_t;
typedef __fsid_t fsid_t;
typedef __loff_t loff_t;
typedef __id_t id_t;
typedef __daddr_t daddr_t;
typedef __caddr_t caddr_t;
typedef __key_t key_t;
typedef __clock_t clock_t;
typedef __clockid_t clockid_t;
typedef __timer_t timer_t;
typedef __useconds_t useconds_t;
typedef __suseconds_t suseconds_t;
typedef unsigned long int ulong;
typedef unsigned short int ushort;
typedef unsigned int uint;
typedef __uint8_t u_int8_t;
typedef __uint16_t u_int16_t;
typedef __uint32_t u_int32_t;
typedef __uint64_t u_int64_t;
typedef int register_t __attribute__ ((__mode__ (__word__)));
static __inline __uint16_t
__bswap_16 (__uint16_t __bsx)
{
  return __builtin_bswap16 (__bsx);
}
static __inline __uint32_t
__bswap_32 (__uint32_t __bsx)
{
  return __builtin_bswap32 (__bsx);
}
__extension__ static __inline __uint64_t
__bswap_64 (__uint64_t __bsx)
{
  return __builtin_bswap64 (__bsx);
}
static __inline __uint16_t
__uint16_identity (__uint16_t __x)
{
  return __x;
}
static __inline __uint32_t
__uint32_identity (__uint32_t __x)
{
  return __x;
}
static __inline __uint64_t
__uint64_identity (__uint64_t __x)
{
  return __x;
}
struct timeval
{
  __time_t tv_sec;
  __suseconds_t tv_usec;
};
typedef long int __fd_mask;
typedef struct
  {
    __fd_mask fds_bits[1024 / (8 * (int) sizeof (__fd_mask))];
  } fd_set;
typedef __fd_mask fd_mask;

extern int select (int __nfds, fd_set *__restrict __readfds,
     fd_set *__restrict __writefds,
     fd_set *__restrict __exceptfds,
     struct timeval *__restrict __timeout);
extern int pselect (int __nfds, fd_set *__restrict __readfds,
      fd_set *__restrict __writefds,
      fd_set *__restrict __exceptfds,
      const struct timespec *__restrict __timeout,
      const __sigset_t *__restrict __sigmask);
extern long int __fdelt_chk (long int __d);
extern long int __fdelt_warn (long int __d)
  __attribute__((__warning__ ("bit outside of fd_set selected")));

typedef __fsblkcnt_t fsblkcnt_t;
typedef __fsfilcnt_t fsfilcnt_t;
typedef __blkcnt64_t blkcnt64_t;
typedef __fsblkcnt64_t fsblkcnt64_t;
typedef __fsfilcnt64_t fsfilcnt64_t;


typedef enum
{
  P_ALL,
  P_PID,
  P_PGID
} idtype_t;
extern __pid_t wait (int *__stat_loc);
extern __pid_t waitpid (__pid_t __pid, int *__stat_loc, int __options);
extern int waitid (idtype_t __idtype, __id_t __id, siginfo_t *__infop,
     int __options);
struct rusage;
extern __pid_t wait3 (int *__stat_loc, int __options,
        struct rusage * __usage) __attribute__ ((__nothrow__));
extern __pid_t wait4 (__pid_t __pid, int *__stat_loc, int __options,
        struct rusage *__usage) __attribute__ ((__nothrow__));

struct timex
{
  unsigned int modes;
  __syscall_slong_t offset;
  __syscall_slong_t freq;
  __syscall_slong_t maxerror;
  __syscall_slong_t esterror;
  int status;
  __syscall_slong_t constant;
  __syscall_slong_t precision;
  __syscall_slong_t tolerance;
  struct timeval time;
  __syscall_slong_t tick;
  __syscall_slong_t ppsfreq;
  __syscall_slong_t jitter;
  int shift;
  __syscall_slong_t stabil;
  __syscall_slong_t jitcnt;
  __syscall_slong_t calcnt;
  __syscall_slong_t errcnt;
  __syscall_slong_t stbcnt;
  int tai;
  int :32; int :32; int :32; int :32;
  int :32; int :32; int :32; int :32;
  int :32; int :32; int :32;
};

extern int clock_adjtime (__clockid_t __clock_id, struct timex *__utx) __attribute__ ((__nothrow__ , __leaf__));

struct tm
{
  int tm_sec;
  int tm_min;
  int tm_hour;
  int tm_mday;
  int tm_mon;
  int tm_year;
  int tm_wday;
  int tm_yday;
  int tm_isdst;
  long int tm_gmtoff;
  const char *tm_zone;
};
struct itimerspec
  {
    struct timespec it_interval;
    struct timespec it_value;
  };
struct sigevent;

extern clock_t clock (void) __attribute__ ((__nothrow__ , __leaf__));
extern time_t time (time_t *__timer) __attribute__ ((__nothrow__ , __leaf__));
extern double difftime (time_t __time1, time_t __time0)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern time_t mktime (struct tm *__tp) __attribute__ ((__nothrow__ , __leaf__));
extern size_t strftime (char *__restrict __s, size_t __maxsize,
   const char *__restrict __format,
   const struct tm *__restrict __tp) __attribute__ ((__nothrow__ , __leaf__));
extern char *strptime (const char *__restrict __s,
         const char *__restrict __fmt, struct tm *__tp)
     __attribute__ ((__nothrow__ , __leaf__));
extern size_t strftime_l (char *__restrict __s, size_t __maxsize,
     const char *__restrict __format,
     const struct tm *__restrict __tp,
     locale_t __loc) __attribute__ ((__nothrow__ , __leaf__));
extern char *strptime_l (const char *__restrict __s,
    const char *__restrict __fmt, struct tm *__tp,
    locale_t __loc) __attribute__ ((__nothrow__ , __leaf__));
extern struct tm *gmtime (const time_t *__timer) __attribute__ ((__nothrow__ , __leaf__));
extern struct tm *localtime (const time_t *__timer) __attribute__ ((__nothrow__ , __leaf__));
extern struct tm *gmtime_r (const time_t *__restrict __timer,
       struct tm *__restrict __tp) __attribute__ ((__nothrow__ , __leaf__));
extern struct tm *localtime_r (const time_t *__restrict __timer,
          struct tm *__restrict __tp) __attribute__ ((__nothrow__ , __leaf__));
extern char *asctime (const struct tm *__tp) __attribute__ ((__nothrow__ , __leaf__));
extern char *ctime (const time_t *__timer) __attribute__ ((__nothrow__ , __leaf__));
extern char *asctime_r (const struct tm *__restrict __tp,
   char *__restrict __buf) __attribute__ ((__nothrow__ , __leaf__));
extern char *ctime_r (const time_t *__restrict __timer,
        char *__restrict __buf) __attribute__ ((__nothrow__ , __leaf__));
extern char *__tzname[2];
extern int __daylight;
extern long int __timezone;
extern char *tzname[2];
extern void tzset (void) __attribute__ ((__nothrow__ , __leaf__));
extern int daylight;
extern long int timezone;
extern time_t timegm (struct tm *__tp) __attribute__ ((__nothrow__ , __leaf__));
extern time_t timelocal (struct tm *__tp) __attribute__ ((__nothrow__ , __leaf__));
extern int dysize (int __year) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern int nanosleep (const struct timespec *__requested_time,
        struct timespec *__remaining);
extern int clock_getres (clockid_t __clock_id, struct timespec *__res) __attribute__ ((__nothrow__ , __leaf__));
extern int clock_gettime (clockid_t __clock_id, struct timespec *__tp) __attribute__ ((__nothrow__ , __leaf__));
extern int clock_settime (clockid_t __clock_id, const struct timespec *__tp)
     __attribute__ ((__nothrow__ , __leaf__));
extern int clock_nanosleep (clockid_t __clock_id, int __flags,
       const struct timespec *__req,
       struct timespec *__rem);
extern int clock_getcpuclockid (pid_t __pid, clockid_t *__clock_id) __attribute__ ((__nothrow__ , __leaf__));
extern int timer_create (clockid_t __clock_id,
    struct sigevent *__restrict __evp,
    timer_t *__restrict __timerid) __attribute__ ((__nothrow__ , __leaf__));
extern int timer_delete (timer_t __timerid) __attribute__ ((__nothrow__ , __leaf__));
extern int timer_settime (timer_t __timerid, int __flags,
     const struct itimerspec *__restrict __value,
     struct itimerspec *__restrict __ovalue) __attribute__ ((__nothrow__ , __leaf__));
extern int timer_gettime (timer_t __timerid, struct itimerspec *__value)
     __attribute__ ((__nothrow__ , __leaf__));
extern int timer_getoverrun (timer_t __timerid) __attribute__ ((__nothrow__ , __leaf__));
extern int timespec_get (struct timespec *__ts, int __base)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int getdate_err;
extern struct tm *getdate (const char *__string);
extern int getdate_r (const char *__restrict __string,
        struct tm *__restrict __resbufp);


typedef __socklen_t socklen_t;
extern int access (const char *__name, int __type) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int euidaccess (const char *__name, int __type)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int eaccess (const char *__name, int __type)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int faccessat (int __fd, const char *__file, int __type, int __flag)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2))) __attribute__ ((__warn_unused_result__));
extern __off_t lseek (int __fd, __off_t __offset, int __whence) __attribute__ ((__nothrow__ , __leaf__));
extern __off64_t lseek64 (int __fd, __off64_t __offset, int __whence)
     __attribute__ ((__nothrow__ , __leaf__));
extern int close (int __fd);
extern ssize_t read (int __fd, void *__buf, size_t __nbytes) __attribute__ ((__warn_unused_result__));
extern ssize_t write (int __fd, const void *__buf, size_t __n) __attribute__ ((__warn_unused_result__));
extern ssize_t pread (int __fd, void *__buf, size_t __nbytes,
        __off_t __offset) __attribute__ ((__warn_unused_result__));
extern ssize_t pwrite (int __fd, const void *__buf, size_t __n,
         __off_t __offset) __attribute__ ((__warn_unused_result__));
extern ssize_t pread64 (int __fd, void *__buf, size_t __nbytes,
   __off64_t __offset) __attribute__ ((__warn_unused_result__));
extern ssize_t pwrite64 (int __fd, const void *__buf, size_t __n,
    __off64_t __offset) __attribute__ ((__warn_unused_result__));
extern int pipe (int __pipedes[2]) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int pipe2 (int __pipedes[2], int __flags) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern unsigned int alarm (unsigned int __seconds) __attribute__ ((__nothrow__ , __leaf__));
extern unsigned int sleep (unsigned int __seconds);
extern __useconds_t ualarm (__useconds_t __value, __useconds_t __interval)
     __attribute__ ((__nothrow__ , __leaf__));
extern int usleep (__useconds_t __useconds);
extern int pause (void);
extern int chown (const char *__file, __uid_t __owner, __gid_t __group)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int fchown (int __fd, __uid_t __owner, __gid_t __group) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int lchown (const char *__file, __uid_t __owner, __gid_t __group)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int fchownat (int __fd, const char *__file, __uid_t __owner,
       __gid_t __group, int __flag)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2))) __attribute__ ((__warn_unused_result__));
extern int chdir (const char *__path) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int fchdir (int __fd) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern char *getcwd (char *__buf, size_t __size) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern char *get_current_dir_name (void) __attribute__ ((__nothrow__ , __leaf__));
extern char *getwd (char *__buf)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__deprecated__)) __attribute__ ((__warn_unused_result__));
extern int dup (int __fd) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int dup2 (int __fd, int __fd2) __attribute__ ((__nothrow__ , __leaf__));
extern int dup3 (int __fd, int __fd2, int __flags) __attribute__ ((__nothrow__ , __leaf__));
extern char **__environ;
extern char **environ;
extern int execve (const char *__path, char *const __argv[],
     char *const __envp[]) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int fexecve (int __fd, char *const __argv[], char *const __envp[])
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int execv (const char *__path, char *const __argv[])
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int execle (const char *__path, const char *__arg, ...)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int execl (const char *__path, const char *__arg, ...)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int execvp (const char *__file, char *const __argv[])
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int execlp (const char *__file, const char *__arg, ...)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int execvpe (const char *__file, char *const __argv[],
      char *const __envp[])
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern int nice (int __inc) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern void _exit (int __status) __attribute__ ((__noreturn__));
enum
  {
    _PC_LINK_MAX,
    _PC_MAX_CANON,
    _PC_MAX_INPUT,
    _PC_NAME_MAX,
    _PC_PATH_MAX,
    _PC_PIPE_BUF,
    _PC_CHOWN_RESTRICTED,
    _PC_NO_TRUNC,
    _PC_VDISABLE,
    _PC_SYNC_IO,
    _PC_ASYNC_IO,
    _PC_PRIO_IO,
    _PC_SOCK_MAXBUF,
    _PC_FILESIZEBITS,
    _PC_REC_INCR_XFER_SIZE,
    _PC_REC_MAX_XFER_SIZE,
    _PC_REC_MIN_XFER_SIZE,
    _PC_REC_XFER_ALIGN,
    _PC_ALLOC_SIZE_MIN,
    _PC_SYMLINK_MAX,
    _PC_2_SYMLINKS
  };
enum
  {
    _SC_ARG_MAX,
    _SC_CHILD_MAX,
    _SC_CLK_TCK,
    _SC_NGROUPS_MAX,
    _SC_OPEN_MAX,
    _SC_STREAM_MAX,
    _SC_TZNAME_MAX,
    _SC_JOB_CONTROL,
    _SC_SAVED_IDS,
    _SC_REALTIME_SIGNALS,
    _SC_PRIORITY_SCHEDULING,
    _SC_TIMERS,
    _SC_ASYNCHRONOUS_IO,
    _SC_PRIORITIZED_IO,
    _SC_SYNCHRONIZED_IO,
    _SC_FSYNC,
    _SC_MAPPED_FILES,
    _SC_MEMLOCK,
    _SC_MEMLOCK_RANGE,
    _SC_MEMORY_PROTECTION,
    _SC_MESSAGE_PASSING,
    _SC_SEMAPHORES,
    _SC_SHARED_MEMORY_OBJECTS,
    _SC_AIO_LISTIO_MAX,
    _SC_AIO_MAX,
    _SC_AIO_PRIO_DELTA_MAX,
    _SC_DELAYTIMER_MAX,
    _SC_MQ_OPEN_MAX,
    _SC_MQ_PRIO_MAX,
    _SC_VERSION,
    _SC_PAGESIZE,
    _SC_RTSIG_MAX,
    _SC_SEM_NSEMS_MAX,
    _SC_SEM_VALUE_MAX,
    _SC_SIGQUEUE_MAX,
    _SC_TIMER_MAX,
    _SC_BC_BASE_MAX,
    _SC_BC_DIM_MAX,
    _SC_BC_SCALE_MAX,
    _SC_BC_STRING_MAX,
    _SC_COLL_WEIGHTS_MAX,
    _SC_EQUIV_CLASS_MAX,
    _SC_EXPR_NEST_MAX,
    _SC_LINE_MAX,
    _SC_RE_DUP_MAX,
    _SC_CHARCLASS_NAME_MAX,
    _SC_2_VERSION,
    _SC_2_C_BIND,
    _SC_2_C_DEV,
    _SC_2_FORT_DEV,
    _SC_2_FORT_RUN,
    _SC_2_SW_DEV,
    _SC_2_LOCALEDEF,
    _SC_PII,
    _SC_PII_XTI,
    _SC_PII_SOCKET,
    _SC_PII_INTERNET,
    _SC_PII_OSI,
    _SC_POLL,
    _SC_SELECT,
    _SC_UIO_MAXIOV,
    _SC_IOV_MAX = _SC_UIO_MAXIOV,
    _SC_PII_INTERNET_STREAM,
    _SC_PII_INTERNET_DGRAM,
    _SC_PII_OSI_COTS,
    _SC_PII_OSI_CLTS,
    _SC_PII_OSI_M,
    _SC_T_IOV_MAX,
    _SC_THREADS,
    _SC_THREAD_SAFE_FUNCTIONS,
    _SC_GETGR_R_SIZE_MAX,
    _SC_GETPW_R_SIZE_MAX,
    _SC_LOGIN_NAME_MAX,
    _SC_TTY_NAME_MAX,
    _SC_THREAD_DESTRUCTOR_ITERATIONS,
    _SC_THREAD_KEYS_MAX,
    _SC_THREAD_STACK_MIN,
    _SC_THREAD_THREADS_MAX,
    _SC_THREAD_ATTR_STACKADDR,
    _SC_THREAD_ATTR_STACKSIZE,
    _SC_THREAD_PRIORITY_SCHEDULING,
    _SC_THREAD_PRIO_INHERIT,
    _SC_THREAD_PRIO_PROTECT,
    _SC_THREAD_PROCESS_SHARED,
    _SC_NPROCESSORS_CONF,
    _SC_NPROCESSORS_ONLN,
    _SC_PHYS_PAGES,
    _SC_AVPHYS_PAGES,
    _SC_ATEXIT_MAX,
    _SC_PASS_MAX,
    _SC_XOPEN_VERSION,
    _SC_XOPEN_XCU_VERSION,
    _SC_XOPEN_UNIX,
    _SC_XOPEN_CRYPT,
    _SC_XOPEN_ENH_I18N,
    _SC_XOPEN_SHM,
    _SC_2_CHAR_TERM,
    _SC_2_C_VERSION,
    _SC_2_UPE,
    _SC_XOPEN_XPG2,
    _SC_XOPEN_XPG3,
    _SC_XOPEN_XPG4,
    _SC_CHAR_BIT,
    _SC_CHAR_MAX,
    _SC_CHAR_MIN,
    _SC_INT_MAX,
    _SC_INT_MIN,
    _SC_LONG_BIT,
    _SC_WORD_BIT,
    _SC_MB_LEN_MAX,
    _SC_NZERO,
    _SC_SSIZE_MAX,
    _SC_SCHAR_MAX,
    _SC_SCHAR_MIN,
    _SC_SHRT_MAX,
    _SC_SHRT_MIN,
    _SC_UCHAR_MAX,
    _SC_UINT_MAX,
    _SC_ULONG_MAX,
    _SC_USHRT_MAX,
    _SC_NL_ARGMAX,
    _SC_NL_LANGMAX,
    _SC_NL_MSGMAX,
    _SC_NL_NMAX,
    _SC_NL_SETMAX,
    _SC_NL_TEXTMAX,
    _SC_XBS5_ILP32_OFF32,
    _SC_XBS5_ILP32_OFFBIG,
    _SC_XBS5_LP64_OFF64,
    _SC_XBS5_LPBIG_OFFBIG,
    _SC_XOPEN_LEGACY,
    _SC_XOPEN_REALTIME,
    _SC_XOPEN_REALTIME_THREADS,
    _SC_ADVISORY_INFO,
    _SC_BARRIERS,
    _SC_BASE,
    _SC_C_LANG_SUPPORT,
    _SC_C_LANG_SUPPORT_R,
    _SC_CLOCK_SELECTION,
    _SC_CPUTIME,
    _SC_THREAD_CPUTIME,
    _SC_DEVICE_IO,
    _SC_DEVICE_SPECIFIC,
    _SC_DEVICE_SPECIFIC_R,
    _SC_FD_MGMT,
    _SC_FIFO,
    _SC_PIPE,
    _SC_FILE_ATTRIBUTES,
    _SC_FILE_LOCKING,
    _SC_FILE_SYSTEM,
    _SC_MONOTONIC_CLOCK,
    _SC_MULTI_PROCESS,
    _SC_SINGLE_PROCESS,
    _SC_NETWORKING,
    _SC_READER_WRITER_LOCKS,
    _SC_SPIN_LOCKS,
    _SC_REGEXP,
    _SC_REGEX_VERSION,
    _SC_SHELL,
    _SC_SIGNALS,
    _SC_SPAWN,
    _SC_SPORADIC_SERVER,
    _SC_THREAD_SPORADIC_SERVER,
    _SC_SYSTEM_DATABASE,
    _SC_SYSTEM_DATABASE_R,
    _SC_TIMEOUTS,
    _SC_TYPED_MEMORY_OBJECTS,
    _SC_USER_GROUPS,
    _SC_USER_GROUPS_R,
    _SC_2_PBS,
    _SC_2_PBS_ACCOUNTING,
    _SC_2_PBS_LOCATE,
    _SC_2_PBS_MESSAGE,
    _SC_2_PBS_TRACK,
    _SC_SYMLOOP_MAX,
    _SC_STREAMS,
    _SC_2_PBS_CHECKPOINT,
    _SC_V6_ILP32_OFF32,
    _SC_V6_ILP32_OFFBIG,
    _SC_V6_LP64_OFF64,
    _SC_V6_LPBIG_OFFBIG,
    _SC_HOST_NAME_MAX,
    _SC_TRACE,
    _SC_TRACE_EVENT_FILTER,
    _SC_TRACE_INHERIT,
    _SC_TRACE_LOG,
    _SC_LEVEL1_ICACHE_SIZE,
    _SC_LEVEL1_ICACHE_ASSOC,
    _SC_LEVEL1_ICACHE_LINESIZE,
    _SC_LEVEL1_DCACHE_SIZE,
    _SC_LEVEL1_DCACHE_ASSOC,
    _SC_LEVEL1_DCACHE_LINESIZE,
    _SC_LEVEL2_CACHE_SIZE,
    _SC_LEVEL2_CACHE_ASSOC,
    _SC_LEVEL2_CACHE_LINESIZE,
    _SC_LEVEL3_CACHE_SIZE,
    _SC_LEVEL3_CACHE_ASSOC,
    _SC_LEVEL3_CACHE_LINESIZE,
    _SC_LEVEL4_CACHE_SIZE,
    _SC_LEVEL4_CACHE_ASSOC,
    _SC_LEVEL4_CACHE_LINESIZE,
    _SC_IPV6 = _SC_LEVEL1_ICACHE_SIZE + 50,
    _SC_RAW_SOCKETS,
    _SC_V7_ILP32_OFF32,
    _SC_V7_ILP32_OFFBIG,
    _SC_V7_LP64_OFF64,
    _SC_V7_LPBIG_OFFBIG,
    _SC_SS_REPL_MAX,
    _SC_TRACE_EVENT_NAME_MAX,
    _SC_TRACE_NAME_MAX,
    _SC_TRACE_SYS_MAX,
    _SC_TRACE_USER_EVENT_MAX,
    _SC_XOPEN_STREAMS,
    _SC_THREAD_ROBUST_PRIO_INHERIT,
    _SC_THREAD_ROBUST_PRIO_PROTECT
  };
enum
  {
    _CS_PATH,
    _CS_V6_WIDTH_RESTRICTED_ENVS,
    _CS_GNU_LIBC_VERSION,
    _CS_GNU_LIBPTHREAD_VERSION,
    _CS_V5_WIDTH_RESTRICTED_ENVS,
    _CS_V7_WIDTH_RESTRICTED_ENVS,
    _CS_LFS_CFLAGS = 1000,
    _CS_LFS_LDFLAGS,
    _CS_LFS_LIBS,
    _CS_LFS_LINTFLAGS,
    _CS_LFS64_CFLAGS,
    _CS_LFS64_LDFLAGS,
    _CS_LFS64_LIBS,
    _CS_LFS64_LINTFLAGS,
    _CS_XBS5_ILP32_OFF32_CFLAGS = 1100,
    _CS_XBS5_ILP32_OFF32_LDFLAGS,
    _CS_XBS5_ILP32_OFF32_LIBS,
    _CS_XBS5_ILP32_OFF32_LINTFLAGS,
    _CS_XBS5_ILP32_OFFBIG_CFLAGS,
    _CS_XBS5_ILP32_OFFBIG_LDFLAGS,
    _CS_XBS5_ILP32_OFFBIG_LIBS,
    _CS_XBS5_ILP32_OFFBIG_LINTFLAGS,
    _CS_XBS5_LP64_OFF64_CFLAGS,
    _CS_XBS5_LP64_OFF64_LDFLAGS,
    _CS_XBS5_LP64_OFF64_LIBS,
    _CS_XBS5_LP64_OFF64_LINTFLAGS,
    _CS_XBS5_LPBIG_OFFBIG_CFLAGS,
    _CS_XBS5_LPBIG_OFFBIG_LDFLAGS,
    _CS_XBS5_LPBIG_OFFBIG_LIBS,
    _CS_XBS5_LPBIG_OFFBIG_LINTFLAGS,
    _CS_POSIX_V6_ILP32_OFF32_CFLAGS,
    _CS_POSIX_V6_ILP32_OFF32_LDFLAGS,
    _CS_POSIX_V6_ILP32_OFF32_LIBS,
    _CS_POSIX_V6_ILP32_OFF32_LINTFLAGS,
    _CS_POSIX_V6_ILP32_OFFBIG_CFLAGS,
    _CS_POSIX_V6_ILP32_OFFBIG_LDFLAGS,
    _CS_POSIX_V6_ILP32_OFFBIG_LIBS,
    _CS_POSIX_V6_ILP32_OFFBIG_LINTFLAGS,
    _CS_POSIX_V6_LP64_OFF64_CFLAGS,
    _CS_POSIX_V6_LP64_OFF64_LDFLAGS,
    _CS_POSIX_V6_LP64_OFF64_LIBS,
    _CS_POSIX_V6_LP64_OFF64_LINTFLAGS,
    _CS_POSIX_V6_LPBIG_OFFBIG_CFLAGS,
    _CS_POSIX_V6_LPBIG_OFFBIG_LDFLAGS,
    _CS_POSIX_V6_LPBIG_OFFBIG_LIBS,
    _CS_POSIX_V6_LPBIG_OFFBIG_LINTFLAGS,
    _CS_POSIX_V7_ILP32_OFF32_CFLAGS,
    _CS_POSIX_V7_ILP32_OFF32_LDFLAGS,
    _CS_POSIX_V7_ILP32_OFF32_LIBS,
    _CS_POSIX_V7_ILP32_OFF32_LINTFLAGS,
    _CS_POSIX_V7_ILP32_OFFBIG_CFLAGS,
    _CS_POSIX_V7_ILP32_OFFBIG_LDFLAGS,
    _CS_POSIX_V7_ILP32_OFFBIG_LIBS,
    _CS_POSIX_V7_ILP32_OFFBIG_LINTFLAGS,
    _CS_POSIX_V7_LP64_OFF64_CFLAGS,
    _CS_POSIX_V7_LP64_OFF64_LDFLAGS,
    _CS_POSIX_V7_LP64_OFF64_LIBS,
    _CS_POSIX_V7_LP64_OFF64_LINTFLAGS,
    _CS_POSIX_V7_LPBIG_OFFBIG_CFLAGS,
    _CS_POSIX_V7_LPBIG_OFFBIG_LDFLAGS,
    _CS_POSIX_V7_LPBIG_OFFBIG_LIBS,
    _CS_POSIX_V7_LPBIG_OFFBIG_LINTFLAGS,
    _CS_V6_ENV,
    _CS_V7_ENV
  };
extern long int pathconf (const char *__path, int __name)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern long int fpathconf (int __fd, int __name) __attribute__ ((__nothrow__ , __leaf__));
extern long int sysconf (int __name) __attribute__ ((__nothrow__ , __leaf__));
extern size_t confstr (int __name, char *__buf, size_t __len) __attribute__ ((__nothrow__ , __leaf__));
extern __pid_t getpid (void) __attribute__ ((__nothrow__ , __leaf__));
extern __pid_t getppid (void) __attribute__ ((__nothrow__ , __leaf__));
extern __pid_t getpgrp (void) __attribute__ ((__nothrow__ , __leaf__));
extern __pid_t __getpgid (__pid_t __pid) __attribute__ ((__nothrow__ , __leaf__));
extern __pid_t getpgid (__pid_t __pid) __attribute__ ((__nothrow__ , __leaf__));
extern int setpgid (__pid_t __pid, __pid_t __pgid) __attribute__ ((__nothrow__ , __leaf__));
extern int setpgrp (void) __attribute__ ((__nothrow__ , __leaf__));
extern __pid_t setsid (void) __attribute__ ((__nothrow__ , __leaf__));
extern __pid_t getsid (__pid_t __pid) __attribute__ ((__nothrow__ , __leaf__));
extern __uid_t getuid (void) __attribute__ ((__nothrow__ , __leaf__));
extern __uid_t geteuid (void) __attribute__ ((__nothrow__ , __leaf__));
extern __gid_t getgid (void) __attribute__ ((__nothrow__ , __leaf__));
extern __gid_t getegid (void) __attribute__ ((__nothrow__ , __leaf__));
extern int getgroups (int __size, __gid_t __list[]) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int group_member (__gid_t __gid) __attribute__ ((__nothrow__ , __leaf__));
extern int setuid (__uid_t __uid) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int setreuid (__uid_t __ruid, __uid_t __euid) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int seteuid (__uid_t __uid) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int setgid (__gid_t __gid) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int setregid (__gid_t __rgid, __gid_t __egid) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int setegid (__gid_t __gid) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int getresuid (__uid_t *__ruid, __uid_t *__euid, __uid_t *__suid)
     __attribute__ ((__nothrow__ , __leaf__));
extern int getresgid (__gid_t *__rgid, __gid_t *__egid, __gid_t *__sgid)
     __attribute__ ((__nothrow__ , __leaf__));
extern int setresuid (__uid_t __ruid, __uid_t __euid, __uid_t __suid)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int setresgid (__gid_t __rgid, __gid_t __egid, __gid_t __sgid)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern __pid_t fork (void) __attribute__ ((__nothrow__));
extern __pid_t vfork (void) __attribute__ ((__nothrow__ , __leaf__));
extern char *ttyname (int __fd) __attribute__ ((__nothrow__ , __leaf__));
extern int ttyname_r (int __fd, char *__buf, size_t __buflen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2))) __attribute__ ((__warn_unused_result__));
extern int isatty (int __fd) __attribute__ ((__nothrow__ , __leaf__));
extern int ttyslot (void) __attribute__ ((__nothrow__ , __leaf__));
extern int link (const char *__from, const char *__to)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2))) __attribute__ ((__warn_unused_result__));
extern int linkat (int __fromfd, const char *__from, int __tofd,
     const char *__to, int __flags)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 4))) __attribute__ ((__warn_unused_result__));
extern int symlink (const char *__from, const char *__to)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2))) __attribute__ ((__warn_unused_result__));
extern ssize_t readlink (const char *__restrict __path,
    char *__restrict __buf, size_t __len)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2))) __attribute__ ((__warn_unused_result__));
extern int symlinkat (const char *__from, int __tofd,
        const char *__to) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 3))) __attribute__ ((__warn_unused_result__));
extern ssize_t readlinkat (int __fd, const char *__restrict __path,
      char *__restrict __buf, size_t __len)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3))) __attribute__ ((__warn_unused_result__));
extern int unlink (const char *__name) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int unlinkat (int __fd, const char *__name, int __flag)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int rmdir (const char *__path) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern __pid_t tcgetpgrp (int __fd) __attribute__ ((__nothrow__ , __leaf__));
extern int tcsetpgrp (int __fd, __pid_t __pgrp_id) __attribute__ ((__nothrow__ , __leaf__));
extern char *getlogin (void);
extern int getlogin_r (char *__name, size_t __name_len) __attribute__ ((__nonnull__ (1)));
extern int setlogin (const char *__name) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));

extern char *optarg;
extern int optind;
extern int opterr;
extern int optopt;
extern int getopt (int ___argc, char *const *___argv, const char *__shortopts)
       __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3)));



extern int gethostname (char *__name, size_t __len) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int sethostname (const char *__name, size_t __len)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int sethostid (long int __id) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int getdomainname (char *__name, size_t __len)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int setdomainname (const char *__name, size_t __len)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int vhangup (void) __attribute__ ((__nothrow__ , __leaf__));
extern int revoke (const char *__file) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int profil (unsigned short int *__sample_buffer, size_t __size,
     size_t __offset, unsigned int __scale)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int acct (const char *__name) __attribute__ ((__nothrow__ , __leaf__));
extern char *getusershell (void) __attribute__ ((__nothrow__ , __leaf__));
extern void endusershell (void) __attribute__ ((__nothrow__ , __leaf__));
extern void setusershell (void) __attribute__ ((__nothrow__ , __leaf__));
extern int daemon (int __nochdir, int __noclose) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int chroot (const char *__path) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern char *getpass (const char *__prompt) __attribute__ ((__nonnull__ (1)));
extern int fsync (int __fd);
extern int syncfs (int __fd) __attribute__ ((__nothrow__ , __leaf__));
extern long int gethostid (void);
extern void sync (void) __attribute__ ((__nothrow__ , __leaf__));
extern int getpagesize (void) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__const__));
extern int getdtablesize (void) __attribute__ ((__nothrow__ , __leaf__));
extern int truncate (const char *__file, __off_t __length)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int truncate64 (const char *__file, __off64_t __length)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int ftruncate (int __fd, __off_t __length) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int ftruncate64 (int __fd, __off64_t __length) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int brk (void *__addr) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern void *sbrk (intptr_t __delta) __attribute__ ((__nothrow__ , __leaf__));
extern long int syscall (long int __sysno, ...) __attribute__ ((__nothrow__ , __leaf__));
ssize_t copy_file_range (int __infd, __off64_t *__pinoff,
    int __outfd, __off64_t *__poutoff,
    size_t __length, unsigned int __flags);
extern int fdatasync (int __fildes);
extern char *crypt (const char *__key, const char *__salt)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
extern void swab (const void *__restrict __from, void *__restrict __to,
    ssize_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));
int getentropy (void *__buffer, size_t __length) __attribute__ ((__warn_unused_result__));
extern ssize_t __read_chk (int __fd, void *__buf, size_t __nbytes,
      size_t __buflen) __attribute__ ((__warn_unused_result__));
extern ssize_t __read_alias (int __fd, void *__buf, size_t __nbytes) __asm__ ("" "read") __attribute__ ((__warn_unused_result__));
extern ssize_t __read_chk_warn (int __fd, void *__buf, size_t __nbytes, size_t __buflen) __asm__ ("" "__read_chk")
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("read called with bigger length than size of " "the destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__warn_unused_result__)) ssize_t
read (int __fd, void *__buf, size_t __nbytes)
{
  if (__builtin_object_size (__buf, 0) != (size_t) -1)
    {
      if (!__builtin_constant_p (__nbytes))
 return __read_chk (__fd, __buf, __nbytes, __builtin_object_size (__buf, 0));
      if (__nbytes > __builtin_object_size (__buf, 0))
 return __read_chk_warn (__fd, __buf, __nbytes, __builtin_object_size (__buf, 0));
    }
  return __read_alias (__fd, __buf, __nbytes);
}
extern ssize_t __pread_chk (int __fd, void *__buf, size_t __nbytes,
       __off_t __offset, size_t __bufsize) __attribute__ ((__warn_unused_result__));
extern ssize_t __pread64_chk (int __fd, void *__buf, size_t __nbytes,
         __off64_t __offset, size_t __bufsize) __attribute__ ((__warn_unused_result__));
extern ssize_t __pread_alias (int __fd, void *__buf, size_t __nbytes, __off_t __offset) __asm__ ("" "pread") __attribute__ ((__warn_unused_result__));
extern ssize_t __pread64_alias (int __fd, void *__buf, size_t __nbytes, __off64_t __offset) __asm__ ("" "pread64") __attribute__ ((__warn_unused_result__));
extern ssize_t __pread_chk_warn (int __fd, void *__buf, size_t __nbytes, __off_t __offset, size_t __bufsize) __asm__ ("" "__pread_chk")
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("pread called with bigger length than size of " "the destination buffer")));
extern ssize_t __pread64_chk_warn (int __fd, void *__buf, size_t __nbytes, __off64_t __offset, size_t __bufsize) __asm__ ("" "__pread64_chk")
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("pread64 called with bigger length than size of " "the destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__warn_unused_result__)) ssize_t
pread (int __fd, void *__buf, size_t __nbytes, __off_t __offset)
{
  if (__builtin_object_size (__buf, 0) != (size_t) -1)
    {
      if (!__builtin_constant_p (__nbytes))
 return __pread_chk (__fd, __buf, __nbytes, __offset, __builtin_object_size (__buf, 0));
      if ( __nbytes > __builtin_object_size (__buf, 0))
 return __pread_chk_warn (__fd, __buf, __nbytes, __offset,
     __builtin_object_size (__buf, 0));
    }
  return __pread_alias (__fd, __buf, __nbytes, __offset);
}
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__warn_unused_result__)) ssize_t
pread64 (int __fd, void *__buf, size_t __nbytes, __off64_t __offset)
{
  if (__builtin_object_size (__buf, 0) != (size_t) -1)
    {
      if (!__builtin_constant_p (__nbytes))
 return __pread64_chk (__fd, __buf, __nbytes, __offset, __builtin_object_size (__buf, 0));
      if ( __nbytes > __builtin_object_size (__buf, 0))
 return __pread64_chk_warn (__fd, __buf, __nbytes, __offset,
       __builtin_object_size (__buf, 0));
    }
  return __pread64_alias (__fd, __buf, __nbytes, __offset);
}
extern ssize_t __readlink_chk (const char *__restrict __path,
          char *__restrict __buf, size_t __len,
          size_t __buflen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2))) __attribute__ ((__warn_unused_result__));
extern ssize_t __readlink_alias (const char *__restrict __path, char *__restrict __buf, size_t __len) __asm__ ("" "readlink") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (1, 2))) __attribute__ ((__warn_unused_result__));
extern ssize_t __readlink_chk_warn (const char *__restrict __path, char *__restrict __buf, size_t __len, size_t __buflen) __asm__ ("" "__readlink_chk") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (1, 2))) __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("readlink called with bigger length " "than size of destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__nonnull__ (1, 2))) __attribute__ ((__warn_unused_result__)) ssize_t
__attribute__ ((__nothrow__ , __leaf__)) readlink (const char *__restrict __path, char *__restrict __buf, size_t __len)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__len))
 return __readlink_chk (__path, __buf, __len, __builtin_object_size (__buf, 2 > 1));
      if ( __len > __builtin_object_size (__buf, 2 > 1))
 return __readlink_chk_warn (__path, __buf, __len, __builtin_object_size (__buf, 2 > 1));
    }
  return __readlink_alias (__path, __buf, __len);
}
extern ssize_t __readlinkat_chk (int __fd, const char *__restrict __path,
     char *__restrict __buf, size_t __len,
     size_t __buflen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2, 3))) __attribute__ ((__warn_unused_result__));
extern ssize_t __readlinkat_alias (int __fd, const char *__restrict __path, char *__restrict __buf, size_t __len) __asm__ ("" "readlinkat") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (2, 3))) __attribute__ ((__warn_unused_result__));
extern ssize_t __readlinkat_chk_warn (int __fd, const char *__restrict __path, char *__restrict __buf, size_t __len, size_t __buflen) __asm__ ("" "__readlinkat_chk") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (2, 3))) __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("readlinkat called with bigger " "length than size of destination " "buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__nonnull__ (2, 3))) __attribute__ ((__warn_unused_result__)) ssize_t
__attribute__ ((__nothrow__ , __leaf__)) readlinkat (int __fd, const char *__restrict __path, char *__restrict __buf, size_t __len)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__len))
 return __readlinkat_chk (__fd, __path, __buf, __len, __builtin_object_size (__buf, 2 > 1));
      if (__len > __builtin_object_size (__buf, 2 > 1))
 return __readlinkat_chk_warn (__fd, __path, __buf, __len,
          __builtin_object_size (__buf, 2 > 1));
    }
  return __readlinkat_alias (__fd, __path, __buf, __len);
}
extern char *__getcwd_chk (char *__buf, size_t __size, size_t __buflen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern char *__getcwd_alias (char *__buf, size_t __size) __asm__ ("" "getcwd") __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern char *__getcwd_chk_warn (char *__buf, size_t __size, size_t __buflen) __asm__ ("" "__getcwd_chk") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("getcwd caller with bigger length than size of " "destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__warn_unused_result__)) char *
__attribute__ ((__nothrow__ , __leaf__)) getcwd (char *__buf, size_t __size)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__size))
 return __getcwd_chk (__buf, __size, __builtin_object_size (__buf, 2 > 1));
      if (__size > __builtin_object_size (__buf, 2 > 1))
 return __getcwd_chk_warn (__buf, __size, __builtin_object_size (__buf, 2 > 1));
    }
  return __getcwd_alias (__buf, __size);
}
extern char *__getwd_chk (char *__buf, size_t buflen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern char *__getwd_warn (char *__buf) __asm__ ("" "getwd") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("please use getcwd instead, as getwd " "doesn't specify buffer size")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__deprecated__)) __attribute__ ((__warn_unused_result__)) char *
__attribute__ ((__nothrow__ , __leaf__)) getwd (char *__buf)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    return __getwd_chk (__buf, __builtin_object_size (__buf, 2 > 1));
  return __getwd_warn (__buf);
}
extern size_t __confstr_chk (int __name, char *__buf, size_t __len,
        size_t __buflen) __attribute__ ((__nothrow__ , __leaf__));
extern size_t __confstr_alias (int __name, char *__buf, size_t __len) __asm__ ("" "confstr") __attribute__ ((__nothrow__ , __leaf__));
extern size_t __confstr_chk_warn (int __name, char *__buf, size_t __len, size_t __buflen) __asm__ ("" "__confstr_chk") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__((__warning__ ("confstr called with bigger length than size of destination " "buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) size_t
__attribute__ ((__nothrow__ , __leaf__)) confstr (int __name, char *__buf, size_t __len)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__len))
 return __confstr_chk (__name, __buf, __len, __builtin_object_size (__buf, 2 > 1));
      if (__builtin_object_size (__buf, 2 > 1) < __len)
 return __confstr_chk_warn (__name, __buf, __len, __builtin_object_size (__buf, 2 > 1));
    }
  return __confstr_alias (__name, __buf, __len);
}
extern int __getgroups_chk (int __size, __gid_t __list[], size_t __listlen)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int __getgroups_alias (int __size, __gid_t __list[]) __asm__ ("" "getgroups") __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__warn_unused_result__));
extern int __getgroups_chk_warn (int __size, __gid_t __list[], size_t __listlen) __asm__ ("" "__getgroups_chk") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("getgroups called with bigger group count than what " "can fit into destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) getgroups (int __size, __gid_t __list[])
{
  if (__builtin_object_size (__list, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__size) || __size < 0)
 return __getgroups_chk (__size, __list, __builtin_object_size (__list, 2 > 1));
      if (__size * sizeof (__gid_t) > __builtin_object_size (__list, 2 > 1))
 return __getgroups_chk_warn (__size, __list, __builtin_object_size (__list, 2 > 1));
    }
  return __getgroups_alias (__size, __list);
}
extern int __ttyname_r_chk (int __fd, char *__buf, size_t __buflen,
       size_t __nreal) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (2)));
extern int __ttyname_r_alias (int __fd, char *__buf, size_t __buflen) __asm__ ("" "ttyname_r") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (2)));
extern int __ttyname_r_chk_warn (int __fd, char *__buf, size_t __buflen, size_t __nreal) __asm__ ("" "__ttyname_r_chk") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (2))) __attribute__((__warning__ ("ttyname_r called with bigger buflen than " "size of destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) ttyname_r (int __fd, char *__buf, size_t __buflen)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__buflen))
 return __ttyname_r_chk (__fd, __buf, __buflen, __builtin_object_size (__buf, 2 > 1));
      if (__buflen > __builtin_object_size (__buf, 2 > 1))
 return __ttyname_r_chk_warn (__fd, __buf, __buflen, __builtin_object_size (__buf, 2 > 1));
    }
  return __ttyname_r_alias (__fd, __buf, __buflen);
}
extern int __getlogin_r_chk (char *__buf, size_t __buflen, size_t __nreal)
     __attribute__ ((__nonnull__ (1)));
extern int __getlogin_r_alias (char *__buf, size_t __buflen) __asm__ ("" "getlogin_r") __attribute__ ((__nonnull__ (1)));
extern int __getlogin_r_chk_warn (char *__buf, size_t __buflen, size_t __nreal) __asm__ ("" "__getlogin_r_chk")
     __attribute__ ((__nonnull__ (1))) __attribute__((__warning__ ("getlogin_r called with bigger buflen than " "size of destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
getlogin_r (char *__buf, size_t __buflen)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__buflen))
 return __getlogin_r_chk (__buf, __buflen, __builtin_object_size (__buf, 2 > 1));
      if (__buflen > __builtin_object_size (__buf, 2 > 1))
 return __getlogin_r_chk_warn (__buf, __buflen, __builtin_object_size (__buf, 2 > 1));
    }
  return __getlogin_r_alias (__buf, __buflen);
}
extern int __gethostname_chk (char *__buf, size_t __buflen, size_t __nreal)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int __gethostname_alias (char *__buf, size_t __buflen) __asm__ ("" "gethostname") __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1)));
extern int __gethostname_chk_warn (char *__buf, size_t __buflen, size_t __nreal) __asm__ ("" "__gethostname_chk") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (1))) __attribute__((__warning__ ("gethostname called with bigger buflen than " "size of destination buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) gethostname (char *__buf, size_t __buflen)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__buflen))
 return __gethostname_chk (__buf, __buflen, __builtin_object_size (__buf, 2 > 1));
      if (__buflen > __builtin_object_size (__buf, 2 > 1))
 return __gethostname_chk_warn (__buf, __buflen, __builtin_object_size (__buf, 2 > 1));
    }
  return __gethostname_alias (__buf, __buflen);
}
extern int __getdomainname_chk (char *__buf, size_t __buflen, size_t __nreal)
     __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int __getdomainname_alias (char *__buf, size_t __buflen) __asm__ ("" "getdomainname") __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__));
extern int __getdomainname_chk_warn (char *__buf, size_t __buflen, size_t __nreal) __asm__ ("" "__getdomainname_chk") __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__nonnull__ (1))) __attribute__ ((__warn_unused_result__)) __attribute__((__warning__ ("getdomainname called with bigger " "buflen than size of destination " "buffer")));
extern __inline __attribute__ ((__always_inline__)) __attribute__ ((__gnu_inline__)) __attribute__ ((__artificial__)) int
__attribute__ ((__nothrow__ , __leaf__)) getdomainname (char *__buf, size_t __buflen)
{
  if (__builtin_object_size (__buf, 2 > 1) != (size_t) -1)
    {
      if (!__builtin_constant_p (__buflen))
 return __getdomainname_chk (__buf, __buflen, __builtin_object_size (__buf, 2 > 1));
      if (__buflen > __builtin_object_size (__buf, 2 > 1))
 return __getdomainname_chk_warn (__buf, __buflen, __builtin_object_size (__buf, 2 > 1));
    }
  return __getdomainname_alias (__buf, __buflen);
}
extern __pid_t gettid (void) __attribute__ ((__nothrow__ , __leaf__));

static uint64_t collector_deadline;
struct stream {
    unsigned char data[1024u];
    size_t kept;
    uint64_t observed, eof_ns;
    int eof;
};
struct result {
    struct stream out, err;
    int pid;
    int status, fault, timeout, clean;
    int child_stage, child_errno;
    uint64_t started, reaped, finished;
};
struct child_fault { int stage, number; };
static const char nd_core_case[] = "threads";
static char *const payload_argv[] = {
    "/bin/mcexec", "-t", "1", "0", "app", (char *)nd_core_case, ((void *)0)
};
static char *const payload_env[] = {"PATH=/usr/bin:/bin", "COKERNEL_PATH=/apps", ((void *)0)};
static char *const helper_env[] = {"PATH=/bin:/sbin:/usr/bin:/usr/sbin", "LC_ALL=C", ((void *)0)};
static uint64_t now_ns(void)
{
    struct timespec t;
    if (clock_gettime(1, &t)) return 0;
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}
static unsigned helper_timeout_ms(const char *path)
{
    return !strcmp(path, "/bin/native-boot") ? 60000u : 10000u;
}
static uint64_t bounded_deadline(uint64_t deadline, uint64_t reserve)
{
    if (collector_deadline && deadline > collector_deadline - reserve)
        return collector_deadline - reserve;
    return deadline;
}
static void outer_expired(int number)
{
    (void)number;
    for (;;) pause();
}
static int make_pipe(int p[2])
{
    if (pipe2(p, 02000000)) return -1;
    for (int i = 0; i != 2; ++i) {
        if (p[i] < 3) {
            int n = fcntl(p[i], 1030, 3);
            if (n < 0) { close(p[0]); close(p[1]); return -1; }
            close(p[i]); p[i] = n;
        }
    }
    int flags = fcntl(p[0], 3);
    if (flags < 0 || fcntl(p[0], 4, flags | 04000)) {
        close(p[0]); close(p[1]); return -1;
    }
    return 0;
}
static void child_abort(int fd, int stage)
{
    struct child_fault f = {stage, (*__errno_location ())};
    ssize_t n;
    do { n = write(fd, &f, sizeof f); } while (n < 0 && (*__errno_location ()) == 4);
    _exit(126);
}
static int drain(int fd, struct stream *s, uint64_t deadline)
{
    unsigned char b[512];
    for (int i = 0; i != 4 && !s->eof; ++i) {
        uint64_t now = now_ns();
        if (!now) return -1;
        if (now >= deadline) break;
        ssize_t n = read(fd, b, sizeof b);
        if (n > 0) {
            size_t keep = (size_t)n;
            if (keep > 1024u - s->kept) keep = 1024u - s->kept;
            memcpy(s->data + s->kept, b, keep); s->kept += keep;
            if ((18446744073709551615UL) - s->observed < (uint64_t)n) return -1;
            s->observed += (uint64_t)n;
        } else if (!n) { s->eof = 1; s->eof_ns = now_ns(); }
        else if ((*__errno_location ()) == 11 || (*__errno_location ()) == 11) break;
        else if ((*__errno_location ()) != 4) return -1;
    }
    return 0;
}
static int signal_owned(pid_t p, int sig)
{
    int bad = 0;
    if (kill(-p, sig) && (*__errno_location ()) != 3) bad = 1;
    if (kill(p, sig) && (*__errno_location ()) != 3) bad = 1;
    return bad ? -1 : 0;
}
static void supervise(const char *path, char *const av[], char *const env[],
                      const char *cwd, unsigned timeout_ms, struct result *r)
{
    int pipes[3][2] = {{-1,-1},{-1,-1},{-1,-1}};
    pid_t child = -1;
    unsigned char setup[sizeof(struct child_fault) + 1];
    size_t setup_n = 0;
    int setup_eof = 0, stopping = 0, killed = 0, leader_ready = 0;
    uint64_t stop_at = 0, limit;
    memset(r, 0, sizeof *r); r->status = -1;
    r->started = now_ns();
    if (!r->started) { r->fault = 1; goto done; }
    limit = r->started + (uint64_t)timeout_ms * 1000000ull;
    limit = bounded_deadline(limit, 2000 * 1000000ull);
    if (limit <= r->started) { r->fault = r->timeout = 1; goto done; }
    for (int i = 0; i != 3; ++i) {
        if (make_pipe(pipes[i])) { r->fault = 1; goto done; }
    }
    child = fork();
    if (child < 0) { r->fault = 1; goto done; }
    if (!child) {
        if (setpgid(0, 0)) child_abort(pipes[2][1], 1);
        if (dup2(pipes[0][1], 1) < 0 || dup2(pipes[1][1], 2) < 0)
            child_abort(pipes[2][1], 2);
        for (int i = 0; i != 3; ++i) {
            close(pipes[i][0]);
            if (i != 2) close(pipes[i][1]);
        }
        int nullfd = open("/dev/null", 00 | 02000000);
        if (nullfd < 0 || dup2(nullfd, 0) < 0) child_abort(pipes[2][1], 3);
        if (nullfd != 0) close(nullfd);
        else if (fcntl(0, 2, 0)) child_abort(pipes[2][1], 3);
        if (cwd && chdir(cwd)) child_abort(pipes[2][1], 4);
        execve(path, av, env);
        child_abort(pipes[2][1], 5);
    }
    r->pid=child;
    for (int i = 0; i != 3; ++i) { close(pipes[i][1]); pipes[i][1] = -1; }
    if (setpgid(child, child) && (*__errno_location ()) != 13 && (*__errno_location ()) != 3) r->fault = 1;
    for (;;) {
        uint64_t now = now_ns();
        if (!now) {
            r->fault = 1;
            (void)signal_owned(child, 9);
            break;
        }
        if (!leader_ready) {
            siginfo_t si; memset(&si, 0, sizeof si);
            if (waitid(P_PID, child, &si, 4 | 1 | 0x01000000)) {
                if ((*__errno_location ()) != 4) r->fault = 1;
            } else leader_ready = si._sifields._kill.si_pid == child;
        }
        if (!stopping && (leader_ready || now >= limit || r->fault)) {
            r->timeout = !leader_ready && now >= limit;
            stopping = 1; stop_at = now;
            if (signal_owned(child, 15)) r->fault = 1;
        }
        if (stopping && !killed && now - stop_at >= 100 * 1000000ull) {
            if (signal_owned(child, 9)) r->fault = 1;
            killed = 1;
        }
        if (stopping && now - stop_at >= 2000 * 1000000ull) { r->fault = 1; break; }
        uint64_t drain_end = stopping ? stop_at + 2000 * 1000000ull : limit;
        if (drain(pipes[0][0], &r->out, drain_end) ||
            drain(pipes[1][0], &r->err, drain_end)) r->fault = 1;
        if (!setup_eof) {
            ssize_t n = read(pipes[2][0], setup + setup_n, sizeof setup - setup_n);
            if (n > 0) { setup_n += (size_t)n; if (setup_n == sizeof setup) r->fault = 1; }
            else if (!n) setup_eof = 1;
            else if ((*__errno_location ()) != 11 && (*__errno_location ()) != 4) r->fault = 1;
        }
        if (killed) {
            pid_t p; int status;
            while ((p = waitpid(-1, &status, 1)) > 0) {
                if (p == child) { r->status = status; r->reaped = now_ns(); }
            }
            if (p < 0 && (*__errno_location ()) == 10) r->clean = 1;
            else if (p < 0 && (*__errno_location ()) != 4) r->fault = 1;
            if (r->clean && r->out.eof && r->err.eof && setup_eof) break;
        }
        struct pollfd pf[3];
        for (int i = 0; i != 3; ++i) pf[i] = (struct pollfd){pipes[i][0], 0x001, 0};
        if (poll(pf, 3, 5) < 0 && (*__errno_location ()) != 4) r->fault = 1;
    }
    if (setup_n == sizeof(struct child_fault)) {
        struct child_fault f; memcpy(&f, setup, sizeof f);
        r->child_stage = f.stage; r->child_errno = f.number; r->fault = 1;
    } else if (setup_n || !setup_eof) r->fault = 1;
done:
    for (int i = 0; i != 3; ++i) for (int j = 0; j != 2; ++j)
        if (pipes[i][j] >= 0) close(pipes[i][j]);
    r->finished = now_ns();
}
static int retired_at(const char *path)
{
    DIR *d = opendir(path);
    if (!d) return -1;
    struct dirent *e; int empty = 1;
    (*__errno_location ()) = 0;
    while ((e = readdir(d))) {
        if (e->d_name[0] >= '0' && e->d_name[0] <= '9') empty = 0;
    }
    if ((*__errno_location ())) empty = -1;
    if (closedir(d)) empty = -1;
    return empty;
}
static int append(char *b, size_t *n, const char *fmt, ...)
{
    va_list ap; __builtin_va_start(ap,fmt);
    int z = vsnprintf(b + *n, 4096u - *n, fmt, ap); __builtin_va_end(ap);
    if (z < 0 || (size_t)z >= 4096u - *n) return -1;
    *n += (size_t)z; return 0;
}
static int stream_json(char *b, size_t *n, const struct stream *s)
{
    char h[1024u * 2 + 1];
    const char *hex = "0123456789abcdef";
    for (size_t i = 0; i != s->kept; ++i) {
        h[2*i] = hex[s->data[i] >> 4]; h[2*i+1] = hex[s->data[i] & 15];
    }
    h[2*s->kept] = 0;
    return append(b, n, "{\"hex\":\"%s\",\"eof\":%s,\"truncated\":%s,"
                  "\"observed\":%llu,\"retained\":%zu,\"discarded\":%llu,"
                  "\"limit\":%u,\"eof_ns\":%llu}", h, s->eof ? "true" : "false",
                  s->observed != s->kept ? "true" : "false",
                  (unsigned long long)s->observed, s->kept,
                  (unsigned long long)(s->observed - s->kept), 1024u,
                  (unsigned long long)s->eof_ns);
}
static int frame(char *b, const struct result *r, int empty)
{
    size_t n = 0;
    const char *const argv_case = nd_core_case;
    if (append(b, &n, "ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\","
               "\"app\",\"%s\"],\"cwd\":\"/case/work\","
               "\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},"
               "\"raw_wait_status\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,"
               "\"finished_ns\":%llu,\"streams\":{\"stdout\":", argv_case, r->status,
               (unsigned long long)r->started, (unsigned long long)r->reaped,
               (unsigned long long)r->finished) ||
        stream_json(b, &n, &r->out) || append(b, &n, ",\"stderr\":") ||
        stream_json(b, &n, &r->err) ||
        append(b, &n, "},\"procfs_empty\":%s}\n",
               empty && r->clean && !r->fault && !r->timeout ? "true" : "false")) return -1;
    return (int)n;
}
static int write_all(int fd, const void *data, size_t len);
static int publish(int fd, const struct result *r, int empty)
{
    char b[4096u];
    int n = frame(b, r, empty);
    if (n < 0) {
        struct result failed = *r;
        failed.fault = 1; failed.out.kept = 0; failed.err.kept = 0;
        n = frame(b, &failed, 0);
    }
    if (n <= 0 || n > (int)4096) return -1;
    ssize_t written;
    do { written = write(fd, b, (size_t)n); } while (written < 0 && (*__errno_location ()) == 4);
    return written == n ? 0 : -1;
}
static int write_all(int fd, const void *data, size_t len)
{
    const unsigned char *p = data;
    uint64_t start = now_ns();
    if (!start) return -1;
    uint64_t deadline = bounded_deadline(start + 2000 * 1000000ull, 0);
    while (len) {
        uint64_t current = now_ns();
        if (!current || current >= deadline) break;
        ssize_t n = write(fd, p, len);
        if (n > 0) { p += n; len -= (size_t)n; }
        else if (n < 0 && ((*__errno_location ()) == 4 || (*__errno_location ()) == 11)) {
            struct pollfd f = {fd, 0x004, 0};
            if (poll(&f, 1, 5) < 0 && (*__errno_location ()) != 4) return -1;
        } else return -1;
    }
    return len ? -1 : 0;
}
static int save_file(const char *path, const void *p, size_t n)
{
    int fd = open(path, 01 | 0100 | 0200 | 02000000, 0600);
    if (fd < 0) return -1;
    int bad = write_all(fd, p, n);
    if (close(fd)) bad = -1;
    return bad;
}
static int helper(const char *tag, const char *path, char *const av[], int *safe)
{
    struct result r; char name[128], record[256];
    supervise(path, av, helper_env, ((void *)0), helper_timeout_ms(path), &r);
    if (!r.clean) *safe = 0;
    int bad = r.fault || r.timeout || !r.clean || r.status != 0 ||
              !r.out.eof || !r.err.eof || r.out.observed != r.out.kept ||
              r.err.observed != r.err.kept;
    snprintf(name, sizeof name, "/case/evidence/%s.stdout", tag);
    if (save_file(name, r.out.data, r.out.kept)) bad = 1;
    snprintf(name, sizeof name, "/case/evidence/%s.stderr", tag);
    if (save_file(name, r.err.data, r.err.kept)) bad = 1;
    int n = snprintf(record, sizeof record, "status=%d fault=%d timeout=%d clean=%d stage=%d errno=%d\n",
                     r.status, r.fault, r.timeout, r.clean, r.child_stage, r.child_errno);
    snprintf(name, sizeof name, "/case/evidence/%s.status", tag);
    if (n < 0 || (size_t)n >= sizeof record || save_file(name, record, (size_t)n)) bad = 1;
    return bad ? -1 : 0;
}
static int mount_one(const char *type, const char *path)
{
    return mount(type, path, type, 0, ((void *)0));
}
static void remain_pid1(void)
{
    for (;;) { struct timespec t = {1, 0}; nanosleep(&t, ((void *)0)); }
}
static void poweroff_forever(int console)
{
    struct result r;
    supervise("/poweroff", (char *const[]){"/poweroff", ((void *)0)}, helper_env, ((void *)0), 2000, &r);
    const char message[] = "native diagnostic teardown error: poweroff returned\n";
    if (console >= 0) (void)write_all(console, message, sizeof message - 1);
    remain_pid1();
}
static unsigned pair_active_round;
static const char *pair_fail_phase="setup";
static int pair_rounds_initialized;
static char pair_evidence_dir[128];
static int pair_host_cpus[2];
static int pair_read_value(const char *path,const char *expected)
{
    char b[32];int fd=open(path,00|02000000|0400000);
    if(fd<0)return -1;
    ssize_t n=read(fd,b,sizeof b);int ok=n==(ssize_t)strlen(expected) && !memcmp(b,expected,(size_t)n);
    if(ok)ok=read(fd,b,sizeof b)==0;
    if(close(fd))ok=0;
    return ok?0:-1;
}

ssize_t getrandom (void *__buffer, size_t __length,
                   unsigned int __flags) __attribute__ ((__warn_unused_result__));
int getentropy (void *__buffer, size_t __length) __attribute__ ((__warn_unused_result__));

struct pair_assignment {
    unsigned long magic, nonce[2];
    unsigned int os, count;
    unsigned long generation;
    int physical[2];
};
_Static_assert(sizeof(struct pair_assignment)==48,"LP64 assignment record");
static inline int pair_literal(const char **p,const char *end,const char *text)
{
    const char *q=*p;
    while(*text) { if(q==end || *q++!=*text++)return -1; }
    *p=q;return 0;
}
static inline int pair_number(const char **p,const char *end,unsigned long *out)
{
    const char *q=*p;unsigned long n=0;
    if(q==end || *q<'0' || *q>'9')return -1;
    while(q!=end && *q>='0' && *q<='9') {
        unsigned long d=(unsigned long)(*q++-'0');
        if(n>(~0UL-d)/10)return -1;
        n=n*10+d;
    }
    *p=q;*out=n;return 0;
}
static inline int pair_routes(const char *log,unsigned long size,
                              const struct pair_assignment *a,unsigned long *generation)
{
    unsigned seen=0;unsigned long gen=0;
    const char *end=log+size;
    for(const char *line=log;line<end;) {
        const char *next=line;while(next<end && *next!='\n')next++;
        for(const char *p=line;p<next;p++) {
            const char *q=p;unsigned long os,g,port,rank,cpu;
            if(pair_literal(&q,next,"IHK-SMP: control accepted os="))continue;
            if(pair_number(&q,next,&os) || pair_literal(&q,next," generation=") ||
               pair_number(&q,next,&g) || pair_literal(&q,next," port=") ||
               pair_number(&q,next,&port))return -1;
            if(os!=a->os || port!=501)continue;
            if(pair_literal(&q,next," guest_cpu=") || pair_number(&q,next,&rank) ||
               pair_literal(&q,next," linux_cpu=") || pair_number(&q,next,&cpu) ||
               pair_literal(&q,next," cookie=") || !g || rank>=2 ||
               cpu!=(unsigned long)a->physical[rank] || (seen&(1U<<rank)) ||
               (seen && gen!=g))return -1;
            gen=g;seen|=1U<<rank;
        }
        line=next<end?next+1:end;
    }
    if(seen!=3)return -1;
    *generation=gen;return 0;
}
static inline int pair_assignment_valid(const struct pair_assignment *a,
                                      const unsigned long nonce[2])
{
    return a->magic==0x3155504344524150UL && a->nonce[0]==nonce[0] &&
        a->nonce[1]==nonce[1] && (nonce[0]||nonce[1]) && a->os==0 &&
        a->count==2 && a->generation>0 && a->physical[0]==1 && a->physical[1]==2;
}
static unsigned long pair_nonce[2];
static unsigned long pair_generation;
static unsigned int pair_os;
static int pair_prepare_challenge(void)
{
    ssize_t n=getrandom(pair_nonce,sizeof pair_nonce,0x01);
    if(n!=(ssize_t)sizeof pair_nonce || !(pair_nonce[0]||pair_nonce[1]))return -1;
    return save_file("/case/evidence/pair.challenge",pair_nonce,sizeof pair_nonce);
}
static struct stat pair_assignment_identity;
static int pair_assignment_bound;
static int pair_trace_same(const struct stat *,const struct stat *);
static int pair_route_reuse(const char *,size_t,const struct pair_assignment *,unsigned long *);
static int pair_discover(int cpus[2])
{
    struct pair_assignment a;char tail;struct stat s={0};
    int proof=open("/case/evidence/pair.assignment",00|02000000|0400000|04000);
    if(proof<0)return 77;
    int ok=fstat(proof,&s)==0 && ((((s.st_mode)) & 0170000) == (0100000)) && s.st_uid==0 && s.st_gid==0 &&
        s.st_nlink==1 && (s.st_mode&07777)==0600 && s.st_size==(off_t)sizeof a;
    if(ok)ok=read(proof,&a,sizeof a)==(ssize_t)sizeof a && read(proof,&tail,1)==0 &&
        pair_assignment_valid(&a,pair_nonce);
    struct stat after,assignment_stat=s;
    if(ok)ok=!fstat(proof,&after) && pair_trace_same(&s,&after);
    if(ok && pair_active_round)ok=pair_assignment_bound && pair_trace_same(&pair_assignment_identity,&s) &&
        a.os==pair_os && a.generation==pair_generation && a.physical[0]==pair_host_cpus[0] && a.physical[1]==pair_host_cpus[1];
    if(close(proof))ok=0;
    if(!ok)return 77;
    char log[262144];unsigned long generation=0;
    int n=klogctl(3,log,sizeof log);
    if(pair_active_round) {
        if(n<=0 || n>(int)sizeof log || pair_route_reuse(log,(size_t)n,&a,&generation))return 77;
    } else
    if(n<=0 || n==(int)sizeof log || pair_routes(log,(unsigned long)n,&a,&generation))return 77;
    if(generation!=a.generation)return 77;
    int fd=open("/dev/mcos0",00|02000000|0400000);if(fd<0)return 77;
    ok=fstat(fd,&s)==0 && ((((s.st_mode)) & 0170000) == (0020000)) && ioctl(fd,0x30a02907,0)==2;
    if(ok)ok=pair_read_value("/sys/devices/system/cpu/online","0,3\n")==0 &&
        pair_read_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/num_processors","2\n")==0 &&
        pair_read_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online","1\n")==0 &&
        pair_read_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu1/online","1\n")==0;
    if(ok)ok=ioctl(fd,0x30a02907,0)==2;
    if(close(fd))ok=0;
    if(!ok)return 77;
    pair_host_cpus[0]=a.physical[0];pair_host_cpus[1]=a.physical[1];
    pair_generation=a.generation;pair_os=a.os;
    if(!pair_active_round){pair_assignment_identity=assignment_stat;pair_assignment_bound=1;}
    cpus[0]=0;cpus[1]=1;
    return 0;
}
static struct result pair_results[2];
static int pair_load_results(void)
{
    for(int i=0;i<2;i++) {
        char p[4096];snprintf(p,sizeof p,"%s/app%d.result",pair_evidence_dir,i);
        int fd=open(p,00|0400000|02000000|04000);if(fd<0)return -1;
        struct stat s;int ok=!fstat(fd,&s) && ((((s.st_mode)) & 0170000) == (0100000)) && s.st_size==(off_t)sizeof(struct result);
        size_t pos=0;while(ok && pos<sizeof(struct result)) {
            ssize_t n=read(fd,(char*)&pair_results[i]+pos,sizeof(struct result)-pos);
            if(n>0)pos+=(size_t)n;else if(n<0 && (*__errno_location ())==4)continue;else ok=0;
        }
        if(close(fd))ok=0;
        if(!ok || pair_results[i].out.kept>1024u || pair_results[i].err.kept>1024u)return -1;
    }
    return 0;
}
static int publish_pair(int fd,int empty)
{
    char b[4096u];size_t n=0;
    if(append(b,&n,"ND_PAIR {\"os\":%u,\"generation\":%lu,\"host_cpus\":[%d,%d],\"cpus\":[0,1],\"procfs_empty\":%s,\"apps\":[",pair_os,pair_generation,pair_host_cpus[0],pair_host_cpus[1],empty?"true":"false"))return -1;
    for(int i=0;i<2;i++) {
        struct result *r=&pair_results[i];
        if(append(b,&n,"%s{\"id\":%d,\"pid\":%d,\"cpu\":%d,\"cwd\":\"/case/two-app/work%d\",\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"-c\",\"%d\",\"0\",\"/apps/app%d\"],\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\",\"PAIR_CPU\":\"%d\"},\"raw_wait_status\":%d,\"clean\":%d,\"fault\":%d,\"timeout\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,\"finished_ns\":%llu,\"streams\":{\"stdout\":",i?",":"",i,r->pid,i,i,i,i,i,r->status,r->clean,r->fault,r->timeout,(unsigned long long)r->started,(unsigned long long)r->reaped,(unsigned long long)r->finished) ||
           stream_json(b,&n,&r->out) || append(b,&n,",\"stderr\":") || stream_json(b,&n,&r->err) || append(b,&n,"}}"))return -1;
    }
    if(append(b,&n,"]}\n"))return -1;
    return write_all(fd,b,n);
}
static const unsigned char pair_round_stdout_0[] = {98,97,116,99,104,32,98,101,103,105,110,32,99,97,115,101,115,61,50,32,109,105,120,101,100,95,114,111,117,110,100,115,61,51,10,114,117,115,116,45,102,105,108,101,45,114,111,117,110,100,116,114,105,112,32,105,110,105,116,105,97,108,61,49,54,32,111,118,101,114,119,114,105,116,101,61,52,32,115,104,114,105,110,107,61,49,48,32,103,114,111,119,61,49,52,32,122,101,114,111,115,61,52,32,116,97,105,108,61,97,97,98,98,99,99,32,105,110,118,97,108,105,100,95,115,101,101,107,61,50,50,32,99,117,114,115,111,114,61,49,52,32,99,104,101,99,107,101,100,95,99,108,111,115,101,61,49,32,114,101,109,111,118,101,100,61,49,10,109,105,120,101,100,32,114,111,117,110,100,115,61,51,32,98,121,116,101,115,95,101,97,99,104,61,56,49,57,51,32,99,104,101,99,107,115,117,109,95,116,111,116,97,108,61,51,48,55,50,50,55,48,10,102,105,108,101,115,61,51,32,99,104,101,99,107,101,100,95,99,108,111,115,101,115,61,54,32,114,101,111,112,101,110,101,100,61,51,32,101,111,102,61,51,32,114,101,109,111,118,101,100,61,51,10,106,111,105,110,101,100,95,116,104,114,101,97,100,115,61,54,32,116,117,114,110,115,95,101,97,99,104,61,49,50,56,32,99,111,117,110,116,101,114,95,116,111,116,97,108,61,55,54,56,10,98,97,116,99,104,32,112,97,115,115,32,99,97,115,101,115,61,50,32,99,104,101,99,107,101,100,95,99,108,111,115,101,115,61,55,32,114,101,109,111,118,101,100,61,52,32,106,111,105,110,101,100,95,116,104,114,101,97,100,115,61,54,10};
static const unsigned char pair_round_stdout_1[] = {70,80,84,72,82,69,65,68,32,118,49,32,116,104,114,101,97,100,115,61,50,32,115,97,109,101,95,112,101,114,109,105,116,116,101,100,95,99,112,117,61,49,32,100,105,115,116,105,110,99,116,95,116,105,100,61,49,10,116,104,114,101,97,100,48,32,114,111,117,110,100,115,61,54,52,32,121,109,109,95,108,97,110,101,115,61,54,52,32,112,101,101,114,95,112,114,111,103,114,101,115,115,61,54,52,32,121,105,101,108,100,95,109,105,110,61,54,52,32,99,111,110,116,114,111,108,115,61,48,55,55,102,47,51,102,56,48,32,114,101,115,116,111,114,101,100,61,49,10,116,104,114,101,97,100,49,32,114,111,117,110,100,115,61,54,52,32,121,109,109,95,108,97,110,101,115,61,54,52,32,112,101,101,114,95,112,114,111,103,114,101,115,115,61,54,52,32,121,105,101,108,100,95,109,105,110,61,54,52,32,99,111,110,116,114,111,108,115,61,48,98,55,102,47,53,102,56,48,32,114,101,115,116,111,114,101,100,61,49,10,70,80,84,72,82,69,65,68,32,80,65,83,83,10};
static struct stat pair_workspace[3];
static int pair_seen_pids[20], pair_seen_pid_count;
static unsigned long long pair_seen_tokens[240];
static unsigned pair_seen_token_count;
static int pair_round_workdirs(void)
{
    static const char *paths[]={"/case" "/two-app","/case" "/two-app/work0","/case" "/two-app/work1"};
    if(pair_active_round==0)for(int i=0;i<3;i++)if(mkdir(paths[i],0700))return -1;
    for(int i=0;i<3;i++) {
        struct stat s;
        if(lstat(paths[i],&s) || !((((s.st_mode)) & 0170000) == (0040000)) || s.st_uid!=geteuid() ||
           s.st_gid!=getegid() || (s.st_mode&07777)!=0700)return -1;
        if(pair_active_round==0)pair_workspace[i]=s;
        else if(s.st_dev!=pair_workspace[i].st_dev || s.st_ino!=pair_workspace[i].st_ino ||
                s.st_uid!=pair_workspace[i].st_uid || s.st_gid!=pair_workspace[i].st_gid ||
                s.st_mode!=pair_workspace[i].st_mode || s.st_nlink!=pair_workspace[i].st_nlink)return -1;
        if(i) {
            DIR *d=opendir(paths[i]);if(!d)return -1;
            struct dirent *e;int bad=0;(*__errno_location ())=0;
            while((e=readdir(d)))if(strcmp(e->d_name,".") && strcmp(e->d_name,".."))bad=1;
            if((*__errno_location ()))bad=1;
            if(closedir(d))bad=1;
            if(bad)return -1;
        }
    }
    return 0;
}
static int pair_round_streams(void)
{
    const unsigned char *expected[]={pair_round_stdout_0,pair_round_stdout_1};
    const size_t lengths[]={sizeof pair_round_stdout_0,sizeof pair_round_stdout_1};
    if(pair_os!=0 || pair_generation!=1 || pair_host_cpus[0]!=1 || pair_host_cpus[1]!=2)return -1;
    for(int i=0;i<2;i++) {
        struct result *r=&pair_results[i];
        if(r->pid<=0 || r->status || r->fault || r->timeout || !r->clean ||
           !r->out.eof || !r->err.eof || r->out.kept!=lengths[i] ||
           r->out.observed!=lengths[i] || r->err.kept || r->err.observed ||
           memcmp(r->out.data,expected[i],lengths[i]) || !r->started ||
           r->started>r->reaped || r->reaped>r->finished ||
           r->out.eof_ns<r->started || r->out.eof_ns>r->finished ||
           r->err.eof_ns<r->started || r->err.eof_ns>r->finished)return -1;
        for(int j=0;j<pair_seen_pid_count;j++)if(pair_seen_pids[j]==r->pid)return -1;
        if(pair_seen_pid_count>=20)return -1;
        pair_seen_pids[pair_seen_pid_count++]=r->pid;
    }
    return pair_results[0].started<pair_results[1].reaped &&
           pair_results[1].started<pair_results[0].reaped?0:-1;
}
struct pair_round_delivery { unsigned long long worker,serial;unsigned number;int returned,routed,launcher; };
static int pair_round_trace(const char *log,int pid,int cpu)
{
    struct pair_round_delivery calls[256];unsigned count=0,exits=0,attempts=0;
    int schedules=0,published=0,deleted=0,releases=0,last_errno=-1,terminal=0;
    for(const char *p=log;*p;) {
        const char *end=strchr(p,'\n');size_t n=end?(size_t)(end-p):strlen(p);
        if(n>=512) {const char *app=strstr(p,"application");if(app && (!end || app<end))return -1;p=end?end+1:p+n;continue;}
        char line[512];memcpy(line,p,n);line[n]=0;
        p=end?end+1:p+n;
        char *mark;unsigned osid=0;unsigned long generation=0;int found=0,c=-1,used=0;
        if((mark=strstr(line,"application_syscall="))) {
            char kind[24];int offset=0;
            if(sscanf(mark,"application_syscall=%23s os=%u generation=%lu pid=%d %n",kind,&osid,&generation,&found,&offset)!=4)return -1;
            if(found!=pid)continue;
            if(osid || generation!=1)return -1;
            unsigned long long worker=0,serial=0;unsigned number=0;long value=0;int launcher=-1;
            char *tail=mark+offset;struct pair_round_delivery *d=((void *)0);
            if(!strcmp(kind,"delivered")) {
                if(sscanf(tail,"worker=%llu delivery=%llu cpu=%d number=%u%n",&worker,&serial,&c,&number,&used)!=4 || tail[used] || !worker || !serial || c!=cpu || terminal || number==60 || count==256)return -1;
                for(unsigned j=0;j<count;j++)if(calls[j].worker==worker && calls[j].serial==serial)return -1;
                calls[count++]=(struct pair_round_delivery){worker,serial,number,0,0,-1};
                if(number==231){terminal=1;exits++;}
            } else {
                if(!strcmp(kind,"returned")) {
                    if(sscanf(tail,"worker=%llu delivery=%llu cpu=%d value=%ld%n",&worker,&serial,&c,&value,&used)!=4 || tail[used] || c!=cpu || terminal)return -1;
                } else if(!strcmp(kind,"return_route")) {
                    if(sscanf(tail,"worker=%llu delivery=%llu launcher_cpu=%d guest_cpu=%d%n",&worker,&serial,&launcher,&c,&used)!=4 || tail[used] || c!=cpu || launcher<0 || launcher>1 || launcher==cpu || terminal)return -1;
                } else return -1;
                for(unsigned j=0;j<count;j++)if(calls[j].worker==worker && calls[j].serial==serial)d=&calls[j];
                if(!d || d->number==231 || d->returned)return -1;
                if(!strcmp(kind,"returned"))d->returned=1;
                else {if(d->routed)return -1;d->routed=1;d->launcher=launcher;}
            }
        } else if((mark=strstr(line,"application SCHEDULE "))) {
            if(sscanf(mark,"application SCHEDULE os=%u generation=%lu pid=%d cpu=%d%n",&osid,&generation,&found,&c,&used)!=4)return -1;
            if(found==pid){if(osid || generation!=1 || c!=cpu || mark[used] || ++schedules!=1)return -1;}
        } else if((mark=strstr(line,"application retirement "))) {
            unsigned long long token=0;int error=0;
            if(sscanf(mark,"application retirement os=%u generation=%lu pid=%d token=%llu errno=%d%n",&osid,&generation,&found,&token,&error,&used)!=5)return -1;
            if(found!=pid)continue;
            if(osid || generation!=1 || mark[used] || !terminal || !token || last_errno==0 || (error!=-11 && error!=0) || ++attempts>12 || pair_seen_token_count==240)return -1;
            for(unsigned j=0;j<pair_seen_token_count;j++)if(pair_seen_tokens[j]==token)return -1;
            pair_seen_tokens[pair_seen_token_count++]=token;last_errno=error;
        } else if((mark=strstr(line,"application_process=release "))) {
            int error=0;
            if(sscanf(mark,"application_process=release os=%u generation=%lu pid=%d cleanup_errno=%d%n",&osid,&generation,&found,&error,&used)!=4)return -1;
            if(found==pid && (osid || generation!=1 || mark[used] || error || last_errno!=0 || ++releases!=1))return -1;
        } else if((mark=strstr(line,"application procfs "))) {
            char op[16];int tid=-1;
            if(sscanf(mark,"application procfs %15s os=%u generation=%lu pid=%d tid=%d%n",op,&osid,&generation,&found,&tid,&used)!=5)return -1;
            if(found==pid) {
                if(osid || generation!=1 || tid<=0 || mark[used])return -1;
                if(strcmp(op,"published") && strcmp(op,"deleted"))return -1;
                if(tid==pid) {if(!strcmp(op,"published"))published++;else deleted++;}
            }
        }
    }
    if(!count || exits!=1 || !attempts || last_errno || releases!=1 || schedules!=1 || published!=1 || deleted!=1)return -1;
    for(unsigned j=0;j<count;j++)if(calls[j].number!=231) {
        if(!calls[j].returned)return -1;
        int slot=calls[j].routed?calls[j].launcher:cpu;
        for(unsigned k=0;k<j;k++)if(calls[k].worker==calls[j].worker && calls[k].number!=231 &&
            (calls[k].routed?calls[k].launcher:cpu)!=slot)return -1;
    }
    return 0;
}
struct pair_trace_record { int fd,pids[2];size_t bytes,offset;struct stat identity; };
static struct pair_trace_record pair_trace_records[10];
static size_t pair_trace_total;
static char pair_trace_authenticated[(2u*1024u*1024u)];
static int pair_trace_application(const char *line)
{
    return strstr(line,"application_syscall=") || strstr(line,"application SCHEDULE ") ||
           strstr(line,"application retirement ") || strstr(line,"application_process=release ") ||
           strstr(line,"application procfs ");
}
static int pair_trace_once(const char *line)
{
    return strstr(line,"control accepted ") || strstr(line,"NATIVE_PAIR_CPU ");
}
static int pair_trace_same(const struct stat *a,const struct stat *b)
{
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino && a->st_uid==b->st_uid &&
           a->st_gid==b->st_gid && a->st_mode==b->st_mode && a->st_nlink==b->st_nlink &&
           a->st_size==b->st_size && a->st_mtim.tv_sec==b->st_mtim.tv_sec &&
           a->st_mtim.tv_nsec==b->st_mtim.tv_nsec && a->st_ctim.tv_sec==b->st_ctim.tv_sec &&
           a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int pair_trace_member(const char *line,size_t length,int pid,size_t *cursor)
{
    for(unsigned round=0;round<pair_active_round && round<10;round++) {
        struct pair_trace_record *r=&pair_trace_records[round];struct stat current;
        if(pid>0 && pid!=r->pids[0] && pid!=r->pids[1])continue;
        if(r->fd<0 || !r->bytes || fstat(r->fd,&current) || !pair_trace_same(&r->identity,&current))return -1;
        size_t off=r->offset,end=r->offset+r->bytes;
        while(off<end) {
            const char *lf=memchr(pair_trace_authenticated+off,'\n',end-off);if(!lf)return -1;
            size_t count=(size_t)(lf-(pair_trace_authenticated+off))+1;
            if(off>=*cursor && count==length && !memcmp(pair_trace_authenticated+off,line,length)){*cursor=off+count;return 1;}
            off+=count;
        }
    }
    return 0;
}
static int pair_trace_pid(const char *line)
{
    const char *id=strstr(line," os=");unsigned osid=0;unsigned long generation=0;int pid=0;
    if(!id || sscanf(id," os=%u generation=%lu pid=%d",&osid,&generation,&pid)!=3 || osid || generation!=1 || pid<=0)return -1;
    return pid;
}
static int pair_trace_save(const char *log,size_t bytes)
{
    static char selected[1048576];size_t used=0,cursor=0;int current_seen=0;
    if(pair_active_round>=10 || !bytes || memchr(log,0,bytes))return -1;
    for(size_t off=0;off<bytes;) {
        const char *end=memchr(log+off,'\n',bytes-off);if(!end)return -1;
        size_t length=(size_t)(end-(log+off))+1;int keep=1;
        static char line[65536];if(length>=sizeof line)return -1;
        memcpy(line,log+off,length);line[length]=0;
        if(pair_trace_application(line)) {
            int pid=pair_trace_pid(line);if(pid<0)return -1;
            keep=pid==pair_results[0].pid || pid==pair_results[1].pid;
            if(keep)current_seen=1;
            else if(current_seen || pair_trace_member(log+off,length,pid,&cursor)!=1)return -1;
        } else if(pair_trace_once(line) && pair_active_round) {
            if(current_seen || pair_trace_member(log+off,length,0,&cursor)!=1)return -1;
            keep=0;
        }
        if(keep) {if(length>sizeof selected-used)return -1;memcpy(selected+used,log+off,length);used+=length;}
        off+=length;
    }
    if(!used || used>(2u*1024u*1024u)-pair_trace_total)return -1;
    char path[4096];int count=snprintf(path,sizeof path,"%s/current-trace.log",pair_evidence_dir);
    if(count<0 || (size_t)count>=sizeof path || save_file(path,selected,used))return -1;
    struct pair_trace_record *r=&pair_trace_records[pair_active_round];
    r->fd=open(path,00|0400000|02000000|04000);
    if(r->fd<0 || fstat(r->fd,&r->identity) || !((((r->identity.st_mode)) & 0170000) == (0100000)) || r->identity.st_nlink!=1 || r->identity.st_size!=(off_t)used)return -1;
    r->pids[0]=pair_results[0].pid;r->pids[1]=pair_results[1].pid;r->bytes=used;
    char identity[256];count=snprintf(identity,sizeof identity,"{\"round\":%u,\"pids\":[%d,%d],\"bytes\":%zu,\"device\":%llu,\"inode\":%llu}\n",pair_active_round,r->pids[0],r->pids[1],used,(unsigned long long)r->identity.st_dev,(unsigned long long)r->identity.st_ino);
    int pn=snprintf(path,sizeof path,"%s/current-trace.identity.json",pair_evidence_dir);
    if(count<0 || (size_t)count>=sizeof identity || pn<0 || (size_t)pn>=sizeof path || save_file(path,identity,(size_t)count))return -1;
    r->offset=pair_trace_total;memcpy(pair_trace_authenticated+r->offset,selected,used);
    pair_trace_total+=used;return 0;
}
static int pair_trace_publish(int console,const char *last,size_t bytes)
{
    static char chunk[16384];size_t published=0,cursor=0;
    for(unsigned round=0;round<10;round++) {
        struct pair_trace_record *r=&pair_trace_records[round];struct stat before,after;
        if(r->fd<0 || !r->bytes || r->pids[0]!=pair_seen_pids[round*2] || r->pids[1]!=pair_seen_pids[round*2+1] ||
           fstat(r->fd,&before) || !pair_trace_same(&r->identity,&before) || lseek(r->fd,0,0)!=0)return -1;
        size_t off=0;while(off<r->bytes) {
            size_t want=r->bytes-off;if(want>sizeof chunk)want=sizeof chunk;
            ssize_t n=read(r->fd,chunk,want);if(n<0 && (*__errno_location ())==4)continue;
            if(n<=0 || memcmp(chunk,pair_trace_authenticated+r->offset+off,(size_t)n) || write_all(console,chunk,(size_t)n))return -1;
            off+=(size_t)n;
        }
        if(fstat(r->fd,&after) || !pair_trace_same(&before,&after))return -1;
        published+=off;
    }
    if(published!=pair_trace_total || published>(2u*1024u*1024u) || memchr(last,0,bytes))return -1;
    for(size_t off=0;off<bytes;) {
        const char *end=memchr(last+off,'\n',bytes-off);if(!end)return -1;
        size_t length=(size_t)(end-(last+off))+1;static char line[65536];if(length>=sizeof line)return -1;
        memcpy(line,last+off,length);line[length]=0;
        if(pair_trace_application(line)) {
            int pid=pair_trace_pid(line);if(pid<0 || pair_trace_member(last+off,length,pid,&cursor)!=1)return -1;
        } else if(pair_trace_once(line)) {
            if(pair_trace_member(last+off,length,0,&cursor)!=1)return -1;
        } else {
            if(length>(2u*1024u*1024u)-published || write_all(console,last+off,length))return -1;
            published+=length;
        }
        off+=length;
    }
    for(unsigned round=0;round<10;round++){if(close(pair_trace_records[round].fd))return -1;pair_trace_records[round].fd=-1;}
    return 0;
}
static int pair_diagnostic_file(int console,int fd,const struct stat *identity,
                                const char *data,size_t bytes,const char *kind,unsigned round)
{
    struct stat before,after;char chunk[1024],row[2304];
    if(fd<0 || !bytes || bytes>(2u*1024u*1024u) || fstat(fd,&before) ||
       !pair_trace_same(identity,&before) || !((((before.st_mode)) & 0170000) == (0100000)) ||
       before.st_nlink!=1 || before.st_size!=(off_t)bytes || lseek(fd,0,0)!=0)return -1;
    for(size_t off=0;off<bytes;) {
        size_t want=bytes-off;if(want>sizeof chunk)want=sizeof chunk;
        ssize_t n=read(fd,chunk,want);if(n<0 && (*__errno_location ())==4)continue;
        if(n<=0 || memcmp(chunk,data+off,(size_t)n))return -1;
        off+=(size_t)n;
    }
    if(fstat(fd,&after) || !pair_trace_same(&before,&after))return -1;
    int n=snprintf(row,sizeof row,"ND_PAIR_DIAGNOSTIC_BEGIN {\"kind\":\"%s\",\"round\":%u,\"bytes\":%zu}\n",kind,round,bytes);
    if(n<0 || (size_t)n>=sizeof row || write_all(console,row,(size_t)n))return -1;
    for(size_t off=0;off<bytes;) {
        size_t take=bytes-off;if(take>sizeof chunk)take=sizeof chunk;
        n=snprintf(row,sizeof row,"ND_PAIR_DIAGNOSTIC_CHUNK {\"kind\":\"%s\",\"round\":%u,\"offset\":%zu,\"hex\":\"",kind,round,off);
        if(n<0 || (size_t)n+take*2+4>=sizeof row)return -1;
        size_t used=(size_t)n;static const char hex[]="0123456789abcdef";
        for(size_t j=0;j<take;j++){unsigned char c=(unsigned char)data[off+j];row[used++]=hex[c>>4];row[used++]=hex[c&15];}
        memcpy(row+used,"\"}\n",3);used+=3;
        if(write_all(console,row,used))return -1;
        off+=take;
    }
    n=snprintf(row,sizeof row,"ND_PAIR_DIAGNOSTIC_END {\"kind\":\"%s\",\"round\":%u,\"bytes\":%zu}\n",kind,round,bytes);
    return n<0 || (size_t)n>=sizeof row || write_all(console,row,(size_t)n)?-1:0;
}
static int pair_failure_export(int console,const char *last,size_t bytes)
{
    if(!pair_rounds_initialized || bytes==0 || bytes>=1048576)return -1;
    int fd=open("/case" "/evidence/kernel.log",00|0400000|02000000|04000);
    struct stat identity;int bad=fd<0 || fstat(fd,&identity);
    if(!bad)bad=pair_diagnostic_file(console,fd,&identity,last,bytes,"current_raw",pair_active_round);
    if(fd>=0 && close(fd))bad=1;
    if(bad)return -1;
    for(unsigned round=0;round<10;round++) {
        struct pair_trace_record *r=&pair_trace_records[round];
        if(r->fd<0)break;
        if(!r->bytes || r->offset>pair_trace_total || r->bytes>pair_trace_total-r->offset ||
           pair_diagnostic_file(console,r->fd,&r->identity,pair_trace_authenticated+r->offset,r->bytes,"retained",round))return -1;
    }
    return 0;
}
static int pair_route_reuse(const char *log,size_t bytes,const struct pair_assignment *a,unsigned long *generation)
{
    struct pair_trace_record *r=&pair_trace_records[0];struct stat current;
    if(!pair_active_round || !bytes || bytes>262144 || memchr(log,0,bytes) ||
       r->fd<0 || !r->bytes || r->offset!=0 || r->bytes>pair_trace_total ||
       r->pids[0]!=pair_seen_pids[0] || r->pids[1]!=pair_seen_pids[1] ||
       fstat(r->fd,&current) || !pair_trace_same(&r->identity,&current) ||
       pair_routes(pair_trace_authenticated,r->bytes,a,generation) || *generation!=a->generation)return -1;
    size_t cursor=0;
    for(size_t off=0;off<bytes;) {
        const char *end=memchr(log+off,'\n',bytes-off);if(!end)return -1;
        size_t length=(size_t)(end-(log+off))+1;char line[65536];
        if(length>=sizeof line)return -1;
        memcpy(line,log+off,length);line[length]=0;
        if(pair_trace_once(line) && pair_trace_member(log+off,length,0,&cursor)!=1)return -1;
        off+=length;
    }
    return 0;
}
static int pair_round_gate(void)
{
    static char log[1048577];int n=klogctl(3,log,sizeof log-1);
    pair_fail_phase="kernel_snapshot";
    if(n<=0 || n==(int)sizeof log-1)return -1;
    log[n]=0;
    pair_fail_phase="stream_identity_oracle";
    if(pair_round_streams())return -1;
    pair_fail_phase="application_membership";
    for(const char *p=log;*p;p++)if(!strncmp(p,"application_syscall=",20) || !strncmp(p,"application SCHEDULE ",21)) {
        const char *end=strchr(p,'\n'),*id=strstr(p," pid=");int pid=0;unsigned j=0;
        if(!id || (end && id>=end) || sscanf(id," pid=%d",&pid)!=1)return -1;
        for(;j<(unsigned)pair_seen_pid_count;j++)if(pair_seen_pids[j]==pid)break;
        if(j==(unsigned)pair_seen_pid_count)return -1;
    }
    for(int i=0;i<2;i++){pair_fail_phase=i?"app1_trace_oracle":"app0_trace_oracle";if(pair_round_trace(log,pair_results[i].pid,i))return -1;}
    pair_fail_phase="trace_retention";
    return pair_trace_save(log,(size_t)n);
}
static int pair_worker(int i, int cpu)
{
    char cpuenv[32], core[16], work[4096], app[32], name[4096], status[256];
    struct result r;
    snprintf(cpuenv,sizeof cpuenv,"PAIR_CPU=%d",cpu);
    snprintf(core,sizeof core,"%d",cpu);
    snprintf(work,sizeof work,"/case" "/two-app/work%d",i);
    snprintf(app,sizeof app,"/apps/app%d",i);
    char *av[]={"/bin/mcexec","-t","1","-c",core,"0",app,((void *)0)};
    char *env[]={"PATH=/usr/bin:/bin","COKERNEL_PATH=/apps",cpuenv,((void *)0)};
    supervise("/bin/mcexec",av,env,work,10000,&r);
    int good=!r.fault && !r.timeout && r.clean && r.status==0 &&
        r.out.eof && r.err.eof && r.out.observed==r.out.kept &&
        r.err.observed==r.err.kept;
    snprintf(name,sizeof name,"%s/app%d.stdout",pair_evidence_dir,i);
    if(save_file(name,r.out.data,r.out.kept))good=0;
    snprintf(name,sizeof name,"%s/app%d.stderr",pair_evidence_dir,i);
    if(save_file(name,r.err.data,r.err.kept))good=0;
    int n=snprintf(status,sizeof status,
        "{\"app\":%d,\"cpu\":%d,\"raw_wait_status\":%d,\"clean\":%d,\"fault\":%d,\"timeout\":%d,\"started_ns\":%llu,\"finished_ns\":%llu}\n",
        i,cpu,r.status,r.clean,r.fault,r.timeout,
        (unsigned long long)r.started,(unsigned long long)r.finished);
    snprintf(name,sizeof name,"%s/app%d.status.json",pair_evidence_dir,i);
    if(n<0 || (size_t)n>=sizeof status || save_file(name,status,(size_t)n))good=0;
    snprintf(name,sizeof name,"%s/app%d.result",pair_evidence_dir,i);
    if(save_file(name,&r,sizeof r))good=0;
    return !r.clean ? 2 : !good;
}
static int pair_run_assigned(const int cpus[2], int *safe)
{
    int joined[2]={0,0}, statuses[2]={-1,-1}, bad=0;
    pid_t owners[2]={-1,-1};
    *safe=1;
    if(cpus[0]<0 || cpus[1]<0 || cpus[0]>=1024 || cpus[1]>=1024 || cpus[0]==cpus[1])return 77;
    if(pair_round_workdirs())return 1;
    uint64_t started=now_ns();
    if(!started)return 1;
    uint64_t end=bounded_deadline(started+15000*1000000ull,0);
    *safe=0;
    for(int i=0;i<2;i++) {
        owners[i]=fork();
        if(owners[i]==0) {
            if(prctl(36,1))_exit(2);
            _exit(pair_worker(i,cpus[i]));
        }
        if(owners[i]<0){bad=1;joined[i]=1;break;}
    }
    for(int i=0;i<2;i++)if(owners[i]<0)joined[i]=1;
    while(!joined[0] || !joined[1]) {
        for(int i=0;i<2;i++)if(!joined[i]) {
            pid_t r=waitpid(owners[i],&statuses[i],1);
            if(r==owners[i])joined[i]=1;
            else if(r<0 && (*__errno_location ())!=4)return 1;
        }
        if(joined[0] && joined[1])break;
        uint64_t now=now_ns();
        if(!now || now>=end)return 1;
        struct timespec t={0,1000000};nanosleep(&t,((void *)0));
    }
    *safe=1;
    for(int i=0;i<2;i++)if(owners[i]>0) {
        if(!(((statuses[i]) & 0x7f) == 0) || (((statuses[i]) & 0xff00) >> 8)==2)*safe=0;
        if(statuses[i]!=0)bad=1;
    }
    return bad;
}
static int pair_run(int *safe)
{
    int cpus[2];
    *safe=1;
    if(pair_discover(cpus))return 77;
    return pair_run_assigned(cpus,safe);
}
static int pair_round_empty(void)
{
    uint64_t begin=now_ns(),end=bounded_deadline(begin+5000*1000000ull,0);
    while(begin) {
        uint64_t current=now_ns();if(!current || current>=end)return 0;
        int state=retired_at("/proc/mcos0");if(state==1)return 1;if(state<0)return 0;
        struct timespec pause={0,10000000};nanosleep(&pause,((void *)0));
    }
    return 0;
}
static int pair_round_mark(int fd,const char *kind,unsigned round,uint64_t stamp,int empty)
{
    char b[256];int n=snprintf(b,sizeof b,"ND_PAIR_ROUND_%s {\"round\":%u,\"time_ns\":%llu,\"procfs_empty\":%s}\n",kind,round,(unsigned long long)stamp,empty?"true":"false");
    return n<0 || (size_t)n>=sizeof b || write_all(fd,b,(size_t)n)?-1:0;
}
static int pair_round_fail(int console,const char *phase,int safe)
{
    pair_fail_phase=phase;
    char row[256];int n=snprintf(row,sizeof row,"ND_PAIR_ROUND_FAIL {\"round\":%u,\"phase\":\"%s\",\"safe\":%s}\n",pair_active_round,phase,safe?"true":"false");
    if(n>0 && (size_t)n<sizeof row)(void)write_all(console,row,(size_t)n);
    return -1;
}
static int pair_run_launch_expansion(int console,int *safe,int *empty)
{
    pair_seen_pid_count=0;pair_seen_token_count=0;pair_trace_total=0;*empty=0;
    for(unsigned i=0;i<10;i++)pair_trace_records[i].fd=-1;
    pair_rounds_initialized=1;
    for(pair_active_round=0;pair_active_round<10;pair_active_round++) {
        *safe=1;
        if(!pair_round_empty())return pair_round_fail(console,"pre_round_procfs",*safe);
        int n=snprintf(pair_evidence_dir,sizeof pair_evidence_dir,"/case" "/evidence/round%u",pair_active_round);
        if(n<0 || (size_t)n>=sizeof pair_evidence_dir || mkdir(pair_evidence_dir,0700))return pair_round_fail(console,"evidence_directory",*safe);
        uint64_t start=now_ns();if(!start || pair_round_mark(console,"START",pair_active_round,start,1))return pair_round_fail(console,"start_marker",*safe);
        int run=pair_run(safe);
        if(!*safe)return pair_round_fail(console,"unsafe_owner_handoff",0);
        if(run)return pair_round_fail(console,"pair_run",*safe);
        if(pair_load_results())return pair_round_fail(console,"result_load",*safe);
        if(!pair_round_empty())return pair_round_fail(console,"post_round_procfs",*safe);
        if(pair_round_gate())return pair_round_fail(console,pair_fail_phase,*safe);
        uint64_t finish=now_ns();
        if(!finish || finish<start || pair_results[0].started<start || pair_results[1].started<start ||
           pair_results[0].finished>finish || pair_results[1].finished>finish)return pair_round_fail(console,"round_timestamps",*safe);
        if(publish_pair(console,1) || pair_round_mark(console,"END",pair_active_round,finish,1))return pair_round_fail(console,"result_publication",*safe);
        char name[4096],row[160];n=snprintf(name,sizeof name,"%s/round.json",pair_evidence_dir);
        int size=snprintf(row,sizeof row,"{\"round\":%u,\"started_ns\":%llu,\"finished_ns\":%llu,\"procfs_empty\":true}\n",pair_active_round,(unsigned long long)start,(unsigned long long)finish);
        if(n<0 || (size_t)n>=sizeof name || size<0 || (size_t)size>=sizeof row || save_file(name,row,(size_t)size))return pair_round_fail(console,"round_record",*safe);
    }
    *empty=1;return 0;
}
int main(void)
{
    struct result payload; memset(&payload, 0, sizeof payload); payload.status = -1;
    int console = -1, good = 1, safe = 1, loaded = 0, empty = 0;
    (void)payload_argv; (void)payload_env; (void)publish;
    int saved_level = -1;
    if (getpid() != 1 || geteuid() != 0) return 125;
    uint64_t beginning = now_ns();
    if (!beginning) remain_pid1();
    collector_deadline = beginning + 120u * 1000ull * 1000000ull;
    struct sigaction alarm_action; memset(&alarm_action, 0, sizeof alarm_action);
    alarm_action.__sigaction_handler.sa_handler = outer_expired;
    if (sigemptyset(&alarm_action.sa_mask) || sigaction(14, &alarm_action, ((void *)0)))
        remain_pid1();
    alarm(120u);
    if (mount_one("proc", "/proc") || mount_one("sysfs", "/sys") ||
        mount_one("devtmpfs", "/dev") ||
        mount_one("debugfs", "/sys/kernel/debug")) { good = 0; goto finish; }
    console = open("/dev/console", 01 | 02000000 | 04000);
    if (console < 0) { good = 0; goto finish; }
    if (mkdir("/case/evidence", 0700) && (*__errno_location ()) != 17) { good = 0; goto finish; }
    int fd = open("/proc/sys/kernel/printk", 00 | 02000000);
    char levels[128]; ssize_t count = fd < 0 ? -1 : read(fd, levels, sizeof levels - 1);
    if (fd >= 0 && close(fd)) count = -1;
    if (count <= 0) { good = 0; goto finish; }
    levels[count] = 0;
    if (sscanf(levels, "%d", &saved_level) != 1 || saved_level < 1 || saved_level > 8 ||
        klogctl(6, ((void *)0), 0)) { saved_level = -1; good = 0; goto finish; }
    if (save_file("/case/evidence/printk.original", levels, (size_t)count)) { good = 0; goto finish; }
    if (helper("load-ihk", "/sbin/insmod", (char *const[]){"insmod","/modules/ihk.ko",((void *)0)}, &safe)) { good = 0; goto finish; }
    loaded = 1;
    if (helper("load-smp", "/sbin/insmod", (char *const[]){"insmod","/modules/ihk-smp-x86_64.ko","ihk_trampoline=524288",((void *)0)}, &safe)) { good = 0; goto finish; }
    loaded = 2;
    if (helper("load-mcctrl", "/sbin/insmod", (char *const[]){"insmod","/modules/mcctrl.ko",((void *)0)}, &safe)) { good = 0; goto finish; }
    loaded = 3;
    if(pair_prepare_challenge()) { good=0; goto finish; }
    if (helper("boot", "/bin/native-boot", (char *const[]){"/bin/native-boot",((void *)0)}, &safe)) { good = 0; goto finish; }
    if(pair_run_launch_expansion(console,&safe,&empty))good=0;
    if(!safe)remain_pid1();
finish:;
    char teardown[160];
    int length = snprintf(teardown, sizeof teardown,
                          "modules_loaded=%d processes_reaped=%d procfs_empty=%d nested_os_retained=1\n",
                          loaded, safe, empty);
    if (length < 0 || (size_t)length >= sizeof teardown ||
        save_file("/case/evidence/teardown", teardown, (size_t)length)) good = 0;
    static char kernel_log[1048576];
    int n = klogctl(3, kernel_log, sizeof kernel_log);
    if (n < 0 || n == (int)sizeof kernel_log) good = 0;
    else if (save_file("/case/evidence/kernel.log", kernel_log, (size_t)n) || console < 0) good = 0;
    else {
        if(good) { if(pair_trace_publish(console,kernel_log,(size_t)n))good=0; }
        else if(safe && pair_rounds_initialized && pair_failure_export(console,kernel_log,(size_t)n))good=0;
    }
    if (saved_level < 0 || klogctl(8, ((void *)0), saved_level) || klogctl(6, ((void *)0), 0)) good = 0;
    int evidence_fd = open("/case/evidence", 00 | 0200000 | 02000000);
    if (evidence_fd < 0) good = 0;
    else { if (syncfs(evidence_fd)) good = 0; if (close(evidence_fd)) good = 0; }
    if (!good || !safe) payload.fault = 1;
    payload.finished = now_ns();
    if (console >= 0 && safe) {
        static const char complete[]="ND_PAIR_ROUNDS_COMPLETE {\"rounds\":10,\"os\":0,\"generation\":1,\"procfs_empty\":true}\n";
        int publication = good && empty ? write_all(console,complete,sizeof complete-1) : -1;
        if (publication) payload.fault = 1;
    }
    if (saved_level >= 0 && klogctl(8, ((void *)0), saved_level)) {
        const char message[] = "native diagnostic teardown error: printk restoration\n";
        if (console >= 0) (void)write_all(console, message, sizeof message - 1);
        remain_pid1();
    }
    poweroff_forever(console);
    return 125;
}
