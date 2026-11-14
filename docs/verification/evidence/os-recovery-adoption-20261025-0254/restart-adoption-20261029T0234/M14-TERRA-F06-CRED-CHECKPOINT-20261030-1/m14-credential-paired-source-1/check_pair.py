from pathlib import Path
import subprocess,re
pre=Path('preimage/kernel/syscall.c').read_text();post=Path('postimage/kernel/syscall.c').read_text()
start='void\ndo_setresuid()\n{'; after='\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nlong sys_setresuid'
def sample(s,ispost):
 if ispost:
  a=s.index('#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)');b=s.index(after,a)
 else:
  a=s.index(start);b=s.index(after,a)
 chunk=s[a:b]
 for sym in ('do_setresuid','do_setresgid'):
  needle='void\n'+sym+'()\n{'; assert chunk.count(needle)==1
  chunk=chunk.replace(needle,'enum { '+sym+'_line = __LINE__ }; void\n'+sym+'()\n{')
 return '#line 19539\n'+chunk+'\nenum { next_line = __LINE__ };\n'
def cpp(s,defs):return subprocess.run(['cc','-E','-P','-x','c','-']+['-D'+x for x in defs],input=s,text=True,capture_output=True,check=True).stdout
def vals(s):return {k:int(v) for k,v in re.findall(r'(do_setresuid_line|do_setresgid_line|next_line)\s*=\s*(\d+)',s)}
for name,defs in [('policy',['MCKERNEL_RUST_SYSCALL_POLICY_HELPERS']),('fallback',[])]:
 orig=cpp(sample(pre,False),defs);off=cpp(sample(post,True),defs);on=cpp(sample(post,True),defs+['MCKERNEL_RUST_F03_CREDENTIAL_REFRESH_EXPERIMENTAL'])
 assert vals(orig)==vals(off),(name,vals(orig),vals(off))
 assert vals(orig)['next_line']==vals(on)['next_line'],(name,vals(orig),vals(on))
 selected=bool(defs)
 assert ('extern void do_setresuid(void)' in on)==selected
 if not selected: assert vals(on)==vals(orig)
 print(name,'off',vals(off),'on',vals(on),'selected',selected)
cm=Path('postimage/kernel/CMakeLists.txt').read_text();rust=Path('postimage/kernel/rust/syscall_policy.rs').read_text();assert cm.count('if (MCKERNEL_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)')==2
assert 'if result != 0 { return null_mut(); }' in rust and '#[cfg(f03_credential_refresh_candidate)]' in rust
print('PASS isolated CPP source positions and selected/error source pairing; no full TU/runtime proof')
