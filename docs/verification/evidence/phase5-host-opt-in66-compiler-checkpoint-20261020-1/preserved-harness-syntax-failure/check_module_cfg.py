from pathlib import Path
import ast,hashlib,importlib.util,json,signal,shlex
N=Path(__file__).resolve().parent
P=json.loads((N/'AFFECTED-ORDINARY-PROPOSAL.json').read_text())
def pin(r):
 b=Path(r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];return b
for r in P['inputs']+list(P['tools'].values()):pin(r)
spec=importlib.util.spec_from_file_location('capture',P['capture']['path']);cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
cap.CENSUS_SOURCE=Path(P['census']['path']);cap.STOP_SIGNALS|={signal.SIGHUP,signal.SIGQUIT}
for sig in cap.STOP_SIGNALS:signal.signal(sig,cap.stop)
out=N/'affected-guard-output-1';out.mkdir(mode=0o700)
def put(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
records=[]
def run(label,argv):
 d=out/label;d.mkdir(mode=0o700);put(d/'command.json',dict(argv=argv));r=cap.owned_capture(dict(argv=argv),d,10,lambda:None);put(d/'status.json',r);records.append(r)
 assert r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None
 return r['returncode'],(d/'stdout').read_text(),(d/'stderr').read_text()
def main():
 kbuild=P['Kbuild']['path'];make=P['tools']['make']['path'];rust=P['tools']['rustc']['path']
 mk=out/'Makefile';mk.write_text('include '+kbuild+'\n.PHONY: mode\nmode:\n\t@printf '%s\\n' "$(RUSTFLAGS_mcctrl_rust.o)"\n')
 flags={}
 for mode in ('off','on'):
  rc,text,_=run('make-'+mode,[make,'--no-print-directory','-rR','-f',str(mk),'mode','MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN='+('1' if mode=='on' else '0')]);assert rc==0;flags[mode]=shlex.split(text.strip())
 assert flags['off']==['--check-cfg','cfg(mckernel_current_fork_adoption_opt_in)','--check-cfg','cfg(MODULE)'] and flags['on']==flags['off']+['--cfg','mckernel_current_fork_adoption_opt_in']
 source=pin(P['gate_source']).decode();line=next(x for x in source.splitlines() if x.startswith('const CURRENT_FORK_ADOPTION_ENABLED:bool='))
 root=pin(P['module_source']).decode();assert '#[cfg(MODULE)]' in root and '#[cfg(not(MODULE))]' in root
 module_attrs=[x for x in root.splitlines() if x in ('#[cfg(MODULE)]','#[cfg(not(MODULE))]')];assert module_attrs==['#[cfg(MODULE)]','#[cfg(not(MODULE))]']
 def fixture(mode,extra=''):
  return '#![deny(unexpected_cfgs)]\n'+line+'\n'+module_attrs[0]+'\nconst MODULE_PROBE:bool=true;\n'+module_attrs[1]+'\nconst MODULE_PROBE:bool=false;\n'+extra+'\nfn main(){assert!(MODULE_PROBE);assert_eq!(CURRENT_FORK_ADOPTION_ENABLED,'+str(mode=='on').lower()+');}\n'
 for mode in ('off','on'):
  f=out/(mode+'.rs');f.write_text(fixture(mode));binary=out/mode
  rc,_,_=run('rust-'+mode,[rust,'--edition=2021','--crate-name','module_cfg_guard','--cfg','MODULE',*flags[mode],str(f),'-o',str(binary)]);assert rc==0
  rc,_,_=run('execute-'+mode,[str(binary)]);assert rc==0
 for label,cmdflags,extra,diagnostic in [('missing-MODULE',flags['off'][:2],'','unexpected `cfg` condition name: `MODULE`'),('unknown-cfg',flags['off'],'#[cfg(UNREGISTERED)] const UNUSED:bool=false;','unexpected `cfg` condition name: `UNREGISTERED`')]:
  f=out/(label+'.rs');f.write_text(fixture('off',extra));rc,_,err=run('rust-'+label,[rust,'--edition=2021','--crate-name','module_cfg_guard','--cfg','MODULE',*cmdflags,str(f),'-o',str(out/label)]);assert rc!=0 and diagnostic in err
 tree=ast.parse(pin(P['driver']).decode());nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ('require','adoption_rust_command_mode')];ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-driver>','exec'),ns)
 for mode in ('off','on'):ns['adoption_rust_command_mode'](flags[mode],mode=='on')
 for bad in (flags['off'][:2],flags['off']+['--check-cfg','cfg(MODULE)']):
  try:ns['adoption_rust_command_mode'](bad,False)
  except (ValueError,AssertionError):pass
  else:raise AssertionError('missing/duplicate MODULE registration accepted')
 put(out/'report.json',dict(status='PASS_AFFECTED_MODULE_CHECKCFG_ONLY',commands=records,savedcmd_refusals=2,defaultOFF=True,explicitON=True,unknowncfg_still_rejected=True,missingMODULE_reproduces_failure=True,sourcebodies_unchanged=True,SDK_or_backend_or_native_acceptance=False,compiler='Retained ordinaryRust1.95; fullSDKRust1.92 stillrequired'))
 print(json.dumps(dict(status='PASS_AFFECTED_MODULE_CHECKCFG_ONLY',commands=len(records),savedcmd_refusals=2)))
try:main()
except BaseException as exc:
 put(out/'FAILED-OR-STOPPED.json',dict(status='FAIL_NO_PASS',error=repr(exc)));raise
