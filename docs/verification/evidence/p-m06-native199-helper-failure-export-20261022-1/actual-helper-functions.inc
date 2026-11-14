static int append(char *b, size_t *n, const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt);
    int z = vsnprintf(b + *n, FRAME_LIMIT - *n, fmt, ap); va_end(ap);
    if (z < 0 || (size_t)z >= FRAME_LIMIT - *n) return -1;
    *n += (size_t)z; return 0;
}

static int stream_json(char *b, size_t *n, const struct stream *s)
{
    char h[STREAM_LIMIT * 2 + 1];
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
                  (unsigned long long)(s->observed - s->kept), STREAM_LIMIT,
                  (unsigned long long)s->eof_ns);
}

static int helper_export_failure(int console,const char *tag,const struct result *r,
                                 int evidence_failed,int evidence_errno)
{
    char b[FRAME_LIMIT];size_t used=0;
    if(append(b,&used,"ND_HELPER_FAILURE {\"tag\":\"%s\",\"raw_wait_status\":%d,\"fault\":%d,\"timeout\":%d,\"clean\":%d,\"stage\":%d,\"errno\":%d,\"evidence_failed\":%d,\"evidence_errno\":%d,\"started_ns\":%llu,\"reaped_ns\":%llu,\"finished_ns\":%llu}\n",
              tag,r->status,r->fault,r->timeout,r->clean,r->child_stage,r->child_errno,
              evidence_failed,evidence_errno,(unsigned long long)r->started,
              (unsigned long long)r->reaped,(unsigned long long)r->finished) ||
       write_all(console,b,used))return -1;
    const struct stream *streams[]={&r->out,&r->err};
    const char *names[]={"stdout","stderr"};
    for(int i=0;i<2;i++) {
        used=0;
        if(append(b,&used,"ND_HELPER_STREAM {\"tag\":\"%s\",\"stream\":\"%s\",\"data\":",tag,names[i]) ||
           stream_json(b,&used,streams[i]) || append(b,&used,"}\n") ||
           write_all(console,b,used))return -1;
    }
    return 0;
}

static int helper(const char *tag, const char *path, char *const av[], int *safe,int console)
{
    struct result r; char name[128], record[256];
    int evidence_failed=0,evidence_errno=0;
    supervise(path, av, helper_env, NULL, helper_timeout_ms(path), &r);
    if (!r.clean) *safe = 0;
    int bad = r.fault || r.timeout || !r.clean || r.status != 0 ||
              !r.out.eof || !r.err.eof || r.out.observed != r.out.kept ||
              r.err.observed != r.err.kept;
    snprintf(name, sizeof name, "/case/evidence/%s.stdout", tag);
    errno=0;
    if (save_file(name, r.out.data, r.out.kept)) {bad=1;evidence_failed|=1;evidence_errno=errno;}
    snprintf(name, sizeof name, "/case/evidence/%s.stderr", tag);
    errno=0;
    if (save_file(name, r.err.data, r.err.kept)) {bad=1;evidence_failed|=2;if(!evidence_errno)evidence_errno=errno;}
    int n = snprintf(record, sizeof record, "status=%d fault=%d timeout=%d clean=%d stage=%d errno=%d\n",
                     r.status, r.fault, r.timeout, r.clean, r.child_stage, r.child_errno);
    snprintf(name, sizeof name, "/case/evidence/%s.status", tag);
    if (n < 0 || (size_t)n >= sizeof record) {bad=1;evidence_failed|=4;if(!evidence_errno)evidence_errno=EOVERFLOW;}
    else {
        errno=0;
        if(save_file(name,record,(size_t)n)) {bad=1;evidence_failed|=4;if(!evidence_errno)evidence_errno=errno;}
    }
    if(bad && console>=0)(void)helper_export_failure(console,tag,&r,evidence_failed,evidence_errno);
    return bad ? -1 : 0;
}

