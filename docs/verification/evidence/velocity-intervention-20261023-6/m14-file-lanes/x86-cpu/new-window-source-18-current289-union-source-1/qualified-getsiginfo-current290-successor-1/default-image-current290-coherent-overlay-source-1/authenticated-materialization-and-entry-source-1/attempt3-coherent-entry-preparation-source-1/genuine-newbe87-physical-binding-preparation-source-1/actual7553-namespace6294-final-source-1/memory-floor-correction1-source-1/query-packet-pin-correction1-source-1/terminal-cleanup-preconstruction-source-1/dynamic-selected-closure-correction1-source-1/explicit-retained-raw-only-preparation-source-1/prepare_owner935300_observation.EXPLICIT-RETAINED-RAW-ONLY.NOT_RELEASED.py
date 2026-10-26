"""Functional OS only; no security testing. Explicit RETAINED-RAW-ONLY; zeroqueries/actions."""
import argparse,hashlib,importlib.util,json,os,time
from pathlib import Path
PROFILE=Path(__file__).parent/'EXACT-EXPLICIT-RETAINED-RAW-ONLY-PROFILE.json'
PROFILE_SHA='59900ca11121143bbdf5cfbc77d65375fbf370d7c4df5c9bfc0d90fe0b0dda20'
def need(value,message):
 if not value:raise ValueError(message)
def read(ref):
 raw=Path(ref['path']).read_bytes();need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'pinnedretainedbytes:'+ref['path']);return raw

def prepare():
 raw=PROFILE.read_bytes();need(hashlib.sha256(raw).hexdigest()==PROFILE_SHA,'retainedprofilepin');p=json.loads(raw);need(os.getuid()==os.geteuid()==1000 and os.getgid()==os.getegid()==1000 and os.sched_getaffinity(0)=={0},'ordinaryUID1000CPU0')
 read(p['producer']);read(p['producer_profile']);read(p['copy_receipt']);original_outer=json.loads(read(p['original_query_outer_join']));need(len(p['six_exact_raw_copies'])==6 and p['query_budget']==p['Popen_budget']==p['ownership_action_budget']==0,'exactretained6zeroqueries');copies={Path(row['path']).name:(row,read(row)) for row in p['six_exact_raw_copies']};need(set(copies)=={'inspect.stdout','inspect.stderr','inspect.status.json','findmnt.stdout','findmnt.stderr','findmnt.status.json'},'exact6rawnames')
 original_status={}
 for label in ('inspect','findmnt'):
  status=json.loads(copies[label+'.status.json'][1]);need(status['returncode']==0 and copies[label+'.stderr'][1]==b'','originalquerysuccessful');original_status[label]=status
  for stream in ('stdout','stderr'):
   row=copies[label+'.'+stream][0];need(status['captures'][stream]['path']==row['original_path'] and status['captures'][stream]['sha256']==row['sha256'] and status['captures'][stream]['bytes']==row['bytes'],'originalstatusrawbinding')
 spec=importlib.util.spec_from_file_location('unchanged9a_realproducer',p['producer']['path']);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);q,e=a.bootstrap();need(q['query_allowlist']['inspect']==original_status['inspect']['argv'] and q['query_allowlist']['findmnt']==original_status['findmnt']['argv'],'originalexactqueryargv')
 # Metadata time is new; original raw/status bytes and times stay original.
 started=time.time();obs=a.produce(q,e,lambda label:copies[label+'.stdout'][1]);finished=time.time();out=Path(p['output_directory']);out.mkdir(mode=0o700);observation=a.publish(out,'OBSERVATION.json',e.canonical(obs));provenance=dict(scope=p['scope'],status='PASS_RETAINED_QUERY_FACTS_WITH_CURRENT_METADATA_ONLY_NOT_CLEANUP_RELEASE',query_count=0,ownership_actions=0,metadata_started_epoch=started,metadata_finished_epoch=finished,original_query_status=original_status,original_query_window={'started_at':original_outer['started_at'],'finished_at':original_outer['finished_at']},original_query_outer_join=p['original_query_outer_join'],original_query_timestamps='Originalstatus contains no perqueryclockfields; actualoriginalouterwindowretained. Noquerytimefabricated.',exact_raw_copies=p['six_exact_raw_copies'],copy_receipt=p['copy_receipt'],producer=p['producer'],producer_profile=p['producer_profile'],holder=p['continuous_holder'],Docker_mount_query_freshness='RETAINED_NOT_NEW',cleanup_engine_fresh_inspect_and_mount_required=True,observation=observation,actual_cleanup_authorized=False);proof=a.publish(out,'RETAINED-RAW-PROVENANCE.json',e.canonical(provenance));return dict(status=provenance['status'],observation=observation,provenance=proof,queries=0,actions=0)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--prepare-retained-raw-only',action='store_true');args=parser.parse_args();need(args.prepare_retained_raw_only,'explicitretainedmode');print(json.dumps(prepare(),sort_keys=True))
if __name__=='__main__':main()
