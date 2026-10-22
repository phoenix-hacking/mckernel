from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('supervisor','/home/holden/mckernel/scripts/application-tests/supervisor.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
(R/'home').mkdir(mode=0o700);(R/'tmp').mkdir(mode=0o700)
rows=[]
for name,script in [('admission','check-source-admission.py'),('terminal','check-whole-terminal-consumer.py')]:
 report=s.run_supervised(['/usr/bin/python3','-I','-B',str(R/script)],cwd=str(R),env={'PATH':'/usr/bin:/bin','HOME':str(R/'home'),'TMPDIR':str(R/'tmp'),'LC_ALL':'C'},attempt_dir=str(R/(name+'-capture-1')),timeout_seconds=25,cleanup_timeout_seconds=3,stdout_limit_bytes=1048576,stderr_limit_bytes=1048576)
 rows.append({'name':name,'report':report});(R/'whole-checks.json').write_text(json.dumps(rows,indent=2)+'\n')
 assert report['status']=='COMPLETED' and report['cleanup_complete'] and report['wait_status']=={'kind':'exited','code':0},(name,report['wait_status'])
 assert (R/(name+'-capture-1')/'stderr.bin').read_bytes()==b'',name
print('PASS sourceadmission8 + wholeterminal9; elapsed',sum(row['report']['elapsed_seconds'] for row in rows))
