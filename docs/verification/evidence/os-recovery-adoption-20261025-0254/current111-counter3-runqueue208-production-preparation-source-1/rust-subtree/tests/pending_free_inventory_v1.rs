//! Finite private model only. It imports no production memory or list code.
#[path = "pending_free_inventory_vectors_v1.rs"] mod vectors;

pub const MAX: usize = 8;
pub const PAGE: u64 = 4096;
pub const OK: i32 = 0;
pub const EINVAL: i32 = -22;
pub const EOVERFLOW: i32 = -75;
pub const ENOSPC: i32 = -28;
pub type DescriptorId = u64;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DescriptorRecord {
    pub id: DescriptorId, pub physical_start: u64, pub page_count: u64,
    pub generation: u32, pub mode: u8, pub next: DescriptorId, pub prev: DescriptorId,
}

/// The exclusive input borrow makes fixture validation read-only by construction.
pub struct DescriptorArena<'a> {
    records: &'a mut [DescriptorRecord], sentinel: DescriptorId, generation: u32,
    physical_base: u64, physical_limit: u64, mutation_epoch: u64,
}
impl<'a> DescriptorArena<'a> {
    pub fn new(records: &'a mut [DescriptorRecord], sentinel: DescriptorId, generation: u32,
               physical_base: u64, physical_limit: u64, mutation_epoch: u64) -> Result<Self, i32> {
        if records.len() < 2 || records.len() > MAX || sentinel == 0 ||
           physical_base % PAGE != 0 || physical_limit % PAGE != 0 || physical_base >= physical_limit {
            return Err(EINVAL);
        }
        let mut sentinel_count = 0usize;
        for (index, record) in records.iter().enumerate() {
            if record.id == 0 { return Err(EINVAL); }
            if record.id == sentinel { sentinel_count += 1; }
            for prior in records[..index].iter() { if prior.id == record.id { return Err(EINVAL); } }
        }
        if sentinel_count != 1 { return Err(EINVAL); }
        Ok(Self { records, sentinel, generation, physical_base, physical_limit, mutation_epoch })
    }
    pub fn sentinel(&self) -> DescriptorId { self.sentinel }
    pub fn generation(&self) -> u32 { self.generation }
    pub fn count(&self) -> usize { self.records.len() }
    /// Identity lookup precedes every descriptor-field inspection.
    pub fn resolve(&self, id: DescriptorId) -> Option<&DescriptorRecord> {
        self.records.iter().find(|record| record.id == id)
    }
    fn contains(&self, id: DescriptorId) -> bool { self.resolve(id).is_some() }
}

pub struct InventoryBuilder<'a> { arena: &'a DescriptorArena<'a>, ids: [DescriptorId; MAX], count: usize, reserved: usize }
impl<'a> InventoryBuilder<'a> {
    pub fn reserve(arena: &'a DescriptorArena<'a>, reserved: usize) -> Result<Self, i32> {
        if reserved > MAX || reserved >= arena.count() { return Err(ENOSPC); }
        Ok(Self { arena, ids: [0; MAX], count: 0, reserved })
    }
    pub fn push(&mut self, id: DescriptorId) -> i32 {
        if self.count >= self.reserved { return ENOSPC; }
        if id == 0 || id == self.arena.sentinel() || !self.arena.contains(id) || self.ids[..self.count].contains(&id) { return EINVAL; }
        self.ids[self.count] = id; self.count += 1; OK
    }
    pub fn freeze(self) -> FrozenInventory<'a> {
        FrozenInventory { arena: self.arena, ids: self.ids, selected: self.count, claimed_count: self.count as u64, observed_epoch: self.arena.mutation_epoch }
    }
    /// Fixture-only malformed-count constructor; it never touches the arena.
    pub fn freeze_claimed(self, claimed_count: u64) -> FrozenInventory<'a> {
        FrozenInventory { arena: self.arena, ids: self.ids, selected: self.count, claimed_count, observed_epoch: self.arena.mutation_epoch }
    }
}
pub struct FrozenInventory<'a> { arena: &'a DescriptorArena<'a>, ids: [DescriptorId; MAX], selected: usize, claimed_count: u64, observed_epoch: u64 }
pub struct ValidatedInventory<'a> { arena: &'a DescriptorArena<'a>, ids: [DescriptorId; MAX], count: usize }
impl<'a> FrozenInventory<'a> {
    pub fn validate(self) -> Result<ValidatedInventory<'a>, i32> {
        if self.observed_epoch != self.arena.mutation_epoch { return Err(EINVAL); }
        let count = usize::try_from(self.claimed_count).map_err(|_| EOVERFLOW)?;
        let count_plus_sentinel = count.checked_add(1).ok_or(EOVERFLOW)?;
        if count == 0 || count != self.selected || count > MAX { return Err(EINVAL); }
        if count_plus_sentinel != self.arena.count() { return Err(EINVAL); }
        let sentinel = self.arena.resolve(self.arena.sentinel()).ok_or(EINVAL)?;
        if sentinel.next == 0 || sentinel.prev == 0 || sentinel.next == self.arena.sentinel() || sentinel.prev == self.arena.sentinel() || sentinel.next != self.ids[0] || sentinel.prev != self.ids[count - 1] { return Err(EINVAL); }
        for index in 0..count {
            let id = self.ids[index];
            if id == 0 || id == self.arena.sentinel() || self.ids[..index].contains(&id) { return Err(EINVAL); }
            let descriptor = self.arena.resolve(id).ok_or(EINVAL)?;
            let expected_prev = if index == 0 { self.arena.sentinel() } else { self.ids[index - 1] };
            let expected_next = if index + 1 == count { self.arena.sentinel() } else { self.ids[index + 1] };
            if descriptor.generation != self.arena.generation() || descriptor.mode != 1 || descriptor.prev != expected_prev || descriptor.next != expected_next { return Err(EINVAL); }
            if descriptor.page_count == 0 { return Err(EINVAL); }
            let bytes = descriptor.page_count.checked_mul(PAGE).ok_or(EOVERFLOW)?;
            let end = descriptor.physical_start.checked_add(bytes).ok_or(EOVERFLOW)?;
            if descriptor.physical_start % PAGE != 0 || descriptor.physical_start < self.arena.physical_base || end > self.arena.physical_limit { return Err(EINVAL); }
            for prior_index in 0..index {
                let prior = self.arena.resolve(self.ids[prior_index]).ok_or(EINVAL)?;
                let prior_bytes = prior.page_count.checked_mul(PAGE).ok_or(EOVERFLOW)?;
                let prior_end = prior.physical_start.checked_add(prior_bytes).ok_or(EOVERFLOW)?;
                if prior.physical_start < end && descriptor.physical_start < prior_end { return Err(EINVAL); }
            }
        }
        Ok(ValidatedInventory { arena: self.arena, ids: self.ids, count })
    }
}
impl<'a> ValidatedInventory<'a> {
    pub fn len(&self) -> usize { self.count }
    pub fn descriptor(&self, index: usize) -> Option<&DescriptorRecord> { if index >= self.count { None } else { self.arena.resolve(self.ids[index]) } }
}

