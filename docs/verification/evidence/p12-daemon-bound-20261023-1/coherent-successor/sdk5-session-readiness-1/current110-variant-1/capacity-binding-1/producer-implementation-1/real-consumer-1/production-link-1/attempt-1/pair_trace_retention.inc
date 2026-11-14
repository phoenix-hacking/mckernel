/* Fixed ten-round trace retention. Existing Linux save/write APIs only. */
#define PAIR_TRACE_TOTAL_MAX (2u*1024u*1024u)
struct pair_trace_record { int fd,pids[2];size_t bytes,offset;struct stat identity; };
static struct pair_trace_record pair_trace_records[10];
static size_t pair_trace_total;
static char pair_trace_authenticated[PAIR_TRACE_TOTAL_MAX];
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
        /* Temporarily terminate one exact raw line for existing marker parsing. */
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
    if(!used || used>PAIR_TRACE_TOTAL_MAX-pair_trace_total)return -1;
    char path[PATH_MAX];int count=snprintf(path,sizeof path,"%s/current-trace.log",pair_evidence_dir);
    if(count<0 || (size_t)count>=sizeof path || save_file(path,selected,used))return -1;
    struct pair_trace_record *r=&pair_trace_records[pair_active_round];
    r->fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);
    if(r->fd<0 || fstat(r->fd,&r->identity) || !S_ISREG(r->identity.st_mode) || r->identity.st_nlink!=1 || r->identity.st_size!=(off_t)used)return -1;
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
           fstat(r->fd,&before) || !pair_trace_same(&r->identity,&before) || lseek(r->fd,0,SEEK_SET)!=0)return -1;
        size_t off=0;while(off<r->bytes) {
            size_t want=r->bytes-off;if(want>sizeof chunk)want=sizeof chunk;
            ssize_t n=read(r->fd,chunk,want);if(n<0 && errno==EINTR)continue;
            if(n<=0 || memcmp(chunk,pair_trace_authenticated+r->offset+off,(size_t)n) || write_all(console,chunk,(size_t)n))return -1;
            off+=(size_t)n;
        }
        if(fstat(r->fd,&after) || !pair_trace_same(&before,&after))return -1;
        published+=off;
    }
    if(published!=pair_trace_total || published>PAIR_TRACE_TOTAL_MAX || memchr(last,0,bytes))return -1;
    /* Current-PID traces and boot/control records already have one immutable source.
     * Retain final other diagnostics, never emit duplicate application history. */
    for(size_t off=0;off<bytes;) {
        const char *end=memchr(last+off,'\n',bytes-off);if(!end)return -1;
        size_t length=(size_t)(end-(last+off))+1;static char line[65536];if(length>=sizeof line)return -1;
        memcpy(line,last+off,length);line[length]=0;
        if(pair_trace_application(line)) {
            int pid=pair_trace_pid(line);if(pid<0 || pair_trace_member(last+off,length,pid,&cursor)!=1)return -1;
        } else if(pair_trace_once(line)) {
            if(pair_trace_member(last+off,length,0,&cursor)!=1)return -1;
        } else {
            if(length>PAIR_TRACE_TOTAL_MAX-published || write_all(console,last+off,length))return -1;
            published+=length;
        }
        off+=length;
    }
    for(unsigned round=0;round<10;round++){if(close(pair_trace_records[round].fd))return -1;pair_trace_records[round].fd=-1;}
    return 0;
}

/* Failure-only transport. Hex framing keeps raw trace bytes out of application
 * output and the strict success parser. No trace or completion is invented. */
static int pair_diagnostic_file(int console,int fd,const struct stat *identity,
                                const char *data,size_t bytes,const char *kind,unsigned round)
{
    struct stat before,after;char chunk[1024],row[2304];
    if(fd<0 || !bytes || bytes>PAIR_TRACE_TOTAL_MAX || fstat(fd,&before) ||
       !pair_trace_same(identity,&before) || !S_ISREG(before.st_mode) ||
       before.st_nlink!=1 || before.st_size!=(off_t)bytes || lseek(fd,0,SEEK_SET)!=0)return -1;
    /* Authenticate the whole immutable source before publishing its first byte. */
    for(size_t off=0;off<bytes;) {
        size_t want=bytes-off;if(want>sizeof chunk)want=sizeof chunk;
        ssize_t n=read(fd,chunk,want);if(n<0 && errno==EINTR)continue;
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
    /* main has just exclusively saved these exact bytes, even on round failure. */
    int fd=open(PAIR_ROOT "/evidence/kernel.log",O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);
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

/* Startup route proof stays bound to the existing immutable round0 trace.
 * Current control records are an ordered exact subsequence of that proof;
 * absence after ring rollover does not erase authenticated startup identity. */
static int pair_route_reuse(const char *log,size_t bytes,const struct pair_assignment *a,unsigned long *generation)
{
    struct pair_trace_record *r=&pair_trace_records[0];struct stat current;
    if(!pair_active_round || !bytes || bytes>PAIR_LOG_LIMIT || memchr(log,0,bytes) ||
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
