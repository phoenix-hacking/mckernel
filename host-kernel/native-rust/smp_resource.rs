// SPDX-License-Identifier: GPL-2.0
//! Allocation-free SMP resource ownership and transaction policy.
//!
//! This module contains no kernel bindings, allocation, FFI, or internal
//! synchronization.  It is a policy core for a future `ihk-smp-x86_64`
//! adapter.  The tables and their workspaces must be constructed in pinned,
//! off-stack backing.  The adapter must provide one audited sleepable outer
//! lock; no spin/irq-disabled guard may be held across Linux hotplug or page
//! ownership work.  This source models policy state only and makes no claim of
//! physical CPU, page, APIC, IRQ, or McKernel integration.
//!
//! CPU transactions enter an explicit pending state immediately.  Committing
//! installs the final state; explicit rollback or dropping an uncommitted
//! transaction restores every prior slot.  Memory mutations construct and
//! validate a fixed-capacity candidate map before external work starts and
//! before replacing live state.  Once external page effects are declared,
//! abandonment poisons the map until a future adapter reconciles physical
//! truth; only compensated rollback may safely discard the candidate.

/// Frozen legacy x86-64 SMP CPU ceiling.
pub(crate) const SMP_MAX_CPUS: usize = 512;
pub(crate) const OS_TOKEN_CAPACITY: u32 = 64;
pub(crate) const OS_TOKEN_MAX_GENERATION: u64 = (1_u64 << 41) - 1;
pub(crate) const X86_64_PAGE_SIZE: u64 = 4096;
/// The legacy userspace memory request granule is 4 MiB.  The future ABI
/// adapter must validate that coarser request contract; internal extents stay
/// page-granular because split legacy chunks can be only one page.
pub(crate) const USER_MEMORY_REQUEST_GRANULE: u64 = 4 * 1024 * 1024;

/// Resource-policy failures.  Errno translation belongs at the future ABI
/// adapter boundary rather than in this kernel-independent state machine.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ResourceError {
    InvalidCapacity,
    InvalidCpu,
    InvalidToken,
    EmptyRequest,
    RequestTooLarge,
    DuplicateCpu,
    DuplicateIkcSource,
    InvalidState,
    Ownership,
    IkcDestinationBusy,
    RangeInvalid,
    RangeUnavailable,
    Overlap,
    Capacity,
    OutputTooSmall { needed: usize },
    ArithmeticOverflow,
    ExternalEffectsPending,
    ExternalEffectsNotStarted,
    Poisoned,
    Corrupt,
}

/// An OS registry slot plus its bounded, non-zero incarnation.
///
/// Production code cannot mint this token.  Construction awaits a versioned
/// IHK-to-SMP lease ABI that proves the provider registry slot and generation;
/// until then this policy core intentionally cannot become Linux-reachable.
/// Reusing a registry slot must advance `generation`, so a token copied by an
/// old OS cannot release resources owned by its replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct OsToken {
    slot: u32,
    generation: u64,
}

impl OsToken {
    pub(crate) const fn slot(self) -> u32 {
        self.slot
    }

    pub(crate) const fn generation(self) -> u64 {
        self.generation
    }

    fn validate(self) -> Result<(), ResourceError> {
        if self.slot >= OS_TOKEN_CAPACITY
            || self.generation == 0
            || self.generation > OS_TOKEN_MAX_GENERATION
        {
            Err(ResourceError::InvalidToken)
        } else {
            Ok(())
        }
    }

    #[cfg(test)]
    pub(crate) fn test_only(slot: u32, generation: u64) -> Result<Self, ResourceError> {
        let token = Self { slot, generation };
        token.validate()?;
        Ok(token)
    }
}

/// Internal CPU lifecycle states.  Pending states are visible only while the
/// table is mutably borrowed by a `CpuTransaction`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum CpuState {
    Absent,
    Online,
    ReservePending,
    Available,
    AssignPending,
    Assigned,
    ReleasePending,
    OnlinePending,
    Quarantined,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CpuSlot {
    hardware_id: u32,
    numa_node: u32,
    state: CpuState,
    owner: Option<OsToken>,
    assignment_rank: Option<u16>,
}

impl CpuSlot {
    const EMPTY: Self = Self {
        hardware_id: u32::MAX,
        numa_node: u32::MAX,
        state: CpuState::Absent,
        owner: None,
        assignment_rank: None,
    };

    pub(crate) const fn hardware_id(self) -> u32 {
        self.hardware_id
    }

    pub(crate) const fn numa_node(self) -> u32 {
        self.numa_node
    }

    pub(crate) const fn state(self) -> CpuState {
        self.state
    }

    pub(crate) const fn owner(self) -> Option<OsToken> {
        self.owner
    }

    pub(crate) const fn assignment_rank(self) -> Option<u16> {
        self.assignment_rank
    }

