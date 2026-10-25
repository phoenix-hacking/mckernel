"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute only the actual configure proof-path AST gate; no cleanup/observer/import effects.
"""
import ast,unittest
from pathlib import Path
SOURCE=Path(__file__).with_name('cleanup_current_retained_F03_image.SOURCE-ONLY.NOT-RELEASED.py')
OBSERVER=Path(__file__).with_name('observe_current_retained_F03.READONLY.SOURCE-ONLY.NOT-RELEASED.py')
HISTORICAL='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/CLOSED-IMAGE-OWNER-CLI-PROOF.json'
CURRENT='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/CLOSED-CURRENT-F03-OWNER-CLI-PROOF.json'
class Refusal(Exception):pass
class ConfigureProofPath(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(SOURCE.read_text());cfg=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='configure')
  self.gate=next(n for n in ast.walk(cfg) if isinstance(n,ast.If) and len(n.body)==1 and isinstance(n.body[0],ast.Raise) and isinstance(n.body[0].exc,ast.Call) and n.body[0].exc.args and isinstance(n.body[0].exc.args[0],ast.Constant) and n.body[0].exc.args[0].value=='image-guard-proof-path')
  self.code=compile(ast.Module(body=[self.gate],type_ignores=[]),'<actual-configure-proof-path-gate>','exec')
 def run_gate(self,path):exec(self.code,{'Path':Path,'proof_key':'guard_proof','ROOT_TERMINAL':Path(path),'Refusal':Refusal})
 def test_current_observer_path_accepted(self):
  tree=ast.parse(OBSERVER.read_text());node=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CLI_PROOF' for t in n.targets));actual=ast.literal_eval(node.args[0]);self.assertEqual(actual,CURRENT);self.run_gate(actual)
 def test_historical_path_rejected(self):
  with self.assertRaisesRegex(Refusal,'image-guard-proof-path'):self.run_gate(HISTORICAL)
 def test_neighbor_paths_rejected(self):
  for path in (CURRENT+'.wrong',str(Path(CURRENT).parent/'OTHER.json')):
   with self.subTest(path=path):
    with self.assertRaisesRegex(Refusal,'image-guard-proof-path'):self.run_gate(path)
if __name__=='__main__':unittest.main()
