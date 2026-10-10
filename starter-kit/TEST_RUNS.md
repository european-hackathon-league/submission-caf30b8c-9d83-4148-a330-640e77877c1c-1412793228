# Sandbox test-run journal

Record each Atira rehearsal here as soon as it is started. This makes the live
platform recording, its package, the Git/Entire checkpoint, and the hypothesis
easy to reconnect later.

| Started (Berlin) | Commit | Run ID | Hypothesis / change | Result and follow-up |
| --- | --- | --- | --- | --- |
| 2026-10-10 | `024f8b3` | `run_3c3568bb65f5871e` (`reh_3462880dc545db9e`) | Baseline after action state verification, extraction schema gate, pre-submit review, and recovery safeguards. | Queued; inspect live logs and score before choosing the next variant. |

Use `atira status` to find a run ID, `atira logs <run-id> --follow` for its
console trace, and `atira package <run-id>` to inspect exactly what the sandbox
received. Keep the platform's score/breakdown and the next decision in the last
column after it finishes.
