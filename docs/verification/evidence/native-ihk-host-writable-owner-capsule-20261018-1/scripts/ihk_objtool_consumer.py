"""Fixed IHK-only accepted-objtool consumer proposal; no container/ownership authority."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,shlex,stat,subprocess
P=argparse.ArgumentParser();P.add_argument('--execute',action='store_true');P.add_argument('--candidate',type=Path,default=Path('/candidate'));P.add_argument('--evidence',type=Path,default=Path('/candidate/evidence'));a=P.parse_args()
R=Path(__file__).resolve().parent;v=json.loads((R/'module-source-authority.json').read_text())
def need(x,s):
 if not x:raise ValueError(s)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if not a.execute:print(json.dumps({'status':'PLAN_ONLY','argv':v['make_argv'],'module':'ihk','source_files':len(v['source_files']),'execution_authority':False}));raise SystemExit(0)
need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={2,3,4,5},'reviewed unprivileged container required')
need(a.candidate==Path('/candidate') and a.evidence==Path('/candidate/evidence'),'fixed namespace required')
expected={q['path']:q for q in v['source_files']};actual={str(p.relative_to(a.candidate/'modules')):p for p in (a.candidate/'modules').rglob('*') if not p.is_dir()}
need(set(actual)==set(expected),'exact isolated IHK source subset required')
for name,p in actual.items():need(not p.is_symlink() and stat.S_ISREG(p.lstat().st_mode) and p.stat().st_nlink==1 and p.stat().st_size==expected[name]['bytes'] and digest(p)==expected[name]['sha256'],'source drift:'+name)
tool=Path(v['tool']['container_path']);need(digest(tool)==v['tool']['sha256'],'accepted objtool bytes differ')
helper=Path(v['reference_driver']['container_path']);need(digest(helper)==v['reference_driver']['sha256'],'frozen ELF/reference parser drift')
s=importlib.util.spec_from_file_location('frozen_strict_elf_consumer',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
need(not a.evidence.exists(),'fresh evidence required');a.evidence.mkdir();receipt={'status':'FAIL','scope':'IHK-only strict tool consumer','module_acceptance':False,'three_module_acceptance':False,'native_acceptance':False,'argv':v['make_argv']}
try:
 with (a.evidence/'make.stdout').open('xb') as out,(a.evidence/'make.stderr').open('xb') as err:result=subprocess.run(v['make_argv'],cwd=v['cwd'],env=v['environment'],stdout=out,stderr=err,timeout=v['timeout_seconds'],check=False)
 receipt['make_returncode']=result.returncode;need(result.returncode==0,'IHK make failed')
 d=a.candidate/'modules';need({p.name for p in d.glob('*.ko')}=={'ihk.ko'},'foreign/missing module')
 need((d/'modules.order').read_text().splitlines()==['/candidate/modules/ihk.o'],'exact IHK modules.order required')
 saved=(d/'.ihk.o.cmd').read_text();savedrows=[x for x in saved.splitlines() if x.startswith('savedcmd_')];need(len(savedrows)==1 and savedrows[0].startswith('savedcmd_/candidate/modules/ihk.o := '),'exact saved compiler target required');parts=savedrows[0].split(':=',1)[1].strip().split(';');need(len(parts)==2,'one Rust/objtool boundary required');rust=shlex.split(parts[0]);strict=shlex.split(parts[1])
 need(len(rust)>2 and rust[0]=='RUST_MODFILE=/candidate/modules/ihk' and rust[1] in ('rustc','/usr/bin/rustc'),'actual Rust compiler required')
 need('-Dwarnings' in rust and '/candidate/modules/ihk.rs' in rust and '--crate-name' in rust and rust[rust.index('--crate-name')+1]=='ihk' and '--emit=obj=/candidate/modules/ihk.o' in rust and '--emit=dep-info=/candidate/modules/.ihk.o.d' in rust,'exact Rust crate/object/dependency binding required')
 need(re.findall(r'^source_[^\n]+ := ([^\n]+)$',saved,re.M)==['/candidate/modules/ihk.rs'] and 'source_/candidate/modules/ihk.o := /candidate/modules/ihk.rs' in saved,'exact Rust source assignment required')
 need(strict==[str(tool),*v['toolflags'],'/candidate/modules/ihk.o'],'strict accepted tool/flag invocation differs')
 need(re.search(r'^deps_/candidate/modules/ihk\.o :=',saved,re.M) is not None,'exact saved dependency header required')
 need(re.search(r'^  /out/.*drivers/misc/mckernel/',saved,re.M) is None,'foreign production source dependency')
 deps=set(re.findall(r'^  /candidate/modules/([^ \n]+) ',saved,re.M));deps.add('ihk.rs');need(deps==set(expected)-{'Kbuild'},'actual compiler source closure differs')
 info=m.modinfo(d/'ihk.ko');need(info.get('name')=='ihk' and info.get('license')=='GPL v2' and info.get('vermagic','').startswith('6.12.0-211.44.1.el10_2.mckernel1.x86_64 '),'module identity/vermagic differs')
 symbols=(d/'Module.symvers').read_text()
 for version in (6,7,8,9):need(re.search(r'\tihk_os_create_unbooted_v'+str(version)+r'\t/candidate/modules/ihk\t',symbols) is not None,'missing frozen IHK factory export')
 receipt.update(status='PASS_IHK_STRICT_TOOL_CONSUMER_ONLY',artifact={'sha256':digest(d/'ihk.ko'),'bytes':(d/'ihk.ko').stat().st_size},modinfo=info,command_sha256=digest(d/'.ihk.o.cmd'))
except BaseException as e:receipt['error']=repr(e);raise
finally:(a.evidence/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'native_acceptance':False}))
