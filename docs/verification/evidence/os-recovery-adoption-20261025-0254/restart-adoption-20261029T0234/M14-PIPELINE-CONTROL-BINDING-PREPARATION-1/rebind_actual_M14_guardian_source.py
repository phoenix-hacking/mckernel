"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bound exact source generation only; no imported control code or runtime admission.
"""
from pathlib import Path
from decimal import Decimal
import argparse, ast, difflib, hashlib, json, math, re
D=Path(__file__).resolve().parent
ORIGINAL=D.parents[1]/'restart-operation-guard-source-20261028-1/guardian_guard.py'
NEWSC=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1930-pacific-1')
OLD_SHA='48893862bb3262a2c81d282215e4b9771b8f659e635a21856096c41233774f18'
RUN='7f4af94a83b14cc08f97401f5891d965';CEILING=Decimal('57774.852125');FLOOR=Decimal('22812.3311')
WINDOW_SHA='0bfb54bff698f53c744d797e2f57db94db08cd20120da70566d555fa6c1e320e'
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb';UTC=1793253600;MONO=1035704.5689393478;BCAP=1051042.6959879305
OLD_ACTORS={2109395,2109397,2109399,2111552,2111966}
def need(v,s):
 if not v:raise ValueError(s)
def reference(p):
 p=Path(p);need(p.is_absolute() and not p.is_symlink() and p.is_file(),'regular absolute source input')
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def authenticate(r):
 need(type(r)is dict and set(r)=={'path','bytes','sha256'} and reference(r['path'])==r,'exact input bytes')
 return json.loads(Path(r['path']).read_text())
def valid_ref(r,path):
 need(type(r)is dict and set(r)=={'path','bytes','sha256'} and r['path']==str(path) and type(r['bytes'])is int and r['bytes']>0 and re.fullmatch('[a-f0-9]{64}',r['sha256']) is not None,'exact late-bound input reference')
def validate_inputs(bundle,armed,config,packet,bridge):
 """Pure value validation. TEST_ONLY fixtures carry no execution authority."""
 need(bundle.get('scope')=='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','scope')
 for key,rel in [('armed','ACTUAL-CONTROLS-ARMED.json'),('config','armed-controller/CONFIG.json'),('packet','armed-controller/FROZEN-PACKET.json'),('bridge','armed-controller/bridge-start.json')]:valid_ref(bundle[key],NEWSC/rel)
 need(armed['status']=='LIVE_SAME_WINDOW_M14_EXCLUSIVE_CONTROLS' and armed['phase']=='running' and armed['goal_status']=='active' and armed['native_release'] is False,'actual arm state')
 thread=armed['thread_id'];need(type(thread)is str and re.fullmatch('[a-f0-9-]{36}',thread) is not None and thread=='01a18582-1fc6-77b1-bfb6-15c86483f579','current thread')
 need(armed['guardian_packet_sha256']==bundle['packet']['sha256'] and armed['original_window_sha256']==WINDOW_SHA and armed['steering_interval_seconds']==1200,'packet/window/steering')
 need(armed['auxiliary_leases_held']==dict(guardian=True,monitor=True,phone=True),'auxiliary leases')
 caps=armed['earliest_control_caps'];need(caps['deadline_epoch']==UTC,'same UTC')
 for k,maximum in [('monotonic_deadline',MONO),('boot_deadline',BCAP)]:need(type(caps[k]) in (int,float) and math.isfinite(caps[k]) and 0<caps[k]<=maximum,'no cap extension '+k)
 credit=armed['credit_budget'];need(credit['id']==RUN and Decimal(credit['budget'])==CEILING and FLOOR<=Decimal(credit['spent'])<CEILING,'same cumulative allowance')
 actors=armed['actors'];need(set(actors)=={'watcher','worker','server','guardian','monitor','phone'},'six exact actors')
 for k,a in actors.items():need(type(a['pid'])is int and a['pid']>0 and type(a['start'])is str and a['start'].isdigit() and type(a['ppid'])is int and a['ppid']>0 and a['state'] not in ('Z','X'),'actor identity '+k)
 need(len({a['pid'] for a in actors.values()})==6,'distinct actors')
 need(all(a['pid'] not in OLD_ACTORS for a in actors.values()),'no retired actor reuse')
 need((actors['phone']['pid'],actors['phone']['start'],actors['phone']['ppid'])==(1894242,'96505809',1311),'retained phone')
 need(actors['worker']['ppid']==actors['watcher']['pid'] and actors['server']['ppid']==actors['worker']['pid'],'current PPID chain')
 need(config['expected_thread']==thread and config['credit_run_id']==RUN and Decimal(config['credit_ceiling'])==CEILING and Decimal(config['credit_spent_floor'])>=FLOOR,'controller account/thread')
 need(config['included_first'] is True and config['automatic_credit_purchase'] is False and config['api_key_billing'] is False,'unchanged billing')
 clock=config['initial_watch_clock'];need(clock['boot_id']==BOOT and clock['deadline']==UTC and (clock['watcher_pid'],clock['watcher_start'])==(actors['watcher']['pid'],actors['watcher']['start']),'current initial watch clock')
 need(type(clock['boot_deadline']) in (int,float) and math.isfinite(clock['boot_deadline']) and 0<clock['boot_deadline']<=1051043.6959931096 and type(clock['watcher_cutoff_lower']) in (int,float) and math.isfinite(clock['watcher_cutoff_lower']) and 0<clock['watcher_cutoff_lower']<=caps['monotonic_deadline'],'initial watch clamp')
 need(bridge['deadline']==UTC and (bridge['pid'],bridge['birth']['pid'],bridge['birth']['start'])==(actors['guardian']['pid'],actors['guardian']['pid'],actors['guardian']['start']) and type(bridge['birth']['ppid'])is int and bridge['birth']['ppid']>0,'guardian launch identity')
 need(type(packet)is dict and set(('private','canonical'))<=set(packet),'packet closure')
 return actors,caps

def render(original,bundle,armed,config,packet,bridge):
 actors,caps=validate_inputs(bundle,armed,config,packet,bridge)
 need(hashlib.sha256(original.encode()).hexdigest()==OLD_SHA,'original guardian pin')
 replacements={
  "CONTROL = BASE / 'restart-20261028-1200-pacific-1'":"CONTROL = BASE / 'restart-20261028-1930-pacific-1'",
 }
 replacements["'LIVE_CONTINUED_CAMPAIGN_GUARDIAN_20MIN_STEERING_AND_RETAINED_PHONE'"] = "'LIVE_SAME_WINDOW_M14_EXCLUSIVE_CONTROLS'"
 replacements["'original_window_unchanged_sha256'"] = "'original_window_sha256'"
 tree=ast.parse(original)
 constants=dict(ARM_RECEIPT_REF=bundle['armed'],CONFIG_SHA=bundle['config']['sha256'],PACKET_SHA=bundle['packet']['sha256'],THREAD=armed['thread_id'],INITIAL={k:(actors[k]['pid'],actors[k]['start']) for k in ('watcher','worker','server')},BOOT_CAP=caps['boot_deadline'],MONO_CAP=caps['monotonic_deadline'])
 for n in tree.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in constants:
   replacements[ast.get_source_segment(original,n)]=n.targets[0].id+' = '+repr(constants[n.targets[0].id])
 replacements['owner.get(\'ppid\') == 2111551']= "owner.get('ppid') == GUARDIAN_LAUNCH_PPID"
 replacements["armed['actors']['guardian']['ppid'] == 1311"]="armed['actors']['guardian']['ppid'] == GUARDIAN_RECORDED_PPID"
 replacements["expected = dict(INITIAL, guardian=(2111552, '101236067'),\n                    monitor=(2111966, '101243270'), phone=(1894242, '96505809'))"]='expected = EXPECTED_ACTORS'
 replacements['recorded = dict(guardian=1311,monitor=2111963,phone=1311)']='recorded = AUX_RECORDED_PPIDS'
 out=original
 for before,after in replacements.items():need(out.count(before)==1,'single declared replacement '+before);out=out.replace(before,after)
 anchor='\n\ndef need(value, message):'
 extra='\nGUARDIAN_LAUNCH_PPID = '+repr(bridge['birth']['ppid'])+'\nGUARDIAN_RECORDED_PPID = '+repr(actors['guardian']['ppid'])+'\nEXPECTED_ACTORS = '+repr({k:(v['pid'],v['start']) for k,v in actors.items()})+'\nAUX_RECORDED_PPIDS = '+repr({k:actors[k]['ppid'] for k in ('guardian','monitor','phone')})+'\n'
 need(out.count(anchor)==1,'single constants insertion');out=out.replace(anchor,extra+anchor)
 ast.parse(out);return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--inputs-sha256',required=True);a=p.parse_args()
 rr=reference(a.inputs);need(rr['sha256']==a.inputs_sha256,'exact explicit input bundle');b=authenticate(rr)
 need(b.get('TEST_ONLY') is not True,'TEST_ONLY never materialized')
 vals=[authenticate(b[k]) for k in ('armed','config','packet','bridge')]
 source=render(ORIGINAL.read_text(),b,*vals)
 # Authenticate packet private/canonical closure without importing or running it.
 for k,sha in vals[2]['private'].items():need(reference(NEWSC/'armed-controller'/k)['sha256']==sha,'packet private '+k)
 for k,sha in vals[2]['canonical'].items():need(reference(Path('/home/holden/mckernel/scripts')/k)['sha256']==sha,'packet canonical '+k)
 dest=D/'new-guardian-source-1';need(not dest.exists(),'fresh source namespace');dest.mkdir()
 (dest/'guardian_guard.py').write_text(source)
 (dest/'MINIMAL-DIFF.patch').write_text(''.join(difflib.unified_diff(ORIGINAL.read_text().splitlines(True),source.splitlines(True),fromfile=str(ORIGINAL),tofile=str(dest/'guardian_guard.py'))))
 (dest/'SOURCE-ONLY.json').write_text(json.dumps(dict(scope=b['scope'],runtime_authority=None,inputs=rr,original=reference(ORIGINAL),successor=reference(dest/'guardian_guard.py'),controls_imported_or_called=0),indent=2)+'\n')
 print(json.dumps(reference(dest/'guardian_guard.py')))
if __name__=='__main__':main()
