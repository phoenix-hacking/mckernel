"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse exact TEST_ONLY positive14-command/result oracle; no live effects or Actual.
"""
from pathlib import Path
import ast,hashlib,importlib.util
D=Path(__file__).resolve().parent
TEST_SOURCE_SHA='43d69380f844f432d0685c62a5b18a05bdfec5211830dd3af4fb01d212dcfe01'

def build_result_fixture(directory):
 """Write hypothetical TEST_ONLY captures beneath caller's existing fresh temp dir.
 Return (result, frozen_bindings); no guard, lock, subprocess or Docker is invoked.
 """
 path=D/'test_retirement_executor.py';raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==TEST_SOURCE_SHA
 spec=importlib.util.spec_from_file_location('BFD_TEST_ONLY_SHARED_ORACLE',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 cls=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='ReleaseAndConsumer')
 node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='test_success_result_still_requires_parent_join_and_fresh_current')
 context=node.body[0];assert isinstance(context,ast.With)
 statements=[]
 for statement in context.body:
  if isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call) and isinstance(statement.value.func,ast.Attribute) and isinstance(statement.value.func.value,ast.Name) and statement.value.func.value.id=='self':break
  statements.append(statement)
 namespace=dict(vars(module));namespace['tmp']=str(directory)
 exec(compile(ast.Module(body=statements,type_ignores=[]),str(path),'exec'),namespace)
 value=namespace['value'];assert value['TEST_ONLY'] is True
 return value,namespace['B']
