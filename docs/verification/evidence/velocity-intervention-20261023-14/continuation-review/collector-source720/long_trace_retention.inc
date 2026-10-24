/* Fixed ten-round trace retention. Existing Linux save/write APIs only. */
#define PAIR_TRACE_TOTAL_MAX (256u*1024u*1024u)
struct pair_trace_record { int fd,pids[2];size_t bytes,offset;struct stat identity; char path[PATH_MAX]; };
static struct pair_trace_record pair_trace_records[2048];
static size_t pair_trace_total;
static char pair_trace_authenticated[PAIR_TRACE_TOTAL_MAX];
static int pair_trace_application(const char *line)
{
    return strstr(line,"application_syscall=") || strstr(line,"application SCHEDULE ") ||
           strstr(line,"application retirement ") || strstr(line,"application_process=cleanup_requested ") || strstr(line,"application cleanup ACK ") ||
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
/* Reopen exactly one immutable per-round source at a time; no 2048-fd leak. */
static int long_trace_stat(struct pair_trace_record *r,struct stat *out)
{
    int fd=open(r->path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);
    if(fd<0)return -1;
    int bad=fstat(fd,out);if(close(fd))bad=1;return bad?-1:0;
}
static int pair_trace_member(const char *line,size_t length,int pid,size_t *cursor)
{
    for(unsigned round=0;round<pair_active_round && round<2048;round++) {
        struct pair_trace_record *r=&pair_trace_records[round];struct stat current;
        if(pid>0 && pid!=r->pids[0] && pid!=r->pids[1])continue;
        if(!r->bytes || long_trace_stat(r,&current) || !pair_trace_same(&r->identity,&current))return -1;
        size_t off=r->offset,end=r->offset+r->bytes;
        /* Exact-match cursor is a newline boundary; preserve identity check above. */
        if(off<*cursor)off=*cursor;
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
    if(pair_active_round>=2048 || !bytes || memchr(log,0,bytes))return -1;
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
    if(strlen(path)>=sizeof r->path || close(r->fd))return -1;
    strcpy(r->path,path);r->fd=-1;
    r->pids[0]=pair_results[0].pid;r->pids[1]=pair_results[1].pid;r->bytes=used;
    char identity[256];count=snprintf(identity,sizeof identity,"{\"round\":%u,\"pids\":[%d,%d],\"bytes\":%zu,\"device\":%llu,\"inode\":%llu}\n",pair_active_round,r->pids[0],r->pids[1],used,(unsigned long long)r->identity.st_dev,(unsigned long long)r->identity.st_ino);
    int pn=snprintf(path,sizeof path,"%s/current-trace.identity.json",pair_evidence_dir);
    if(count<0 || (size_t)count>=sizeof identity || pn<0 || (size_t)pn>=sizeof path || save_file(path,identity,(size_t)count))return -1;
    r->offset=pair_trace_total;memcpy(pair_trace_authenticated+r->offset,selected,used);
    pair_trace_total+=used;return 0;
}
/* Startup route proof stays bound to the existing immutable round0 trace.
 * Current control records are an ordered exact subsequence of that proof;
 * absence after ring rollover does not erase authenticated startup identity. */
static int pair_route_reuse(const char *log,size_t bytes,const struct pair_assignment *a,unsigned long *generation)
{
    struct pair_trace_record *r=&pair_trace_records[0];struct stat current;
    if(!pair_active_round || !bytes || bytes>PAIR_LOG_LIMIT || memchr(log,0,bytes) ||
       !r->bytes || r->offset!=0 || r->bytes>pair_trace_total ||
       r->pids[0]!=pair_seen_pids[0] || r->pids[1]!=pair_seen_pids[1] ||
       long_trace_stat(r,&current) || !pair_trace_same(&r->identity,&current) ||
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
