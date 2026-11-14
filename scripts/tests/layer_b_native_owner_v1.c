/*
 * Unreleased Layer-B native pidfd/subreaper owner.
 * TERM, INT, CHLD and PIPE are blocked before fork. Numeric PIDs are audit
 * data only; signalling uses pidfd_send_signal exclusively.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/random.h>
#include <sys/resource.h>
#include <sys/signalfd.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#if !defined(__x86_64__) || defined(__ILP32__)
#error "Layer-B owner requires native x86-64 LP64"
#endif

#ifndef P_PIDFD
#define P_PIDFD 3
#endif
#ifndef SYS_pidfd_open
#define SYS_pidfd_open 434
#endif
#ifndef SYS_pidfd_send_signal
#define SYS_pidfd_send_signal 424
#endif
#ifndef __X32_SYSCALL_BIT
#define __X32_SYSCALL_BIT 0x40000000U
#endif

#define OWNER_MAX_CHILDREN 64U
#define OWNER_PAYLOAD_NS (60ULL * 1000000000ULL)
#define OWNER_TERM_GRACE_NS (3ULL * 1000000000ULL)
#define OWNER_CLEANUP_NS (12ULL * 1000000000ULL)
#define OWNER_RETAIN_POLL_MS 1000

/* This table is also consumed by the source-model tests. Only a successful
 * durable record or reap advances ownership. Every error leaves it retained. */
enum child_phase { ACQUIRED, OWNED, TERMINAL_RECORDED, RETIRED };
enum child_event { ACQUISITION_DURABLE, TERMINAL_DURABLE, REAP_SUCCEEDED,
                   NO_STATUS, WAIT_ERROR, RECORD_ERROR };
static const enum child_phase child_steps[4][6] = {
    {OWNED, ACQUIRED, ACQUIRED, ACQUIRED, ACQUIRED, ACQUIRED},
    {OWNED, TERMINAL_RECORDED, OWNED, OWNED, OWNED, OWNED},
    {TERMINAL_RECORDED, TERMINAL_RECORDED, RETIRED,
     TERMINAL_RECORDED, TERMINAL_RECORDED, TERMINAL_RECORDED},
    {RETIRED, RETIRED, RETIRED, RETIRED, RETIRED, RETIRED},
};

/* Collection and parent-observation policies are explicit finite decisions;
 * tests interpret these exact arrays as well as the BPF bytecode below. */
enum pass_action { STOP_PASS, ADVANCE_SLOT, COMPACTED_SLOT };
static const enum pass_action pass_actions[3] = {
    STOP_PASS, ADVANCE_SLOT, COMPACTED_SLOT, /* collect result -1, 0, 1 */
};
enum scan_event { SCAN_ERROR, SCAN_ECHILD, SCAN_LIVE, SCAN_KNOWN,
                  SCAN_NEW, SCAN_FULL };
enum scan_action { FAIL_SCAN, CLEAR_PARENT, KEEP_PARENT, ACQUIRE_CHILD };
static const enum scan_action scan_actions[6] = {
    FAIL_SCAN, CLEAR_PARENT, KEEP_PARENT, KEEP_PARENT, ACQUIRE_CHILD, FAIL_SCAN,
};

enum payload_outcome {
    PAYLOAD_RUNNING, PAYLOAD_OK, PAYLOAD_EXIT_FAILURE,
    PAYLOAD_INTERRUPTED, PAYLOAD_TIMEOUT, PAYLOAD_OWNER_ERROR,
};

struct child {
    int pidfd;
    pid_t observed_pid; /* never passed to a signal primitive */
    bool payload_root;
    bool term_attempted, kill_sent;
    unsigned long long sequence;
    enum child_phase phase;
    siginfo_t terminal;
};

struct owner {
    int output_fd, signal_fd;
    struct child children[OWNER_MAX_CHILDREN]; /* active only */
    size_t count;
    unsigned long long record_sequence, child_sequence;
    uint64_t started_ns, cleanup_deadline_ns;
    pid_t owner_pid;
    char nonce[33];
    pid_t root_pid; /* retained only until the root is reaped */
    bool capacity_overflow, unidentified_live_child;
    enum payload_outcome outcome;
    int payload_exit;
};

static char *const child_environment[] = {
    "PATH=/usr/bin:/bin", "LANG=C", "LC_ALL=C",
    "HOME=/nonexistent", "TMPDIR=/nonexistent", "PYTHONDONTWRITEBYTECODE=1",
    NULL,
};

