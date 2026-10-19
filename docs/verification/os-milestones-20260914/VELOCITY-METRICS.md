# Live velocity measurements

Updated: 2026-10-19T18:39:31.954135Z. Baseline: 2026-10-19T10:27:41Z (8.20 wall hours).

| Metric | Value since baseline | Rate / basis | Working target |
|---|---:|---|---|
| Practical checks closed | 0 | 0.00/h | Track closures |
| New native behaviors | 0 | 0.00/h | Track accepted gains |
| New production Rust paths | 0 | 0.00/h | Track accepted gains |
| Known production/native outcomes | 3 | 0.37/h | Raise useful feedback throughput |
| Build to native feedback | ~89 min | 1 measured image handoff | <=30 min |
| Current build to native feedback | >=42.1 min; pending | Since accepted producer finish | <=30 min |
| Failed guard to accepted physical release | 44.0 min; completed | Named NEW205 failed case | <=10 min |
| Successful snapshot review age | 17.72 sec | Latest completed native review | Launch <=30 sec; hard limit 60 |
| Included quota consumed | 9.0 percentage points | 71% used | Stop at 97% |
| Largest observation gap | 299.5 min | Missing sample coverage | Sample about every 5 min while available |

Known guarded build/native invocation time: 465.68s (1.58% of this wall interval). This partial inventory is not CPU utilization.

Counters are last confirmed accepted evidence, not engineering completion percentages. Elapsed wall rates include host/network unavailability and observation gaps. The active supervisor samples about every five minutes and reviews every thirty minutes; this collector creates no background service.