    fn valid(self) -> bool {
        match self.state {
            CpuState::Absent => {
                self.hardware_id == u32::MAX
                    && self.numa_node == u32::MAX
                    && self.owner.is_none()
                    && self.assignment_rank.is_none()
            }
            CpuState::Online
            | CpuState::ReservePending
            | CpuState::Available
            | CpuState::OnlinePending => {
                self.hardware_id != u32::MAX
                    && self.numa_node != u32::MAX
                    && self.owner.is_none()
                    && self.assignment_rank.is_none()
            }
            CpuState::AssignPending | CpuState::Assigned | CpuState::ReleasePending => {
                self.hardware_id != u32::MAX
                    && self.numa_node != u32::MAX
                    && self.owner.is_some_and(|owner| owner.validate().is_ok())
                    && self.assignment_rank.is_some()
            }
            CpuState::Quarantined => {
                self.hardware_id != u32::MAX
                    && self.numa_node != u32::MAX
                    && self.owner.is_some() == self.assignment_rank.is_some()
                    && self.owner.is_none_or(|owner| owner.validate().is_ok())
            }
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum CpuOperation {
    Reserve,
    ReturnToHost,
    Assign,
    Release,
}

/// Caller-owned transaction workspace entry.  Future kernel wiring must place
/// the workspace in pinned/preallocated storage, never a 512-entry stack
/// local.
#[derive(Clone, Copy)]
pub(crate) struct CpuChange {
    cpu: usize,
    before: CpuSlot,
    pending: CpuSlot,
    after: CpuSlot,
}

impl CpuChange {
    pub(crate) const fn empty() -> Self {
        Self::EMPTY
    }

    const EMPTY: Self = Self {
        cpu: usize::MAX,
        before: CpuSlot::EMPTY,
        pending: CpuSlot::EMPTY,
        after: CpuSlot::EMPTY,
    };
}

/// Fixed-capacity CPU ownership and IKC map.
///
/// `N = 512` is too large for a kernel stack local.  Production integration
/// must construct this table in pinned, off-stack module storage.  All
/// mutation requires `&mut self`; the future adapter must provide a sleepable
/// outer lock compatible with hotplug operations.
pub(crate) struct CpuTable<const N: usize> {
    slots: [CpuSlot; N],
    ikc_destinations: [Option<usize>; N],
}

impl<const N: usize> CpuTable<N> {
    pub(crate) const fn new() -> Self {
        Self {
            slots: [CpuSlot::EMPTY; N],
            ikc_destinations: [None; N],
        }
    }

    pub(crate) const fn capacity(&self) -> usize {
        N
    }

    pub(crate) fn add_online_cpu(
        &mut self,
        cpu: usize,
        hardware_id: u32,
        numa_node: u32,
    ) -> Result<(), ResourceError> {
        self.validate_capacity()?;
        self.check_cpu(cpu)?;
        if hardware_id == u32::MAX || numa_node == u32::MAX {
            return Err(ResourceError::InvalidCpu);
        }
        if self.slots[cpu].state != CpuState::Absent {
            return Err(ResourceError::InvalidState);
        }
        if self
            .slots
            .iter()
            .any(|slot| slot.state != CpuState::Absent && slot.hardware_id == hardware_id)
        {
            return Err(ResourceError::InvalidCpu);
        }
        self.slots[cpu] = CpuSlot {
            hardware_id,
            numa_node,
            state: CpuState::Online,
            owner: None,
            assignment_rank: None,
        };
        Ok(())
    }

    pub(crate) fn slot(&self, cpu: usize) -> Result<CpuSlot, ResourceError> {
        self.check_cpu(cpu)?;
        Ok(self.slots[cpu])
    }

    pub(crate) fn count_state(&self, state: CpuState) -> usize {
        self.slots.iter().filter(|slot| slot.state == state).count()
    }

    pub(crate) fn prepare_reserve<'table, 'workspace>(
        &'table mut self,
        cpus: &[usize],
        workspace: &'workspace mut [CpuChange],
    ) -> Result<CpuTransaction<'table, 'workspace, N>, ResourceError> {
        self.prepare(CpuOperation::Reserve, None, cpus, workspace)
    }

    pub(crate) fn prepare_return_to_host<'table, 'workspace>(
        &'table mut self,
        cpus: &[usize],
        workspace: &'workspace mut [CpuChange],
    ) -> Result<CpuTransaction<'table, 'workspace, N>, ResourceError> {
        self.prepare(CpuOperation::ReturnToHost, None, cpus, workspace)
    }

    pub(crate) fn prepare_assign<'table, 'workspace>(
        &'table mut self,
        owner: OsToken,
        cpus: &[usize],
        workspace: &'workspace mut [CpuChange],
    ) -> Result<CpuTransaction<'table, 'workspace, N>, ResourceError> {
        owner.validate()?;
        self.prepare(CpuOperation::Assign, Some(owner), cpus, workspace)
    }

    pub(crate) fn prepare_release<'table, 'workspace>(
        &'table mut self,
        owner: OsToken,
        cpus: &[usize],
        workspace: &'workspace mut [CpuChange],
    ) -> Result<CpuTransaction<'table, 'workspace, N>, ResourceError> {
        owner.validate()?;
        self.prepare(CpuOperation::Release, Some(owner), cpus, workspace)
    }

    pub(crate) fn assigned_cpus(
        &self,
        owner: OsToken,
        output: &mut [usize],
    ) -> Result<usize, ResourceError> {
        owner.validate()?;
        self.ensure_owner_not_poisoned(owner)?;
        self.validate()?;
        let needed = self
            .slots
            .iter()
            .filter(|slot| slot.state == CpuState::Assigned && slot.owner == Some(owner))
            .count();
        if output.len() < needed {
            return Err(ResourceError::OutputTooSmall { needed });
        }
        for rank in 0..needed {
            let mut found = None;
            for (cpu, slot) in self.slots.iter().enumerate() {
                if slot.state == CpuState::Assigned
                    && slot.owner == Some(owner)
                    && slot.assignment_rank == Some(rank as u16)
                {
                    found = Some(cpu);
                    break;
                }
            }
            output[rank] = found.ok_or(ResourceError::Corrupt)?;
        }
        Ok(needed)
    }

    /// Replace mappings for the listed sources atomically.  Multiple sources
    /// may intentionally share one online Linux destination.  This core
    /// permits partial replacement; a future ABI adapter must explicitly
    /// choose optional-map compatibility or require complete coverage of every
    /// assigned source before calling this method.
    pub(crate) fn set_ikc_map(
        &mut self,
        owner: OsToken,
        pairs: &[IkcPair],
    ) -> Result<(), ResourceError> {
        owner.validate()?;
        self.ensure_owner_not_poisoned(owner)?;
        self.validate()?;
        if pairs.is_empty() {
            return Err(ResourceError::EmptyRequest);
        }
        if pairs.len() > N || pairs.len() > SMP_MAX_CPUS {
            return Err(ResourceError::RequestTooLarge);
        }
        for (position, pair) in pairs.iter().enumerate() {
            self.check_cpu(pair.source)?;
            self.check_cpu(pair.destination)?;
            if pairs[..position]
                .iter()
                .any(|prior| prior.source == pair.source)
            {
                return Err(ResourceError::DuplicateIkcSource);
            }
            let source = self.slots[pair.source];
            if source.state != CpuState::Assigned || source.owner != Some(owner) {
                return Err(ResourceError::Ownership);
            }
            if self.slots[pair.destination].state != CpuState::Online {
                return Err(ResourceError::InvalidState);
            }
        }
        for pair in pairs {
            self.ikc_destinations[pair.source] = Some(pair.destination);
        }
        Ok(())
    }

    pub(crate) fn clear_ikc_map(
        &mut self,
        owner: OsToken,
        sources: &[usize],
    ) -> Result<(), ResourceError> {
        owner.validate()?;
        self.ensure_owner_not_poisoned(owner)?;
        self.validate()?;
        self.validate_request(sources)?;
        for &source in sources {
            let slot = self.slots[source];
            if slot.state != CpuState::Assigned || slot.owner != Some(owner) {
                return Err(ResourceError::Ownership);
            }
        }
        for &source in sources {
            self.ikc_destinations[source] = None;
        }
        Ok(())
    }

    pub(crate) fn ikc_destination(
        &self,
        source: usize,
    ) -> Result<Option<usize>, ResourceError> {
        self.check_cpu(source)?;
        Ok(self.ikc_destinations[source])
    }

    pub(crate) fn ikc_pairs(
        &self,
        owner: OsToken,
        output: &mut [IkcPair],
    ) -> Result<usize, ResourceError> {
        owner.validate()?;
        self.ensure_owner_not_poisoned(owner)?;
        self.validate()?;
        let needed = self
            .slots
            .iter()
            .enumerate()
            .filter(|(source, slot)| {
                slot.state == CpuState::Assigned
                    && slot.owner == Some(owner)
                    && self.ikc_destinations[*source].is_some()
            })
            .count();
        if output.len() < needed {
            return Err(ResourceError::OutputTooSmall { needed });
        }
        let owner_cpu_count = self
            .slots
            .iter()
            .filter(|slot| slot.state == CpuState::Assigned && slot.owner == Some(owner))
            .count();
        let mut written = 0;
        for rank in 0..owner_cpu_count {
            for (source, slot) in self.slots.iter().enumerate() {
                if slot.state == CpuState::Assigned
                    && slot.owner == Some(owner)
                    && slot.assignment_rank == Some(rank as u16)
                {
                    if let Some(destination) = self.ikc_destinations[source] {
                        output[written] = IkcPair {
                            source,
                            destination,
                        };
                        written += 1;
                    }
                    break;
                }
            }
        }
        Ok(written)
    }

    pub(crate) fn validate(&self) -> Result<(), ResourceError> {
        self.validate_capacity()?;
        for (cpu, slot) in self.slots.iter().enumerate() {
            if !slot.valid() {
                return Err(ResourceError::Corrupt);
            }
            if slot.state != CpuState::Absent
                && self.slots[..cpu].iter().any(|prior| {
                    prior.state != CpuState::Absent && prior.hardware_id == slot.hardware_id
                })
            {
                return Err(ResourceError::Corrupt);
            }
            if let (Some(owner), Some(rank)) = (slot.owner, slot.assignment_rank) {
                let owner_cpu_count = self
                    .slots
                    .iter()
                    .filter(|candidate| {
                        candidate.owner == Some(owner)
                            && matches!(
                                candidate.state,
                                CpuState::AssignPending
                                    | CpuState::Assigned
                                    | CpuState::ReleasePending
                                    | CpuState::Quarantined
                            )
                    })
                    .count();
                if rank as usize >= owner_cpu_count
                    || self.slots[..cpu].iter().any(|prior| {
                        prior.owner == Some(owner) && prior.assignment_rank == Some(rank)
                    })
                {
                    return Err(ResourceError::Corrupt);
                }
            }
            if let Some(destination) = self.ikc_destinations[cpu] {
                if !matches!(
                    slot.state,
                    CpuState::Assigned | CpuState::ReleasePending | CpuState::Quarantined
                ) {
                    return Err(ResourceError::Corrupt);
                }
                self.check_cpu(destination)?;
                if self.slots[destination].state != CpuState::Online {
                    return Err(ResourceError::Corrupt);
                }
            }
        }
        Ok(())
    }

    fn prepare<'table, 'workspace>(
        &'table mut self,
        operation: CpuOperation,
        owner: Option<OsToken>,
        cpus: &[usize],
        workspace: &'workspace mut [CpuChange],
    ) -> Result<CpuTransaction<'table, 'workspace, N>, ResourceError> {
        self.validate()?;
        self.validate_request(cpus)?;
        if let Some(token) = owner {
            self.ensure_owner_not_poisoned(token)?;
        }
        if workspace.len() < cpus.len() {
            return Err(ResourceError::OutputTooSmall { needed: cpus.len() });
        }
        let assignment_base = if operation == CpuOperation::Assign {
            let token = owner.ok_or(ResourceError::InvalidToken)?;
            self.slots
                .iter()
                .filter(|slot| slot.state == CpuState::Assigned && slot.owner == Some(token))
                .count()
        } else {
            0
        };
        if assignment_base
            .checked_add(cpus.len())
            .ok_or(ResourceError::ArithmeticOverflow)?
            > SMP_MAX_CPUS
        {
            return Err(ResourceError::RequestTooLarge);
        }
        let changes = &mut workspace[..cpus.len()];
        for (position, &cpu) in cpus.iter().enumerate() {
            let before = self.slots[cpu];
            let (pending_state, after_state, pending_owner, after_owner, pending_rank, after_rank) =
                match operation {
                    CpuOperation::Reserve => {
                        if before.state != CpuState::Online || before.owner.is_some() {
                            return Err(ResourceError::InvalidState);
                        }
                        if self
                            .ikc_destinations
                            .iter()
                            .any(|destination| *destination == Some(cpu))
                        {
                            return Err(ResourceError::IkcDestinationBusy);
                        }
                        (
                            CpuState::ReservePending,
                            CpuState::Available,
                            None,
                            None,
                            None,
                            None,
                        )
                    }
                    CpuOperation::ReturnToHost => {
                        if before.state != CpuState::Available || before.owner.is_some() {
                            return Err(ResourceError::InvalidState);
                        }
                        (
                            CpuState::OnlinePending,
                            CpuState::Online,
                            None,
                            None,
                            None,
                            None,
                        )
                    }
                    CpuOperation::Assign => {
                        let token = owner.ok_or(ResourceError::InvalidToken)?;
                        if before.state != CpuState::Available || before.owner.is_some() {
                            return Err(ResourceError::InvalidState);
                        }
                        let rank = assignment_base + position;
                        (
                            CpuState::AssignPending,
                            CpuState::Assigned,
                            Some(token),
                            Some(token),
                            Some(rank as u16),
                            Some(rank as u16),
                        )
                    }
                    CpuOperation::Release => {
                        let token = owner.ok_or(ResourceError::InvalidToken)?;
                        if before.state != CpuState::Assigned {
                            return Err(ResourceError::InvalidState);
                        }
                        if before.owner != Some(token) {
                            return Err(ResourceError::Ownership);
                        }
                        (
                            CpuState::ReleasePending,
                            CpuState::Available,
                            Some(token),
                            None,
                            before.assignment_rank,
                            None,
                        )
                    }
                };
            changes[position] = CpuChange {
                cpu,
                before,
                pending: CpuSlot {
                    state: pending_state,
                    owner: pending_owner,
                    assignment_rank: pending_rank,
                    ..before
                },
                after: CpuSlot {
                    state: after_state,
                    owner: after_owner,
                    assignment_rank: after_rank,
                    ..before
                },
            };
        }
        for change in changes.iter() {
            self.slots[change.cpu] = change.pending;
        }
        Ok(CpuTransaction {
            table: self,
            operation,
            changes,
            active: true,
            external_effects_started: false,
            preflight_release_owner: None,
        })
    }

    fn validate_request(&self, cpus: &[usize]) -> Result<(), ResourceError> {
        if cpus.is_empty() {
            return Err(ResourceError::EmptyRequest);
        }
        if cpus.len() > N || cpus.len() > SMP_MAX_CPUS {
            return Err(ResourceError::RequestTooLarge);
        }
        for (position, &cpu) in cpus.iter().enumerate() {
            self.check_cpu(cpu)?;
            if cpus[..position].contains(&cpu) {
                return Err(ResourceError::DuplicateCpu);
            }
        }
        Ok(())
    }

    fn validate_capacity(&self) -> Result<(), ResourceError> {
        if N == 0 || N > SMP_MAX_CPUS {
            Err(ResourceError::InvalidCapacity)
        } else {
            Ok(())
        }
    }

    fn check_cpu(&self, cpu: usize) -> Result<(), ResourceError> {
        if cpu >= N || cpu >= SMP_MAX_CPUS {
            Err(ResourceError::InvalidCpu)
        } else {
            Ok(())
        }
    }

    fn ensure_owner_not_poisoned(&self, owner: OsToken) -> Result<(), ResourceError> {
        if self
            .slots
            .iter()
            .any(|slot| slot.state == CpuState::Quarantined && slot.owner == Some(owner))
        {
            Err(ResourceError::Poisoned)
        } else {
            Ok(())
        }
    }
}

/// A prepared CPU mutation.
///
/// Before external work starts, explicit rollback or `Drop` restores exact
/// policy state.  `begin_external_effects` performs every fallible commit
/// preflight and changes the drop contract: thereafter only
/// `compensated_rollback` may restore prior policy.  Dropping, or attempting an
/// ordinary rollback, quarantines every affected CPU because hardware truth is
/// unknown.
#[must_use = "a CPU transaction must commit, roll back, or quarantine"]
pub(crate) struct CpuTransaction<'table, 'workspace, const N: usize> {
    table: &'table mut CpuTable<N>,
    operation: CpuOperation,
    changes: &'workspace mut [CpuChange],
    active: bool,
    external_effects_started: bool,
    preflight_release_owner: Option<OsToken>,
}

impl<const N: usize> CpuTransaction<'_, '_, N> {
    pub(crate) const fn operation(&self) -> CpuOperation {
        self.operation
    }

    pub(crate) const fn len(&self) -> usize {
        self.changes.len()
    }

    pub(crate) const fn is_empty(&self) -> bool {
        self.changes.is_empty()
    }

    pub(crate) fn cpu_at(&self, position: usize) -> Option<usize> {
        if position < self.changes.len() {
            Some(self.changes[position].cpu)
        } else {
            None
        }
    }

    pub(crate) fn prepared_slot(&self, position: usize) -> Option<CpuSlot> {
        if position < self.changes.len() {
            Some(self.changes[position].pending)
        } else {
            None
        }
    }

    pub(crate) const fn external_effects_have_started(&self) -> bool {
        self.external_effects_started
    }

    /// Complete all fallible logical preflight before the adapter performs a
    /// hotplug, reset, or other external action.
    pub(crate) fn begin_external_effects(&mut self) -> Result<(), ResourceError> {
        if self.external_effects_started {
            return Err(ResourceError::ExternalEffectsPending);
        }
        self.preflight_release_owner = self.preflight_commit()?;
        self.external_effects_started = true;
        Ok(())
    }

    pub(crate) fn commit(mut self) -> Result<(), ResourceError> {
        if !self.external_effects_started {
            return Err(ResourceError::ExternalEffectsNotStarted);
        }
        // `begin_external_effects` completed every fallible check while policy
        // state was exclusively borrowed.  Do not introduce a failure edge
        // after the adapter may have changed hardware.
        let release_owner = self.preflight_release_owner;
        // No fallible operation is permitted below this point.
        for position in 0..self.changes.len() {
            let change = self.changes[position];
            self.table.slots[change.cpu] = change.after;
            if self.operation == CpuOperation::Release {
                self.table.ikc_destinations[change.cpu] = None;
            }
        }
        if self.operation == CpuOperation::Release {
            for slot in self.table.slots.iter_mut() {
                if slot.state != CpuState::Assigned || slot.owner != release_owner {
                    continue;
                }
                let Some(prior_rank) = slot.assignment_rank else {
                    continue;
                };
                let removed_before = self
                    .changes
                    .iter()
                    .filter(|change| {
                        change
                            .before
                            .assignment_rank
                            .is_some_and(|removed_rank| removed_rank < prior_rank)
                    })
                    .count();
                slot.assignment_rank = Some(prior_rank - removed_before as u16);
            }
        }
        self.active = false;
        Ok(())
    }

    /// Test-only logical commit with no physical CPU effects.
    #[cfg(test)]
    pub(crate) fn commit_policy_only(mut self) -> Result<(), ResourceError> {
        self.begin_external_effects()?;
        self.commit()
    }

    pub(crate) fn rollback(mut self) -> Result<(), ResourceError> {
        if self.external_effects_started {
            return Err(ResourceError::ExternalEffectsPending);
        }
        self.restore();
        Ok(())
    }

    /// Restore prior policy only after the adapter has successfully reversed
    /// every completed external action in reverse order.
    pub(crate) fn compensated_rollback(mut self) -> Result<(), ResourceError> {
        if !self.external_effects_started {
            return Err(ResourceError::ExternalEffectsNotStarted);
        }
        self.restore();
        Ok(())
    }

    fn preflight_commit(&self) -> Result<Option<OsToken>, ResourceError> {
        if self.changes.is_empty() {
            return Err(ResourceError::Corrupt);
        }
        for change in self.changes.iter() {
            if self.table.slots[change.cpu] != change.pending {
                return Err(ResourceError::Corrupt);
            }
            if self.operation == CpuOperation::Release
                && change.before.assignment_rank.is_none()
            {
                return Err(ResourceError::Corrupt);
            }
        }
        if self.operation == CpuOperation::Release {
            let owner = self.changes[0].before.owner;
            for slot in self.table.slots.iter() {
                if slot.state != CpuState::Assigned || slot.owner != owner {
                    continue;
                }
                let prior_rank = slot.assignment_rank.ok_or(ResourceError::Corrupt)?;
                let removed_before = self
                    .changes
                    .iter()
                    .filter(|change| {
                        change
                            .before
                            .assignment_rank
                            .is_some_and(|removed_rank| removed_rank < prior_rank)
                    })
                    .count();
                if removed_before > prior_rank as usize {
                    return Err(ResourceError::Corrupt);
                }
            }
            Ok(owner)
        } else {
            Ok(None)
        }
    }

    fn restore(&mut self) {
        if !self.active {
            return;
        }
        let mut position = self.changes.len();
        while position != 0 {
            position -= 1;
            let change = self.changes[position];
            self.table.slots[change.cpu] = change.before;
        }
        self.active = false;
    }

    fn quarantine(&mut self) {
        if !self.active {
            return;
        }
        for change in self.changes.iter() {
            self.table.slots[change.cpu] = CpuSlot {
                state: CpuState::Quarantined,
                ..change.pending
            };
        }
        self.active = false;
    }
}

impl<const N: usize> Drop for CpuTransaction<'_, '_, N> {
    fn drop(&mut self) {
        if self.external_effects_started {
            self.quarantine();
        } else {
            self.restore();
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct IkcPair {
    pub(crate) source: usize,
    pub(crate) destination: usize,
}

/// One half-open physical-memory extent `[start, start + length)`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MemoryExtent {
    start: u64,
    length: u64,
    numa_node: u32,
    owner: Option<OsToken>,
}

impl MemoryExtent {
    pub(crate) fn new(
        start: u64,
        length: u64,
        numa_node: u32,
        owner: Option<OsToken>,
    ) -> Result<Self, ResourceError> {
        if length == 0 || numa_node == u32::MAX {
            return Err(ResourceError::RangeInvalid);
        }
        if let Some(token) = owner {
            token.validate()?;
        }
        start
            .checked_add(length)
            .ok_or(ResourceError::ArithmeticOverflow)?;
        if start % X86_64_PAGE_SIZE != 0 || length % X86_64_PAGE_SIZE != 0 {
            return Err(ResourceError::RangeInvalid);
        }
        Ok(Self {
            start,
            length,
            numa_node,
            owner,
        })
    }

    pub(crate) const fn start(self) -> u64 {
        self.start
    }

    pub(crate) const fn length(self) -> u64 {
        self.length
    }

    pub(crate) const fn numa_node(self) -> u32 {
        self.numa_node
    }

    pub(crate) const fn owner(self) -> Option<OsToken> {
        self.owner
    }

    pub(crate) fn end(self) -> Result<u64, ResourceError> {
        self.start
            .checked_add(self.length)
            .ok_or(ResourceError::ArithmeticOverflow)
    }

    fn same_class(self, other: Self) -> bool {
        self.numa_node == other.numa_node && self.owner == other.owner
    }
}

/// Caller-owned staging for an atomic memory-map rebuild.
///
/// Kernel wiring must allocate and pin this backing slice outside the kernel
/// stack.  A workspace may be reused after success or failure; each operation
/// clears it before constructing a new candidate.
pub(crate) struct MemoryWorkspace<'storage> {
    extents: &'storage mut [Option<MemoryExtent>],
    length: usize,
}

impl<'storage> MemoryWorkspace<'storage> {
    pub(crate) fn new(
        extents: &'storage mut [Option<MemoryExtent>],
    ) -> Result<Self, ResourceError> {
        if extents.is_empty() {
            return Err(ResourceError::InvalidCapacity);
        }
        for extent in extents.iter_mut() {
            *extent = None;
        }
        Ok(Self { extents, length: 0 })
    }

    pub(crate) fn capacity(&self) -> usize {
        self.extents.len()
    }

    pub(crate) fn len(&self) -> usize {
        self.length
    }

    fn reset(&mut self) {
        for extent in self.extents.iter_mut() {
            *extent = None;
        }
        self.length = 0;
    }

    fn push_normalized(&mut self, extent: MemoryExtent) -> Result<(), ResourceError> {
        MemoryExtent::new(
            extent.start,
            extent.length,
            extent.numa_node,
            extent.owner,
        )?;
        if self.length != 0 {
            let previous = self.extents[self.length - 1].ok_or(ResourceError::Corrupt)?;
            let previous_end = previous.end()?;
            if previous_end > extent.start {
                return Err(ResourceError::Overlap);
            }
            if previous_end == extent.start && previous.same_class(extent) {
                let merged_length = previous
                    .length
                    .checked_add(extent.length)
                    .ok_or(ResourceError::ArithmeticOverflow)?;
                self.extents[self.length - 1] = Some(MemoryExtent::new(
                    previous.start,
                    merged_length,
                    previous.numa_node,
                    previous.owner,
                )?);
                return Ok(());
            }
        }
        if self.length >= self.extents.len() {
            return Err(ResourceError::Capacity);
        }
        self.extents[self.length] = Some(extent);
        self.length += 1;
        Ok(())
    }

    fn validate(&self) -> Result<(), ResourceError> {
        if self.length > self.extents.len() {
            return Err(ResourceError::Corrupt);
        }
        let mut previous: Option<MemoryExtent> = None;
        for (index, current) in self.extents.iter().copied().enumerate() {
            if index < self.length {
                let extent = current.ok_or(ResourceError::Corrupt)?;
                MemoryExtent::new(
                    extent.start,
                    extent.length,
                    extent.numa_node,
                    extent.owner,
                )?;
                if let Some(prior) = previous {
                    let prior_end = prior.end()?;
                    if prior_end > extent.start {
                        return Err(ResourceError::Overlap);
                    }
                    if prior_end == extent.start && prior.same_class(extent) {
                        return Err(ResourceError::Corrupt);
                    }
                }
                previous = Some(extent);
            } else if current.is_some() {
                return Err(ResourceError::Corrupt);
            }
        }
        Ok(())
    }
}

/// Sorted, canonical, fixed-capacity memory ownership map.  Production must
/// construct both this generic array and its workspace in pinned off-stack
/// storage; no small `N` is an implied production limit.
pub(crate) struct MemoryMap<const N: usize> {
    extents: [Option<MemoryExtent>; N],
    length: usize,
    poisoned: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum MemoryOperation {
    InsertFree,
    Assign,
    Release,
    ReleaseAll,
    RemoveFree,
}

/// A validated candidate memory map.  The live map remains unchanged until
/// `commit`.  Before external effects, rollback or `Drop` clears caller-owned
/// staging exactly.  After `begin_external_effects`, only a compensated
/// rollback is safe: ordinary rollback or `Drop` poisons the live map because
/// Linux page ownership may no longer match policy state.
#[must_use = "a memory transaction must commit, compensate, or poison the map"]
pub(crate) struct MemoryTransaction<
    'map,
    'workspace,
    'storage,
    const N: usize,
> {
    map: &'map mut MemoryMap<N>,
    workspace: &'workspace mut MemoryWorkspace<'storage>,
    operation: MemoryOperation,
    active: bool,
    external_effects_started: bool,
}

impl<const N: usize> MemoryTransaction<'_, '_, '_, N> {
    pub(crate) const fn operation(&self) -> MemoryOperation {
        self.operation
    }

    pub(crate) fn candidate_len(&self) -> usize {
        self.workspace.length
    }

    pub(crate) fn candidate_extent(&self, index: usize) -> Option<MemoryExtent> {
        if index < self.workspace.length {
            self.workspace.extents[index]
        } else {
            None
        }
    }

    pub(crate) fn live_len(&self) -> usize {
        self.map.length
    }

    pub(crate) fn live_extent(&self, index: usize) -> Option<MemoryExtent> {
        if index < self.map.length {
            self.map.extents[index]
        } else {
            None
        }
    }

    pub(crate) const fn external_effects_have_started(&self) -> bool {
        self.external_effects_started
    }

    /// Complete every fallible candidate/live-map check before the adapter
    /// acquires, transfers, or returns physical pages.
    pub(crate) fn begin_external_effects(&mut self) -> Result<(), ResourceError> {
        if self.external_effects_started {
            return Err(ResourceError::ExternalEffectsPending);
        }
        self.preflight_commit()?;
        self.external_effects_started = true;
        Ok(())
    }

    pub(crate) fn commit(mut self) -> Result<(), ResourceError> {
        if !self.external_effects_started {
            return Err(ResourceError::ExternalEffectsNotStarted);
        }
        // `begin_external_effects` performed every failure check while both
        // map and workspace were exclusively borrowed.  No fallible operation
        // is permitted below this point.
        for index in 0..N {
            self.map.extents[index] = if index < self.workspace.length {
                self.workspace.extents[index]
            } else {
                None
            };
        }
        self.map.length = self.workspace.length;
        self.workspace.reset();
        self.active = false;
        Ok(())
    }

    pub(crate) fn rollback(mut self) -> Result<(), ResourceError> {
        if self.external_effects_started {
            self.poison();
            return Err(ResourceError::ExternalEffectsPending);
        }
        self.discard();
        Ok(())
    }

    /// Discard the candidate after the adapter has reversed every completed
    /// physical-page operation.
    pub(crate) fn compensated_rollback(mut self) -> Result<(), ResourceError> {
        if !self.external_effects_started {
            return Err(ResourceError::ExternalEffectsNotStarted);
        }
        self.discard();
        Ok(())
    }

    fn preflight_commit(&self) -> Result<(), ResourceError> {
        self.map.validate()?;
        self.workspace.validate()?;
        if self.workspace.capacity() < N {
            return Err(ResourceError::OutputTooSmall { needed: N });
        }
        if self.workspace.length > N {
            return Err(ResourceError::Capacity);
        }
        Ok(())
    }

    fn discard(&mut self) {
        if self.active {
            self.workspace.reset();
            self.active = false;
        }
    }

    fn poison(&mut self) {
        if self.active {
            self.map.poisoned = true;
            self.workspace.reset();
            self.active = false;
        }
    }
}

impl<const N: usize> Drop for MemoryTransaction<'_, '_, '_, N> {
    fn drop(&mut self) {
        if self.external_effects_started {
            self.poison();
        } else {
            self.discard();
        }
    }
}

impl<const N: usize> MemoryMap<N> {
    pub(crate) const fn new() -> Self {
        Self {
            extents: [None; N],
            length: 0,
            poisoned: false,
        }
    }

    pub(crate) const fn capacity(&self) -> usize {
        N
    }

    pub(crate) const fn len(&self) -> usize {
        self.length
    }

    pub(crate) const fn is_empty(&self) -> bool {
        self.length == 0
    }

    /// A poisoned map may be inspected for diagnostics, but every validated
    /// query and mutation fails closed until a future adapter reconciles it.
    pub(crate) const fn is_poisoned(&self) -> bool {
        self.poisoned
    }

    pub(crate) fn extent(&self, index: usize) -> Option<MemoryExtent> {
        if index < self.length {
            self.extents[index]
        } else {
            None
        }
    }

    /// Prepare adding host-reserved memory to the free pool.  Adjacent free
    /// extents on the same NUMA node are canonicalized in staging.
    pub(crate) fn prepare_insert_free<'map, 'workspace, 'storage>(
        &'map mut self,
        start: u64,
        length: u64,
        numa_node: u32,
        workspace: &'workspace mut MemoryWorkspace<'storage>,
    ) -> Result<MemoryTransaction<'map, 'workspace, 'storage, N>, ResourceError> {
        self.validate()?;
        self.prepare_workspace(workspace)?;
        let inserted = MemoryExtent::new(start, length, numa_node, None)?;
        let mut emitted = false;
        for index in 0..self.length {
            let current = self.extents[index].ok_or(ResourceError::Corrupt)?;
            if !emitted && inserted.start <= current.start {
                workspace.push_normalized(inserted)?;
                emitted = true;
            }
            workspace.push_normalized(current)?;
        }
        if !emitted {
            workspace.push_normalized(inserted)?;
        }
        Self::validate_candidate(workspace)?;
        Ok(MemoryTransaction {
            map: self,
            workspace,
            operation: MemoryOperation::InsertFree,
            active: true,
            external_effects_started: false,
        })
    }

    /// Prepare transferring one free range to an OS.  The range must be wholly
    /// contained in one free extent; cross-NUMA assignment is rejected.
    pub(crate) fn prepare_assign<'map, 'workspace, 'storage>(
        &'map mut self,
        owner: OsToken,
        start: u64,
        length: u64,
        workspace: &'workspace mut MemoryWorkspace<'storage>,
    ) -> Result<MemoryTransaction<'map, 'workspace, 'storage, N>, ResourceError> {
        owner.validate()?;
        self.validate()?;
        let assigned = MemoryExtent::new(start, length, 0, Some(owner))?;
        let end = assigned.end()?;
        let target = self.find_containing(start, end, None)?;
        let container = self.extents[target].ok_or(ResourceError::Corrupt)?;
        let assigned = MemoryExtent::new(start, length, container.numa_node, Some(owner))?;
        self.build_replacement(
            target,
            container,
            start,
            end,
            Some(assigned),
            workspace,
        )?;
        Ok(MemoryTransaction {
            map: self,
            workspace,
            operation: MemoryOperation::Assign,
            active: true,
            external_effects_started: false,
        })
    }

    /// Prepare returning an exact owned subrange to the free pool.  Owner
    /// generation is part of the match.
    pub(crate) fn prepare_release<'map, 'workspace, 'storage>(
        &'map mut self,
        owner: OsToken,
        start: u64,
        length: u64,
        workspace: &'workspace mut MemoryWorkspace<'storage>,
    ) -> Result<MemoryTransaction<'map, 'workspace, 'storage, N>, ResourceError> {
        owner.validate()?;
        self.validate()?;
        let released = MemoryExtent::new(start, length, 0, Some(owner))?;
        let end = released.end()?;
        let target = self.find_containing(start, end, Some(owner))?;
        let container = self.extents[target].ok_or(ResourceError::Corrupt)?;
        let released = MemoryExtent::new(start, length, container.numa_node, None)?;
        self.build_replacement(
            target,
            container,
            start,
            end,
            Some(released),
            workspace,
        )?;
        Ok(MemoryTransaction {
            map: self,
            workspace,
            operation: MemoryOperation::Release,
            active: true,
            external_effects_started: false,
        })
    }

    pub(crate) fn prepare_release_all<'map, 'workspace, 'storage>(
        &'map mut self,
        owner: OsToken,
        workspace: &'workspace mut MemoryWorkspace<'storage>,
    ) -> Result<MemoryTransaction<'map, 'workspace, 'storage, N>, ResourceError> {
        owner.validate()?;
        self.validate()?;
        self.prepare_workspace(workspace)?;
        for index in 0..self.length {
            let mut extent = self.extents[index].ok_or(ResourceError::Corrupt)?;
            if extent.owner == Some(owner) {
                extent.owner = None;
            }
            workspace.push_normalized(extent)?;
        }
        Self::validate_candidate(workspace)?;
        Ok(MemoryTransaction {
            map: self,
            workspace,
            operation: MemoryOperation::ReleaseAll,
            active: true,
            external_effects_started: false,
        })
    }

    /// Prepare removing a free managed range so a future adapter can return
    /// its pages to Linux.  Owned bytes are never removable through this path.
    pub(crate) fn prepare_remove_free<'map, 'workspace, 'storage>(
        &'map mut self,
        start: u64,
        length: u64,
        workspace: &'workspace mut MemoryWorkspace<'storage>,
    ) -> Result<MemoryTransaction<'map, 'workspace, 'storage, N>, ResourceError> {
        self.validate()?;
        let removed = MemoryExtent::new(start, length, 0, None)?;
        let end = removed.end()?;
        let target = self.find_containing(start, end, None)?;
        let container = self.extents[target].ok_or(ResourceError::Corrupt)?;
        self.build_replacement(target, container, start, end, None, workspace)?;
        Ok(MemoryTransaction {
            map: self,
            workspace,
            operation: MemoryOperation::RemoveFree,
            active: true,
            external_effects_started: false,
        })
    }

    /// Test-only policy convenience with no physical page effects.
    #[cfg(test)]
    pub(crate) fn insert_free(
        &mut self,
        start: u64,
        length: u64,
        numa_node: u32,
        workspace: &mut MemoryWorkspace<'_>,
    ) -> Result<(), ResourceError> {
        let mut transaction = self.prepare_insert_free(start, length, numa_node, workspace)?;
        transaction.begin_external_effects()?;
        transaction.commit()
    }

    /// Test-only policy convenience with no physical page effects.
    #[cfg(test)]
    pub(crate) fn assign(
        &mut self,
        owner: OsToken,
        start: u64,
        length: u64,
        workspace: &mut MemoryWorkspace<'_>,
    ) -> Result<(), ResourceError> {
        let mut transaction = self.prepare_assign(owner, start, length, workspace)?;
        transaction.begin_external_effects()?;
        transaction.commit()
    }

    /// Test-only policy convenience with no physical page effects.
    #[cfg(test)]
    pub(crate) fn release(
        &mut self,
        owner: OsToken,
        start: u64,
        length: u64,
        workspace: &mut MemoryWorkspace<'_>,
    ) -> Result<(), ResourceError> {
        let mut transaction = self.prepare_release(owner, start, length, workspace)?;
        transaction.begin_external_effects()?;
        transaction.commit()
    }

    /// Test-only policy convenience with no physical page effects.
    #[cfg(test)]
    pub(crate) fn release_all(
        &mut self,
        owner: OsToken,
        workspace: &mut MemoryWorkspace<'_>,
    ) -> Result<(), ResourceError> {
        let mut transaction = self.prepare_release_all(owner, workspace)?;
        transaction.begin_external_effects()?;
        transaction.commit()
    }

    /// Test-only policy convenience with no physical page effects.
    #[cfg(test)]
    pub(crate) fn remove_free(
        &mut self,
        start: u64,
        length: u64,
        workspace: &mut MemoryWorkspace<'_>,
    ) -> Result<(), ResourceError> {
        let mut transaction = self.prepare_remove_free(start, length, workspace)?;
        transaction.begin_external_effects()?;
        transaction.commit()
    }

    pub(crate) fn owned_extents(
        &self,
        owner: OsToken,
        output: &mut [MemoryExtent],
    ) -> Result<usize, ResourceError> {
        owner.validate()?;
        self.validate()?;
        self.copy_matching(Some(owner), output)
    }

    pub(crate) fn free_extents(
        &self,
        output: &mut [MemoryExtent],
    ) -> Result<usize, ResourceError> {
        self.validate()?;
        self.copy_matching(None, output)
    }

    pub(crate) fn bytes_owned_by(&self, owner: OsToken) -> Result<u64, ResourceError> {
        owner.validate()?;
        self.validate()?;
        self.sum_matching(Some(owner))
    }

    pub(crate) fn free_bytes(&self) -> Result<u64, ResourceError> {
        self.validate()?;
        self.sum_matching(None)
    }

    pub(crate) fn validate(&self) -> Result<(), ResourceError> {
        if self.poisoned {
            return Err(ResourceError::Poisoned);
        }
        if N == 0 || self.length > N {
            return Err(ResourceError::InvalidCapacity);
        }
        let mut previous: Option<MemoryExtent> = None;
        for index in 0..N {
            let current = self.extents[index];
            if index < self.length {
                let extent = current.ok_or(ResourceError::Corrupt)?;
                MemoryExtent::new(
                    extent.start,
                    extent.length,
                    extent.numa_node,
                    extent.owner,
                )?;
                if let Some(prior) = previous {
                    let prior_end = prior.end()?;
                    if prior_end > extent.start {
                        return Err(ResourceError::Overlap);
                    }
                    if prior_end == extent.start && prior.same_class(extent) {
                        return Err(ResourceError::Corrupt);
                    }
                }
                previous = Some(extent);
            } else if current.is_some() {
                return Err(ResourceError::Corrupt);
            }
        }
        Ok(())
    }

    fn build_replacement(
        &self,
        target: usize,
        container: MemoryExtent,
        range_start: u64,
        range_end: u64,
        replacement: Option<MemoryExtent>,
        workspace: &mut MemoryWorkspace<'_>,
    ) -> Result<(), ResourceError> {
        let container_end = container.end()?;
        if range_start < container.start || range_end > container_end || range_start >= range_end {
            return Err(ResourceError::RangeUnavailable);
        }
        if let Some(extent) = replacement {
            if extent.start != range_start || extent.end()? != range_end {
                return Err(ResourceError::Corrupt);
            }
        }
        self.prepare_workspace(workspace)?;
        for index in 0..self.length {
            let current = self.extents[index].ok_or(ResourceError::Corrupt)?;
            if index != target {
                workspace.push_normalized(current)?;
                continue;
            }
            if range_start > container.start {
                workspace.push_normalized(MemoryExtent::new(
                    container.start,
                    range_start - container.start,
                    container.numa_node,
                    container.owner,
                )?)?;
            }
            if let Some(extent) = replacement {
                workspace.push_normalized(extent)?;
            }
            if range_end < container_end {
                workspace.push_normalized(MemoryExtent::new(
                    range_end,
                    container_end - range_end,
                    container.numa_node,
                    container.owner,
                )?)?;
            }
        }
        Self::validate_candidate(workspace)
    }

    fn find_containing(
        &self,
        start: u64,
        end: u64,
        owner: Option<OsToken>,
    ) -> Result<usize, ResourceError> {
        for index in 0..self.length {
            let extent = self.extents[index].ok_or(ResourceError::Corrupt)?;
            if extent.start <= start && end <= extent.end()? {
                return if extent.owner == owner {
                    Ok(index)
                } else {
                    Err(ResourceError::Ownership)
                };
            }
        }
        Err(ResourceError::RangeUnavailable)
    }

    fn prepare_workspace(
        &self,
        workspace: &mut MemoryWorkspace<'_>,
    ) -> Result<(), ResourceError> {
        if workspace.capacity() < N {
            return Err(ResourceError::OutputTooSmall { needed: N });
        }
        workspace.reset();
        Ok(())
    }

    fn validate_candidate(workspace: &MemoryWorkspace<'_>) -> Result<(), ResourceError> {
        workspace.validate()?;
        if workspace.length > N {
            return Err(ResourceError::Capacity);
        }
        Ok(())
    }

    fn copy_matching(
        &self,
        owner: Option<OsToken>,
        output: &mut [MemoryExtent],
    ) -> Result<usize, ResourceError> {
        let needed = self.extents[..self.length]
            .iter()
            .filter(|extent| extent.is_some_and(|value| value.owner == owner))
            .count();
        if output.len() < needed {
            return Err(ResourceError::OutputTooSmall { needed });
        }
        let mut written = 0;
        for extent in self.extents[..self.length].iter().flatten() {
            if extent.owner == owner {
                output[written] = *extent;
                written += 1;
            }
        }
        Ok(written)
    }

    fn sum_matching(&self, owner: Option<OsToken>) -> Result<u64, ResourceError> {
        let mut total = 0_u64;
        for extent in self.extents[..self.length].iter().flatten() {
            if extent.owner == owner {
                total = total
                    .checked_add(extent.length)
                    .ok_or(ResourceError::ArithmeticOverflow)?;
            }
        }
        Ok(total)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn token(slot: u32, generation: u64) -> OsToken {
        OsToken::test_only(slot, generation).unwrap()
    }

    fn table() -> CpuTable<8> {
        let mut table = CpuTable::new();
        for cpu in 0..8 {
            table
                .add_online_cpu(cpu, 0x20 + cpu as u32, (cpu / 4) as u32)
                .unwrap();
        }
        table
    }

    fn reserve(table: &mut CpuTable<8>, cpus: &[usize]) {
        let mut workspace = [CpuChange::empty(); 8];
        table
            .prepare_reserve(cpus, &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
    }

    fn assign(table: &mut CpuTable<8>, owner: OsToken, cpus: &[usize]) {
        let mut workspace = [CpuChange::empty(); 8];
        table
            .prepare_assign(owner, cpus, &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
    }

    #[test]
    fn test_only_tokens_enforce_canonical_slot_and_generation_bounds() {
        assert_eq!(OsToken::test_only(2, 0), Err(ResourceError::InvalidToken));
        assert_eq!(
            OsToken::test_only(OS_TOKEN_CAPACITY, 1),
            Err(ResourceError::InvalidToken)
        );
        assert_eq!(
            OsToken::test_only(1, OS_TOKEN_MAX_GENERATION + 1),
            Err(ResourceError::InvalidToken)
        );
        assert_eq!(token(2, 7).slot(), 2);
        assert_eq!(token(2, 7).generation(), 7);
        assert_eq!(token(3, OS_TOKEN_MAX_GENERATION).generation(), OS_TOKEN_MAX_GENERATION);
    }

    #[test]
    fn topology_rejects_bounds_sentinels_and_duplicate_hardware_ids() {
        let mut cpus = CpuTable::<2>::new();
        cpus.add_online_cpu(0, 7, 0).unwrap();
        assert_eq!(cpus.add_online_cpu(1, 7, 0), Err(ResourceError::InvalidCpu));
        assert_eq!(cpus.add_online_cpu(2, 8, 0), Err(ResourceError::InvalidCpu));
        assert_eq!(
            cpus.add_online_cpu(1, u32::MAX, 0),
            Err(ResourceError::InvalidCpu)
        );
        assert_eq!(CpuTable::<0>::new().validate(), Err(ResourceError::InvalidCapacity));
        assert_eq!(
            CpuTable::<513>::new().validate(),
            Err(ResourceError::InvalidCapacity)
        );
    }

    #[test]
    fn exact_512_cpu_boundary_is_usable_but_512_is_not_an_index() {
        let mut cpus = CpuTable::<SMP_MAX_CPUS>::new();
        cpus.add_online_cpu(511, 0x2ff, 0).unwrap();
        assert_eq!(cpus.slot(511).unwrap().hardware_id(), 0x2ff);
        assert_eq!(cpus.slot(512), Err(ResourceError::InvalidCpu));
        assert_eq!(
            cpus.add_online_cpu(512, 0x300, 0),
            Err(ResourceError::InvalidCpu)
        );
        let mut workspace = [CpuChange::empty(); 1];
        cpus
            .prepare_reserve(&[511], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        assert_eq!(cpus.slot(511).unwrap().state(), CpuState::Available);
    }

    #[test]
    fn reserve_commit_explicit_rollback_and_drop_are_exact() {
        let mut cpus = table();
        let mut workspace = [CpuChange::empty(); 8];
        {
            let transaction = cpus.prepare_reserve(&[1, 3], &mut workspace).unwrap();
            assert_eq!(transaction.operation(), CpuOperation::Reserve);
            assert_eq!(transaction.len(), 2);
            assert!(!transaction.is_empty());
            assert_eq!(transaction.cpu_at(0), Some(1));
            assert_eq!(transaction.cpu_at(2), None);
            assert_eq!(
                transaction.prepared_slot(1).unwrap().state(),
                CpuState::ReservePending
            );
            transaction.rollback().unwrap();
        }
        assert_eq!(cpus.slot(1).unwrap().state(), CpuState::Online);
        assert_eq!(cpus.slot(3).unwrap().state(), CpuState::Online);

        {
            let _automatic_abort = cpus.prepare_reserve(&[1, 3], &mut workspace).unwrap();
        }
        assert_eq!(cpus.slot(1).unwrap().state(), CpuState::Online);
        cpus
            .prepare_reserve(&[1, 3], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        assert_eq!(cpus.slot(1).unwrap().state(), CpuState::Available);
        assert_eq!(cpus.slot(3).unwrap().state(), CpuState::Available);
        cpus.validate().unwrap();
    }

    #[test]
    fn external_effects_require_compensation_or_quarantine() {
        let mut cpus = table();
        let mut workspace = [CpuChange::empty(); 8];
        {
            let mut transaction = cpus.prepare_reserve(&[1], &mut workspace).unwrap();
            transaction.begin_external_effects().unwrap();
            assert!(transaction.external_effects_have_started());
            transaction.compensated_rollback().unwrap();
        }
        assert_eq!(cpus.slot(1).unwrap().state(), CpuState::Online);

        let commit_without_effects = cpus
            .prepare_reserve(&[5], &mut workspace)
            .unwrap()
            .commit();
        assert_eq!(
            commit_without_effects,
            Err(ResourceError::ExternalEffectsNotStarted)
        );
        assert_eq!(cpus.slot(5).unwrap().state(), CpuState::Online);
        {
            let mut transaction = cpus.prepare_reserve(&[5], &mut workspace).unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.commit().unwrap();
        }
        assert_eq!(cpus.slot(5).unwrap().state(), CpuState::Available);

        let rollback_result = {
            let mut transaction = cpus.prepare_reserve(&[2], &mut workspace).unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.rollback()
        };
        assert_eq!(
            rollback_result,
            Err(ResourceError::ExternalEffectsPending)
        );
        assert_eq!(cpus.slot(2).unwrap().state(), CpuState::Quarantined);

        {
            let mut transaction = cpus.prepare_reserve(&[3], &mut workspace).unwrap();
            transaction.begin_external_effects().unwrap();
        }
        assert_eq!(cpus.slot(3).unwrap().state(), CpuState::Quarantined);

        let compensation_without_effects = cpus
            .prepare_reserve(&[4], &mut workspace)
            .unwrap()
            .compensated_rollback();
        assert_eq!(
            compensation_without_effects,
            Err(ResourceError::ExternalEffectsNotStarted)
        );
        assert_eq!(cpus.slot(4).unwrap().state(), CpuState::Online);

        let owner = token(20, 1);
        assign(&mut cpus, owner, &[5]);
        cpus.set_ikc_map(
            owner,
            &[IkcPair {
                source: 5,
                destination: 6,
            }],
        )
        .unwrap();
        {
            let mut transaction = cpus
                .prepare_release(owner, &[5], &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.compensated_rollback().unwrap();
        }
        assert_eq!(cpus.slot(5).unwrap().state(), CpuState::Assigned);
        assert_eq!(cpus.ikc_destination(5).unwrap(), Some(6));
        {
            let mut transaction = cpus
                .prepare_release(owner, &[5], &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
        }
        assert_eq!(cpus.slot(5).unwrap().state(), CpuState::Quarantined);
        assert_eq!(cpus.ikc_destination(5).unwrap(), Some(6));
        let mut output = [usize::MAX; 1];
        assert_eq!(
            cpus.assigned_cpus(owner, &mut output),
            Err(ResourceError::Poisoned)
        );
    }

    #[test]
    fn cpu_requests_are_preflighted_before_any_mutation() {
        let mut cpus = table();
        let mut workspace = [CpuChange::empty(); 8];
        let before = cpus.slot(1).unwrap();
        assert!(matches!(
            cpus.prepare_reserve(&[], &mut workspace),
            Err(ResourceError::EmptyRequest)
        ));
        assert!(matches!(
            cpus.prepare_reserve(&[1, 1], &mut workspace),
            Err(ResourceError::DuplicateCpu)
        ));
        assert!(matches!(
            cpus.prepare_reserve(&[1, 8], &mut workspace),
            Err(ResourceError::InvalidCpu)
        ));
        let mut short_workspace = [CpuChange::empty(); 1];
        assert!(matches!(
            cpus.prepare_reserve(&[1, 3], &mut short_workspace),
            Err(ResourceError::OutputTooSmall { needed: 2 })
        ));
        assert_eq!(cpus.slot(1).unwrap(), before);
        reserve(&mut cpus, &[2]);
        assert!(matches!(
            cpus.prepare_reserve(&[1, 2], &mut workspace),
            Err(ResourceError::InvalidState)
        ));
        assert_eq!(cpus.slot(1).unwrap(), before);
    }

    #[test]
    fn assign_release_and_return_require_exact_owner_and_state() {
        let first = token(1, 8);
        let stale = token(1, 7);
        let mut cpus = table();
        let mut workspace = [CpuChange::empty(); 8];
        reserve(&mut cpus, &[2, 4]);
        assign(&mut cpus, first, &[2, 4]);
        assert_eq!(cpus.slot(2).unwrap().owner(), Some(first));
        assert!(matches!(
            cpus.prepare_release(stale, &[2], &mut workspace),
            Err(ResourceError::Ownership)
        ));
        cpus
            .prepare_release(first, &[2], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        assert_eq!(cpus.slot(2).unwrap().state(), CpuState::Available);
        assert_eq!(cpus.slot(2).unwrap().owner(), None);
        cpus
            .prepare_return_to_host(&[2], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        assert_eq!(cpus.slot(2).unwrap().state(), CpuState::Online);
        assert!(matches!(
            cpus.prepare_assign(first, &[2], &mut workspace),
            Err(ResourceError::InvalidState)
        ));
    }

    #[test]
    fn assigned_cpu_query_preflights_output_and_preserves_order() {
        let owner = token(9, 1);
        let mut cpus = table();
        let mut workspace = [CpuChange::empty(); 8];
        reserve(&mut cpus, &[5, 1, 6]);
        assign(&mut cpus, owner, &[5, 1, 6]);
        let mut short = [usize::MAX; 2];
        assert_eq!(
            cpus.assigned_cpus(owner, &mut short),
            Err(ResourceError::OutputTooSmall { needed: 3 })
        );
        assert_eq!(short, [usize::MAX; 2]);
        let mut output = [usize::MAX; 3];
        assert_eq!(cpus.assigned_cpus(owner, &mut output).unwrap(), 3);
        assert_eq!(output, [5, 1, 6]);
        cpus
            .prepare_release(owner, &[1], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        let mut compacted = [usize::MAX; 2];
        assert_eq!(cpus.assigned_cpus(owner, &mut compacted).unwrap(), 2);
        assert_eq!(compacted, [5, 6]);
        assert_eq!(cpus.slot(5).unwrap().assignment_rank(), Some(0));
        assert_eq!(cpus.slot(6).unwrap().assignment_rank(), Some(1));
    }

    #[test]
    fn second_assignment_appends_rank_and_unordered_release_compacts() {
        let owner = token(9, 2);
        let mut cpus = table();
        reserve(&mut cpus, &[5, 1]);
        assign(&mut cpus, owner, &[5, 1]);
        reserve(&mut cpus, &[6, 2]);
        assign(&mut cpus, owner, &[6, 2]);

        let mut before = [usize::MAX; 4];
        assert_eq!(cpus.assigned_cpus(owner, &mut before).unwrap(), 4);
        assert_eq!(before, [5, 1, 6, 2]);

        let mut workspace = [CpuChange::empty(); 8];
        cpus
            .prepare_release(owner, &[6, 5], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        let mut after = [usize::MAX; 2];
        assert_eq!(cpus.assigned_cpus(owner, &mut after).unwrap(), 2);
        assert_eq!(after, [1, 2]);
        assert_eq!(cpus.slot(1).unwrap().assignment_rank(), Some(0));
        assert_eq!(cpus.slot(2).unwrap().assignment_rank(), Some(1));
    }

    #[test]
    fn assign_and_release_rollback_preserve_ranks_and_ikc() {
        let owner = token(12, 3);
        let mut cpus = table();
        reserve(&mut cpus, &[3, 4]);
        let mut workspace = [CpuChange::empty(); 8];
        {
            let _drop_rollback = cpus
                .prepare_assign(owner, &[3, 4], &mut workspace)
                .unwrap();
        }
        assert_eq!(cpus.slot(3).unwrap().state(), CpuState::Available);
        cpus
            .prepare_assign(owner, &[3, 4], &mut workspace)
            .unwrap()
            .rollback()
            .unwrap();
        assert_eq!(cpus.slot(4).unwrap().assignment_rank(), None);

        assign(&mut cpus, owner, &[3, 4]);
        cpus.set_ikc_map(
            owner,
            &[
                IkcPair {
                    source: 3,
                    destination: 6,
                },
                IkcPair {
                    source: 4,
                    destination: 7,
                },
            ],
        )
        .unwrap();
        {
            let _drop_rollback = cpus
                .prepare_release(owner, &[3], &mut workspace)
                .unwrap();
        }
        assert_eq!(cpus.slot(3).unwrap().assignment_rank(), Some(0));
        assert_eq!(cpus.ikc_destination(3).unwrap(), Some(6));
        cpus
            .prepare_release(owner, &[4], &mut workspace)
            .unwrap()
            .rollback()
            .unwrap();
        assert_eq!(cpus.slot(4).unwrap().assignment_rank(), Some(1));
        assert_eq!(cpus.ikc_destination(4).unwrap(), Some(7));
    }

    #[test]
    fn ikc_mapping_is_atomic_owned_and_blocks_destination_hotplug() {
        let owner = token(3, 4);
        let other = token(4, 1);
        let mut cpus = table();
        let mut workspace = [CpuChange::empty(); 8];
        reserve(&mut cpus, &[1, 2]);
        assign(&mut cpus, owner, &[1, 2]);
        cpus.set_ikc_map(
            owner,
            &[
                IkcPair {
                    source: 1,
                    destination: 6,
                },
                IkcPair {
                    source: 2,
                    destination: 6,
                },
            ],
        )
        .unwrap();
        assert_eq!(cpus.ikc_destination(1).unwrap(), Some(6));
        assert!(matches!(
            cpus.prepare_reserve(&[6], &mut workspace),
            Err(ResourceError::IkcDestinationBusy)
        ));

        assert_eq!(
            cpus.set_ikc_map(
                owner,
                &[
                    IkcPair {
                        source: 1,
                        destination: 7,
                    },
                    IkcPair {
                        source: 1,
                        destination: 6,
                    },
                ],
            ),
            Err(ResourceError::DuplicateIkcSource)
        );
        assert_eq!(cpus.ikc_destination(1).unwrap(), Some(6));
        assert_eq!(
            cpus.set_ikc_map(
                other,
                &[IkcPair {
                    source: 1,
                    destination: 7,
                }]
            ),
            Err(ResourceError::Ownership)
        );
        cpus
            .prepare_release(owner, &[1], &mut workspace)
            .unwrap()
            .commit_policy_only()
            .unwrap();
        assert_eq!(cpus.ikc_destination(1).unwrap(), None);
        cpus.clear_ikc_map(owner, &[2]).unwrap();
        assert_eq!(cpus.ikc_destination(2).unwrap(), None);
        cpus.validate().unwrap();
    }

    #[test]
    fn late_ikc_set_and_clear_failures_leave_every_mapping_unchanged() {
        let owner = token(3, 4);
        let other = token(4, 1);
        let mut cpus = table();
        reserve(&mut cpus, &[1, 2]);
        assign(&mut cpus, owner, &[1]);
        assign(&mut cpus, other, &[2]);
        cpus.set_ikc_map(
            owner,
            &[IkcPair {
                source: 1,
                destination: 6,
            }],
        )
        .unwrap();
        cpus.set_ikc_map(
            other,
            &[IkcPair {
                source: 2,
                destination: 7,
            }],
        )
        .unwrap();

        assert_eq!(
            cpus.set_ikc_map(
                owner,
                &[
                    IkcPair {
                        source: 1,
                        destination: 5,
                    },
                    IkcPair {
                        source: 2,
                        destination: 6,
                    },
                ],
            ),
            Err(ResourceError::Ownership)
        );
        assert_eq!(cpus.ikc_destination(1).unwrap(), Some(6));
        assert_eq!(cpus.ikc_destination(2).unwrap(), Some(7));
        assert_eq!(
            cpus.clear_ikc_map(owner, &[1, 2]),
            Err(ResourceError::Ownership)
        );
        assert_eq!(cpus.ikc_destination(1).unwrap(), Some(6));
        assert_eq!(cpus.ikc_destination(2).unwrap(), Some(7));
    }

    #[test]
    fn ikc_query_is_all_or_nothing() {
        let owner = token(3, 4);
        let mut cpus = table();
        reserve(&mut cpus, &[1, 2]);
        assign(&mut cpus, owner, &[1, 2]);
        cpus.set_ikc_map(
            owner,
            &[
                IkcPair {
                    source: 1,
                    destination: 6,
                },
                IkcPair {
                    source: 2,
                    destination: 7,
                },
            ],
        )
        .unwrap();
        let mut short = [IkcPair {
            source: usize::MAX,
            destination: usize::MAX,
        }];
        assert_eq!(
            cpus.ikc_pairs(owner, &mut short),
            Err(ResourceError::OutputTooSmall { needed: 2 })
        );
        assert_eq!(short[0].source, usize::MAX);
        let mut pairs = [IkcPair {
            source: usize::MAX,
            destination: usize::MAX,
        }; 2];
        assert_eq!(cpus.ikc_pairs(owner, &mut pairs).unwrap(), 2);
        assert_eq!(pairs[0].source, 1);
        assert_eq!(pairs[1].source, 2);
    }

    #[test]
    fn memory_transaction_visibility_drop_commit_and_remove_rollback() {
        let mut memory = MemoryMap::<6>::new();
        let mut staging = [None; 6];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        {
            let transaction = memory
                .prepare_insert_free(0x1000, 0x6000, 0, &mut workspace)
                .unwrap();
            assert_eq!(transaction.operation(), MemoryOperation::InsertFree);
            assert_eq!(transaction.live_len(), 0);
            assert_eq!(transaction.candidate_len(), 1);
            assert_eq!(transaction.candidate_extent(0).unwrap().length(), 0x6000);
        }
        assert!(memory.is_empty());

        {
            let mut transaction = memory
                .prepare_insert_free(0x1000, 0x6000, 0, &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.commit().unwrap();
        }
        assert_eq!(memory.len(), 1);
        {
            let transaction = memory
                .prepare_remove_free(0x2000, 0x1000, &mut workspace)
                .unwrap();
            assert_eq!(transaction.operation(), MemoryOperation::RemoveFree);
            assert_eq!(transaction.live_len(), 1);
            assert_eq!(transaction.live_extent(0).unwrap().length(), 0x6000);
            assert_eq!(transaction.candidate_len(), 2);
        }
        assert_eq!(memory.len(), 1);
        memory
            .prepare_remove_free(0x2000, 0x1000, &mut workspace)
            .unwrap()
            .rollback()
            .unwrap();
        assert_eq!(memory.len(), 1);
        {
            let mut transaction = memory
                .prepare_remove_free(0x2000, 0x1000, &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.commit().unwrap();
        }
        assert_eq!(memory.len(), 2);
        assert_eq!(memory.extent(0).unwrap().end().unwrap(), 0x2000);
        assert_eq!(memory.extent(1).unwrap().start(), 0x3000);
    }

    #[test]
    fn assign_release_and_release_all_are_true_two_phase_transactions() {
        let owner = token(6, 2);
        let mut memory = MemoryMap::<8>::new();
        let mut staging = [None; 8];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x1000, 0x8000, 0, &mut workspace)
            .unwrap();

        {
            let transaction = memory
                .prepare_assign(owner, 0x2000, 0x2000, &mut workspace)
                .unwrap();
            assert_eq!(transaction.operation(), MemoryOperation::Assign);
            assert_eq!(transaction.live_extent(0).unwrap().owner(), None);
            assert_eq!(transaction.candidate_len(), 3);
            transaction.rollback().unwrap();
        }
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0);
        {
            let mut transaction = memory
                .prepare_assign(owner, 0x2000, 0x2000, &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.commit().unwrap();
        }
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0x2000);
        assert!(matches!(
            memory.prepare_remove_free(0x2000, 0x1000, &mut workspace),
            Err(ResourceError::Ownership)
        ));
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0x2000);

        memory
            .prepare_release(owner, 0x2000, 0x1000, &mut workspace)
            .unwrap()
            .rollback()
            .unwrap();
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0x2000);
        {
            let mut transaction = memory
                .prepare_release(owner, 0x2000, 0x2000, &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.commit().unwrap();
        }
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0);

        memory
            .assign(owner, 0x1000, 0x1000, &mut workspace)
            .unwrap();
        memory
            .assign(owner, 0x4000, 0x1000, &mut workspace)
            .unwrap();
        {
            let transaction = memory
                .prepare_release_all(owner, &mut workspace)
                .unwrap();
            assert_eq!(transaction.operation(), MemoryOperation::ReleaseAll);
            assert_eq!(transaction.candidate_len(), 1);
        }
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0x2000);
        {
            let mut transaction = memory
                .prepare_release_all(owner, &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.commit().unwrap();
        }
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0);
        assert_eq!(memory.len(), 1);
    }

    #[test]
    fn memory_external_effects_require_commit_compensation_or_poison() {
        let owner = token(11, 4);
        let mut memory = MemoryMap::<6>::new();
        let mut staging = [None; 6];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x1000, 0x6000, 0, &mut workspace)
            .unwrap();

        let commit_without_effects = memory
            .prepare_assign(owner, 0x2000, 0x1000, &mut workspace)
            .unwrap()
            .commit();
        assert_eq!(
            commit_without_effects,
            Err(ResourceError::ExternalEffectsNotStarted)
        );
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0);

        {
            let mut transaction = memory
                .prepare_assign(owner, 0x2000, 0x1000, &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            assert!(transaction.external_effects_have_started());
            assert_eq!(
                transaction.begin_external_effects(),
                Err(ResourceError::ExternalEffectsPending)
            );
            transaction.compensated_rollback().unwrap();
        }
        assert!(!memory.is_poisoned());
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0);

        let rollback_after_effects = {
            let mut transaction = memory
                .prepare_assign(owner, 0x2000, 0x1000, &mut workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
            transaction.rollback()
        };
        assert_eq!(
            rollback_after_effects,
            Err(ResourceError::ExternalEffectsPending)
        );
        assert!(memory.is_poisoned());
        assert_eq!(memory.validate(), Err(ResourceError::Poisoned));
        assert_eq!(memory.bytes_owned_by(owner), Err(ResourceError::Poisoned));

        let mut dropped = MemoryMap::<4>::new();
        let mut dropped_staging = [None; 4];
        let mut dropped_workspace = MemoryWorkspace::new(&mut dropped_staging).unwrap();
        dropped
            .insert_free(0x8000, 0x4000, 0, &mut dropped_workspace)
            .unwrap();
        {
            let mut transaction = dropped
                .prepare_remove_free(0x8000, 0x1000, &mut dropped_workspace)
                .unwrap();
            transaction.begin_external_effects().unwrap();
        }
        assert!(dropped.is_poisoned());
        assert_eq!(dropped.free_bytes(), Err(ResourceError::Poisoned));
    }

    #[test]
    fn memory_insert_is_sorted_coalesced_and_overlap_safe() {
        let mut memory = MemoryMap::<6>::new();
        let mut staging = [None; 6];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x3000, 0x1000, 0, &mut workspace)
            .unwrap();
        memory
            .insert_free(0x1000, 0x1000, 0, &mut workspace)
            .unwrap();
        memory
            .insert_free(0x2000, 0x1000, 0, &mut workspace)
            .unwrap();
        assert_eq!(memory.len(), 1);
        assert_eq!(memory.extent(0).unwrap().start(), 0x1000);
        assert_eq!(memory.extent(0).unwrap().length(), 0x3000);
        assert_eq!(
            memory.insert_free(0x2000, 0x1000, 0, &mut workspace),
            Err(ResourceError::Overlap)
        );
        assert_eq!(memory.len(), 1);
        assert_eq!(memory.free_bytes().unwrap(), 0x3000);

        memory
            .insert_free(0x4000, 0x1000, 1, &mut workspace)
            .unwrap();
        assert_eq!(memory.len(), 2);
        assert_eq!(memory.extent(1).unwrap().numa_node(), 1);
    }

    #[test]
    fn memory_assign_split_release_and_neighbor_coalesce() {
        let owner = token(1, 1);
        let mut memory = MemoryMap::<8>::new();
        let mut staging = [None; 8];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x1000, 0x8000, 2, &mut workspace)
            .unwrap();
        memory
            .assign(owner, 0x3000, 0x2000, &mut workspace)
            .unwrap();
        assert_eq!(memory.len(), 3);
        assert_eq!(memory.extent(0).unwrap().owner(), None);
        assert_eq!(memory.extent(1).unwrap().owner(), Some(owner));
        assert_eq!(memory.extent(1).unwrap().numa_node(), 2);
        assert_eq!(memory.extent(2).unwrap().owner(), None);
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0x2000);
        assert_eq!(memory.free_bytes().unwrap(), 0x6000);

        memory
            .release(owner, 0x3000, 0x2000, &mut workspace)
            .unwrap();
        assert_eq!(memory.len(), 1);
        assert_eq!(memory.extent(0).unwrap().start(), 0x1000);
        assert_eq!(memory.extent(0).unwrap().length(), 0x8000);
        memory.validate().unwrap();
    }

    #[test]
    fn partial_memory_release_preserves_owned_edges() {
        let owner = token(2, 3);
        let mut memory = MemoryMap::<8>::new();
        let mut staging = [None; 8];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x10_0000, 0x10_0000, 0, &mut workspace)
            .unwrap();
        memory
            .assign(owner, 0x10_0000, 0x10_0000, &mut workspace)
            .unwrap();
        memory
            .release(owner, 0x14_0000, 0x20_000, &mut workspace)
            .unwrap();
        assert_eq!(memory.len(), 3);
        assert_eq!(memory.extent(0).unwrap().owner(), Some(owner));
        assert_eq!(memory.extent(1).unwrap().owner(), None);
        assert_eq!(memory.extent(2).unwrap().owner(), Some(owner));
        assert_eq!(memory.bytes_owned_by(owner).unwrap(), 0xe_0000);
        assert_eq!(memory.free_bytes().unwrap(), 0x2_0000);
    }

    #[test]
    fn memory_capacity_failure_is_atomic() {
        let owner = token(1, 1);
        let mut memory = MemoryMap::<2>::new();
        let mut staging = [None; 2];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x1000, 0x5000, 0, &mut workspace)
            .unwrap();
        assert_eq!(
            memory.assign(owner, 0x2000, 0x1000, &mut workspace),
            Err(ResourceError::Capacity)
        );
        assert_eq!(memory.len(), 1);
        assert_eq!(memory.extent(0).unwrap().start(), 0x1000);
        assert_eq!(memory.extent(0).unwrap().length(), 0x5000);
        assert_eq!(memory.extent(0).unwrap().owner(), None);
        memory
            .assign(owner, 0x1000, 0x5000, &mut workspace)
            .unwrap();
        assert_eq!(memory.len(), 1);
        assert_eq!(memory.extent(0).unwrap().owner(), Some(owner));
    }

    #[test]
    fn undersized_memory_workspace_is_rejected_before_live_mutation() {
        let owner = token(1, 1);
        let mut memory = MemoryMap::<4>::new();
        let mut short_staging = [None; 3];
        let mut short = MemoryWorkspace::new(&mut short_staging).unwrap();
        assert_eq!(short.capacity(), 3);
        assert_eq!(short.len(), 0);
        assert_eq!(
            memory.insert_free(0x1000, 0x4000, 0, &mut short),
            Err(ResourceError::OutputTooSmall { needed: 4 })
        );
        assert!(memory.is_empty());

        let mut full_staging = [None; 4];
        let mut full = MemoryWorkspace::new(&mut full_staging).unwrap();
        memory
            .insert_free(0x1000, 0x4000, 0, &mut full)
            .unwrap();
        assert_eq!(
            memory.assign(owner, 0x2000, 0x1000, &mut short),
            Err(ResourceError::OutputTooSmall { needed: 4 })
        );
        assert_eq!(memory.len(), 1);
        assert_eq!(memory.extent(0).unwrap().owner(), None);
        assert_eq!(memory.extent(0).unwrap().length(), 0x4000);
    }

    #[test]
    fn memory_generation_and_owner_checks_fail_closed() {
        let current = token(4, 9);
        let stale = token(4, 8);
        let foreign = token(5, 1);
        let mut memory = MemoryMap::<6>::new();
        let mut staging = [None; 6];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x1000, 0x4000, 0, &mut workspace)
            .unwrap();
        memory
            .assign(current, 0x1000, 0x2000, &mut workspace)
            .unwrap();
        assert_eq!(
            memory.release(stale, 0x1000, 0x1000, &mut workspace),
            Err(ResourceError::Ownership)
        );
        assert_eq!(
            memory.release(foreign, 0x1000, 0x1000, &mut workspace),
            Err(ResourceError::Ownership)
        );
        assert_eq!(memory.bytes_owned_by(current).unwrap(), 0x2000);
        memory.release_all(stale, &mut workspace).unwrap();
        assert_eq!(memory.bytes_owned_by(current).unwrap(), 0x2000);
        memory.release_all(current, &mut workspace).unwrap();
        assert_eq!(memory.bytes_owned_by(current).unwrap(), 0);
        assert_eq!(memory.len(), 1);
    }

    #[test]
    fn memory_ranges_reject_zero_overflow_and_cross_extent_assignment() {
        let owner = token(1, 1);
        let mut memory = MemoryMap::<6>::new();
        let mut staging = [None; 6];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        assert_eq!(
            memory.insert_free(0x1000, 0, 0, &mut workspace),
            Err(ResourceError::RangeInvalid)
        );
        assert_eq!(X86_64_PAGE_SIZE, 4096);
        assert_eq!(USER_MEMORY_REQUEST_GRANULE, 4 * 1024 * 1024);
        assert_eq!(
            memory.insert_free(0x1800, 0x1000, 0, &mut workspace),
            Err(ResourceError::RangeInvalid)
        );
        assert_eq!(
            memory.insert_free(0x1000, 0x1800, 0, &mut workspace),
            Err(ResourceError::RangeInvalid)
        );
        assert_eq!(
            memory.insert_free(
                u64::MAX - (X86_64_PAGE_SIZE - 1),
                X86_64_PAGE_SIZE,
                0,
                &mut workspace,
            ),
            Err(ResourceError::ArithmeticOverflow)
        );
        memory
            .insert_free(0x1000, 0x1000, 0, &mut workspace)
            .unwrap();
        memory
            .insert_free(0x2000, 0x1000, 1, &mut workspace)
            .unwrap();
        assert_eq!(
            memory.assign(owner, 0x1000, 0x2000, &mut workspace),
            Err(ResourceError::RangeUnavailable)
        );
        assert_eq!(memory.free_bytes().unwrap(), 0x2000);
    }

    #[test]
    fn memory_queries_preflight_output_without_partial_copy() {
        let owner = token(8, 2);
        let mut memory = MemoryMap::<8>::new();
        let mut staging = [None; 8];
        let mut workspace = MemoryWorkspace::new(&mut staging).unwrap();
        memory
            .insert_free(0x1000, 0x6000, 0, &mut workspace)
            .unwrap();
        memory
            .assign(owner, 0x2000, 0x1000, &mut workspace)
            .unwrap();
        memory
            .assign(owner, 0x5000, 0x1000, &mut workspace)
            .unwrap();
        let sentinel = MemoryExtent::new(0xa000, 0x1000, 9, None).unwrap();
        let mut short = [sentinel];
        assert_eq!(
            memory.owned_extents(owner, &mut short),
            Err(ResourceError::OutputTooSmall { needed: 2 })
        );
        assert_eq!(short, [sentinel]);
        let mut owned = [sentinel; 2];
        assert_eq!(memory.owned_extents(owner, &mut owned).unwrap(), 2);
        assert_eq!(owned[0].start(), 0x2000);
        assert_eq!(owned[1].start(), 0x5000);
        let mut free = [sentinel; 3];
        assert_eq!(memory.free_extents(&mut free).unwrap(), 3);
    }
}
