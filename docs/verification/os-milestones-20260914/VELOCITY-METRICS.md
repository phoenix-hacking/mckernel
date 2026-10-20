# Live velocity measurements

Updated: 2026-10-19T23:59:36.333860Z. Baseline: 2026-10-19T10:27:41Z (13.53 wall hours).

| Metric | Value since baseline | Rate / basis | Working target |
|---|---:|---|---|
| Practical checks closed | 4 | 0.30/h | Track closures |
| New native behaviors | 1 | 0.07/h | Track accepted gains |
| New production Rust paths | 0 | 0.00/h | Track accepted gains |
| New Rust paths with native proof | 3 | 0.22/h | Accepted selected-path coverage |
| Known production/native outcomes | 12 | 0.89/h | Raise useful feedback throughput |
| Previous build to native feedback | ~89 min | Earlier measured image handoff | <=30 min |
| Current build to native feedback | 127.6 min; completed | first_observed_result | <=30 min |
| Current build to artifact acceptance | 45.2 min | Accepted canonical artifact report | Reduce preparation and review delay |
| Failed guard to accepted physical release | 44.0 min; completed | Named NEW205 failed case | <=10 min |
| Successful snapshot review age | 17.72 sec | Latest completed native review | Launch <=30 sec; hard limit 60 |
| Included quota consumed | 24.0 percentage points | 86% used | Stop at 97% |
| Largest observation gap | 299.5 min | Missing sample coverage | Sample about every 5 min while available |

Known guarded build/native invocation time: 753.89s (1.55% of this wall interval). This partial inventory is not CPU utilization.

Counters are last confirmed accepted evidence, not engineering completion percentages. Elapsed wall rates include host/network unavailability and observation gaps. The active supervisor samples about every five minutes and reviews every thirty minutes; this collector creates no background service.
