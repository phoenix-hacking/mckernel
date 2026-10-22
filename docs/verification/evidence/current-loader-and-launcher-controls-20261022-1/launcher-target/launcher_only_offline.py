#!/usr/bin/env python3
"""One production mcexec target on a disjoint configured-build copy. No kernel build.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse,hashlib,importlib.util,json,os,re,shutil,stat,sys,time
from pathlib import Path
SCHEMA='mckernel.native-exact-launcher-build-receipt.v1'
NEW_SOURCE_SHA='c9b1d55b3b25d18ff1336b9b18e46b845fa0407d246c36d7d25d79276722d78b'
PLAN=Path('/launcher-plan.json')
REL='executer/user/rust/mcexec_helpers.rs'
ARTIFACTS={'mcexec':'executer/user/mcexec','mcexec_helpers.o':'executer/user/rust/mcexec_helpers.o','mcexec.c.o':'executer/user/CMakeFiles/mcexec.dir/mcexec.c.o','libmcexec.a':'executer/user/libmcexec.a','mcexec-rust-build.make':'executer/user/CMakeFiles/mcexec_rust_helpers.dir/build.make','mcexec-link.txt':'executer/user/CMakeFiles/mcexec.dir/link.txt'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,why):
 if not ok:raise RuntimeError(why)
def load_base(plan):
 path=Path('/image_driver_base.py');need(sha(path)==plan['base_driver']['sha256'],'accepted base driver drift')
 spec=importlib.util.spec_from_file_location('_accepted_image_driver_helpers',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def controls(plan):
 root=Path(plan['retained_build']['path']);return {str(Path(row['path']).relative_to(root)):row for row in plan['retained_controls']}

def run(a,base):
 plan=json.loads(PLAN.read_bytes());need(plan['schema']=='mckernel.exact-launcher-only-plan.v1' and a.jobs==1,'single fixed launcher target only')
 output=a.output;evidence=a.evidence
 base._no_symlink_parents(output,'launcher output');base._no_symlink_parents(evidence,'launcher evidence');need(not os.path.lexists(output) and not os.path.lexists(evidence),'fresh output/evidence required')
 base._disjoint((a.source_root,output,evidence));need(output==Path('/work/output') and evidence==Path('/work/evidence'),'accepted configured namespace only')
 source=a.source_root/REL;original=Path('/launcher-original.rs');need(sha(source)==NEW_SOURCE_SHA==plan['source_override']['sha256'],'actual onefile source overlay')
 old=original.read_bytes();new=source.read_bytes();need(sha(original)==plan['original_source']['sha256']=='80e59ae27fe87bdced4e08bd3bdb580185b439311a4fba1daaade7308630afc8' and old.count(b'const PLD_MPOL_MAX: c_int = 4;')==1 and hashlib.sha256(old.replace(b'const PLD_MPOL_MAX: c_int = 4;',b'const PLD_MPOL_MAX: c_int = 5;')).hexdigest()==plan['accepted_predecessor_source']['sha256']=='da71f31656ccfc58a79c4dcca01f9c6742135c292b213b7d86113ebddc4cae0a' and hashlib.sha256(new).hexdigest()==NEW_SOURCE_SHA,'exact accepted base/sentinel predecessor/error-propagation overlay')
 retained=Path('/retained-build');need(retained.is_dir() and type(plan['retained_build_bytes']) is int and plan['retained_build_bytes']>0 and plan['clone_growth_bytes']>=plan['retained_build_bytes']+(256<<20),'bound configured-copy growth')
 for rel,ref in controls(plan).items():need(sha(retained/rel)==ref['sha256'] and (retained/rel).stat().st_size==ref['bytes'],'retained control drift '+rel)
 text=(retained/'CMakeFiles/Makefile2').read_text();deps=[line for line in text.splitlines() if line.startswith('executer/user/CMakeFiles/mcexec.dir/all:')];need(deps==['executer/user/CMakeFiles/mcexec.dir/all: executer/user/CMakeFiles/libmcexec.dir/all','executer/user/CMakeFiles/mcexec.dir/all: executer/user/CMakeFiles/mcexec_rust_helpers.dir/all'],'actual mcexec dependency graph differs')
 tools=base._validate_toolchain(a.toolchain);env=dict(base.REPRO_ENV,PATH=tools['path'],CC=tools['tools']['cc']['path'],RUSTC=tools['tools']['rustc']['path'],KERNEL_DIR=tools['kernel_dir'],**tools['environment'])
 output.mkdir(mode=0o700);evidence.mkdir(mode=0o700);(evidence/'artifacts').mkdir(mode=0o700)
 stdout=evidence/'build.stdout.log';stderr=evidence/'build.stderr.log';stdout.touch();stderr.touch()
 result=dict(schema=SCHEMA,status='FAIL',operation_scope='launcher-only',kernel_rebuilt=False,candidate_sha=a.candidate_sha,ihk_sha=a.ihk_sha,source_manifest_sha256=sha(a.manifest),toolchain_manifest_sha256=sha(a.toolchain),launcher_source_sha256=NEW_SOURCE_SHA,native_fork_owned_transaction=a.native_fork_owned_transaction,commands=[],artifacts={},artifact_copies={},started_at=time.time())
 if a.gitlink_manifest:result['gitlink_manifest_sha256']=sha(a.gitlink_manifest)
 try:
  need(a.native_fork_owned_transaction is True,'accepted diagnostic opt-in required')
  build=output/'build';shutil.copytree(retained,build,copy_function=shutil.copy2,symlinks=True)
  # Invalidate only selected target outputs in the private new copy; originals stay RO.
  for rel in ('executer/user/rust/mcexec_helpers.o','executer/user/mcexec'):
   p=build/rel;need(p.is_file() and not p.is_symlink(),'expected retained selected output');p.unlink()
  command=[tools['tools']['cmake']['path'],'--build',str(build),'--target','mcexec','-j1'];row=dict(phase='production-mcexec-only',argv=command,cwd=str(a.source_root),exit_code=None);result['commands'].append(row)
  row['exit_code']=base._run_process(command,a.source_root,env,stdout,stderr,a.timeout,'production-mcexec-only');need(row['exit_code']==0,'real launcher target failed')
  user=build/'executer/user';flags=(user/'CMakeFiles/mcexec.dir/flags.make').read_text();need(flags.count('-DMCEXEC_RUST_HELPERS')==1 and '-I/src/.kernel-sdk' in flags,'actual C/Rust consumer flags')
  make=(user/'CMakeFiles/mcexec_rust_helpers.dir/build.make').read_text();need('--crate-name mcexec_helpers' in make and tools['tools']['rustc']['path'] in make and str(source) in make,'actual whole Rust compiler source/tool')
  link=(user/'CMakeFiles/mcexec.dir/link.txt').read_text();need('rust/mcexec_helpers.o' in link and 'CMakeFiles/mcexec.dir/mcexec.c.o' in link and 'libmcexec.a' in link,'real linked C/Rust/asm providers')
  nm=tools['tools']['nm']['path'];texts={}
  for name,p in [('linked',user/'mcexec'),('rust',user/'rust/mcexec_helpers.o'),('consumer',user/'CMakeFiles/mcexec.dir/mcexec.c.o')]:
   texts[name]=base._bounded_output([nm,'-g',str(p)],'launcher '+name+' providers',env=env);base._write_fsync(evidence/(name+'-symbols.txt'),texts[name])
  entry='mcexec_main_loop_thread_func_body';need(len(re.findall(r'\bU\s+'+entry+r'\s*$',texts['consumer'],re.M))==1,'real C mainloop import')
  for sym in [entry,'act_clone_complete','mcexec_fork_sync_complete_result']:
   for name in ['linked','rust']:need(len(re.findall(r'\bT\s+'+sym+r'\s*$',texts[name],re.M))==1,'unique Rust provider '+sym)
  need(len(re.findall(r'\bT\s+mcexec_clone_child_bridge\s*$',texts['linked'],re.M))==1,'linked child bridge')
  readelf=tools['tools']['readelf']['path'];needed={}
  for name,p in [('baseline',retained/'executer/user/mcexec'),('new',user/'mcexec')]:
   dynamic=base._bounded_output([readelf,'-d',str(p)],'launcher '+name+' dynamic',env=env);base._write_fsync(evidence/(name+'-dynamic.txt'),dynamic);needed[name]=re.findall(r'\(NEEDED\).*?\[([^]]+)\]',dynamic)
  need(needed['new']==needed['baseline'],'actual launcher dynamic dependency names changed')
  for name,rel in ARTIFACTS.items():
   item=build/rel;result['artifacts'][name]=base._artifact(item,'actual '+name);copy=evidence/'artifacts'/name;shutil.copy2(item,copy);result['artifact_copies'][name]=base._artifact(copy,'retained '+name)
  for rel,ref in controls(plan).items():need(sha(retained/rel)==ref['sha256'],'original configured controls changed')
  need(sha(source)==NEW_SOURCE_SHA and original.read_bytes()==old,'source drift after target')
  result.update(status='PASS',target='mcexec',source_change='transfer_image failure and fatal exec caller propagation over accepted sentinel5 source only',actual_elf_needed_provider_join=True,needed=needed,baseline_configured_tree_modified=False,finished_at=time.time())
 except BaseException as exc:result.update(error_type=type(exc).__name__,error=str(exc),finished_at=time.time())
 # Preserve the accepted driver's evidence sealing/publication boundary.
 try:
  base._check_signal()
  result['inventory']={str(item.relative_to(evidence)):{'size':item.stat().st_size,'sha256':base._sha256(item)} for item in sorted(evidence.rglob('*')) if item.is_file() and not item.is_symlink() and item.name!='receipt.json'}
  if result['status']=='PASS':
   for item in result['artifacts'].values():need(base._artifact(item['path'],'final artifact')==item,'artifact changed before receipt')
   for item in result['artifact_copies'].values():need(base._artifact(item['path'],'final evidence')==item,'evidence artifact changed before receipt')
  base._check_signal()
 except BaseException as exc:result.update(status='FAIL',error_type=type(exc).__name__,error=str(exc))
 result['finished_at']=time.time()
 if base._signal_requested():result.update(status='FAIL',error='interrupt (signal %s)'%base._signal_requested())
 base._atomic_json(evidence/'receipt.json',result)
 if base._signal_requested():
  result.update(status='FAIL',error='interrupt (signal %s)'%base._signal_requested());base._atomic_json(evidence/'receipt.json',result)
 return result

def main():
 p=argparse.ArgumentParser(allow_abbrev=False)
 for key in ['source-root','manifest','toolchain','output','evidence']:p.add_argument('--'+key,required=True,type=Path)
 for key in ['candidate-sha','ihk-sha']:p.add_argument('--'+key,required=True)
 p.add_argument('--jobs',required=True,type=int);p.add_argument('--timeout',required=True,type=int);p.add_argument('--gitlink-manifest',type=Path);p.add_argument('--native-fork-owned-transaction',action='store_true');a=p.parse_args();base=load_base(json.loads(PLAN.read_bytes()))
 with base.SignalLatch():r=run(a,base)
 print(json.dumps(r,sort_keys=True));return 0 if r['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