static uint64_t monotonic_ns(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return 0;
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

static int pidfd_open_checked(pid_t observed_pid) {
    return (int)syscall(SYS_pidfd_open, observed_pid, 0U);
}

/* Sole signalling primitive. */
static int pidfd_send_signal_checked(int pidfd, int signal_number) {
    return (int)syscall(SYS_pidfd_send_signal, pidfd, signal_number, NULL, 0U);
}

static int write_all(int fd, const void *data, size_t len) {
    const char *cursor = data;
    while (len != 0U) {
        ssize_t written = write(fd, cursor, len);
        if (written < 0) { if (errno == EINTR) continue; return -1; }
        if (written == 0) { errno = EIO; return -1; }
        cursor += written; len -= (size_t)written;
    }
    return 0;
}

static int record_open(struct owner *owner, const char *kind) {
    char name[96];
    int n = snprintf(name, sizeof(name), "%s-%06llu-%s.json",
                     owner->nonce, ++owner->record_sequence, kind);
    if (n < 0 || (size_t)n >= sizeof(name)) { errno = ENAMETOOLONG; return -1; }
    return openat(owner->output_fd, name,
                  O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
}

static int record_finish(struct owner *owner, int fd) {
    int saved = 0;
    if (fsync(fd) != 0) saved = errno;
    if (close(fd) != 0 && saved == 0) saved = errno;
    if (saved == 0 && fsync(owner->output_fd) != 0) saved = errno;
    if (saved != 0) { errno = saved; return -1; }
    return 0;
}

static int record_write(struct owner *owner, const char *kind, const char *body) {
    int fd = record_open(owner, kind);
    if (fd < 0) return -1;
    if (write_all(fd, body, strlen(body)) != 0) {
        int saved = errno; close(fd); errno = saved; return -1;
    }
    return record_finish(owner, fd);
}

/* argv evidence is hex, avoiding text interpolation and every shell path. */
static int record_start(struct owner *owner, char *const command[]) {
    static const char hex[] = "0123456789abcdef";
    int fd = record_open(owner, "start");
    char header[256];
    int n = snprintf(header, sizeof(header),
        "{\"state\":\"START\",\"nonce\":\"%s\",\"owner_pid\":%ld,"
        "\"owner_started_ns\":%" PRIu64 ",\"argv_hex\":[",
        owner->nonce, (long)owner->owner_pid, owner->started_ns);
    if (fd < 0 || n < 0 || (size_t)n >= sizeof(header)) goto fail;
    if (write_all(fd, header, (size_t)n) != 0) goto fail;
    for (size_t i = 0; command[i] != NULL; ++i) {
        if ((i && write_all(fd, ",", 1) != 0) || write_all(fd, "\"", 1) != 0) goto fail;
        for (const unsigned char *p = (const unsigned char *)command[i]; *p; ++p) {
            char encoded[2] = {hex[*p >> 4], hex[*p & 15U]};
            if (write_all(fd, encoded, sizeof(encoded)) != 0) goto fail;
        }
        if (write_all(fd, "\"", 1) != 0) goto fail;
    }
    if (write_all(fd, "]}\n", 3) != 0) goto fail;
    return record_finish(owner, fd);
fail:
    { int saved = errno; if (fd >= 0) close(fd); errno = saved; return -1; }
}

static uint64_t owned_pidfd_fingerprint(const struct owner *owner) {
    uint64_t value = UINT64_C(1469598103934665603);
    for (size_t i = 0; i < owner->count; ++i) {
        const struct child *child = &owner->children[i];
        value ^= child->sequence; value *= UINT64_C(1099511628211);
        value ^= (uint64_t)(unsigned long)child->observed_pid; value *= UINT64_C(1099511628211);
        value ^= (uint64_t)(unsigned int)child->pidfd; value *= UINT64_C(1099511628211);
    }
    return value;
}

static int record_child(struct owner *owner, const char *kind, const char *state,
                        const struct child *child, const siginfo_t *status,
                        const char *reason) {
    char body[640];
    int n = snprintf(body, sizeof(body),
        "{\"state\":\"%s\",\"nonce\":\"%s\",\"owner_pid\":%ld,"
        "\"sequence\":%llu,\"pid_observation\":%ld,\"pidfd_fd\":%d,\"pidfd_inventory\":\"%016" PRIx64 "\","
        "\"waitid_wnowait\":%s,\"si_code\":%d,\"si_status\":%d,\"reason\":\"%s\"}\n",
        state, owner->nonce, (long)owner->owner_pid, child ? child->sequence : 0ULL,
        child ? (long)child->observed_pid : 0L, child ? child->pidfd : -1,
        owned_pidfd_fingerprint(owner),
        status ? "true" : "false", status ? status->si_code : 0,
        status ? status->si_status : 0, reason ? reason : "");
    if (n < 0 || (size_t)n >= sizeof(body)) { errno = EOVERFLOW; return -1; }
    return record_write(owner, kind, body);
}

static int record_unresolved(struct owner *owner, const char *reason) {
    char body[640];
    int n = snprintf(body, sizeof(body),
        "{\"state\":\"UNRESOLVED\",\"nonce\":\"%s\",\"owner_pid\":%ld,"
        "\"owner_started_ns\":%" PRIu64 ",\"owned_count\":%zu,"
        "\"pidfd_inventory\":\"%016" PRIx64 "\",\"supervision_retained\":true,"
        "\"reason\":\"%s\",\"deadline_ns\":%" PRIu64 "}\n",
        owner->nonce, (long)owner->owner_pid, owner->started_ns, owner->count,
        owned_pidfd_fingerprint(owner), reason, owner->cleanup_deadline_ns);
    if (n < 0 || (size_t)n >= sizeof(body)) { errno = EOVERFLOW; return -1; }
    return record_write(owner, "unresolved", body);
}

static int child_limits(void) {
    const struct rlimit cpu = {60, 60};
    const struct rlimit address = {512ULL * 1024ULL * 1024ULL, 512ULL * 1024ULL * 1024ULL};
    const struct rlimit nofile = {256, 256};
    const struct rlimit fsize = {64ULL * 1024ULL * 1024ULL, 64ULL * 1024ULL * 1024ULL};
    return setrlimit(RLIMIT_CPU, &cpu) || setrlimit(RLIMIT_AS, &address) ||
           setrlimit(RLIMIT_NOFILE, &nofile) || setrlimit(RLIMIT_FSIZE, &fsize);
}

/* x86-64 only. x32 syscall numbers are rejected before socket branches.
 * Denies every connect and socket(AF_INET/AF_INET6); AF_UNIX socketpair stays available. */
static int child_install_network_filter(void) {
    const unsigned int deny = SECCOMP_RET_ERRNO | (EPERM & SECCOMP_RET_DATA);
    struct sock_filter program_code[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        BPF_JUMP(BPF_JMP | BPF_JSET | BPF_K, __X32_SYSCALL_BIT, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_connect, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, deny),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_socket, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, args[0])),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AF_INET, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, deny),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AF_INET6, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, deny),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    };
    struct sock_fprog program = {
        .len = (unsigned short)(sizeof(program_code) / sizeof(program_code[0])),
        .filter = program_code,
    };
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) return -1;
    return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program);
}

