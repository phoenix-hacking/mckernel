#define _GNU_SOURCE
#include <assert.h>
#include <bfd.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pwd.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/eventfd.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#include <ihk/ihklib_private.h>
static void *owners[2];
static size_t owner_sizes[2];
static int allocations,frees,live,opens,closes,statuses,commands,initializations,parent_checks,bfd_opens,case_number,baseline_mode,c_language,inside,checks;
static int device_fd;
static char filename[64],original[64],seen_parent[64];
static char events[128];static size_t event_count;
static void event(char c){assert(event_count+1<sizeof(events));events[event_count++]=c;events[event_count]=0;}
void *observation_malloc(size_t size){assert(allocations<2&&size==(allocations==0?sizeof(dump_mem_chunks_t):0x100000UL));void *p=malloc(size);assert(p);owners[allocations]=p;owner_sizes[allocations++]=size;++live;event('A');return p;}
void observation_free(void *p){if(!p){free(p);return;}assert(closes==1&&commands==5);int found=0;for(int i=0;i<2;i++)if(owners[i]==p){owners[i]=NULL;found=1;break;}assert(found);--live;++frees;event(inside?'F':'R');free(p);errno=EDOM;}
int observation_os_open(int index){assert(index==17&&opens==0&&live==0);device_fd=eventfd(0,EFD_CLOEXEC);assert(device_fd>=0);++opens;event('O');return device_fd;}
int observation_status(int index){assert(index==17&&opens==1&&statuses==0);++statuses;event('S');return IHK_STATUS_RUNNING;}
int observation_ioctl(int fd,unsigned long request,...){
 assert(fd==device_fd&&fd>=0&&request==IHK_OS_DUMP&&fcntl(fd,F_GETFD)>=0);va_list ap;va_start(ap,request);dumpargs_t *args=va_arg(ap,dumpargs_t *);va_end(ap);assert(args);
 /* The original C request's spare/start fields are uninitialized. Read ONLY
  * fields assigned by the exact body before this synchronous command. */
 const int expected[]={DUMP_SET_LEVEL,DUMP_NMI,DUMP_QUERY_NUM_MEM_AREAS,DUMP_QUERY_MEM_AREAS,DUMP_NMI_CONT};assert(commands<5&&args->cmd==expected[commands]);
 if(commands==0||commands==1)assert(args->level==24);
 if(commands==2){assert(args->size==0);args->size=(long)sizeof(dump_mem_chunks_t);}
 if(commands==3){assert(args->size==(long)sizeof(dump_mem_chunks_t)&&args->buf==owners[0]&&owner_sizes[0]==sizeof(dump_mem_chunks_t));for(size_t i=0;i<sizeof(dump_mem_chunks_t);i++)assert(((unsigned char *)args->buf)[i]==0);dump_mem_chunks_t *chunks=args->buf;chunks->nr_chunks=0;chunks->kernel_base=0;chunks->phys_start=0;}
 if(commands==4){assert(allocations==2&&live==2&&initializations==1);errno=EINTR;}
 ++commands;event('I');return 0;
}
int observation_close(int fd){assert(fd==device_fd&&fd>=0&&closes==0&&commands==5&&live==2);assert(close(fd)==0);errno=0;assert(fcntl(fd,F_GETFD)==-1&&errno==EBADF);device_fd=-1;++closes;event('C');errno=ERANGE;return 0;}
int observation_access(const char *path,int mode){
 assert(mode==W_OK&&parent_checks==0&&initializations==1&&live==2&&case_number!=3);++parent_checks;event('P');assert(strlen(path)<sizeof(seen_parent));strcpy(seen_parent,path);
 char temporary[sizeof(original)];memcpy(temporary,original,sizeof(original));char *last=strrchr(temporary,'/');assert(last);*last=0;assert(!memcmp(filename,temporary,sizeof(filename)));
 const char *expected=case_number<2?(baseline_mode?"":"/"):"/owned-dir";assert(!strcmp(path,expected));
 if(path[0]==0){errno=ENOENT;return -1;}if(case_number==1){errno=EACCES;return -1;}return 0;
}
unsigned int observation_bfd_init(void){assert(commands==4&&live==2&&initializations==0);++initializations;event('B');return 0;}
bfd *observation_bfd_fopen(const char *path,const char *target,const char *mode,int fd){assert(initializations==1&&commands==4&&live==2&&bfd_opens==0&&target==NULL&&!strcmp(mode,"w")&&fd==-1&&path==filename&&!memcmp(filename,original,sizeof(filename)));assert(case_number>=2||(case_number==0&&!baseline_mode));++bfd_opens;event('X');errno=EDOM;return NULL;}
/* Exact selected modern HOST header prototypes. Never reached: the declared
 * BFD boundary ALWAYS fails fopen, before any real BFD object/file exists. */
