"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,json,os,shlex
E=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');D=H/'page-unmap-body-1/production-consumer-1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,v):
 b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
 for p in [D/name,E/name]:
  with p.open('xb') as f:f.write(b)
def main():
 old=json.loads((R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-4/SOURCE-BINDINGS.json').read_text());prior=json.loads((R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-4/PREPARED-COMMANDS.NOT-EXECUTED.json').read_text());source=D/'source';source.mkdir(mode=0o700);rows={}
 expected={'kernel/mem.c':'bac5d4fb766b5cb80e036457465e215743a1cb31622ff11c5b5b605749f3d7fe','kernel/rust/page_helpers.rs':'cfc64f72bf9b94c65417bc8f4e29d65b81f98239fe52ab2a7dd0352ebdfc3f70'}
 for relative in list(old['inputs'])+['kernel/mem.c']:
  original=(H/'page-unmap-body-1/postimage'/relative) if relative in expected else R/relative
  if relative=='kernel/rust/page_helpers.rs':original=H/'page-unmap-body-1/page_helpers.rs'
  b=original.read_bytes();digest=hashlib.sha256(b).hexdigest()
  if relative in expected:assert digest==expected[relative]
  else:assert digest==old['inputs'][relative]['sha256'],'unexpected changed canonical Rust input '+relative
  p=source/relative;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(b)
  assert sha(original)==sha(p)==digest
  rows[relative]=dict(source=str(original),path=str(p),sha256=digest,bytes=len(b))
 assert len(rows)==83
 build=D/'build';build.mkdir(mode=0o700)
 full=prior['fullcrate'];full['argv']=[x.replace(str(H/'production-combined-4/fullcrate-build'),str(build)).replace(str(H/'production-combined-4/source'),str(source)) for x in full['argv']];full['cwd']=str(build)
 W=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work');database=W/'output/build/compile_commands.json';db=json.loads(database.read_text());row=next(x for x in db if x['file']=='/src/kernel/mem.c');args=shlex.split(row['command']);assert args[0]=='/usr/bin/cc' and args.count('-DMCKERNEL_RUST_PAGE_HELPERS')==1
 headers=H/'production-combined-4/default-image-successor-1/source-materialization-attempt-1/materialized-source'
 assert sha(headers/'kernel/include/page.h')==sha(R/'kernel/include/page.h')=='c8f3f5e7804c71430c814395ea14a1ee93267180713caeb39880b662cc9cd0dc'
 args=[x.replace('/src',str(headers)).replace('/work/output',str(W/'output')).replace('/usr/lib/gcc/x86_64-redhat-linux/14/include','/usr/lib/gcc/x86_64-linux-gnu/9/include') for x in args];args[0]='/usr/bin/gcc-9';args.insert(1,'-Werror=incompatible-pointer-types');args[-1]=str(source/'kernel/mem.c');oi=args.index('-o');args[oi+1]=str(build/'mem.c.o')
 pp=args[:oi]+['-E',str(source/'kernel/mem.c')]
 commands=dict(scope=__doc__,fullcrate=full,preprocess=dict(argv=pp,cwd=str(build)),selected_C=dict(argv=args,cwd=str(build)),partial_link=dict(argv=['/usr/bin/ld','-r',str(build/'mem.c.o'),str(build/'mckernel_rust.o'),'-o',str(build/'partial.o')],cwd=str(build)),profile=dict(cpu=0,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,cleanup_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152),compile_row=row,compile_database_authority=dict(path=str(database),recorded_sha256='cbf12ca93c9946c7020b428e5dbc9f08df22659651d94c40704e7c8fa41f006b'),translation='Exact actual mem.c GCC14 production row; only existing accepted GCC9 compiler/builtin-include substitution, accepted incompatible-pointer ABI warning, and source/build/header path translations. No guessed flags. Header roots reuse coherent accepted source; page.h checked.',remaining='Default GCC14 image link/native acceptance remains open.')
 write('SOURCE-BINDINGS.json',dict(scope=__doc__,source_count=83,Rust_source_count=82,inputs=rows,canonical_changed=False,changed_from_prior=['kernel/rust/page_helpers.rs'],new_C_consumer='kernel/mem.c',preserved_all_other_Rust82closure=True))
 write('PREPARED-COMMANDS.json',commands);print(json.dumps(dict(status='PASS_PREPARED',sources=83,commands_sha256=sha(E/'PREPARED-COMMANDS.json'))))
if __name__=='__main__':main()
