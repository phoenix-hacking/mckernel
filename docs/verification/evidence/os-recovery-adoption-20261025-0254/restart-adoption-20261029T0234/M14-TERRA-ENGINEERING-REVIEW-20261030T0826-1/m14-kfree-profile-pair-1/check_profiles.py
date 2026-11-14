from pathlib import Path
import subprocess
s=Path('postimage/kernel/CMakeLists.txt').read_text()
option='MCKERNEL_F03_PTRACE_KFREE_PROFILE_119_EXPERIMENTAL'
blocks=[]
for ind in ('\t\t\t\t','\t\t\t'):
 a=s.index('\n'+ind+'if ('+option+')\n')+1;b=s.index('\n'+ind+'endif()\n',a)+1+len(ind+'endif()\n');blocks.append(s[a:b])
assert 'f03_ptrace_kfree_profile_119' in blocks[0] and 'f03_ptrace_kfree_dispatch_origin' in blocks[0]
assert 'MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119' in blocks[1]
assert not any(x in ''.join(blocks) for x in ['ptrace_wakeup_log','ptrace_detach_do_kill','TERMINATE_HOST'])
for enable,abi,arch,ubsan in [(False,'linux-6.12','x86_64',False),(True,'linux-6.12','x86_64',False),(True,'linux-6.12','aarch64',False),(True,'other','x86_64',False),(True,'linux-6.12','x86_64',True)]:
 expr=f'''set({option} {'ON' if enable else 'OFF'})\nset(ARCH {arch})\nset(ENABLE_UBSAN {'ON' if ubsan else 'OFF'})\nset(MCKERNEL_HOST_IRQ_ABI {abi})\nset(RUST_KERNEL_CFG)\nif(MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12" AND ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n{blocks[0]}\n{blocks[1]}\nendif()\nget_property(CFLAGS SOURCE "${{CMAKE_CURRENT_SOURCE_DIR}}/syscall.c" PROPERTY COMPILE_DEFINITIONS)\nmessage("CFG=${{RUST_KERNEL_CFG}}")\nmessage("CFLAGS=${{CFLAGS}}")\n'''
 Path('fixture.cmake').write_text(expr)
 out=subprocess.run(['cmake','-P','fixture.cmake'],capture_output=True,text=True,check=True).stderr
 active=enable and abi=='linux-6.12' and arch=='x86_64' and not ubsan
 assert ('CFG=--cfg;f03_ptrace_kfree_profile_119;--cfg;f03_ptrace_kfree_dispatch_origin' in out)==active,out
 assert ('CFLAGS=MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119' in out)==active,out
 print(f'{enable=} {abi=} {arch=} {ubsan=} selected={active}')
print('PASS actual CMake fragments: ON/OFF and three profile exclusions; exact full build config remains open')
