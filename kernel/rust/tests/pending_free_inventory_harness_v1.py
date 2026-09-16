#!/usr/bin/env python3
"""Cheap source checks only: compiler, subprocess, and runtime are disabled."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[3]
RS=ROOT/'kernel/rust/tests/pending_free_inventory_vectors_v1.rs'; C=ROOT/'kernel/rust/tests/pending_free_inventory_reference_v1.c'; MODEL=ROOT/'kernel/rust/tests/pending_free_inventory_v1.rs'
REQUIRED=("capacity-zero","capacity-exact","capacity-exceeded","count-mismatch","count-overflow","duplicate-id","foreign-id","null-link","dangling-link","one-sided-link","malformed-sentinel","foreign-cycle","wrong-mode","invalid-page-count","page-count-overflow","misaligned-extent","foreign-extent","overlapping-extent","stale-generation","concurrent-mutation","valid-single","valid-two")
def main():
 model,rust,c=MODEL.read_text(),RS.read_text(),C.read_text()
 for x in ("DescriptorId","DescriptorRecord","DescriptorArena<'a>","&'a mut [DescriptorRecord]","resolve","checked_mul","checked_add","ValidatedInventory<'a>","Result<ValidatedInventory","pub fn validate(self)","sentinel","next.prev","prev.next"):assert x in model,x
 assert '#[derive(Clone, Copy' not in model and 'callback' not in model and 'release' not in model
 assert 'pub fn case(name:&str)' in rust
 rn=re.findall(r'name:\"([^\"]+)\"',rust);cn=re.findall(r'\("([^\"]+)"',c)
 assert rn==list(REQUIRED),(rn,cn);assert cn==list(REQUIRED),(cn,REQUIRED)
 for x in ('static int validate','resolve(c','construct_cases','overlap','__builtin_add_overflow'):assert x in c,x
 print('PASS_SOURCE_INVENTORY_STRUCTURE|vectors=22|constructors=rust,c|compile=disabled|runtime=disabled|equivalence=unclaimed')
if __name__=='__main__':main()
