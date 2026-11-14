"""Finite current pins preparation; no machinery imported or executed.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-terminal-data-preparation-1/actual-binding-1')
def ref(p):
 b=Path(p).read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 pins=json.loads((OLD/'BINDER-INPUT-PINS-CURRENT.json').read_bytes())
 pins['templates']['checker']=ref(OLD/'checker-expert-projection-correction-1/check_current_launcher_bodies.py')
 pins['data']=ref(HERE/'ACTUAL-CURRENT-TERMINAL-DATA.json')
 pins['templates']['observer']=ref(HERE.parent/'observe_current_launcher_retirement.CURRENT-SOURCE-UNRELEASED.py')
 with (HERE/'BINDER-INPUT-PINS-CURRENT.json').open('x') as f:json.dump(pins,f,indent=2,sort_keys=True);f.write('\n')
 text=(HERE/'bind_current_launcher_terminal.TEMPLATE.py').read_text().replace('ROOT_CURRENT_PINS_SHA_REQUIRED',ref(HERE/'BINDER-INPUT-PINS-CURRENT.json')['sha256'])
 ast.parse(text)
 with (HERE/'bind_current_launcher_terminal.py').open('x') as f:f.write(text)
 print(json.dumps(dict(pins=ref(HERE/'BINDER-INPUT-PINS-CURRENT.json'),constructor=ref(HERE/'bind_current_launcher_terminal.py'))))
if __name__=='__main__':main()
