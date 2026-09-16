#if !defined(M02_STORAGE_FAULT_TEST_ONLY) || M02_STORAGE_FAULT_TEST_ONLY != 1
#error "storage-fault seams require test guard exactly one"
#endif
#ifndef M02_STORAGE_FAULT_CASE
#error "storage-fault selector required"
#endif
#if M02_STORAGE_FAULT_CASE < 0 || M02_STORAGE_FAULT_CASE > 6
#error "unknown storage-fault selector"
#endif

#include <sys/socket.h>

#define SF_WITNESS_FD 198
#define SF_PACKET_MAX 4096
#define SF_PACKET_LIMIT 32

enum sf_site { SF_EVENTS_CREATE=1, SF_REQUEST_WRITE=2, SF_REQUEST_SYNC=3,
    SF_REPORT_CREATE=4, SF_REPORT_FLUSH=5, SF_REPORT_SYNC=6 };
enum sf_object { SF_EVENTS=1, SF_REQUEST=2, SF_REPORT=3 };

static unsigned sf_sequence, sf_packets, sf_write_occurrence;
static unsigned sf_acquisition_next, sf_acquisition[4];
static struct stat sf_open_stat[4];
static bool sf_open_stat_valid[4];
static int sf_failed;
static uint64_t sf_ticks;
static char sf_nonce[33], sf_source_sha[65], sf_generated_sha[65];
static char sf_header_sha[65], sf_elf_sha[65];

static bool sf_hex(const char *value, size_t length)
{
    if (!value || strlen(value) != length) return false;
    for (size_t i = 0; i < length; ++i)
        if (!((value[i] >= '0' && value[i] <= '9') || (value[i] >= 'a' && value[i] <= 'f'))) return false;
    return true;
}

static uint64_t sf_now(void)
{
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0 || value.tv_sec < 0) return 0;
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
}

