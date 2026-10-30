"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data32 source-only successor. No lease, validation, compiler, native or tree reads.
A genuine separately reviewed Rust157 joint byte+identity observation is required.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
OLD=BASE/'sdk21-nonheld13-ledger-converter-source-1/sdk13_ledger_converter.py'
OLD_SHA='0493933dc0e8f1f24e28db5bdba52d20e5595cc7c0055a3f3534b0ff54852b16'
FINAL=BASE/'sdk21-nonheld13-data32-source-map-1/SDK13-DATA32-SOURCE-MAP.PROPOSED.json'
FINAL_SHA='4172db42e65b1e30ccfbb86a86c0df1746eb9605ee3497e5a968db0fe16cdd1e'
PROFILE_SHA='e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3'
PROPOSAL_SHA='b9e0fbad132ae43fcd79459b9f2baee776679b4a972e4647d583f0d8ba26b594'
VALIDATION=BASE/'sdk21-nonheld13-input-validation-source-1/sdk13_data32_input_validation.py'
VALIDATION_SHA='a9912953c35ce94a92713d93c39d28a40e788f334de548aadbda656e8dba0587'
SNAPSHOT=BASE/'sdk21-nonheld13-input-validation-source-1/sdk13_data32_input_snapshot.py'
SNAPSHOT_SHA='603644a17f6a9cd7bc7f9dc56051025ab9aa3339ae14f5706b9ec386531a4105'
SOURCE=BASE/'sdk21-nonheld13-source-map-1'
DATA_RECEIPT_SCHEMA='mckernel.sdk13.data32.rust157-joint-observation.v1'

def _bound(path,expected):
 data=path.read_bytes()
 if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('evidence binding changed: '+str(path))
 return data

def _canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def assemble_candidate(rust_receipt_bytes, reviewed_rust_receipt_sha256):
 """Build proposed API input; caller must independently review actual receipt.

 Receipt JSON is a genuine producer result, not a map-derived document:
 schema, root (physical directory path), root_identity (dict in old KEYS form),
 entries (157 file rows each with kind, physical, path, target, bytes, sha256,
 identity). An actual byte read must be jointly tied to each file identity.
 The caller pins the separately reviewed exact receipt hash, and must establish
 supported-filesystem semantics, quiescence, lease and source integrity at the
 operation. This routine can detect inconsistency, not establish those facts.
 It never opens any tree files and is not a validation or an admission.
 """
 if not isinstance(rust_receipt_bytes,bytes) or not isinstance(reviewed_rust_receipt_sha256,str):raise ValueError('independently reviewed Rust157 receipt required')
 if hashlib.sha256(rust_receipt_bytes).hexdigest()!=reviewed_rust_receipt_sha256:raise ValueError('Rust157 receipt digest differs')
 receipt=json.loads(rust_receipt_bytes)
 if set(receipt)!={'schema','root','root_identity','entries'} or receipt['schema']!=DATA_RECEIPT_SCHEMA:raise ValueError('unsupported Rust157 observation schema')
 _bound(OLD,OLD_SHA);_bound(VALIDATION,VALIDATION_SHA);_bound(SNAPSHOT,SNAPSHOT_SHA)
 spec=importlib.util.spec_from_file_location('sdk13_previous_ledger_converter',OLD)
 previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
 old_trees,old_provenance=previous.load_bound()
 m=json.loads(_bound(FINAL,FINAL_SHA))
 if m['profile_sha256']!=PROFILE_SHA or m['proposal_sha256']!=PROPOSAL_SHA:raise ValueError('final profile/proposal binding differs')
 oldmap=json.loads(_bound(SOURCE/'SDK13-SOURCE-MAP.PROPOSED.json',previous.BINDINGS[SOURCE/'SDK13-SOURCE-MAP.PROPOSED.json']))
 for target in ('/src','/nightly'):
  if m['trees'][target]!=oldmap['trees'][target]:raise ValueError('retained tree differs: '+target)
 if m['toolchain_lock']!=oldmap['toolchain_lock']:raise ValueError('lock binding differs')
 if receipt['root']!=m['trees']['/src/kernel/rust']['root']:raise ValueError('Rust157 root differs')
 if not isinstance(receipt['entries'],list) or len(receipt['entries'])!=157:raise ValueError('Rust157 complete receipt required')
 point=json.loads(_bound(SOURCE/'POINT-IN-TIME-IDENTITIES.json',previous.BINDINGS[SOURCE/'POINT-IN-TIME-IDENTITIES.json']))
 point['rust_tree_identities']=receipt['entries']
 for r in point['root_identities']:
  if r['target']=='/src/kernel/rust':r['physical']=receipt['root'];r['identity']=receipt['root_identity']
 # Directory rows are not present in a byte receipt. The mapped directory is
 # deliberately left for the live adoption walk, not invented as an observation.
 # normalize() requires Rust directory rows; use a pure map with Rust directories
 # omitted solely for conversion, while leaving the frozen final map untouched.
 import copy
 without_dirs=copy.deepcopy(m)
 without_dirs['trees']['/src/kernel/rust']['entries']=[x for x in m['trees']['/src/kernel/rust']['entries'] if x['kind']!='dir']
 source_raw=_bound(SOURCE/'current-source6153-1/results/SOURCE6153-IDENTITIES.jsonl',previous.BINDINGS[SOURCE/'current-source6153-1/results/SOURCE6153-IDENTITIES.jsonl'])
 source_rows=[json.loads(line) for line in source_raw.splitlines()]
 sr=json.loads(_bound(SOURCE/'current-source6153-1/results/SOURCE-CURRENT-RESULT.json',previous.BINDINGS[SOURCE/'current-source6153-1/results/SOURCE-CURRENT-RESULT.json']))
 trees,pending=previous.normalize(without_dirs,point,source_rows,sr['source_root_identity'],{'/src':(6104,49),'/src/kernel/rust':(157,0),'/nightly':(2465,0)})
 for target in ('/src','/nightly'):
  if trees[target]!=old_trees[target]:raise ValueError('retained normalized rows differ: '+target)
 pending['/src/kernel/rust']['map_directory_count']=sum(x['kind']=='dir' for x in m['trees']['/src/kernel/rust']['entries'])
 return {'prehashed_trees':trees,'prehashed_trees_sha256':hashlib.sha256(_canonical(trees)).hexdigest(),
  'provenance':{'status':'PROPOSED_DATA_NO_ADMISSION_OR_REVIEW','final_map_sha256':FINAL_SHA,'profile_sha256':PROFILE_SHA,'proposal_sha256':PROPOSAL_SHA,
   'validator_sha256':VALIDATION_SHA,'snapshot_api_sha256':SNAPSHOT_SHA,'rust157_receipt_sha256':reviewed_rust_receipt_sha256,
   'rust157_receipt_independent_review':'REQUIRED_EXTERNAL_TO_CONVERTER','retained_old_provenance':old_provenance,
   'directory_identities':pending,'prior_nightly_resource_metrics':'UNKNOWN','authority':None,'review':None}}
