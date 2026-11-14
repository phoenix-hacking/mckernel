# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,subprocess
P=Path(__file__).resolve().parents[1];F=P/'fixture';O=P/'leaf-output-1';O.mkdir(exist_ok=False)
RUST='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc';GCC='/usr/bin/gcc-9';commands=[]
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def run(argv):
 i=len(commands);r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (O/('%02d.stdout'%i)).write_bytes(r.stdout);(O/('%02d.stderr'%i)).write_bytes(r.stderr)
 commands.append(dict(argv=argv,returncode=r.returncode,stdout=pin(O/('%02d.stdout'%i)),stderr=pin(O/('%02d.stderr'%i))))
 assert r.returncode==0,commands[-1]
 return r.stdout.decode()
try:
 run([RUST,'--edition=2021','--crate-type=lib','--emit=obj','-Dwarnings','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1','-C','relocation-model=static',str(F/'actual.rs'),'-o',str(O/'actual.o')])
 run([GCC,'-std=gnu11','-Wall','-Wextra','-Werror','-O2','-fno-pie','-no-pie',str(F/'main.c'),str(O/'actual.o'),'-o',str(O/'equivalence')])
 output=run([str(O/'equivalence')]);assert 'pairs=129750;' in output
 nm=run(['/usr/bin/nm','-g',str(O/'actual.o')]);rows=[line.split() for line in nm.splitlines()]
 for name,kind in [('spin_sleep_or_schedule','T'),('leaf_spin_sleep_or_schedule_body_result','T'),('futex_wait_schedule_direct_bridge','T'),('get_this_cpu_local_var','U'),('ihk_mc_get_processor_id','U'),('idle_halt','U'),('process_sched_irq_save_bridge','U'),('process_sched_irq_restore_bridge','U'),('process_spin_lock_bridge','U'),('process_spin_unlock_bridge','U'),('process_sched_noirq_lock_bridge','U'),('process_sched_noirq_unlock_bridge','U'),('process_sched_schedule_bridge','U'),('process_sched_zero_free_bridge','U'),('process_sched_pause_bridge','U'),('process_sched_has_signal_bridge','U'),('process_sched_runq_log_bridge','U')]:
  found=[r for r in rows if r[-1:]==[name]];assert len(found)==1 and found[0][-2]==kind,(name,found)
 assert ' U spin_sleep_or_schedule\n' not in nm and ' U process_sched_runqueue_offsets\n' not in nm
 run([GCC,'-std=gnu11','-Werror','-I/home/holden/mckernel/kernel/include','-I/home/holden/mckernel/lib/include','-I/home/holden/mckernel/arch/x86_64/kernel/include','-c',str(F/'abi.c'),'-o',str(O/'abi.o')])
 status='PASS'
finally:
 (O/'receipt.json').write_text(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status=locals().get('status','FAIL'),commands=commands,source_files={p.name:pin(p) for p in F.iterdir() if p.is_file()},tools={p:pin(Path(p)) for p in [RUST,GCC]},test_scope='129750 original-selected-C vs actualRust wrapper cases using existing actualbody/offsetbuilder/4adapters; alternating actual existing futex directcallback consumer; mocked primitive callbacks only; no IRQ/ASM/hostregister/root/guest',whole_C_TU_default_link_native='OPEN'),indent=2)+'\n')
