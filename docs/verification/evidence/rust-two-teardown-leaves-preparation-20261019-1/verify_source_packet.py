"""Exact private source packet integrity check; no compilers/tools/writes."""
from pathlib import Path
import argparse,hashlib,json

def main():
 p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);a=p.parse_args();d=json.loads(a.packet.read_text());bad=[]
 for name,row in d['files'].items():
  f=Path(row['path'])
  if not f.is_file() or f.stat().st_size!=row['bytes'] or hashlib.sha256(f.read_bytes()).hexdigest()!=row['sha256']:bad.append(name)
 assert not bad,bad
 print(json.dumps(dict(status='PASS_SOURCE_PACKET_IDENTITIES_ONLY',files=len(d['files']),mismatches=bad,compiler_or_parity_or_runtime=False)))
if __name__=='__main__':main()
