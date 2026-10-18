# Host ext4 reserve proposal — 2026-10-18

Status: **PROPOSAL_NOT_AUTHORIZED**. This is a read-only proposal for the functional kernel/application campaign. No filesystem setting has changed, and this document does not authorize execution.

The captured root filesystem is `/dev/nvme0n1p2`, ext4, major:minor `259:2`, UUID `983bfa59-3985-4ca8-87af-3675adcfe2b3`, boot ID `7bfc5687-6c04-4d15-84eb-b92ab9a55dcb`. It has 249,919,744 blocks of 4,096 bytes. The proposed reserve is `ceil(249919744/100) = 2,499,198` blocks.

| Quantity | Current | Proposed |
|---|---:|---:|
| Reserved blocks | 12,495,987 | 2,499,198 |
| Reserved bytes | 51,183,562,752 | 10,236,715,008 |
| Reserved GiB | 47.668407 | 9.533684 |
| Mounted available bytes, conditional projection | 17,786,658,816 | 58,733,506,560 |
| Mounted available GiB, conditional projection | 16.565117 | 54.699841 |

This would make up to **40,946,847,744 bytes (38.134724 GiB)** accessible to ordinary allocations while retaining about 9.5 GiB reserved for root. It changes reservation accessibility; it does not reclaim allocated file blocks. `f_bfree` should remain unchanged by the setting itself. Concurrent writes can change actual availability. The mounted `statvfs` capture is the live projection basis; the mounted filesystem's on-disk `dumpe2fs` Free blocks count can be stale.

Proposed command, only after explicit user authorization and independent execution review:

```sh
sudo -A /usr/sbin/tune2fs -r 2499198 /dev/nvme0n1p2
```

Exact reserve-policy rollback:

```sh
sudo -A /usr/sbin/tune2fs -r 12495987 /dev/nvme0n1p2
```

The installed primary manual `/usr/share/man/man8/tune2fs.8.gz` defines `-r reserved-blocks-count` as setting the number of reserved filesystem blocks. Rollback restores the reservation count, not any bytes consumed after the change. If free blocks later fall below the original reserve, restoring it can reduce ordinary-user availability to zero; remeasure and review before rollback.

Before any approved change, freshly verify device, UUID, boot, block counts, block size, mounted capacity and live owner/lease identities; independently review operation and rollback under the serialized heavy-operation scope. Preserve the 16-GiB host/12-GiB scratch floors and all packet reserves. The 97% included-usage stop remains unchanged. Preserve all failed/current files, Conda, Tracker, the 110-GiB scratch backing image and its UUID. No automatic execution follows this proposal.

Exact captured inputs are under `/home/holden/mckernel-work/scratch/host-ext4-reserve-proposal-20261018-1`. Machine-readable calculations and conditions: [proposal evidence](../evidence/host-ext4-reserve-proposal-20261018-1.json).
