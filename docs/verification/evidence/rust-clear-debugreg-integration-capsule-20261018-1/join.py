from pathlib import Path
import json,subprocess,resource,time,hashlib,re
O=Path(__file__).parent;H=O.parent;P=H/'rust-clear-debugreg-cutover-20261018-1';A=H/'rust-scheduler-debug-image-actual-review-20261018-1/actual-review.json';a=json.loads(A.read_text());E=O/'consumer-join-1';E.mkdir()
commands=[]
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3));resource.setrlimit(resource.RLIMIT_FSIZE,(24*1024**2,24*1024**2))
def run(label,argv):
 t=time.monotonic();r=subprocess.run(argv,capture_output=True,text=True,timeout=35,preexec_fn=limits)
 for stream in ['stdout','stderr']:(E/(label+'.'+stream)).write_text(getattr(r,stream))
 commands.append(dict(label=label,argv=argv,status=r.returncode,seconds=time.monotonic()-t));(E/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,label
 return r.stdout
base=Path(a['retained_artifacts']['rust']['retained_path']);data=base.read_bytes();assert hashlib.sha256(data).hexdigest()==a['actual_artifacts']['rust']['sha256']
new=P/'evidence-1/actual.o';selected=P/'evidence-1/selected.o'
inputs={str(p):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in [base,new,selected]};(E/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
run('link',['/usr/bin/ld','-r',str(base),str(new),str(selected),'-o',str(E/'joined.o')])
nm=run('nm',['/usr/bin/nm',str(E/'joined.o')]);lines=[l for l in nm.splitlines() if re.search(r'\b(?:clear_debugreg|sched_schedule_debug_handoff|consumer)$',l)]
assert len([l for l in lines if re.search(r'\bT clear_debugreg$',l)])==1
assert not re.search(r'\bU clear_debugreg$',nm,re.M)
assert re.search(r'\bT sched_schedule_debug_handoff$',nm,re.M)
sched=run('scheduler-disassembly',['/usr/bin/objdump','-dr','--disassemble=sched_schedule_debug_handoff',str(E/'joined.o')]);assert 'clear_debugreg' in sched
clear=run('clear-disassembly',['/usr/bin/objdump','-dr','--disassemble=clear_debugreg',str(E/'joined.o')]);regs=re.findall(r'\bmov\s+%[a-z0-9]+,%db([0-7])\b',clear);assert regs==list('012367'),regs
(E/'result.json').write_text(json.dumps(dict(status='PASS_PARTIAL_RELOCATABLE_CONSUMER_JOIN_ONLY',accepted_real_rust_object=inputs[str(base)],joined_symbols=lines,scheduler_clear_symbol_resolution='no unresolved clear_debugreg; one T clear_debugreg; real accepted scheduler has clear relocation',not_proven=['new integrated full production Rust crate','full selected/fallback syscall.c under GCC14','full image/default link','native debug-register branch']),indent=2)+'\n')
print('PASS partial consumer join: accepted real scheduler Rust object + reviewed new Rust clear body + selected fixture consumer; one resolved clear symbol')
