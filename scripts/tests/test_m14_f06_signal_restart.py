"""Pure actual signal-restart policy; no kernel or native execution.

SIGCHLD handlers obey the same SA_RESTART and never-restart syscall rules as
other handlers. C compiled in both existing signal-frame profiles; Rust receives
its existing explicit profile flag. Numbers are the x86_64 syscall ABI.
"""
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from scripts.tests.test_m14_f06_sigreturn_transaction import item

ROOT=Path(__file__).resolve().parents[2]
NEVER={'pause':34,'rt_sigsuspend':130,'rt_sigtimedwait':128,'epoll_wait':232,
       'epoll_pwait':281,'poll':7,'ppoll':271,'select':23,'pselect6':270,
       'msgrcv':70,'msgsnd':69,'semop':65,'semtimedop':220,'clock_nanosleep':230,
       'nanosleep':35,'io_getevents':208}
RUST=r'''
type CInt=i32;type CLong=i64;type CULong=u64;
const EINTR:i32=4;const SIGCHLD:i32=17;const SIGKILL:i32=9;const SIGSTOP:i32=19;
const SYS_EPOLL_WAIT:i32=232;const SYS_PPOLL:i32=271;const SYS_PSELECT6:i32=270;const SYS_NANOSLEEP:i32=35;
#[test] fn actual_restart_policy() {
    let mut cases=0;
    for native in [0,1] {for sig in [10,17] {for flag in [0,1] {
        for num in F06_SIGNAL_RESTART_NEVER {
            assert_eq!(arch_signal_restart_result(num,(-4i64) as u64,sig,flag,native),0,"num={num} sig={sig} flag={flag} native={native}");cases+=1;
        }
        assert_eq!(arch_signal_restart_result(0,(-4i64) as u64,sig,flag,native),flag);cases+=1;
    }}}
    for native in [0,1] {for num in [-1,0,15] {for sig in [9,19] {
        assert_eq!(arch_signal_restart_result(num,(-4i64) as u64,sig,1,native),0);cases+=1;
    }}}
    assert_eq!(arch_signal_restart_result(15,(-4i64) as u64,10,1,1),0);cases+=1;
    assert_eq!(arch_signal_restart_result(0,0,17,1,0),0);cases+=1;
    assert_eq!(arch_signal_restart_result(-1,(-4i64) as u64,17,1,0),0);cases+=1;
    println!("Rust: {cases} restart cases passed");
}
'''
C_CASES=r'''
#include <assert.h>
#include <stdio.h>
int main(void) {
    const int never[]={34,130,128,232,281,7,271,23,270,70,69,65,220,230,35,208};
    unsigned cases=0;
    for(int native=0;native<2;native++) for(int sig=10;sig<=17;sig+=7) for(int flag=0;flag<2;flag++) {
        for(unsigned n=0;n<sizeof never/sizeof *never;n++) {
            int got=native?isrestart_native(never[n],(unsigned long)-EINTR,sig,flag):isrestart_legacy(never[n],(unsigned long)-EINTR,sig,flag);
            if(got) {fprintf(stderr,"C num=%d sig=%d flag=%d native=%d unexpectedly restarted\n",never[n],sig,flag,native);return 1;}cases++;
        }
        assert((native?isrestart_native(0,(unsigned long)-EINTR,sig,flag):isrestart_legacy(0,(unsigned long)-EINTR,sig,flag))==flag);cases++;
    }
    for(int native=0;native<2;native++) for(int n=-1;n<=15;n+=n<0?1:15) for(int sig=9;sig<=19;sig+=10) {
        assert(!(native?isrestart_native(n,(unsigned long)-EINTR,sig,1):isrestart_legacy(n,(unsigned long)-EINTR,sig,1)));cases++;
    }
    assert(!isrestart_native(15,(unsigned long)-EINTR,10,1));cases++;
    assert(!isrestart_legacy(0,0,17,1));cases++;
    assert(!isrestart_legacy(-1,(unsigned long)-EINTR,17,1));cases++;
    printf("C: %u restart cases passed\n",cases);return 0;
}
'''

class F06SignalRestartTests(unittest.TestCase):
    def checked(self,args):
        r=subprocess.run(args,text=True,capture_output=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r

    def test_actual_c_and_rust_restart_policy(self):
        cc=os.environ.get('CC') or shutil.which('gcc')
        if cc is None:
            self.skipTest('GCC required for the isolated fixture')
        rustc=os.environ.get('RUSTC') or shutil.which('rustc')
        if rustc is None:
            self.skipTest('rustc required for the isolated fixture')
        c=(ROOT/'arch/x86_64/kernel/syscall.c').read_text()
        rust=(ROOT/'kernel/rust/f06_signal_tail.rs').read_text()
        cbody=item(c,'static int\nisrestart(')
        definitions='#include <errno.h>\n#define SIGKILL 9\n#define SIGSTOP 19\n#define SIGCHLD 17\n#define __NR_rt_sigreturn 15\n'
        definitions+=''.join(f'#define __NR_{name} {number}\n' for name,number in NEVER.items())
        code=definitions+cbody.replace('isrestart(','isrestart_legacy(')+'\n#define MCKERNEL_NATIVE_SIGNAL_STACK\n'+cbody.replace('isrestart(','isrestart_native(')+C_CASES
        table=rust[rust.index('const F06_SIGNAL_RESTART_NEVER:'):rust.index('/// Pure policy only:')]
        rcode=RUST+table+item(rust,'pub extern "C" fn arch_signal_restart_result(')
        with tempfile.TemporaryDirectory(prefix='m14-f06-restart-') as tmp:
            path=Path(tmp);(path/'test.c').write_text(code);(path/'test.rs').write_text(rcode)
            self.checked([cc,'-std=gnu11','-Wall','-Wextra','-Werror',str(path/'test.c'),'-o',str(path/'ctest')])
            self.checked([rustc,'--edition=2021','--test',str(path/'test.rs'),'-o',str(path/'rtest')])
            results=[subprocess.run([str(path/name)],text=True,capture_output=True,timeout=30) for name in ['ctest','rtest']]
            evidence='\n'.join(r.stdout+r.stderr for r in results)
            self.assertTrue(all(r.returncode==0 for r in results),evidence);print(evidence)

if __name__=='__main__':unittest.main()
