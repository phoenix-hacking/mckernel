"""Import accepted host observer; require two complete fresh-OS pair cycles."""
import copy,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ORIGINAL=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-compatibility-20261019-1/n3-variant/native_diagnostic.py')
ORIGINAL_SHA='8d29c650b74285d9d22435391059dfca7ae7605d0c1158a2a9cb850bd3aa0e20'
PARENT=Path('/home/holden/mckernel-work/scratch/cp205m-261019-1/manifest.json')
PARENT_SHA='4aa72c2a5a759bda71c4a0e8e33499068261346113ec2c9fd19d4669b3f8e41d'
def load(name,path,digest):
 data=Path(path).read_bytes()
 if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('pinned imported source '+str(path))
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
_base=load('original_single_pair_host_engine',ORIGINAL,ORIGINAL_SHA)
_original_validate=_base._validate_manifest
_original_build=_base.build_command
_case=json.loads((HERE/'runtime-case.json').read_bytes())
_oracle=load('mandatory_complete_cycle_oracle',HERE/'cycle_oracle.py',_case['oracle_sha256'])
def validate(obj):
 raw=PARENT.read_bytes();_base._need(hashlib.sha256(raw).hexdigest()==PARENT_SHA,'frozen selected205 parent')
 parent=json.loads(raw);_original_validate(parent)
 _base._need(set(obj)==set(parent) and obj['case_id']=='practical.rust.selected205.two-complete-native-cycles','fixed complete-cycle case')
 for key in ('schema_version','kind','modules','profile','payload','pair'):_base._need(obj[key]==parent[key],'unchanged original contract '+key)
 for key,row in parent['artifacts'].items():
  if key not in ('native_boot','initramfs','root_base'):_base._need(obj['artifacts'][key]==row,'unchanged artifact '+key)
 _base._need(obj['artifacts']['native_boot']['sha256']==_case['boot_sha256'],'actual two-cycle boot')
 _base._need(obj['artifacts']['initramfs']==obj['artifacts']['root_base']==obj['staging']['base_initramfs'],'whole newbase aliases')
 _base._need(obj['staging']['collector']['sha256']==_case['collector_sha256'] and obj['staging']['overlay_source']['sha256']==_case['stager_sha256'],'actual collector/stager')
 bound=_base._one_validate_manifest({k:v for k,v in obj.items() if k!='pair'})
 old=json.loads(Path(parent['staging']['overlay_manifest']['path']).read_bytes())['final_map']
 final=json.loads(Path(obj['staging']['overlay_manifest']['path']).read_bytes())['final_map'];member='bin/native-resource-release-probe'
 _base._need(set(final)==set(old)|{member},'one mandatory public helper addition')
 for name,row in old.items():
  omit={'size','sha256'} if name in ('init','bin/native-boot') else set()
  _base._need({k:v for k,v in row.items() if k not in omit}=={k:v for k,v in final[name].items() if k not in omit},'unchanged member metadata/bytes '+name)
 _base._need(final[member]['sha256']==_case['release_sha256'] and final[member]['size']==_case['release_bytes'] and final[member]['mode']==0o100755,'actual CPU2 public-release helper')
 return {**bound,'pair':copy.deepcopy(parent['pair'])}
def body(manifest,observation):
 report=_oracle.evaluate_protocol(observation['serial'])
 return dict(schema_version=1,kind='native-diagnostic-result',case_id=manifest['case_id'],status='PROTOCOL_PASS',application_acceptance=False,mckernel_application_executed=False,guest_report=report,observation=observation,runtime_blocker=_base.DIAGNOSTIC_LIMITATION,pair_metrics=dict(completed_cycles=2,completed_apps=4,full_restoration_verified=False))
def build(manifest,attempt):
 plan=_base._thaw(_original_build(manifest,attempt));cycles=[]
 for index in range(2):
  apps=copy.deepcopy(manifest['pair']['apps'])
  for i,a in enumerate(apps):a['cwd']='/case/cycle%d/two-app/work%d'%(index,i)
  cycles.append(dict(cycle=index,pair=apps,control_argv=[['/bin/native-boot'],['/bin/native-lifecycle-probe','0'],['/bin/native-resource-release-probe']],fresh_assignment_required=True))
 plan['payload']=dict(cycles=cycles,logger_seconds=120,generation_expected='source-bound actual48B/fresh501 incarnation; different per boot, never cycle+1')
 plan['overlay']['boot_contract']='two complete native lifecycles; actual fresh48B assignment plus fresh501 incarnation per boot'
 plan['overlay']['guest_destinations']['/bin/native-resource-release-probe']=_case['release_path']
 plan['overlay']['init_sequence']=plan['overlay']['init_sequence'][:3]+['cycle0: fresh boot, two payloads, strictstop, destroy/public CPU+memory release','cycle1: fresh boot/different observed incarnation, two payloads, strictstop, destroy/public CPU+memory release']
 return _base._freeze(plan)
_base._validate_manifest=validate
_base._pair_body=body
_base.build_command=build
globals().update({k:v for k,v in vars(_base).items() if not k.startswith('__')})
