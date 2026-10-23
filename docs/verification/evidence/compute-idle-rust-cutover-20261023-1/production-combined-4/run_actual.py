"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,re,time
D=Path(__file__).resolve().parent;REPO=Path('/home/holden/mckernel');E=REPO/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-4'
SCOPE=__doc__
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
assert sha(D/'PREPARED-COMMANDS.NOT-EXECUTED.json')=='3f2b071ecea686547d716860eca28bda4254e1130b7741b3574c23a0c8a252ac'
assert sha(D/'SOURCE-BINDINGS.json')=='8411b47cb941a5a5356cab45484ccb1f4f9b56f1d8f532e697ff0dd41d41d300'
c=json.loads((D/'PREPARED-COMMANDS.NOT-EXECUTED.json').read_text());bindings=json.loads((D/'SOURCE-BINDINGS.json').read_text())
for row in list(bindings['inputs'].values())+[bindings['C_candidate']]:assert sha(Path(row['path']))==row['sha256']
helperpath=REPO/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py';assert sha(helperpath)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('accepted',helperpath);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
argv=c['fullcrate']['argv'];assert len(argv)==46 and sha(Path(argv[6]))=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
(D/'fullcrate-build').mkdir();(D/'selected-build').mkdir();results=[];streams={};start=time.monotonic();status='FAIL_FIRST_COMMAND_RETAINED';error=None;fullobj=D/'fullcrate-build/mckernel_rust.o';cobj=D/'selected-build/memory.c.o';part=D/'selected-build/selected-consumer-provider.o';fullhash=None;exports={};metadata={}
def run(label,command):
 os.chdir(command.get('cwd',str(D)));cap=D/(label+'-capture-1');cap.mkdir();cmd=dict(command,purpose=SCOPE,shell=False);write(cap/'command.json',cmd);begin=time.monotonic();j=h.owned_capture(cmd,cap,90,lambda:None);write(cap/'whole-join.json',j);results.append({'label':label,'seconds':time.monotonic()-begin,'whole_join':j});streams[label]=(cap/'stdout').read_text();assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'],'first failed '+label;return streams[label]
def symbols(text,name):return [line.split()[-2] for line in text.splitlines() if len(line.split())>=2 and line.split()[-1]==name]
try:
 run('fullcrate',c['fullcrate']);fullhash=sha(fullobj)
 fullsymbols=run('Rust-symbols',{'argv':['/usr/bin/nm','-g',str(fullobj)]})
 expected=list(json.loads((REPO/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-3/ordinary-fullcrate-callback3-1/nm-result.json').read_text())['symbols'])+['x86_clear_free_pages_user_bridge']
 exports={name:symbols(fullsymbols,name) for name in expected};assert len(exports)==12 and all(v==['T'] for v in exports.values())
 for name in ['file','line','flag']:assert symbols(fullsymbols,'x86_clear_free_pages_user_'+name)==['U']
 pp=run('preprocess',c['preprocess']);assert 'extern void x86_clear_free_pages_user_bridge(void *addr, int nr_pages);' in pp;assert not re.search(r'\bx86_clear_free_pages_user_bridge\s*\([^;{}]*\)\s*\{',pp,re.S)
 run('selected-C-TU',c['selected_C']);csymbols=run('C-symbols',{'argv':['/usr/bin/nm','-a',str(cobj)]});assert symbols(csymbols,'x86_clear_free_pages_user_bridge')==['U']
 for name in ['file','line','flag']:metadata[name]=symbols(csymbols,'x86_clear_free_pages_user_'+name);assert metadata[name]==['R']
 relocs=run('relocations',{'argv':['/usr/bin/readelf','-rW',str(cobj)]});assert 'x86_clear_free_pages_user_bridge' in relocs
 run('partial-link',c['partial_link']);joined=run('partial-symbols',{'argv':['/usr/bin/nm','-g',str(part)]});assert symbols(joined,'x86_clear_free_pages_user_bridge')==['T']
 for name in ['file','line','flag']:assert symbols(joined,'x86_clear_free_pages_user_'+name)==['R']
 assert sha(fullobj)==fullhash
 status='PASS_ACTUAL_82INPUT_FULLCRATE_12_EXPORTS_GCC9_SELECTED_TU_AND_PARTIAL_LINK'
except BaseException as exc:error=repr(exc)
result={'scope':SCOPE,'status':status,'error':error,'seconds':time.monotonic()-start,'commands':results,'Rust_object':h.hashed(fullobj,32<<20) if fullobj.exists() else None,'C_object':h.hashed(cobj,32<<20) if cobj.exists() else None,'partial_object':h.hashed(part,32<<20) if part.exists() else None,'Rust_object_unchanged_after_inspection_link':sha(fullobj)==fullhash if fullhash else None,'exports':exports,'C_metadata_symbols':metadata,'callback_relocations':[l for l in streams.get('relocations','').splitlines() if 'x86_clear_free_pages_user_bridge' in l],'provenance_data_ownership':'Selected C owns readonly file[]/line/USER const metadata; actual Rust callback imports3data symbols and existing _ihk_mc_free_pages provider. Partial link resolves callback+data uniquely.','remaining_public_page_unmap_debt':[l for l in streams.get('partial-symbols','').splitlines() if l.split()[-1:]==['page_unmap']],'pinnedGCC14_default_C_acceptance':False,'final_image_link':False,'native':False,'file_or_area_retirement':False,'canonical_modified':False,'automatic_retry':False}
write(D/'RESULT.json',result)
for q in D.rglob('*'):
 if q.is_file() and 'source' not in q.relative_to(D).parts and q.suffix!='.o':
  target=E/q.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(q.read_bytes())
print(json.dumps({'status':status,'error':error,'seconds':result['seconds'],'commands':len(results),'Rust_object':result['Rust_object'],'exports':len(exports),'metadata':metadata}))