bfd_boolean observation_bfd_close(bfd *file){(void)file;abort();}
bfd_boolean observation_bfd_set_format(bfd *file,bfd_format format){(void)file;(void)format;abort();}
asection *observation_bfd_make_section_anyway(bfd *file,const char *name){(void)file;(void)name;abort();}
bfd_boolean observation_bfd_set_section_size(asection *section,bfd_size_type size){(void)section;(void)size;abort();}
bfd_boolean observation_bfd_set_section_flags(asection *section,flagword flags){(void)section;(void)flags;abort();}
asection *observation_bfd_get_section_by_name(bfd *file,const char *name){(void)file;(void)name;abort();}
bfd_boolean observation_bfd_set_section_contents(bfd *file,asection *section,const void *contents,file_ptr offset,bfd_size_type size){(void)file;(void)section;(void)contents;(void)offset;(void)size;abort();}
typedef int (*Dump)(int,char *,int,int);
int observation_run(Dump dump,int baseline,int is_c){
 assert(getuid()==1000&&geteuid()==1000);baseline_mode=baseline;c_language=is_c;
 for(int number=0;number<4;number++){
  assert(live==0);case_number=number;allocations=frees=opens=closes=statuses=commands=initializations=parent_checks=bfd_opens=0;device_fd=-1;event_count=0;events[0]=0;memset(owners,0,sizeof(owners));memset(owner_sizes,0,sizeof(owner_sizes));memset(filename,0,sizeof(filename));memset(original,0,sizeof(original));memset(seen_parent,0,sizeof(seen_parent));
  strcpy(filename,number<2?"/dumpfile":number==2?"/owned-dir/dumpfile":"dumpfile");memcpy(original,filename,sizeof(original));inside=1;errno=19;int result=dump(17,filename,24,0);inside=0;int observed_errno=errno;
  int expected=number<2&&baseline?-ENOENT:number==1?-EACCES:-EINVAL;int expected_bfd=number>=2||(number==0&&!baseline);assert(result==expected&&allocations==2&&opens==1&&closes==1&&statuses==1&&commands==5&&initializations==1&&parent_checks==(number==3?0:1)&&bfd_opens==expected_bfd&&device_fd==-1&&!memcmp(filename,original,sizeof(filename)));
  assert(live==(c_language?2:0)&&frees==(c_language?0:2));
  printf("CASE language=%s mode=%s path=%d parent=%s result=%d bfd-fopen=%d exact-filename-restored=1 allocations=%d sut-frees=%d observed-survivors=%d descriptor-close=1 NMI-CONT-callback=1 errno-observed=%d order=%s\n",c_language?"C-scoped":"Rust-public",baseline?"baseline":"candidate",number,parent_checks?(seen_parent[0]?seen_parent:"<empty>"):"<not-checked>",result,bfd_opens,allocations,frees,live,observed_errno,events);
  /* C's pre-existing two-buffer leak is outside this parent-path correction.
   * Observe it after return, then reclaim both genuine allocations safely. */
  for(int i=0;i<2;i++)if(owners[i])observation_free(owners[i]);
  assert(live==0&&frees==2);++checks;
 }
 assert(checks==4);printf("dump-parent cases=4 language=%s mode=%s exact-path-and-error-order all-owned-allocations-reclaimed all-anonymous-FDs-once-closed no-real-BFD-object\n",c_language?"C-scoped":"Rust-public",baseline?"baseline":"candidate");return 0;
}