fn descriptor(id: u64, start: u64, pages: u64, generation: u32, mode: u8, next: u64, prev: u64) -> DescriptorRecord { DescriptorRecord { id, physical_start: start, page_count: pages, generation, mode, next, prev } }
fn base_records(two: bool) -> Vec<DescriptorRecord> {
    if two { vec![descriptor(1, 0, 0, 0, 0, 2, 3), descriptor(2, 0x1000, 1, 7, 1, 3, 1), descriptor(3, 0x3000, 1, 7, 1, 1, 2)] }
    else { vec![descriptor(1, 0, 0, 0, 0, 2, 2), descriptor(2, 0x1000, 1, 7, 1, 1, 1)] }
}
fn hash(records: &[DescriptorRecord]) -> u64 { let mut value = 0xcbf29ce484222325u64; for record in records { for field in [record.id, record.physical_start, record.page_count, record.generation as u64, record.mode as u64, record.next, record.prev] { value ^= field; value = value.wrapping_mul(0x100000001b3); } } value }
fn run_case(name: &str) -> Result<(i32, u64, u64), i32> {
    let mut records = base_records(matches!(name, "capacity-exceeded" | "count-mismatch" | "overlapping-extent" | "foreign-cycle" | "valid-two"));
    let mut selected: [u64; MAX] = [0; MAX]; let mut selected_count = if records.len() == 3 { 2 } else { 1 }; selected[0] = 2; if selected_count == 2 { selected[1] = 3; }
    let mut reserve = selected_count; let mut claimed = selected_count as u64; let epoch = 9u64; let mut observed = 9u64;
    match name {
        "empty" => { selected_count = 0; claimed = 0; }, "capacity-zero" => reserve = 0, "capacity-exceeded" => reserve = 1,
        "count-mismatch" => { selected_count = 1; claimed = 1; }, "count-overflow" => claimed = u64::MAX,
        "duplicate-id" => records[1].id = 1, "foreign-id" => selected[0] = 99, "null-link" => records[1].next = 0,
        "dangling-link" => records[1].next = 99, "one-sided-link" => records[1].prev = 2, "malformed-sentinel" => records[0].next = 1,
        "foreign-cycle" => records[2].next = 2, "wrong-mode" => records[1].mode = 0, "invalid-page-count" => records[1].page_count = 0,
        "page-count-overflow" => records[1].page_count = u64::MAX, "misaligned-extent" => records[1].physical_start = 0x1001,
        "foreign-extent" => records[1].physical_start = 0x9000, "overlapping-extent" => records[2].physical_start = 0x1000,
        "stale-generation" => records[1].generation = 8, "concurrent-mutation" => observed = 8,
        "capacity-exact" | "valid-single" | "valid-two" => {}, _ => return Err(EINVAL),
    }
    let before = hash(&records);
    let arena = DescriptorArena::new(records.as_mut_slice(), 1, 7, 0x1000, 0x9000, epoch);
    let status = match arena { Err(error) => error, Ok(arena) => if observed != epoch { EINVAL } else {
        match InventoryBuilder::reserve(&arena, reserve) {
            Err(error) => error,
            Ok(mut builder) => {
                let mut pushed = OK; for id in selected[..selected_count].iter().copied() { pushed = builder.push(id); if pushed != OK { break; } }
                if pushed != OK { pushed } else if name == "count-overflow" { builder.freeze_claimed(claimed).validate().err().unwrap_or(OK) } else { builder.freeze().validate().err().unwrap_or(OK) }
            }
        }
    }};
    let after = hash(&records); if before != after { return Err(EINVAL); } Ok((status, before, after))
}
fn main() {
    let selector = std::env::args().nth(1).unwrap_or_default(); let Some(vector) = vectors::case(&selector) else { std::process::exit(2) };
    match run_case(vector.name) { Ok((status, before, after)) if status == vector.expected && before == after => println!("{}|{}|{:016x}|{:016x}", vector.name, status, before, after), Ok(_) | Err(_) => std::process::exit(1) }
}
