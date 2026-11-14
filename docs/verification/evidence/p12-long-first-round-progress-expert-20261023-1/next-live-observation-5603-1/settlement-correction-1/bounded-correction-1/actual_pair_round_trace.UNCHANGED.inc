struct pair_round_delivery { unsigned long long worker,serial;unsigned number;int returned,routed,launcher; };
static int pair_round_trace(const char *log,int pid,int cpu)
{
    struct pair_round_delivery calls[256];unsigned count=0,exits=0,attempts=0;
    int schedules=0,published=0,deleted=0,releases=0,acks=0,last_errno=-1,terminal=0;
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
            char *tail=mark+offset;struct pair_round_delivery *d=NULL;
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
            if(osid || generation!=1 || mark[used] || !terminal || acks!=1 || !token || last_errno==0 || (error!=-11 && error!=0) || ++attempts>12 || pair_seen_token_count==49152)return -1;
            for(unsigned j=0;j<pair_seen_token_count;j++)if(pair_seen_tokens[j]==token)return -1;
            pair_seen_tokens[pair_seen_token_count++]=token;last_errno=error;
        } else if((mark=strstr(line,"application_process=cleanup_requested "))) {
            int error=0;
            if(sscanf(mark,"application_process=cleanup_requested os=%u generation=%lu pid=%d intent_errno=%d%n",&osid,&generation,&found,&error,&used)!=4)return -1;
            if(found==pid && (osid || generation!=1 || mark[used] || error || ++releases!=1))return -1;
        } else if((mark=strstr(line,"application cleanup ACK "))) {
            unsigned long long token=0;int error=0,abandoned=-1;
            if(sscanf(mark,"application cleanup ACK os=%u generation=%lu pid=%d token=%llu errno=%d abandoned=%d%n",&osid,&generation,&found,&token,&error,&abandoned,&used)!=6)return -1;
            if(found==pid && (osid || generation!=1 || mark[used] || !token || error || (abandoned!=0 && abandoned!=1) || ++acks!=1))return -1;
        } else if((mark=strstr(line,"application procfs "))) {
            char op[16];int tid=-1;
            if(sscanf(mark,"application procfs %15s os=%u generation=%lu pid=%d tid=%d%n",op,&osid,&generation,&found,&tid,&used)!=5)return -1;
            if(found==pid) {
                if(osid || generation!=1 || tid<=0 || mark[used])return -1;
                if(strcmp(op,"published") && strcmp(op,"deleted"))return -1;
                /* Thread TIDs are genuine rows; only leader rows prove the
                 * original strict pair leader publication/deletion counts. */
                if(tid==pid) {if(!strcmp(op,"published"))published++;else deleted++;}
            }
        }
    }
    if(!count || exits!=1 || !attempts || last_errno || releases!=1 || acks!=1 || schedules!=1 || published!=1 || deleted!=1)return -1;
    for(unsigned j=0;j<count;j++)if(calls[j].number!=231) {
        if(!calls[j].returned)return -1;
        int slot=calls[j].routed?calls[j].launcher:cpu;
        for(unsigned k=0;k<j;k++)if(calls[k].worker==calls[j].worker && calls[k].number!=231 &&
            (calls[k].routed?calls[k].launcher:cpu)!=slot)return -1;
    }
    return 0;
}
