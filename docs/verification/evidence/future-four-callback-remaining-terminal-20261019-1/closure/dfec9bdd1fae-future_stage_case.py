"""Additive canonical gate consumed by the reused observer/cleanup adapters."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from terminal_contract import need,checked_bytes,validate_known,validate_future_canonical_report

def validate_fourleaf_authority(binding):
 known=json.loads(checked_bytes(binding['known_terminal_inputs']));validate_known(known)
 report_ref=binding['canonical_report'];report=json.loads(checked_bytes(report_ref));extra_ref=binding['future_four_callback_facts'];extra=json.loads(checked_bytes(extra_ref))
 validate_future_canonical_report(report,extra,binding['postbuild_completion']['sha256'],extra_ref['sha256'])
 request=json.loads(checked_bytes(known['request'],64<<20));full=binding['full_fourleaf_source_authority']
 remaining=binding['remaining_operation'];need(remaining['request']==known['request'] and remaining['control_plane_source_map']==known['remaining_control_plane']['source_map'],'exact remaining operation source/request')
 for key,expected in known['remaining_receipt_paths'].items():
  if key in ('owner','driver','adoption'):
   need(remaining[key]['path']==expected,'actual remaining receipt path '+key);checked_bytes(remaining[key],64<<20)
 for key in ('retained_prebuild_acceptance','retained_phase_inputs','corrected_callback_consumers'):
  need(remaining[key]==known[key],'retained/corrected typed input '+key);checked_bytes(remaining[key],64<<20)
 for key in ('source_root','source_identity','source_derivative_sha256','materialization_sha256','candidate_sha','candidate_identity_scope'):
  need(full[key]==request[key],'future full-source request premise:'+key)
 need(full['source_identity']==known['source_identity'],'actual source inode premise')
 need(full['entire_source_manifest']['path']==request['source_manifest'] and all(full['materialization_receipt'][k]==known['materialization_receipt'][k] for k in ('path','sha256')),'actual complete materialization premise')
 need(report['future_four_callbacks']['source11']==known['source11'],'actual canonical source11')
 need(report['future_four_callbacks']['implementation_author'] and report['future_four_callbacks']['reviewer'] not in (report['future_four_callbacks']['implementation_author'],known['implementation_author']) and report['future_four_callbacks']['implementation_ownership'] is False,'independent additive artifact reviewer')
 return dict(path=report_ref['path'],sha256=report_ref['sha256'],schema=report['schema'],decision=report['decision'],four_future_callbacks=True,native_acceptance=False)
