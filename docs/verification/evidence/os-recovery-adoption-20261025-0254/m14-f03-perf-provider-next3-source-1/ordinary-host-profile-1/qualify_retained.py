"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unrun retained-only HOST qualifier: no compiler, harness replay or native action.
Root runs after the seven original commands; fails closed preserving all evidence.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess
D=Path(__file__).resolve().parent
SCOPE=__doc__.splitlines()[0]
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def need(ok,why):
 if not ok:raise ValueError(why)
def read(p):return json.loads(p.read_text())
def nmrows(raw):
 result={}
 for line in raw.splitlines():
  parts=line.split()
  need(len(parts)>=2,'nm record syntax')
  name,kind=parts[:2]
  # GNU final images legitimately contain duplicate local FILE/section names.
  # Only exact boundary/data targets and all undefined names enter this table.
  wanted={'perf_counter_extra_set_bridge','perf_counter_init_raw_bridge',
          'syscall_atomic64_read_bridge','perf_event_atomic64_read_bridge',
          'f03_selected_extra','f03_selected_init','f03_selected_atomic',
          'F03_NEXT3_ABI','fixture_extra_provider','fixture_init_provider',
          'fixture_atomic_provider'}
  if name not in wanted and kind!='U':continue
  need(name not in result,'duplicate relevant nm name '+name)
  result[name]=dict(kind=kind,value=parts[2] if len(parts)>2 else None,size=parts[3] if len(parts)>3 else None)
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--profile-sha256',required=True)
 ap.add_argument('--output',required=True)
 args=ap.parse_args();profile_path=D/'PROFILE.NOT-GRANTED.json'
 need(ref(profile_path)['sha256']==args.profile_sha256,'exact Root reviewed profile')
 p=read(profile_path);output=Path(args.output)
 need(output.is_absolute() and output.parent==D and not os.path.lexists(output),'fresh private qualification output')
 need(len(p['commands'])==7 and p['host_growth_reserve_bytes']==8*2**30,'exact seven commands and full growth reservation')
 need(p['fixed_deadline_UTC']=='2026-10-28T05:36:09Z','fixed actual window')
 for row in p['inputs']+[x['plan'] for x in p['leaves']]:need(ref(Path(row['path']))==row,'sealed input '+row['path'])
 cap=Path(p['capture_root']);leaf=Path(p['leaves'][0]['output']);consumed=read(cap/'CONSUMED-GRANT.json')
 need(consumed['profile']==ref(profile_path),'actual consumed profile binding')
 need(consumed['source']['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34','actual unchanged runner')
 need(ref(Path(consumed['grant']['path']))==consumed['grant'],'actual grant retained exact bytes')
 actualgrant=read(Path(consumed['grant']['path']))
 need(actualgrant['authorized'] is True and actualgrant['authorized_by']=='Root' and actualgrant['profile_sha256']==args.profile_sha256,'actual exact Root grant')
 need(actualgrant['nonce']==consumed['nonce'],'same consumed nonce; never replay')
 results=read(cap/'RESULTS.json')
 need(results['status']=='PASS_HOST_ONLY_READY_FOR_REVIEW' and len(results['results'])==7,'all seven retained command passes')
 for i,row in enumerate(results['results']):
  need(row['index']==i and row['leaf']=='F03perfnext3','exact command order')
  command=read(cap/('step'+str(i))/'command.json');need(command==p['commands'][i],'exact executed argv and purpose')
  join=row['join'];need(join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams'] and not join['error'] and not join['retirement_error'] and not join['timed_out'],'actual joined command '+str(i))
  for key in ['stdout','stderr']:
   path=cap/('step'+str(i))/key;record=join['captures'][key];r=ref(path)
   need(r['sha256']==record['sha256'] and r['bytes']==record['size'],'actual closed stream '+str(i)+key)
  need((cap/('step'+str(i))/'stderr').read_bytes()==b'','no new fixture diagnostics')
 need((cap/'step6/stdout').read_text()==p['leaves'][0]['expected_stdout'],'original872pairs/1744traces/ABI16 oracle')
 output.mkdir(mode=0o700)
 def tool(tag,argv):
  out=output/(tag+'.stdout');err=output/(tag+'.stderr')
  with out.open('xb') as so,err.open('xb') as se:
   run=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=so,stderr=se,timeout=15,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
  need(run.returncode==0 and err.read_bytes()==b'' and out.stat().st_size<=32*2**20,'bounded retained-only tool '+tag)
  return out.read_text()
 rust=nmrows(tool('rust-symbols',['/usr/bin/nm','-a','-S','-P',str(leaf/'providers.o')]))
 selected=nmrows(tool('selected-symbols',['/usr/bin/nm','-a','-S','-P',str(leaf/'selected.o')]))
 final=nmrows(tool('final-symbols',['/usr/bin/nm','-a','-S','-P',str(leaf/'parity')]))
 exports=['perf_counter_extra_set_bridge','perf_counter_init_raw_bridge','syscall_atomic64_read_bridge']
 tables=['f03_selected_extra','f03_selected_init','f03_selected_atomic']
 original=['perf_counter_extra_set_bridge','perf_counter_init_raw_bridge','perf_event_atomic64_read_bridge']
 for name in exports:
  need(rust.get(name,{}).get('kind')=='T','unique genuine Rust boundary '+name)
  need(selected.get(name,{}).get('kind')=='U','selected C resolves Rust boundary '+name)
  need(final.get(name,{}).get('kind')=='T','linked boundary '+name)
 need('perf_event_atomic64_read_bridge' not in rust and 'perf_event_atomic64_read_bridge' not in selected,'existing atomic alias reused, no duplicate body')
 for table in tables:need(selected.get(table,{}).get('kind')=='D' and int(selected[table]['size'],16)==8,'three original pointer tables '+table)
 for rows,label in [(rust,'object'),(final,'image')]:
  need(rows.get('F03_NEXT3_ABI',{}).get('kind')=='R' and int(rows['F03_NEXT3_ABI']['size'],16)==128,'readonly ABI16 '+label)
 fake={'fixture_extra_provider','fixture_init_provider','fixture_atomic_provider'}
 need({n for n,row in rust.items() if row['kind']=='U'}==fake,'only three explicit inert endpoints, no actual PMU/atomic provider')
 rustrel=tool('rust-relocations',['/usr/bin/readelf','-rW',str(leaf/'providers.o')])
 selrel=tool('selected-relocations',['/usr/bin/readelf','-rW',str(leaf/'selected.o')])
 for name in fake:need(re.search(r'\b'+name+r'\b',rustrel) is not None,'actual Rust mock endpoint relocation '+name)
 for name in exports:need(re.search(r'R_X86_64_64\s+\S+\s+'+name+r'\b',selrel) is not None,'selected pointer relocation '+name)
 for tag in ['fallback-none','fallback-helper','fallback-callback']:
  rows=nmrows(tool(tag+'-symbols',['/usr/bin/nm','-a','-S','-P',str(leaf/(tag+'.o'))]))
  for name in original:need(rows.get(name,{}).get('kind')=='t','retained local original fallback '+tag+'/'+name)
  need('syscall_atomic64_read_bridge' not in rows,'no Rust alias selected in fallback '+tag)
 report=dict(scope=SCOPE,status='PASS_EXACT_PERF3_ORDINARY_HOST_ONLY',profile=ref(profile_path),actual_results=ref(cap/'RESULTS.json'),actual_consumed_grant=ref(cap/'CONSUMED-GRANT.json'),artifacts=[ref(leaf/name) for name in ['providers.o','selected.o','fallback-none.o','fallback-helper.o','fallback-callback.o','parity']],mock_pairs=872,exact_mock_traces=1744,ABI_words=16,selected_callbacks=3,new_Rust_wrappers=2,reused_existing_atomic_bridge=1,three_original_fallback_witnesses=True,real_header_binding=ref(D/'REAL-HEADER-BINDING.json'),compiler_invocations_by_qualifier=0,harness_replays=0,production_acceptance=False,native_acceptance=False,whole_file_retirement=False)
 with (output/'RESULT.json').open('x') as f:f.write(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],report=ref(output/'RESULT.json'))))
if __name__=='__main__':main()
