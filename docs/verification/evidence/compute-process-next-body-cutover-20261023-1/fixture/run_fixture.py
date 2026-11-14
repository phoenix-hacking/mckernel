# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# NOT AUTHORIZED TO EXECUTE until dispatcher grants the ordinary CPU6 profile.
import pathlib, subprocess, json, hashlib, os
P=pathlib.Path(__file__).resolve().parents[1]; F=P/'fixture'; O=P/'leaf-output-1'
def identity(p):
 b=p.read_bytes(); return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def run(argv):
 r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE); i=len(commands)
 (O/('%02d.stdout'%i)).write_bytes(r.stdout); (O/('%02d.stderr'%i)).write_bytes(r.stderr)
 commands.append(dict(argv=argv,returncode=r.returncode,stdout=identity(O/('%02d.stdout'%i)),stderr=identity(O/('%02d.stderr'%i))))
 assert r.returncode==0, commands[-1]
 return r.stdout.decode()
O.mkdir(exist_ok=False); commands=[]
RUST='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
GCC='/usr/bin/gcc-9'
try:
 run([RUST,'--edition=2021','--crate-type=lib','--emit=obj','-Dwarnings','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1','-C','relocation-model=static',str(F/'actual.rs'),'-o',str(O/'actual.o')])
 run([GCC,'-std=gnu11','-Wall','-Wextra','-Werror','-fno-pie','-no-pie','-O2',str(F/'main.c'),str(O/'actual.o'),'-o',str(O/'equivalence')])
 output=run([str(O/'equivalence')]); assert 'PASS original-C/actual-Rust' in output
 syms=run(['/usr/bin/nm','-g',str(O/'actual.o')]); assert syms.count(' T set_timer\n')==1 and ' U set_timer\n' not in syms
 for n in ['time_sharing','get_this_cpu_local_var','process_timer_runtime_offsets','process_timer_spin_lock_bridge','process_timer_spin_unlock_bridge','process_timer_lapic_enable_bridge','process_timer_lapic_disable_bridge']:
  assert ' U '+n+'\n' in syms,n
 # Real current header ABI compile is kept distinct from the modeled leaf layout.
 run([GCC,'-std=gnu11','-Werror','-I/home/holden/mckernel/kernel/include','-I/home/holden/mckernel/lib/include','-I/home/holden/mckernel/arch/x86_64/kernel/include','-c',str(F/'abi.c'),'-o',str(O/'abi.o')])
 status='PASS'
finally:
 (O/'receipt.json').write_text(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status=locals().get('status','FAIL'),commands=commands,sources={p.name:identity(p) for p in F.iterdir() if p.is_file()},tools={p:identity(pathlib.Path(p)) for p in [RUST,GCC]},default_kernel_native='OPEN'),indent=2)+'\n')
