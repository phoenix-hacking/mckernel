/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact selected terminal capture body, controlled provider/file/console callbacks.
 * No kernel log syscall is referenced by this host fixture. */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define ND_PAIR_LAUNCH_EXPANSION 1
#if TERMINAL_LONG
#define ND_PAIR_LONG 1
#endif
static int selected_mode, snapshot_calls,save_calls,saved_ok,abort_calls,publish_calls;
static size_t saved_bytes;
int safe=1,pair_rounds_initialized=1;
int klogctl(int action,char *dst,int capacity) {
 assert(action==3 && capacity==1048576);++snapshot_calls;
 if(selected_mode==1 || selected_mode==7){errno=EIO;return -1;}
 size_t n=(selected_mode==6 || selected_mode==8)?127u:1048576u;
 unsigned char *payload=calloc(1048576u,1u);assert(payload);memset(payload,'K',n);memcpy(dst,payload,n);free(payload);
 return selected_mode==2?1048577:(int)n;
}
int save_file(const char *path,const void *payload,size_t n) {
 ++save_calls;assert(!strcmp(path,"/case/evidence/kernel.log") && n<=1048576);
 if(selected_mode==3 || selected_mode==8){errno=EIO;return -1;}
 int fd=open("terminal-capture.saved",O_WRONLY|O_CREAT|O_EXCL,0600);assert(fd>=0);
 size_t done=0;while(done<n){ssize_t k=write(fd,(const char*)payload+done,n-done);assert(k>0);done+=(size_t)k;}
 assert(!close(fd));saved_bytes=n;saved_ok=1;return 0;
}
int write_all(int fd,const void *data,size_t n) {
 assert(fd==7 && n==19 && !memcmp(data,"ND_PAIR_LONG_ABORT\n",19));++abort_calls;
 if(selected_mode==5){errno=EIO;return -1;}return 0;
}
int pair_trace_publish(int fd,const char *data,size_t n) {
 assert(fd==7 && n==127 && data[0]=='K' && data[n-1]=='K');++publish_calls;return 0;
}
int pair_failure_export(int fd,const char *data,size_t n) {
 (void)fd;(void)data;(void)n;assert(!"unexpected nonLONG failure export");return -1;
}
static int terminal_capture(int starting_good,int console) {
 int good=starting_good;
#ifdef ND_PAIR_LAUNCH_EXPANSION
    static char kernel_log[1048576];
#else
    static char kernel_log[262144];
#endif
    int n = klogctl(3, kernel_log, sizeof kernel_log);
#ifdef ND_PAIR_LONG
    if (n < 0 || n > (int)sizeof kernel_log) good = 0;
#else
    if (n < 0 || n == (int)sizeof kernel_log) good = 0;
#endif
    else if (save_file("/case/evidence/kernel.log", kernel_log, (size_t)n) || console < 0) good = 0;
    else {
#ifdef ND_PAIR_LAUNCH_EXPANSION
        #if defined(ND_PAIR_LONG)
        /* LONG trace is already authenticated/published by Rust; raw final
         * kernel.log remains saved above, without a duplicate success trace. */
        if(!good && write_all(console,"ND_PAIR_LONG_ABORT\n",19))good=0;
        #else
        if(good) { if(pair_trace_publish(console,kernel_log,(size_t)n))good=0; }
        else if(safe && pair_rounds_initialized && pair_failure_export(console,kernel_log,(size_t)n))good=0;
        #endif
#else
        if(write_all(console,kernel_log,(size_t)n) || write_all(console,"\n",1))good=0;
#endif
    }

 return good;
}
int main(int argc,char **argv) {
 assert(argc==2);selected_mode=atoi(argv[1]);int starting_good=selected_mode==5?0:1;
 int good=terminal_capture(starting_good,selected_mode==4?-1:7);
 int expected_good=TERMINAL_LONG?selected_mode==0:selected_mode==6;
 int expected_save=TERMINAL_LONG?(selected_mode!=1 && selected_mode!=2):(selected_mode==6 || selected_mode==8);
 int expected_saved=expected_save && selected_mode!=3 && selected_mode!=8;
 assert(snapshot_calls==1 && good==expected_good && save_calls==expected_save && saved_ok==expected_saved);
 assert(abort_calls==(TERMINAL_LONG && selected_mode==5));
 assert(publish_calls==(!TERMINAL_LONG && selected_mode==6));
 if(expected_saved){struct stat st;assert(!stat("terminal-capture.saved",&st) && (size_t)st.st_size==saved_bytes && saved_bytes==(selected_mode==6?127u:1048576u));}
 printf("PASS ACTUAL_TERMINAL_BODY CONTROLLED long=%d mode=%d good=%d snapshots=%d save_calls=%d saved=%zu abort_calls=%d publish_calls=%d\n",TERMINAL_LONG,selected_mode,good,snapshot_calls,save_calls,saved_bytes,abort_calls,publish_calls);return 0;
}
