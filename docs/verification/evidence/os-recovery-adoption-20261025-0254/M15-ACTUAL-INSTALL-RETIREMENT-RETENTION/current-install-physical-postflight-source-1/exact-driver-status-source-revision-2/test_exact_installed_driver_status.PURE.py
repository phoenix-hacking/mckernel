"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure actual-receipt expressions only; no root reader import/entry/execution.
"""
from pathlib import Path
import ast,json,copy,unittest
SOURCE=Path(__file__).with_name('readonly_installed_consumer_current_proc.py')
class ExactDriverStatus(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(SOURCE.read_text());manifest=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MANIFEST' for t in n.targets));self.inputs=json.loads(Path(manifest['path']).read_bytes());self.v=json.loads(Path(self.inputs['receipt']['path']).read_bytes());self.driver=copy.deepcopy(self.v['driver_receipt'])
  calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need']
  self.status=next(n.args[0] for n in calls if len(n.args)>1 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='actual four install/loader command results')
  self.command=next(n.args[0] for n in calls if len(n.args)>1 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='actual four inner command births/joins')
 def check(self,driver):
  self.assertTrue(eval(compile(ast.Expression(self.status),'<exact-driver-predicate>','eval'),{'v':dict(self.v,driver_receipt=driver),'driver':driver}))
  for row in driver['commands']:self.assertTrue(eval(compile(ast.Expression(self.command),'<actual-four-command-joins>','eval'),{'z':row['result']}))
 def test_actual_typed_receipt(self):self.check(self.driver)
 def test_wrong_statuses(self):
  for status in ('PASS','PASS_SELECTED_SDK_FOUR_INSTALL_THREE_LOADER_ONLY_extra','FAIL',''):
   with self.subTest(status=status):
    d=copy.deepcopy(self.driver);d['status']=status
    with self.assertRaises(AssertionError):self.check(d)
 def test_changed_four_command_count(self):
  for count in (0,3,5):
   d=copy.deepcopy(self.driver);d['commands']=(d['commands']*2)[:count]
   with self.subTest(count=count):
    with self.assertRaises(AssertionError):self.check(d)
 def test_each_command_failed_result(self):
  for i in range(4):
   for key,value in [('returncode',1),('group_absent',False),('start',0)]:
    with self.subTest(command=i,key=key):
     d=copy.deepcopy(self.driver);d['commands'][i]['result'][key]=value
     with self.assertRaises(AssertionError):self.check(d)
if __name__=='__main__':unittest.main()