static int restore_child_signal_state(void) {
    const int reset[] = {SIGTERM, SIGINT, SIGCHLD, SIGPIPE};
    struct sigaction normal;
    sigset_t empty;
    memset(&normal, 0, sizeof(normal)); normal.sa_handler = SIG_DFL;
    sigemptyset(&empty);
    for (size_t i = 0; i < sizeof(reset) / sizeof(reset[0]); ++i)
        if (sigaction(reset[i], &normal, NULL) != 0) return -1;
    return sigprocmask(SIG_SETMASK, &empty, NULL);
}

static int close_inherited_fds_except_stdio(void) {
    DIR *directory = opendir("/proc/self/fd");
    if (directory == NULL) return -1;
    int scanner_fd = dirfd(directory);
    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (entry == NULL) break;
        char *end = NULL;
        long fd = strtol(entry->d_name, &end, 10);
        if (*entry->d_name == '\0' || *end != '\0' || fd < 3 || fd == scanner_fd) continue;
        (void)close((int)fd);
    }
    int saved = errno;
    closedir(directory);
    if (saved != 0) { errno = saved; return -1; }
    return 0;
}

static int add_child(struct owner *owner, pid_t observed_pid, int pidfd,
                     bool payload_root, size_t *slot) {
    if (owner->count == OWNER_MAX_CHILDREN) {
        owner->capacity_overflow = true; errno = ENOSPC; return -1;
    }
    *slot = owner->count++;
    owner->children[*slot] = (struct child) {
        .pidfd = pidfd, .observed_pid = observed_pid, .payload_root = payload_root,
        .sequence = ++owner->child_sequence, .phase = ACQUIRED,
    };
    return 0;
}

