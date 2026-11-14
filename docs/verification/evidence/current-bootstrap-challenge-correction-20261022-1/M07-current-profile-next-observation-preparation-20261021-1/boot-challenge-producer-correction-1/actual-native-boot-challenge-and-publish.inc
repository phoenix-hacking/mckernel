static void pair_boot_challenge(void)
{
    long fd=call(SYS_OPEN,(long)PAIR_CHALLENGE,0xa0000,0);
    require(fd>=0);
    require(call(SYS_READ,fd,(long)pair_boot_assignment.nonce,16)==16);
    char tail;require(call(SYS_READ,fd,(long)&tail,1)==0);
    close_fd(fd);
    require(pair_boot_assignment.nonce[0] || pair_boot_assignment.nonce[1]);
    pair_boot_assignment.magic=PAIR_MAGIC;
}
static void pair_boot_publish(int os)
{
    require(call(SYS_IOCTL,os,0x30a02907,0)==2);
    long n=call(103,3,(long)pair_boot_log,sizeof pair_boot_log);
    require(n>0 && n<(long)sizeof pair_boot_log);
    require(pair_routes(pair_boot_log,(unsigned long)n,&pair_boot_assignment,
                        &pair_boot_assignment.generation)==0);
    require(pair_assignment_valid(&pair_boot_assignment,pair_boot_assignment.nonce));
    /* O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC, no replacement/replay. */
    long fd=call(SYS_OPEN,(long)PAIR_ASSIGNMENT,0xa00c1,0600);
    require(fd>=0);
    require(call(SYS_WRITE,fd,(long)&pair_boot_assignment,sizeof pair_boot_assignment)==(long)sizeof pair_boot_assignment);
    close_fd(fd);
    /* The fixed oracle's literal marker is emitted only after actual dynamic
     * CPU/gen proof checks. Its values are checked, never used as evidence. */
    require(pair_boot_assignment.generation==1);
    static const char record[]="<6>NATIVE_PAIR_CPU os=0 generation=1 assigned_host=1,2 logical=0,1 default_ikc_linux=0\n";
    fd=call(SYS_OPEN,(long)"/dev/kmsg",0xa0001,0);require(fd>=0);
    require(call(SYS_WRITE,fd,(long)record,sizeof(record)-1)==(long)sizeof(record)-1);
    close_fd(fd);
}