#define ihklib_os_open observation_os_open
#define ihk_os_get_status observation_status
#define ioctl observation_ioctl
#define close observation_close
#define malloc observation_malloc
#define free observation_free
#define access observation_access
#define bfd_init observation_bfd_init
#define bfd_fopen observation_bfd_fopen
#define bfd_close observation_bfd_close
#define dnprintk(fmt, args...) do {  } while (0)
#define dprintf(fmt, args...) do {  } while (0)
#define dprintk(fmt, args...) do {  } while (0)
#define PHYSMEM_NAME_SIZE 32
int ihk_os_makedumpfile(int index, char *dump_file, int dump_level, int interactive)
{
	int ret;
	static char hname[HOST_NAME_MAX+1];
	bfd *abfd = NULL;
	bfd_boolean ok;
	asection *scn;
	dumpargs_t args;
	unsigned long phys_size, phys_offset;
	int error, i;
	size_t bsize;
	void *buf = NULL;
	uintptr_t addr;
	size_t cpsize;
	time_t t;
	struct tm *tm;
	char *date;
	struct passwd *pw;
	dump_mem_chunks_t *mem_chunks;
	long mem_size;
	char *physmem_name_buf = NULL;
	char physmem_name[PHYSMEM_NAME_SIZE];
	int osfd = -1;
	char *token;
	int dump_nmi_sent = 0;

	dprintk("%s: enter\n", __func__);
	dprintf("%s: index=%d,dump_file=%s,dump_level=%d,interactive=%d\n",
		__func__, index, dump_file, dump_level, interactive);

	if ((osfd = ihklib_os_open(index)) < 0) {
		dprintf("%s: error: ihklib_os_open returned %d\n",
			__func__, osfd);
		ret = osfd;
		goto out;
	}

	ret = ihk_os_get_status(index);
	if (ret < 0) {
		dprintf("%s: ihk_os_get_status returned %d\n",
			__func__, ret);
		goto out;
	}

	if (ret == IHK_STATUS_INACTIVE) {
		ret = -EINVAL;
		goto out;
	}

	t = time(NULL);
	if (t == (time_t)-1) {
		ret = -errno;
		dprintf("%s: error: time returned %d\n",
			__func__, -ret);
		goto out;
	}

	tm = localtime(&t);
	if (!tm) {
		ret = -EINVAL;
		dprintf("%s: error: localtime failed\n",
			__func__);
		goto out;
	}

	error = gethostname(hname, sizeof(hname));
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: gethostname returned %d\n",
			__func__, -ret);
		goto out;
	}

	/* TODO: might be redundant */
	pw = getpwuid(getuid());
	if (pw == NULL) {
		ret = -errno;
		dprintf("%s: error: getpwuid returned %d\n",
			__func__, -ret);
		goto out;
	}

	args.cmd = DUMP_SET_LEVEL;
	args.level = dump_level;
	error = ioctl(osfd, IHK_OS_DUMP, &args);
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: DUMP_SET_LEVEL returned %d\n",
			__func__, -ret);
		goto out;
	}

	args.cmd = DUMP_NMI;
	error = ioctl(osfd, IHK_OS_DUMP, &args);
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: DUMP_NMI returned %d\n",
			__func__, -ret);
		goto out;
	}
	dump_nmi_sent = 1;

	args.cmd = DUMP_QUERY_NUM_MEM_AREAS;
	args.size = 0;
	error = ioctl(osfd, IHK_OS_DUMP, &args);
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: "
			"DUMP_QUERY_NUM_MEM_AREAS returned %d\n",
			__func__, -ret);
		goto out;
	}

	mem_size = args.size;
	mem_chunks = malloc(mem_size);
	if (!mem_chunks) {
		ret = -ENOMEM;
		dprintf("%s: error: alloating mem_chunks\n",
			__func__);
		goto out;
	}

	memset(mem_chunks, 0, args.size);

	args.cmd = DUMP_QUERY_MEM_AREAS;
	args.buf = (void *)mem_chunks;
	error = ioctl(osfd, IHK_OS_DUMP, &args);
	if (error != 0) {
		ret = -errno;
		dprintf("%s: error: DUMP_QUERY_MEM_AREAS returned %d\n",
			__func__, -ret);
		goto out;
	}

	phys_size = 0;
	dprintf("%s: nr chunks: %d\n",
		__func__, mem_chunks->nr_chunks);
	for (i = 0; i < mem_chunks->nr_chunks; ++i) {
		dprintf("%s: 0x%lx:%lu\n",
				__FUNCTION__,
				mem_chunks->chunks[i].addr,
				mem_chunks->chunks[i].size);
		phys_size += mem_chunks->chunks[i].size;
	}

	bsize = 0x100000;
	buf = malloc(bsize);
	if (!buf) {
		ret = -ENOMEM;
		dprintf("%s: error: allocating buf\n", __func__);
		goto out;
	}

	bfd_init();

	if (dump_file == NULL) {
		ret = -EFAULT;
		goto out;
	}

	token = strrchr(dump_file, '/');
	if (token) {
		token[0] = 0;
		ret = access(token == dump_file ? "/" : dump_file, W_OK);
		if (ret) {
			ret = -errno;
			dprintf("%s: %s is inaccessible: %d\n",
				__func__, dump_file, -ret);
			token[0] = '/';
			goto out;
		}
		token[0] = '/';
	}

	abfd = bfd_fopen(dump_file, NULL, "w", -1);
	if (!abfd) {
		ret = -EINVAL;
		dprintf("%s: bfd_fopen failed: %s\n",
			__func__, bfd_errmsg(bfd_get_error()));
		goto out;
	}

 abort(); /* harness: fopen must have returned NULL */

 out:
	if (dump_nmi_sent) {
		args.cmd = DUMP_NMI_CONT;
		ioctl(osfd, IHK_OS_DUMP, &args);
	}

	if (abfd) {
		ok = bfd_close(abfd);
		if (!ok) {
			ret = -EINVAL;
			dprintf("%s: error: bfd_close: %s\n",
				__func__, bfd_errmsg(bfd_get_error()));
		}
	}
	if (osfd >= 0) {
		error = close(osfd);
		if (error) {
			ret = -errno;
			dprintf("%s: error: close: %s\n",
				__func__, strerror(-ret));
		}
	}
	return ret;
}

int main(void){return observation_run(ihk_os_makedumpfile,0,1);}