/* Normal retirement follows durable terminal status plus reap. The sole
 * exceptional caller first proves P_ALL/ECHILD and records lost-status failure. */
static void retire_child(struct owner *owner, size_t slot) {
    if (owner->children[slot].payload_root) owner->root_pid = 0;
    (void)close(owner->children[slot].pidfd);
    owner->children[slot] = owner->children[owner->count - 1U];
    --owner->count;
}

static int waitid_pidfd(int pidfd, siginfo_t *status, int flags) {
    memset(status, 0, sizeof(*status));
    return waitid((idtype_t)P_PIDFD, (id_t)pidfd, status, flags);
}

static void update_payload_outcome(struct owner *owner, const struct child *child,
                                   const siginfo_t *status) {
    if (!child->payload_root) return;
    owner->payload_exit = status->si_code == CLD_EXITED ? status->si_status :
                          128 + status->si_status;
    if (owner->outcome == PAYLOAD_RUNNING)
        owner->outcome = owner->payload_exit == 0 ? PAYLOAD_OK : PAYLOAD_EXIT_FAILURE;
}

static void child_step(struct child *child, enum child_event event) {
    child->phase = child_steps[child->phase][event];
}

/* A failed record retains the handle in ACQUIRED: do not signal/reap it yet. */
static int persist_acquisition(struct owner *owner, struct child *child) {
    if (child->phase != ACQUIRED) return 0;
    if (record_child(owner, child->payload_root ? "spawn" : "adopted",
                     child->payload_root ? "SPAWN" : "ADOPTED",
                     child, NULL, NULL) != 0) {
        child_step(child, RECORD_ERROR); return -1;
    }
    child_step(child, ACQUISITION_DURABLE);
    return 0;
}

static int observe_then_reap(struct owner *owner, size_t slot) {
    siginfo_t status;
    struct child *child = &owner->children[slot];
    if (persist_acquisition(owner, child) != 0) return -1;
    if (child->phase == OWNED) {
        if (waitid_pidfd(child->pidfd, &status, WEXITED | WNOHANG | WNOWAIT) != 0) {
            child_step(child, WAIT_ERROR); return -1;
        }
        if (status.si_pid == 0) { child_step(child, NO_STATUS); return 0; }
        if (status.si_pid != child->observed_pid) { errno = EPROTO; return -1; }
        if (record_child(owner, "terminal", "TERMINAL", child, &status, NULL) != 0) {
            child_step(child, RECORD_ERROR); return -1;
        }
        child->terminal = status;
        child_step(child, TERMINAL_DURABLE);
    }
    if (waitid_pidfd(child->pidfd, &status, WEXITED | WNOHANG) != 0) {
        child_step(child, WAIT_ERROR); return -1;
    }
    if (status.si_pid == 0) { child_step(child, NO_STATUS); return 0; }
    /* Reap already happened. Retire even on an inconsistent status, but latch
     * failure; repeating a reap of this handle could never recover it. */
    bool mismatch = status.si_pid != child->terminal.si_pid ||
                    status.si_code != child->terminal.si_code ||
                    status.si_status != child->terminal.si_status;
    update_payload_outcome(owner, child, &status);
    child_step(child, REAP_SUCCEEDED);
    if (child->phase == RETIRED) retire_child(owner, slot);
    if (mismatch) { owner->outcome = PAYLOAD_OWNER_ERROR; errno = EPROTO; return -1; }
    return 1;
}

/* An unreaped child keeps its PID allocated. In this single-threaded owner,
 * with SIGCHLD normalized and no other reaper, a match is the same identity
 * already held by the pidfd. Numeric PIDs are never signalling authority. */
static size_t find_owned_child(const struct owner *owner, pid_t pid) {
    for (size_t slot = 0; slot < owner->count; ++slot)
        if (owner->children[slot].observed_pid == pid) return slot;
    return owner->count;
}

enum parent_result { PARENT_ERROR = -1, PARENT_PRESENT = 0, PARENT_EMPTY = 1 };

/* One nonblocking parent scan per pass. ECHILD supersedes any earlier live
 * uncertainty. A zero status proves neither emptiness nor acquireable identity. */
