#!/usr/bin/env python3
"""Functional OS/apps migration only; no security testing.
ROOT-EXECUTION ONLY. Compare retained original shell copy and owned fake Rust Host.
This source-preparation worker has not executed this harness or its subprocesses.
"""
import argparse,json,os,pathlib,re,subprocess
FAKE=r"""#!/usr/bin/env python3
import json,os,pathlib,sys
name=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
base=pathlib.Path(os.environ['M15_FAKE_ROOT']).resolve()
def allowed_path(s):
 p=pathlib.Path(s).resolve()
 if p!=base and base not in p.parents:raise SystemExit('outside owned fixture: '+s)
 return p
if name in ('sudo','taskset'):
 if name=='taskset':args=args[2:]
 target=pathlib.Path(args[0]).name
 allowed={'insmod','rmmod','systemctl','cat','chown','ihkconfig','ihkosctl','ihkmond','tee','sync','mkdir','rmdir','rm','kill'}
 if target not in allowed:raise SystemExit('unowned fake command: '+target)
 os.execv(str(base/'fakebin'/target),[target,*args[1:]])
with open(base/'calls.jsonl','a') as out:out.write(json.dumps([name,*args])+'\n')
if name=='getenforce':print('Disabled')
elif name=='id':print('tester')
elif name=='pidof':sys.exit(1)
elif name=='systemctl':sys.exit(1 if args and args[0]=='status' else 0)
elif name=='lsof':sys.exit(1)
elif name=='tee':
 data=sys.stdin.read();allowed_path(args[0]).write_text(data);sys.stdout.write(data)
elif name=='cat':sys.stdout.write(allowed_path(args[0]).read_text())
elif name=='mkdir':
 for a in args:
  if not a.startswith('-'):allowed_path(a).mkdir(parents='-p' in args,exist_ok='-p' in args)
elif name in ('rm','rmdir'):raise SystemExit('unexpected cleanup in happy fixture')
elif name=='kill':raise SystemExit('signals forbidden in fixture')
elif name=='ihkconfig':
 if args==['0','get','buildid']:print('fixture-build')
 if args==['0','query','cpu']:print('2-3')
"""
def selected(calls):
 # Public runtime command groups: reserve/assign/load/kargs/boot versus
 # query/release and module actions. Linux discovery/ownership helpers differ
 # only in how the owned Host supplies inputs and are outside this comparison.
 return [v for v in calls if v[0] in ('ihkconfig','ihkosctl','insmod','rmmod')]
def main():
 a=argparse.ArgumentParser();a.add_argument('--reference-root',type=pathlib.Path,required=True);a.add_argument('--rust-fake',type=pathlib.Path,required=True);a.add_argument('--output',type=pathlib.Path,required=True);o=a.parse_args()
 if o.output.exists():raise SystemExit('output must be new; preserve prior evidence')
 o.output.mkdir(parents=True)
 summary=[]
 for scenario,script,flags in [('boot-existing','mcreboot-smp.sh.in',['-c2-3','-otester']),('stop-retain','mcstop+release-smp.sh.in',['-R'])]:
  base=o.output/scenario;base.mkdir();(base/'fakebin').mkdir();(base/'sbin').mkdir()
  for folder in ('proc/sys/vm','dev','run','sys','etc','modules','kernel'):(base/folder).mkdir(parents=True,exist_ok=True)
  (base/'proc/modules').write_text('ihk 1\nihk_smp_x86_64 1\nmcctrl 1\n')
  (base/'proc/interrupts').write_text('')
  fake=base/'fake.py';fake.write_text(FAKE);fake.chmod(0o700)
  for name in ('sudo','taskset','insmod','rmmod','systemctl','cat','chown','ihkconfig','ihkosctl','ihkmond','tee','sync','mkdir','rmdir','rm','kill','sleep','getenforce','id','pidof','lsof'):(base/'fakebin'/name).symlink_to(fake)
  for name in ('ihkconfig','ihkosctl','ihkmond'):(base/'sbin'/name).symlink_to(fake)
  text=(o.reference_root/'scripts'/script).read_text()
  substitutions={'@prefix@':str(base),'@BINDIR@':str(base/'bin'),'@SBINDIR@':str(base/'sbin'),'@ETCDIR@':str(base/'etc'),'@KMODDIR@':str(base/'modules'),'@KERNDIR@':str(base/'kernel'),'@MCKERNELDIR@':str(base/'kernel'),'@BUILDID@':'fixture-build','@ARCH@':'x86_64','@ENABLE_LINUX_WORK_IRQ_FOR_IKC@':'OFF'}
  # Owned source instrumentation only. References retained unchanged in repo.
  # Rewrite complete literal host paths before configure substitutions so owned
  # prefixes containing path components cannot be rewritten a second time.
  text=re.sub(r'/(?:proc|sys|dev|run)(?=/|\b)',lambda m:str(base)+m.group(0),text)
  for key,value in substitutions.items():text=text.replace(key,value)
  owned=base/'reference.sh';owned.write_text(text)
  env=dict(os.environ,PATH=str(base/'fakebin')+':/usr/bin:/bin',M15_FAKE_ROOT=str(base))
  command=['/bin/bash',str(owned),*flags]
  if scenario=='stop-retain':command+=['-r',str(base/'fakebin/rmmod')]
  original=subprocess.run(command,env=env,text=True,capture_output=True,timeout=15)
  (base/'reference.stdout').write_text(original.stdout);(base/'reference.stderr').write_text(original.stderr)
  if original.returncode:raise SystemExit('original-reference failed; retained '+str(base))
  original_calls=[json.loads(line) for line in (base/'calls.jsonl').read_text().splitlines()]
  candidate=subprocess.run([str(o.rust_fake.resolve()),scenario],text=True,capture_output=True,timeout=15)
  (base/'rust.stdout').write_text(candidate.stdout);(base/'rust.stderr').write_text(candidate.stderr)
  if candidate.returncode:raise SystemExit('Rust owned fake failed; retained '+str(base))
  rust_calls=[[pathlib.Path(v[0]).name,*v[1:]] for line in candidate.stdout.splitlines() if (v:=line.split('\t'))]
  before,after=selected(original_calls),selected(rust_calls)
  (base/'selected.json').write_text(json.dumps({'reference':before,'rust':after},indent=2)+'\n')
  if before!=after:raise SystemExit('public argv mismatch; retained '+str(base))
  summary.append({'scenario':scenario,'status':'PASS','public_calls':len(before)})
 (o.output/'result.json').write_text(json.dumps({'scope':'Functional OS/apps migration only; no security testing.','results':summary},indent=2)+'\n')
if __name__=='__main__':main()
