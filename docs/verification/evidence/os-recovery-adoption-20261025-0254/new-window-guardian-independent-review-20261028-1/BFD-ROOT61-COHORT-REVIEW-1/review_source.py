"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only BFD Root61 producer/source/admission checks; no actual export or runtime.
"""
import hashlib,importlib.util,json
from datetime import datetime,timezone
from pathlib import Path
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
D=E/'m15-bfd-default-next-integration-source-20261028-1/new-window-producer-cohort-source-1/latest-root61-consumer-successor-source-1'
OUT=Path(__file__).resolve().parent

def ref(p):
 raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def auth(row):
 p=Path(row['path']);assert ref(p)==row,row['path'];return p.read_bytes()
ready=json.loads((D/'SOURCE-READY.json').read_bytes())
assert ref(D/'SOURCE-READY.json')['sha256']=='e788bf8f34c31b55047631af48a568db64ddb42a8eac0b8cc5e97f29d4cb4680'
for row in ready['files']:auth(row)
spec=importlib.util.spec_from_file_location('independent_bfd_materializer',D/'materialize_admission.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
contract,profile,ledger,free,actors=m.validate_sources()
assert len(actors)==61 and len(ledger['consumed_nonces'])==70 and ledger['current_physical_clearance_pending'] is False
plan=json.loads(auth(profile['inputs']['source_export_plan']))
oldplan=json.loads(auth(plan['historical_export_plan']))
assert len(plan['records'])==len(oldplan['records'])==3103
oldrows={r['relative']:r for r in oldplan['records']};newrows={r['relative']:r for r in plan['records']}
assert set(oldrows)==set(newrows)
reference_path_changes=[]
for name,before in oldrows.items():
 after=newrows[name]
 if before==after:continue
 assert before['type']==after['type']=='file' and before['source']['bytes']==after['source']['bytes'] and before['source']['sha256']==after['source']['sha256']
 normalized=json.loads(json.dumps(after));normalized['source']['path']=before['source']['path'];assert normalized==before
 assert after['source']['path']==str(Path('/home/holden/mckernel')/name)
 reference_path_changes.append(name)
assert set(reference_path_changes)=={'executer/user/CMakeLists.txt','executer/user/cmake/BfdRustAccessors.cmake','executer/user/cmake/bfd_layout_witness.c','executer/user/rust/bfd_accessors.rs'}
request=json.loads((D/'REQUEST.SOURCE-ONLY.json').read_bytes());assert request['commands']==profile['exact_commands']
for command in request['commands']:
 raw=(json.dumps(command['argv'],sort_keys=True,separators=(',',':'))+'\n').encode()
 assert hashlib.sha256(raw).hexdigest()==command['argv_compact_json_LF_sha256']
adoption=json.loads(auth(profile['actual_source_adoption']));assert len(adoption['adopted_sources'])==4
for row in adoption['adopted_sources']:auth(row)
assetmap=json.loads(auth(profile['inputs']['asset_map']));assert len(assetmap['files'])==3
for row in assetmap['files']:auth(row['reference'])
limits=[1793253600.0,1035705.5689454618,1051043.6959931096]
assert limits==contract['limits']==profile['fixed_three_clock_cutoffs']==m.worker_limits(D/'build_only_worker.py')
commands=json.loads((D/'ROOT-COMMANDS.NOT-AUTHORITY.json').read_bytes())['commands']
report={
 'scope':__doc__.splitlines()[0],
 'reviewer':'/root/independent','independent':True,'implementation_ownership':False,
 'recorded_at':datetime.now(timezone.utc).isoformat(),
 'decision':'PASS_EXACT_BFD_ROOT61_SOURCE_ADMISSION_AND_READONLY_EXPORT_PROFILE_ONLY',
 'source_ready':ref(D/'SOURCE-READY.json'),'ready':ref(D/'READY.json'),
 'profile':ref(D/'PROFILE.SOURCE-ONLY.json'),'contract':ref(D/'CONTRACT.json'),
 'request':ref(D/'REQUEST.SOURCE-ONLY.json'),
 'source_code':[row for row in ready['files'] if row['path'].endswith('.py')],
 'source_export_plan':profile['inputs']['source_export_plan'],
 'actual_four_path_adoption':profile['actual_source_adoption'],
 'previous_four_path_review':adoption['review'],
 'tests':{
  'original_all_nine':ready['source_checks'],
  'independent_focused_eight':'ACTUAL-MATERIALIZER-FOCUSED-CONTROLS.txt',
  'focused_failures':0,
  'actual_emitted_worker_constants_overridden':False,
  'emitted_profile_request_worker_limits_equal':limits,
  'old_BOOT_old_free_original227_alias_and_missing_attestation':'REFUSED',
  '3103_subject_bytes_and_metadata_match_historical_with_only_four_truthful_canonical_path_rebindings':reference_path_changes,
  'four_current_canonical_BFD_source_bytes':'PASS',
  'exact_three_commands_and_command_hashes':'PASS',
  'ninth_test_not_repeated':'Retained9PASS includes2794-file byte inventory; independent review compares exact authenticated3103-record map and verifies four adopted changed subjects, avoiding unchanged full-prefix rehash.'
 },
 'current_boundary':{
  'fragment':contract['Root61_observer_fragment'],
  'fragment_source':contract['Root61_observer_fragment_source'],
  'ledger_count':70,'pending':False,'actor_rows':61,
  'scope':'Only pure accepted35d5 validate_current(CURRENT) is reused. Native4d1c lifecycle and ordinary116 build remain distinct typed history. Original227 observe() is neither invoked nor released as BFD physical authority.'
 },
 'window_credit':{
  'UTC':limits[0],'MONO':limits[1],'BOOT':limits[2],
  'all_controls_minimum':contract['all_controls_minimum_binding'],
  'guardian':'Exact e8a117df read-only adapter bound to genuine parent369',
  'credit_run':'7f4af94a83b14cc08f97401f5891d965','cumulative_ceiling':'57774.852125',
  'included_first':True,'new_purchase_or_API_key_billing':False,
  'old_account_semantics':'Pinned unchanged predecessor accounting plus actual new thread; real holds/credit floors preserved.'
 },
 'source_profile_findings':[
  'Materializer consumes exact real all-controls minimum binding; contract/profile/literal worker cutoffs agree before emitted output. Genuine Root61/free6c83/70nonces/pendingfalse/61actors are validated by the pinned reviewed data parser.',
  'Source-only materializer requires Root author, exact selective four-path adoption and actual canonical postimage bytes; validates fixed relative source map before copying, readbacks exact closed3103 records and seals files/directories readonly. It contains no guard/account/compiler/resource call.',
  'Admission materializer requires genuine export receipt bound to plan/adoption/root and latest/no-intervening attestation. It copies exact five runtime Python sources to fresh cohort, joins emitted profile/worker/request caps and current facts, and emits NULL-author/NULL-decision operation request with no grant/nonce authority.',
  'BFD runtime adapter fixes operation bfd-current-default-two-tools and exact consumer byte subjects. Explicit Root operation successor plus matching independent review are mandatory; original227 alias and stale f76 are rejected.',
  'Source/archive/accepted SDK prefix and BFD body evidence are reused. Only selected two-tool configure, mcinspect/eclair --parallel1, then actual project-object/Rust/bridge259B/twoPIE readback are selected. No SDK21/eightCLI-equivalence/70-library rebuild prefix is requested.',
  'Existing fourCPU2-5/12GiB/noSwap/512tasks/noNet/UID1000/jobs1 profile, soleheavy/permanent27:4, aggregate reservations,4GiB host reserve and16/12GiB floors remain. Holder/grants/execution/resource authority are absent from this source decision.'
 ],
 'source_closure_counts':{'records':3103,'files':2794,'directories':237,'symlinks':72,'changed_canonical_paths':4},
 'minimum_Root_preparation':[
  {'step':1,'action':'Fill ROOT-ACTUAL-SOURCE-MATERIALIZATION-BINDINGS.json from exact template with Root author, actual c186 four-path adoption and literal source-export-1 root. Run source-copy materializer exactly once.', 'argv':commands[0]['argv'],'output':'Genuine ROOT-ACTUAL-CURRENT-SOURCE-EXPORT.json and readonly source tree only.'},
  {'step':2,'action':'Fill ROOT-ACTUAL-BINDINGS.json with genuine source-export receipt, Root61/free6c83 and true latest/no-intervening attestation. Execute metadata materializer into fresh root-adopted-dispatch-1.', 'argv':commands[1]['argv'],'output':'Emitted profile/worker/runner/holder/export descriptor and NULL-author explicit BFD operation request.'},
  {'step':3,'action':'Root supplies exact BFD operation successor, independent PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR and emitted ROOT-OPERATION-BINDINGS.json matching expected byte subjects. These supply no heavy resource authority.'},
  {'step':4,'action':'Publish/fetch-verify actual emitted cohort. Designated independent reviewer must actually wait with verified PID/birth before fresh clocks. Obtain fresh BFD physical/current/resource admission, unchanged120s checks, soleheavy27:4 reservation, independent exact execution release and prewritten one-use grants.'},
  {'step':5,'action':'Only after every gate, invoke exact one holder; it invokes one reviewed runner/grant. Afterwards require actual artifact and normal retirement/currentfree review.', 'argv':commands[2]['argv']}
 ],
 'conditions':[
  'This decision permits exact source-only adoption/data preparation by Root; reviewer performed no actual source-tree export/stage. Root remains sole canonical/Git/ledger/grant/runtime/controller owner.',
  'Root61/free is historical fact, not future reservation. If any operation intervenes before actual BFD admission, use its genuine latest typed successor and no-intervening attestation; never reuse a spent nonce or substitute old free/observer metadata.',
  'If fresh controls tighten, actual operation/profile/worker/contract must be coherently rebound to true earliest caps before execution. No manual worker constant override, recovery window renewal, debit reset or hold clearing.',
  'Actual BFD physical capture/reviewer prewarm/resource/grants and once-entry release remain mandatory. Reusing original227 pure validator does not grant its operation-specific observe/native authority.',
  'Source/profile review supplies no new HOST/default/native/file acceptance. Preserve M15-F03/F04 OPEN until actual matching linked/default and applicable separately released native diagnostic evidence.'
 ],
 'blocking_source_findings':[],
 'actual_actions':{'guard_account':0,'real_source_export_or_stage':0,'compiler_Docker_root_guest':0,'nonce_grant_controller':0,'canonical_mutations':0,'evidence_writes_only':True},
 'runtime_authority':None,
 'acceptance_deltas':{'source_cohort_review':1,'HOST':0,'default':0,'native':0,'files':0}
}
p=OUT/'REVIEW.json';p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'review':ref(p),'decision':report['decision']}))