static int scan_parent(struct owner *owner) {
    siginfo_t status;
    memset(&status, 0, sizeof(status));
    int rc = waitid(P_ALL, 0, &status, WEXITED | WNOHANG | WNOWAIT);
    enum scan_event event = rc != 0 ? (errno == ECHILD ? SCAN_ECHILD : SCAN_ERROR) :
        status.si_pid == 0 ? SCAN_LIVE :
        find_owned_child(owner, status.si_pid) != owner->count ? SCAN_KNOWN :
        owner->count == OWNER_MAX_CHILDREN ? SCAN_FULL : SCAN_NEW;
    enum scan_action action = scan_actions[event];
    if (action == CLEAR_PARENT) {
        owner->unidentified_live_child = false;
        if (owner->count != 0U) {
            /* Impossible under the normal reaper contract. ECHILD nevertheless
             * proves no child needs supervision: log execution failure and close
             * stale handles, never hang or count their status as accepted. */
            owner->outcome = PAYLOAD_OWNER_ERROR;
            (void)record_child(owner, "failure", "FAILURE", NULL, NULL, "lost-child-status");
            while (owner->count != 0U) retire_child(owner, owner->count - 1U);
        }
        return PARENT_EMPTY;
    }
    if (action == KEEP_PARENT) {
        if (event == SCAN_LIVE && owner->count == 0U) owner->unidentified_live_child = true;
        return PARENT_PRESENT;
    }
    if (action == FAIL_SCAN) {
        if (event == SCAN_FULL) { owner->capacity_overflow = true; errno = ENOSPC; }
        return PARENT_ERROR;
    }
    int pidfd = pidfd_open_checked(status.si_pid);
    if (pidfd < 0) return PARENT_ERROR;
    size_t slot = 0;
    if (add_child(owner, status.si_pid, pidfd, status.si_pid == owner->root_pid, &slot) != 0) {
        int saved = errno; close(pidfd); errno = saved; return PARENT_ERROR;
    }
    return persist_acquisition(owner, &owner->children[slot]) == 0 ?
           PARENT_PRESENT : PARENT_ERROR;
}

static void signal_owned_children(struct owner *owner, int signal_number) {
    for (size_t i = 0; i < owner->count; ++i) {
        struct child *child = &owner->children[i];
        if (child->phase == ACQUIRED) continue;
        if (signal_number == SIGTERM) {
            if (child->term_attempted) continue;
            child->term_attempted = true; /* never reenter a TERM handler */
        } else if (child->kill_sent) continue;
        if (pidfd_send_signal_checked(child->pidfd, signal_number) == 0 || errno == ESRCH) {
            if (signal_number == SIGKILL) child->kill_sent = true;
        }
    }
}

static int consume_owner_signal(struct owner *owner) {
    struct signalfd_siginfo event;
    /* Finite drain: a continuous signal producer cannot delay the deadline. */
    for (unsigned int drained = 0; drained < 64U; ++drained) {
        ssize_t n = read(owner->signal_fd, &event, sizeof(event));
        if (n < 0) return (errno == EAGAIN || errno == EINTR) ? 0 : -1;
        if (n != (ssize_t)sizeof(event)) { errno = EIO; return -1; }
        if (event.ssi_signo == SIGTERM || event.ssi_signo == SIGINT) return 1;
        /* CHLD and PIPE are drained; waitid is status authority. */
    }
    return 0;
}

static int collect_once(struct owner *owner) {
    int failure = 0;
    for (size_t slot = 0; slot < owner->count;) {
        int rc = observe_then_reap(owner, slot);
        enum pass_action action = pass_actions[rc + 1];
        if (action == STOP_PASS) { failure = 1; break; }
        if (action == ADVANCE_SLOT) ++slot;
        /* COMPACTED_SLOT already reduced count; all paths make progress. */
    }
    int parent = scan_parent(owner); /* even after errors: ECHILD is authoritative */
    if (failure) owner->outcome = PAYLOAD_OWNER_ERROR;
    if (parent == PARENT_EMPTY) return PARENT_EMPTY;
    return failure ? PARENT_ERROR : parent;
}

static int poll_owner(struct owner *owner, int milliseconds) {
    struct pollfd event = {.fd = owner->signal_fd, .events = POLLIN};
    int ready = poll(&event, 1, milliseconds);
    if (ready < 0) return errno == EINTR ? 0 : -1;
    if (event.revents & (POLLERR | POLLHUP | POLLNVAL)) { errno = EIO; return -1; }
    return ready > 0 && (event.revents & POLLIN) ? consume_owner_signal(owner) : 0;
}

