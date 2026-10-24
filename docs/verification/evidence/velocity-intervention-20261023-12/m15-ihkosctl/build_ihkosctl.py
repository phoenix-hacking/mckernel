#!/usr/bin/env python3
"""Build-time configured IHK ABI feature adapter; no production runtime body.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse,os,re,subprocess
from pathlib import Path
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['rustc','source','output','config']:p.add_argument('--'+name,required=True)
    a=p.parse_args();header=Path(a.config).read_text()
    ids=re.findall(r'^#define\s+BUILDID\s+"([A-Za-z0-9._+\-]+)"\s*$',header,re.M)
    if len(ids)!=1:raise SystemExit('Expected one plain ASCII configured IHK BUILDID')
    env=dict(os.environ,IHKOSCTL_BUILDID=ids[0])
    command=[a.rustc,'--crate-name','ihkosctl','--crate-type=lib','--edition=2021','-C','panic=abort','-C','opt-level=2','-C','debuginfo=1','-C','relocation-model=pic','-C','force-unwind-tables=no','--emit=obj='+a.output]
    if re.search(r'^#define\s+ENABLE_MEMDUMP\s+1\s*$',header,re.M):command+=['--cfg','ihkosctl_memdump']
    command.append(a.source);subprocess.run(command,env=env,check=True)
if __name__=='__main__':main()
