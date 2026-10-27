"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact interface guard for the observed rustc output-directory failure.
"""
from pathlib import Path
import hashlib,os,stat

def need(ok,message):
 if not ok:raise ValueError(message)
def validate(argv,cwd,out,baseline_argv):
 out=Path(out);cwd=Path(cwd)
 need(out.is_absolute() and '..' not in out.parts and cwd==out,'Rust compiler cwd must be exact writable output directory')
 need(isinstance(argv,list) and isinstance(baseline_argv,list),'exact argv arrays')
 need('-o' not in baseline_argv and '--out-dir' not in baseline_argv and not any(item.startswith('--out-dir=') for item in baseline_argv),'exact failed emit-only baseline required')
 need(argv==baseline_argv+['--out-dir',str(out)],'only explicit output-directory correction allowed')
 emit=[item for item in argv if item.startswith('--emit=')]
 need(emit==['--emit=link='+str(out/'ihkmond-Rust')+',obj='+str(out/'ihkmond-Rust.o')],'both explicit artifact paths must stay inside the same output')
 need('link-arg='+str(out/'mock.o') in argv,'exact retained mock object link argument')
 return dict(output_directory=str(out),cwd=str(cwd),metadata_temp_parent=str(out),explicit_link=str(out/'ihkmond-Rust'),explicit_object=str(out/'ihkmond-Rust.o'),Rust_body_or_codegen_flags_changed=False)

PROBE_BYTES=b'Functional OS compiler output/temp preflight only.\n'
def node(path):
 path=Path(path);s=path.lstat();return dict(path=str(path),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode))
def exclusive_probe(parent,label):
 parent=Path(parent);need(parent.resolve(strict=True)==parent and parent.is_dir(),'canonical existing output/temp parent')
 identity=node(parent);need(identity['uid']==identity['gid']==1000 and identity['mode']==0o700,'owned private output/temp parent')
 directory=parent/('.rust-output-exclusive-'+label);directory.mkdir(mode=0o700)
 path=directory/'write-probe';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  need(os.write(fd,PROBE_BYTES)==len(PROBE_BYTES),'short compiler write probe');s=os.fstat(fd);need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_uid==s.st_gid==1000,'owned exclusive probe file')
 finally:os.close(fd)
 need(path.read_bytes()==PROBE_BYTES,'compiler write probe readback differs')
 return dict(parent=identity,directory=node(directory),file=dict(node(path),bytes=len(PROBE_BYTES),sha256=hashlib.sha256(PROBE_BYTES).hexdigest()))
def runtime_preflight(argv,cwd,out,source_root,env,baseline_argv):
 plan=validate(argv,cwd,out,baseline_argv);out=Path(out);source_root=Path(source_root);temporary=out/'rustc-tmp'
 need(source_root.resolve(strict=True)==source_root and os.statvfs(source_root).f_flag&os.ST_RDONLY,'source export must remain an actual readonly mount')
 need(not os.statvfs(out).f_flag&os.ST_RDONLY,'compiler output mount is readonly')
 temporary.mkdir(mode=0o700)
 need(all(env.get(key)==str(temporary) for key in ['TMPDIR','TMP','TEMP']),'all compiler temp variables must name exact owned attempt temp')
 need(not os.statvfs(temporary).f_flag&os.ST_RDONLY,'compiler temp mount is readonly')
 probes=[exclusive_probe(out,'outputs'),exclusive_probe(temporary,'temporaries')]
 return dict(schema='mckernel.rust-output-in-container-preflight.v1',status='PASS_ACTUAL_NAMESPACE_RO_SOURCE_RW_OUTPUT_AND_TEMP',pid=os.getpid(),mount_namespace=os.readlink('/proc/self/ns/mnt'),source_root=str(source_root),source_flags=os.statvfs(source_root).f_flag,output_flags=os.statvfs(out).f_flag,temp_flags=os.statvfs(temporary).f_flag,argv=argv,cwd=str(cwd),environment={key:env[key] for key in ['TMPDIR','TMP','TEMP']},plan=plan,probes=probes)

def validate_receipt(value,logical_out,actual_out,command,fixture_pid=None,baseline_argv=None):
 logical_out=Path(logical_out);actual_out=Path(actual_out)
 need(value.get('schema')=='mckernel.rust-output-in-container-preflight.v1' and value.get('status')=='PASS_ACTUAL_NAMESPACE_RO_SOURCE_RW_OUTPUT_AND_TEMP','actual in-container preflight required')
 need(type(value.get('pid')) is int and value['pid']>0 and (fixture_pid is None or value['pid']==fixture_pid),'preflight must belong to actual fixture actor')
 need(isinstance(value.get('mount_namespace'),str) and value['mount_namespace'].startswith('mnt:['),'actual mount namespace witness required')
 need(value.get('argv')==command['argv'] and value.get('cwd')==command['cwd']==str(logical_out),'actual compiler argv/cwd differs from preflight')
 need(value.get('source_root')==str(logical_out.parent),'actual readonly source root differs')
 baseline_argv=command['argv'][:-2] if baseline_argv is None else baseline_argv
 need(value.get('plan')==validate(command['argv'],command['cwd'],logical_out,baseline_argv),'actual output/metadata route differs')
 expected_env={key:str(logical_out/'rustc-tmp') for key in ['TMPDIR','TMP','TEMP']}
 need(value.get('environment')==command.get('compiler_temporary_environment')==expected_env,'actual compiler TMPDIR/TMP/TEMP differs')
 need(value.get('source_flags',0)&os.ST_RDONLY and not value.get('output_flags',os.ST_RDONLY)&os.ST_RDONLY and not value.get('temp_flags',os.ST_RDONLY)&os.ST_RDONLY,'actual readonly/writable mount flags required')
 probes=value.get('probes');need(isinstance(probes,list) and len(probes)==2,'both actual directory/file probes required')
 for proof,parent in zip(probes,[logical_out,logical_out/'rustc-tmp']):
  need(proof['parent']['path']==str(parent),'exact probed compiler parent differs')
  for kind in ['parent','directory','file']:
   reference=proof[kind];path=Path(reference['path']);need(path==parent or parent in path.parents,'probe escaped owned output/temp parent')
   actual=actual_out/path.relative_to(logical_out);observed=node(actual)
   need(all(observed[key]==reference[key] for key in ['device','inode','uid','gid','mode']),'retained actual probe identity differs')
  raw=(actual_out/Path(proof['file']['path']).relative_to(logical_out)).read_bytes();need(raw==PROBE_BYTES and proof['file']['bytes']==len(raw) and proof['file']['sha256']==hashlib.sha256(raw).hexdigest(),'retained exclusive write probe differs')
 return value