/* No transfer protocol exists. Remain the subreaper, retain handles, and keep
 * making finite nonblocking collection attempts until ECHILD. This is an
 * explicit unresolved lifetime, never a successful cleanup or handoff. */
static int retain_unresolved(struct owner *owner, const char *reason) {
    owner->outcome = PAYLOAD_OWNER_ERROR;
    if (record_unresolved(owner, reason) != 0)
        fprintf(stderr, "UNRESOLVED: %s; record failed: %s\n", reason, strerror(errno));
    for (;;) {
        if (collect_once(owner) == PARENT_EMPTY) return 1;
        signal_owned_children(owner, SIGKILL);
        (void)consume_owner_signal(owner);
        /* A fixed sleep prevents a signal storm or a broken signalfd from
         * turning retained supervision into a spin. No wait for child status. */
        const struct timespec pause = {.tv_sec = OWNER_RETAIN_POLL_MS / 1000, .tv_nsec = 0};
        (void)nanosleep(&pause, NULL);
    }
}

static int cleanup_with_deadline(struct owner *owner) {
    uint64_t now = monotonic_ns();
    if (collect_once(owner) == PARENT_EMPTY) return 0;
    if (now == 0) return retain_unresolved(owner, "clock-failure");
    uint64_t kill_at = now + OWNER_TERM_GRACE_NS;
    owner->cleanup_deadline_ns = now + OWNER_CLEANUP_NS;
    while ((now = monotonic_ns()) != 0 && now < owner->cleanup_deadline_ns) {
        int result = collect_once(owner);
        if (result == PARENT_EMPTY) return 0;
        if (result == PARENT_ERROR) return retain_unresolved(owner, "acquisition-or-reap-error");
        signal_owned_children(owner, now >= kill_at ? SIGKILL : SIGTERM);
        if (poll_owner(owner, 50) < 0) return retain_unresolved(owner, "signal-channel-error");
    }
    return retain_unresolved(owner, owner->capacity_overflow ? "capacity-overflow" :
                             owner->unidentified_live_child ? "live-adopted-unacquired" :
                             now == 0 ? "clock-failure" : "cleanup-deadline");
}

static int wait_for_payload(struct owner *owner) {
    uint64_t now = monotonic_ns();
    if (now == 0) { owner->outcome = PAYLOAD_OWNER_ERROR; return -1; }
    uint64_t deadline = now + OWNER_PAYLOAD_NS;
    while ((now = monotonic_ns()) != 0 && now < deadline) {
        int result = collect_once(owner);
        if (result < 0) { owner->outcome = PAYLOAD_OWNER_ERROR; return -1; }
        if (result == PARENT_EMPTY) return 0;
        int signal_result = poll_owner(owner, 50);
        if (signal_result < 0) { owner->outcome = PAYLOAD_OWNER_ERROR; return -1; }
        if (signal_result > 0) { owner->outcome = PAYLOAD_INTERRUPTED; return 1; }
    }
    owner->outcome = now == 0 ? PAYLOAD_OWNER_ERROR : PAYLOAD_TIMEOUT;
    return 1;
}

static int setup_signalfd(struct owner *owner) {
    sigset_t blocked;
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGTERM); sigaddset(&blocked, SIGINT);
    sigaddset(&blocked, SIGCHLD); sigaddset(&blocked, SIGPIPE);
    if (sigprocmask(SIG_BLOCK, &blocked, NULL) != 0) return -1;
    /* Inherited SIG_IGN or SA_NOCLDWAIT would discard status and release PID
     * identity. Normalize while blocked and before creating any child. */
    struct sigaction normal;
    memset(&normal, 0, sizeof(normal)); normal.sa_handler = SIG_DFL;
    sigemptyset(&normal.sa_mask);
    const int reset[] = {SIGTERM, SIGINT, SIGCHLD, SIGPIPE};
    for (size_t i = 0; i < sizeof(reset) / sizeof(reset[0]); ++i)
        if (sigaction(reset[i], &normal, NULL) != 0) return -1;
    owner->signal_fd = signalfd(-1, &blocked, SFD_CLOEXEC | SFD_NONBLOCK);
    return owner->signal_fd;
}

