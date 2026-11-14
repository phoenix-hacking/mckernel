from pathlib import Path
import subprocess
p=Path(__file__).resolve().parent
out=p/'toolchain-correction-1'
commands=[]
for name in ['baseline','candidate']:
 commands.extend([['/usr/bin/cc','-c',str(p/(name+'.S')),'-o',str(out/(name+'.o'))],['/home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','--cfg',name,'-Awarnings',str(p/(name+'.rs')),'-C','codegen-units=1','-C','link-arg='+str(out/(name+'.o')),'-o',str(out/name)],[str(out/name)]])
commands.extend([['/usr/bin/cc','-std=gnu11','-Wall','-Werror',str(p/'layout.c'),'-o',str(out/'layout')],[str(out/'layout')]])
for argv in commands:
 print('COMMAND',repr(argv),flush=True)
 subprocess.run(argv,check=True,cwd=p)