static bool sf_self_ticks(uint64_t *result)
{
    char raw[4096];
    int fd = open("/proc/self/stat", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return false;
    ssize_t count;
    do { count = read(fd, raw, sizeof raw - 1); } while (count < 0 && errno == EINTR);
    close(fd);
    if (count <= 0 || count == (ssize_t)sizeof raw - 1) return false;
    raw[count] = 0;
    char *cursor = strrchr(raw, ')');
    if (!cursor || cursor[1] != ' ') return false;
    cursor += 2;
    for (unsigned field = 3; field < 22; ++field) {
        while (*cursor && *cursor != ' ') ++cursor;
        while (*cursor == ' ') ++cursor;
        if (!*cursor) return false;
    }
    errno = 0;
    char *end;
    unsigned long long value = strtoull(cursor, &end, 10);
    if (errno || end == cursor || (*end && *end != ' ' && *end != '\n') || !value) return false;
    *result = (uint64_t)value;
    return true;
}

static const char *sf_site_name(int site)
{
    switch (site) {
    case SF_EVENTS_CREATE: return "events-create";
    case SF_REQUEST_WRITE: return "request-write";
    case SF_REQUEST_SYNC: return "request-sync";
    case SF_REPORT_CREATE: return "report-create";
    case SF_REPORT_FLUSH: return "report-flush";
    case SF_REPORT_SYNC: return "report-sync";
    default: return "observation";
    }
}

static const char *sf_object_name(int object)
{
    return object == SF_EVENTS ? "events.jsonl" : object == SF_REQUEST ? "request.bin" :
        object == SF_REPORT ? "report.json" : "collector";
}

static bool sf_stat_text(int fd, char *output, size_t capacity)
{
    struct stat value;
    if (fd < 0 || fstat(fd, &value) != 0) return false;
    int count = snprintf(output, capacity,
        "{\"dev\":%ju,\"ino\":%ju,\"mode\":%ju,\"size\":%jd}",
        (uintmax_t)value.st_dev, (uintmax_t)value.st_ino,
        (uintmax_t)value.st_mode, (intmax_t)value.st_size);
    return count > 0 && (size_t)count < capacity;
}

static bool sf_value_stat_text(const struct stat *value, char *output, size_t capacity)
{
    int count = snprintf(output, capacity,
        "{\"dev\":%ju,\"ino\":%ju,\"mode\":%ju,\"size\":%jd}",
        (uintmax_t)value->st_dev, (uintmax_t)value->st_ino,
        (uintmax_t)value->st_mode, (intmax_t)value->st_size);
    return count > 0 && (size_t)count < capacity;
}

static bool sf_exchange(const char *packet, size_t length, bool release,
                        unsigned packet_sequence)
{
    if (sf_failed || ++sf_packets > SF_PACKET_LIMIT || !length || length > SF_PACKET_MAX) {
        sf_failed = 1; return false;
    }
    uint64_t deadline = sf_now() + UINT64_C(2000000000);
    ssize_t sent = -1;
    while (sf_now() < deadline) {
        sent = send(SF_WITNESS_FD, packet, length, MSG_NOSIGNAL | MSG_DONTWAIT);
        if (sent >= 0 || (errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK)) break;
        struct pollfd writable = { .fd = SF_WITNESS_FD, .events = POLLOUT };
        uint64_t now = sf_now();
        int timeout = now < deadline ? (int)((deadline - now + 999999) / 1000000) : 0;
        int ready = poll(&writable, 1, timeout);
        if (ready < 0 && errno == EINTR) continue;
        if (ready != 1 || !(writable.revents & POLLOUT)) break;
    }
    if (sent != (ssize_t)length) { sf_failed = 1; return false; }
    char response[160], expected[160];
    ssize_t received = -1;
    while (sf_now() < deadline) {
        received = recv(SF_WITNESS_FD, response, sizeof response, MSG_DONTWAIT);
        if (received >= 0 || (errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK)) break;
        struct pollfd readable = { .fd = SF_WITNESS_FD, .events = POLLIN };
        uint64_t now = sf_now();
        int timeout = now < deadline ? (int)((deadline - now + 999999) / 1000000) : 0;
        int ready = poll(&readable, 1, timeout);
        if (ready < 0 && errno == EINTR) continue;
        if (ready != 1 || !(readable.revents & POLLIN)) break;
    }
    int expected_length = release ? snprintf(expected, sizeof expected, "RELEASE %s\n", sf_nonce) :
        snprintf(expected, sizeof expected, "ACK %s %u\n", sf_nonce, packet_sequence);
    if (expected_length <= 0 || received != expected_length ||
        memcmp(response, expected, (size_t)expected_length) != 0) {
        sf_failed = 1; return false;
    }
    struct pollfd extra = { .fd = SF_WITNESS_FD, .events = POLLIN };
    if (poll(&extra, 1, 0) != 0) { sf_failed = 1; return false; }
    return true;
}

static bool sf_record(const char *kind, const char *extra)
{
    char packet[SF_PACKET_MAX + 1];
    unsigned sequence = sf_sequence++;
    int count = snprintf(packet, sizeof packet,
        "{\"schema_version\":2,\"nonce\":\"%s\",\"selector\":%d,\"sequence\":%u,"
        "\"kind\":\"%s\",\"phase\":\"%s\",\"monotonic_ns\":%" PRIu64 ","
        "\"collector_pid\":%ld,\"collector_startticks\":%" PRIu64 ","
        "\"source_sha256\":\"%s\","
        "\"generated_sha256\":\"%s\",\"header_sha256\":\"%s\","
        "\"elf_sha256\":\"%s\"%s}",
        sf_nonce, M02_STORAGE_FAULT_CASE, sequence, kind,
        child_created ? "post-fork" : "pre-fork", sf_now(), (long)getpid(), sf_ticks,
        sf_source_sha, sf_generated_sha, sf_header_sha, sf_elf_sha,
        extra ? extra : "");
    if (count <= 0 || (size_t)count > SF_PACKET_MAX) { sf_failed = 1; return false; }
    return sf_exchange(packet, (size_t)count, false, sequence);
}

static bool sf_emit(const char *kind, int site, int object, unsigned occurrence,
                    int fd, int dirfd, size_t requested, ssize_t returned,
                    bool errno_authoritative, int error, unsigned acquisition,
                    const char *unused)
{
    char target_stat[192], dir_stat[192], fd_text[32], dirfd_text[32];
    char acquisition_text[32], extra[1536];
    bool target_present = sf_stat_text(fd, target_stat, sizeof target_stat);
    bool dir_present = sf_stat_text(dirfd, dir_stat, sizeof dir_stat);
    bool create = site == SF_EVENTS_CREATE || site == SF_REPORT_CREATE;
    bool write_site = site == SF_REQUEST_WRITE;
    (void)unused;
    snprintf(fd_text, sizeof fd_text, "%d", fd);
    snprintf(dirfd_text, sizeof dirfd_text, "%d", dirfd);
    snprintf(acquisition_text, sizeof acquisition_text, "%u", acquisition);
    int count;
    if (!strcmp(kind, "BEFORE")) {
        count = snprintf(extra, sizeof extra,
            ",\"site\":\"%s\",\"object\":\"%s\",\"occurrence\":%u,"
            "\"fd\":%s,\"target_stat\":%s%s%s%s%s,"
            "\"return\":null,\"errno_authoritative\":false,\"errno\":null,"
            "\"acquisition_id\":%s",
            sf_site_name(site), sf_object_name(object), occurrence,
            create ? "null" : fd_text,
            create ? "null" : target_present ? target_stat : "null",
            create ? ",\"dirfd\":" : "", create ? dirfd_text : "",
            create ? ",\"dir_stat\":" : "", create ? (dir_present ? dir_stat : "null") : "",
            create ? "null" : acquisition_text);
        if (count > 0 && write_site)
            count += snprintf(extra + count, sizeof extra - (size_t)count,
                              ",\"requested_bytes\":%zu", requested);
    } else if (!strcmp(kind, "AFTER")) {
        char return_text[32], errno_text[32];
        snprintf(return_text, sizeof return_text, "%zd", returned);
        snprintf(errno_text, sizeof errno_text, "%d", error);
        count = snprintf(extra, sizeof extra,
            ",\"site\":\"%s\",\"object\":\"%s\",\"occurrence\":%u,"
            "\"fd\":%s,\"target_stat\":%s%s%s%s%s,\"return\":%s,"
            "\"errno_authoritative\":%s,\"errno\":%s,\"acquisition_id\":%s",
            sf_site_name(site), sf_object_name(object), occurrence,
            create && returned < 0 ? "null" : fd_text,
            create && returned < 0 ? "null" : target_present ? target_stat : "null",
            create ? ",\"dirfd\":" : "", create ? dirfd_text : "",
            create ? ",\"dir_stat\":" : "", create ? (dir_present ? dir_stat : "null") : "",
            return_text, errno_authoritative ? "true" : "false",
            errno_authoritative ? errno_text : "null",
            create && returned < 0 ? "null" : acquisition_text);
        if (count > 0 && write_site)
            count += snprintf(extra + count, sizeof extra - (size_t)count,
                              ",\"requested_bytes\":%zu,\"actual_bytes\":%zu",
                              requested, returned < 0 ? 0 : (size_t)returned);
    } else {
        sf_failed = 1;
        return false;
    }
    if (count <= 0 || (size_t)count >= sizeof extra) { sf_failed = 1; return false; }
    return sf_record(kind, extra);
}

static bool sf_startup(void)
{
    int type = 0; socklen_t length = sizeof type;
    const char *nonce = getenv("M02_SF_NONCE");
    const char *source = getenv("M02_SF_SOURCE_SHA256");
    const char *generated = getenv("M02_SF_GENERATED_SHA256");
    const char *header = getenv("M02_SF_HEADER_SHA256");
    const char *elf = getenv("M02_SF_ELF_SHA256");
    if (getsockopt(SF_WITNESS_FD, SOL_SOCKET, SO_TYPE, &type, &length) != 0 ||
        type != SOCK_SEQPACKET || !sf_hex(nonce, 32) || !sf_hex(source, 64) ||
        !sf_hex(generated, 64) || !sf_hex(header, 64) || !sf_hex(elf, 64) ||
        !sf_self_ticks(&sf_ticks)) return false;
    memcpy(sf_nonce, nonce, 33); memcpy(sf_source_sha, source, 65);
    memcpy(sf_generated_sha, generated, 65); memcpy(sf_header_sha, header, 65);
    memcpy(sf_elf_sha, elf, 65);
    char packet[1024];
    int count = snprintf(packet, sizeof packet,
        "{\"schema_version\":2,\"nonce\":\"%s\",\"selector\":%d,"
        "\"sequence\":0,\"kind\":\"READY\",\"phase\":\"pre-fork\","
        "\"monotonic_ns\":%" PRIu64 ",\"site\":\"startup\","
        "\"object\":\"collector\",\"occurrence\":0,\"collector_pid\":%ld,"
        "\"collector_startticks\":%" PRIu64 ",\"source_sha256\":\"%s\","
        "\"generated_sha256\":\"%s\",\"header_sha256\":\"%s\","
        "\"elf_sha256\":\"%s\"}", sf_nonce, M02_STORAGE_FAULT_CASE,
        sf_now(), (long)getpid(), sf_ticks, sf_source_sha, sf_generated_sha,
        sf_header_sha, sf_elf_sha);
    if (count <= 0 || (size_t)count >= sizeof packet) return false;
    sf_sequence = 1;
    return sf_exchange(packet, (size_t)count, true, 0);
}

static bool sf_transport_failed(void) { return sf_failed != 0; }

static int sf_open(int site, int object, int dirfd, const char *path, int flags, mode_t mode)
{
    unsigned occurrence = 1;
    (void)sf_emit("BEFORE", site, object, occurrence, -1, dirfd, 0, 0, false, 0, 0, NULL);
    int result;
    if ((M02_STORAGE_FAULT_CASE == 1 && site == SF_EVENTS_CREATE) ||
        (M02_STORAGE_FAULT_CASE == 4 && site == SF_REPORT_CREATE)) {
        errno = ENOSPC; result = -1;
    } else result = openat(dirfd, path, flags, mode);
    int saved = errno;
    unsigned acquisition = result >= 0 ? ++sf_acquisition_next : 0;
    if (result >= 0) {
        sf_acquisition[object] = acquisition;
        sf_open_stat_valid[object] = fstat(result, &sf_open_stat[object]) == 0;
        if (!sf_open_stat_valid[object]) sf_failed = 1;
    }
    (void)sf_emit("AFTER", site, object, occurrence, result, dirfd, 0, result,
                  result < 0, result < 0 ? saved : 0, acquisition, NULL);
    errno = saved;
    return result;
}

static void sf_bind(int site, int object, int oldfd, int newfd)
{
    char extra[768], old_stat[192], new_stat[192];
    bool old_present = sf_open_stat_valid[object] &&
        sf_value_stat_text(&sf_open_stat[object], old_stat, sizeof old_stat);
    bool new_present = sf_stat_text(newfd, new_stat, sizeof new_stat);
    snprintf(extra, sizeof extra,
        ",\"site\":\"%s\",\"object\":\"%s\",\"occurrence\":1,"
        "\"acquisition_id\":%u,\"old_fd\":%d,\"new_fd\":%d,"
        "\"old_stat\":%s,\"new_stat\":%s",
        sf_site_name(site), sf_object_name(object), sf_acquisition[object],
        oldfd, newfd, old_present ? old_stat : "null",
        new_present ? new_stat : "null");
    (void)sf_record("BIND", extra);
}

static ssize_t sf_write(int object, int fd, const void *buffer, size_t count)
{
    unsigned occurrence = ++sf_write_occurrence;
    (void)sf_emit("BEFORE", SF_REQUEST_WRITE, object, occurrence, fd, -1,
                  count, 0, false, 0, sf_acquisition[object], NULL);
    ssize_t result;
    if ((M02_STORAGE_FAULT_CASE == 2 || M02_STORAGE_FAULT_CASE == 6) && occurrence == 1) {
        result = write(fd, buffer, count < 7 ? count : 7);
        if (result != 7) sf_failed = 1;
    } else if ((M02_STORAGE_FAULT_CASE == 2 || M02_STORAGE_FAULT_CASE == 6) && occurrence == 2) {
        errno = ENOSPC; result = -1;
    } else result = write(fd, buffer, count);
    int saved = errno;
    (void)sf_emit("AFTER", SF_REQUEST_WRITE, object, occurrence, fd, -1,
                  count, result, result < 0, result < 0 ? saved : 0,
                  sf_acquisition[object], NULL);
    errno = saved;
    return result;
}

static int sf_sync(int site, int object, int fd)
{
    (void)sf_emit("BEFORE", site, object, 1, fd, -1, 0, 0, false, 0,
                  sf_acquisition[object], NULL);
    int result;
    if (((M02_STORAGE_FAULT_CASE == 3 || M02_STORAGE_FAULT_CASE == 6) && site == SF_REQUEST_SYNC) ||
        ((M02_STORAGE_FAULT_CASE == 5 || M02_STORAGE_FAULT_CASE == 6) && site == SF_REPORT_SYNC)) {
        errno = EIO; result = -1;
    } else result = fsync(fd);
    int saved = errno;
    (void)sf_emit("AFTER", site, object, 1, fd, -1, 0, result,
                  result < 0, result < 0 ? saved : 0, sf_acquisition[object], NULL);
    errno = saved;
    return result;
}

static int sf_flush(int report_fd, FILE *file)
{
    (void)sf_emit("BEFORE", SF_REPORT_FLUSH, SF_REPORT, 1, report_fd, -1,
                  0, 0, false, 0, sf_acquisition[SF_REPORT], NULL);
    int result = fflush(file), saved = errno;
    (void)sf_emit("AFTER", SF_REPORT_FLUSH, SF_REPORT, 1, report_fd, -1,
                  0, result, result < 0, result < 0 ? saved : 0,
                  sf_acquisition[SF_REPORT], NULL);
    errno = saved;
    return result;
}

static void sf_observe_eof(unsigned stream, int closed_fd)
{
    const char *object = stream == 0 ? "stdout" : stream == 1 ? "stderr" : "setup";
    char extra[160]; snprintf(extra, sizeof extra,
        ",\"site\":\"pump\",\"object\":\"%s\",\"occurrence\":%u,\"closed_fd\":%d",
        object, stream + 1, closed_fd);
    (void)sf_record("EOF", extra);
}

static void sf_observe_reap(pid_t pid, uint64_t ticks, int raw)
{
    char extra[256];
    snprintf(extra, sizeof extra, ",\"site\":\"reap\",\"object\":\"leader\",\"occurrence\":1,\"pid\":%ld,\"startticks\":%" PRIu64 ",\"raw_wait_status\":%d", (long)pid, ticks, raw);
    (void)sf_record("REAP", extra);
}

static void sf_observe_setup(const uint64_t words[48], const struct stat *cwd, const struct stat *stdin_stat,
    const struct stat *stdout_pipe, const struct stat *stderr_pipe,
    const struct stat *executable, unsigned seals, pid_t pid, uint64_t ticks)
{
    char extra[3072], cwd_text[192], stdin_text[192], stdout_text[192], stderr_text[192], exec_text[192];
    size_t used = 0;
    if (!sf_value_stat_text(cwd, cwd_text, sizeof cwd_text) || !sf_value_stat_text(stdin_stat, stdin_text, sizeof stdin_text) ||
        !sf_value_stat_text(stdout_pipe, stdout_text, sizeof stdout_text) ||
        !sf_value_stat_text(stderr_pipe, stderr_text, sizeof stderr_text) ||
        !sf_value_stat_text(executable, exec_text, sizeof exec_text)) { sf_failed = 1; return; }
    int count = snprintf(extra, sizeof extra, ",\"site\":\"setup\",\"object\":\"collector\",\"occurrence\":1,\"setup_words\":[");
    if (count <= 0 || (size_t)count >= sizeof extra) { sf_failed = 1; return; }
    used = (size_t)count;
    for (unsigned i = 0; i < 48; ++i) {
        count = snprintf(extra + used, sizeof extra - used, "%s%" PRIu64, i ? "," : "", words[i]);
        if (count <= 0 || (size_t)count >= sizeof extra - used) { sf_failed = 1; return; }
        used += (size_t)count;
    }
    count = snprintf(extra + used, sizeof extra - used,
        "],\"cwd_stat\":%s,\"stdin_stat\":%s,\"stdout_pipe_stat\":%s,\"stderr_pipe_stat\":%s,\"executable_backing\":%s,\"executable_seals\":%u,\"leader_pid\":%ld,\"leader_startticks\":%" PRIu64,
        cwd_text, stdin_text, stdout_text, stderr_text, exec_text, seals, (long)pid, ticks);
    if (count <= 0 || (size_t)count >= sizeof extra - used) { sf_failed = 1; return; }
    (void)sf_record("SETUP", extra);
}

static void sf_observe_cleanup_ready(pid_t pid, uint64_t ticks, int raw)
{
    char extra[512];
    (void)pid; (void)ticks; (void)raw;
    snprintf(extra, sizeof extra, ",\"site\":\"cleanup\",\"object\":\"owned-tree\",\"occurrence\":1,\"waitid_return\":-1,\"waitid_errno\":%d,\"leader_reaped\":true,\"stdout_eof\":true,\"stderr_eof\":true,\"setup_eof\":true", ECHILD);
    (void)sf_record("CLEANUP_READY", extra);
}

static void sf_observe_cleanup_final(uint64_t start, uint64_t deadline,
    uint64_t finished, bool complete, unsigned owners, uint64_t omitted,
    const char *first_failure)
{
    char extra[640];
    snprintf(extra, sizeof extra,
        ",\"site\":\"cleanup\",\"object\":\"owned-tree\",\"occurrence\":1,"
        "\"cleanup_start_ns\":%" PRIu64 ",\"cleanup_deadline_ns\":%" PRIu64
        ",\"cleanup_finished_ns\":%" PRIu64 ",\"cleanup_complete\":%s,"
        "\"group_pinned\":%s,\"owned_count\":%u,\"owned_records_omitted\":%" PRIu64
        ",\"first_failure\":\"%s\",\"first_failure_errno\":%d",
        start, deadline, finished, complete ? "true" : "false",
        group_pinned ? "true" : "false", owners, omitted,
        first_failure, failure_errno);
    (void)sf_record("CLEANUP_FINAL", extra);
}

static void sf_child_close(void) { close(SF_WITNESS_FD); }