static int spawn_after_durable_pidfd(struct owner *owner, char *const command[]) {
    int gate[2];
    if (pipe2(gate, O_CLOEXEC) != 0) return -1;
    pid_t child_pid = fork();
    if (child_pid < 0) {
        int saved = errno; close(gate[0]); close(gate[1]); errno = saved; return -1;
    }
    if (child_pid == 0) {
        char release = 0;
        close(gate[1]);
        if (read(gate[0], &release, 1) != 1 || release != 'R' ||
            child_limits() != 0 || child_install_network_filter() != 0 ||
            restore_child_signal_state() != 0) _exit(127);
        close(gate[0]);
        /* Internal descriptors may occupy closed standard slots. They are
         * still owner internals, never payload stdin/stdout/stderr. */
        close(owner->output_fd); close(owner->signal_fd);
        if (close_inherited_fds_except_stdio() != 0) _exit(127);
        execve(command[0], command, child_environment); /* absolute argv0 only */
        _exit(127);
    }
    close(gate[0]);
    owner->root_pid = child_pid;
    int pidfd = pidfd_open_checked(child_pid);
    if (pidfd < 0) {
        /* Gate close prevents exec; subreaper cleanup then obtains terminal ownership. */
        close(gate[1]); return -1;
    }
    size_t slot = 0;
    if (add_child(owner, child_pid, pidfd, true, &slot) != 0) {
        close(pidfd); close(gate[1]); return -1;
    }
    if (persist_acquisition(owner, &owner->children[slot]) != 0) {
        /* Stored pidfd is never closed here; cleanup retains it. */
        close(gate[1]); return -1;
    }
    if (write_all(gate[1], "R", 1) != 0) {
        close(gate[1]); return -1; /* stored pidfd survives to cleanup */
    }
    close(gate[1]);
    return 0;
}

static int initialize_attempt_identity(struct owner *owner) {
    unsigned char random_bytes[16];
    static const char hex[] = "0123456789abcdef";
    if (getrandom(random_bytes, sizeof(random_bytes), 0) != (ssize_t)sizeof(random_bytes)) return -1;
    for (size_t i = 0; i < sizeof(random_bytes); ++i) {
        owner->nonce[i * 2] = hex[random_bytes[i] >> 4];
        owner->nonce[i * 2 + 1] = hex[random_bytes[i] & 15U];
    }
    owner->nonce[32] = '\0';
    owner->owner_pid = getpid();
    owner->started_ns = monotonic_ns();
    return owner->started_ns == 0 ? -1 : 0;
}

int main(int argc, char **argv) {
    if (argc < 4 || strcmp(argv[2], "--") != 0 || argv[3][0] != '/') {
        fprintf(stderr, "usage: %s OUTPUT_ROOT -- /ABSOLUTE/PROGRAM [ARG ...]\n", argv[0]);
        return 64;
    }
    struct owner owner;
    memset(&owner, 0, sizeof(owner));
    owner.output_fd = open(argv[1], O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (owner.output_fd < 0 || initialize_attempt_identity(&owner) != 0 ||
        prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0 || setup_signalfd(&owner) < 0 ||
        record_start(&owner, &argv[3]) != 0) {
        int saved = errno;
        (void)record_child(&owner, "failure", "FAILURE", NULL, NULL, "pre-fork-setup-failure");
        fprintf(stderr, "owner setup failed: %s\n", strerror(saved));
        return 1;
    }
    if (spawn_after_durable_pidfd(&owner, &argv[3]) != 0) {
        owner.outcome = PAYLOAD_OWNER_ERROR;
        (void)record_child(&owner, "failure", "FAILURE", NULL, NULL, "spawn-setup-failure");
        (void)cleanup_with_deadline(&owner);
    } else {
        (void)wait_for_payload(&owner);
        (void)cleanup_with_deadline(&owner);
    }
    int result = owner.outcome == PAYLOAD_OK ? 0 :
                 owner.outcome == PAYLOAD_EXIT_FAILURE ? owner.payload_exit :
                 owner.outcome == PAYLOAD_TIMEOUT ? 124 :
                 owner.outcome == PAYLOAD_INTERRUPTED ? 130 : 1;
    if (record_child(&owner, "complete", result == 0 ? "COMPLETE" : "FAILURE",
                     NULL, NULL, "parent-echild") != 0) result = 1;
    close(owner.signal_fd); close(owner.output_fd);
    return result;
}
