# Native lifecycle raw matrix inventory draft 1

Date: 2026-09-15
Task: `M02-C-lifecycle-raw-matrix-inventory`
Disposition: `MATRIX_INVENTORY_DRAFT_ONLY`

This independent normalization follows the passing nine-case raw mechanism. It
does not freeze or materialize the full matrix.

The final `RAW_REQUIRED` must retain the nine mechanism names and independently
cover: JSON truncation/root type; top-level missing/unknown fields and exact scalar
types; vector/name/coverage/seed/operations shape and uniqueness; operation arity,
name and contiguous IDs; pool field/name/argument/placeholder/cycle/unused/depth/
expanded-budget boundaries; every applicable numeric lower/upper/type boundary;
every full-key component's required zero, negative, u64 overflow, boolean,
fractional and nonnumber cases; subject/domain/parent shapes; and unused arguments.
No narrower OS-slot bound is frozen; the common u64 representation bound still
applies and no smaller limit may be invented.

Schema-valid ownership, identity, lifecycle, status and capacity failures remain
ordinary model vectors. Add explicit ordinary precedence vectors for parent before
capacity, identity before capacity and capacity before lifecycle. Forged authority
needs exact unused/extra/unknown input mutations or a separate model API test; an
unknown field alone is not an ownership proof.

Positive decoder inventory must cover 1/128 operations, exact input-byte limit and
whitespace, numeric minima/maxima, allocated TID zero, domain-valid keys, exact
capacities, pool arity/dependency and accepted depth/budget boundaries. Expected-
document/row/event/control and malformed model-output cases belong to oracle tests,
not raw input rejection. Artifact metadata/path/cleanup remains a third harness
test category.

Before `RAW_FULL_MATRIX_FROZEN=true`, every expanded name must bind exact bytes and
an intended first failure; harness and test inventories must reconcile; positive
boundaries and depth/budget rules must be independently reviewed. No source,
execution, whole-corpus or acceptance credit follows.
