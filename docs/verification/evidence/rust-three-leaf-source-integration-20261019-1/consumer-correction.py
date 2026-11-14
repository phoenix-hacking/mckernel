from pathlib import Path
import importlib.util,json,re,hashlib
O=Path(__file__).parent;R=Path('/home/holden/mckernel');s=importlib.util.spec_from_file_location('integrated',O/'check-integrated.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.E=O/'consumer-correction-1';m.E.mkdir();E=m.E
expected=json.loads((O/'integration-status.json').read_text())['after_sha256'];assert all(hashlib.sha256((R/f).read_bytes()).hexdigest()==v for f,v in expected.items())
old=(O/'checks-1/actual-integrated-consumer.c').read_text();assert old.count('#endifvoid')==1;text=old.replace('#endifvoid','#endif'+chr(10)+'void',1);(E/'actual-integrated-consumer.c').write_text(text)
names=['__release_tid','process_destroy_thread_time_account_bridge','process_destroy_thread_hash_detach_bridge'];cc=['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror','-Werror=implicit-function-declaration','-fno-pie','-c']
for profile,defs in [('selected',['-DMCKERNEL_RUST_PROCESS_HELPERS']),('fallback',[])]:
 m.run(profile+'-consumer',cc+defs+[str(E/'actual-integrated-consumer.c'),'-o',str(E/(profile+'.o'))]);nm=m.run(profile+'-nm',['/usr/bin/nm',str(E/(profile+'.o'))])
 for n in names:assert len(re.findall(r'\bT '+n+'$',nm,re.M))==(0 if profile=='selected' else 1)
 if profile=='selected':assert re.search(r'\bU __release_tid$',nm,re.M)
m.run('actual-selected-link',['/usr/bin/ld','-r',str(E/'selected.o'),str(O/'checks-1/rust.o'),'-o',str(E/'joined.o')]);nm=m.run('actual-joined-nm',['/usr/bin/nm',str(E/'joined.o')])
for n in names:assert len(re.findall(r'\bT '+n+'$',nm,re.M))==1 and not re.search(r'\bU '+n+'$',nm,re.M)
for n in names:
 dis=m.run(n+'-body',['/usr/bin/objdump','-dr','--disassemble='+n,str(O/'checks-1/rust.o')]);code=dis[dis.index('<'+n+'>:'):];assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',code)
declaration='void __release_tid(struct process *proc, struct thread *thread);';assert text.count(declaration)==1;(E/'missing-declaration-control.c').write_text(text.replace(declaration,'/* deliberately removed real declaration */',1))
try:m.run('missing-declaration-control',cc+['-DMCKERNEL_RUST_PROCESS_HELPERS',str(E/'missing-declaration-control.c'),'-o',str(E/'negative.o')])
except AssertionError:
 row=m.records[-1];assert row['returncode']!=0 and row['direct_child_joined'] and not row['timed_out'];err=(E/'missing-declaration-control.stderr').read_text();assert '__release_tid' in err and 'implicit declaration' in err
else:raise AssertionError('negative prototype control accepted')
assert all(hashlib.sha256((R/f).read_bytes()).hexdigest()==v for f,v in expected.items())
summary=dict(status='PASS_CORRECTED_ACTUAL_INTEGRATED_CHANGED_CONSUMERS',commands=len(m.records),prior_actual_Rust_consumer_and_bodies_reused=True,real_C_selected_and_fallback=True,all_three_unique_joined_exports=True,actual_C_prototype_not_injected=True,negative_missing_prototype_rejected=True,all_required_stages_satisfied=True,source_candidate_unchanged=True,semantic_suites_replayed=False,full_production_or_native=False)
(E/'summary.json').write_text(json.dumps(summary,indent=2)+chr(10));print(json.dumps(summary))
