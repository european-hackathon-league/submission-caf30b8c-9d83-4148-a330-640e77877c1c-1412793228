# Sandbox test-run journal

Record each Atira rehearsal here as soon as it is started. This makes the live
platform recording, its package, the Git/Entire checkpoint, and the hypothesis
easy to reconnect later.

| Started (Berlin) | Commit | Run ID | Hypothesis / change | Result and follow-up |
| --- | --- | --- | --- | --- |
| 2026-10-10 | `024f8b3` | `run_3c3568bb65f5871e` (`reh_3462880dc545db9e`) | Baseline after action state verification, extraction schema gate, pre-submit review, and recovery safeguards. | Finished eligible at quality 70.7 in 18:23. Missing/incorrect position inputs and total consistency were the main score losses; repeated extraction timeouts and a post-confirmation token 401 were also observed. |
| 2026-10-10 | `e1ecb2c` | `run_23a00fcc468b92db` (`reh_4fd47a36fcec6187`) | Copy explicit units from clarifications, trust only recognized unit labels, require reference/positions/total on the review page, and remove the repeated task brief from extraction prompts. | Finished eligible at quality 22.8 in 14:11. Clarification units were extracted correctly, but reasoning-enabled extraction still had a 2:35 p95 and timed out on several pages; the resulting partial bid reached the form, then the run token expired during entry. This was the diagnostic variant that motivated disabling reasoning for schema-constrained transcription. |
| 2026-10-10 | `b8f3228` | `run_60233f96d79c14a0` (`reh_8bfdeb8c7420e1cc`) | Same unit and review safeguards, with reasoning disabled only for typed evidence extraction. | Finished eligible at quality 98.7 in 10:07 (model-call p95 12s). All bid positions were present; the pre-submit checklist reported READY with the review values visible. The final confirmation click was followed by an expired-token 401 before a receipt could be read, but Atira completed scoring the answer. Follow up on post-submit confirmation handling without weakening the checklist. |
| 2026-10-10 | `8902930` | `run_1d8b1f72865d2834` (`reh_a4fe78d459e0841e`) | First run with the coverage gate before a question is closed, the page-limit signal of `collect`, the fill readback and the bounded review gate. | Failed, not eligible, 19:40. The investigation priced every position and the form was filled, but the bid was never signed: the mailbox courier opened the signing-code mail and refused it four times (77 calls), because a marking inside the message calls it unsent and the courier instructions of `2d96c95` said only sent messages count. Not caused by the new gates. |
| 2026-10-10 | `6ebad2e` (branch `claude/courier-restore`) | `run_7b2c0cf9385b6362` (`reh_15fe95e875221634`) | Courier instructions put back to the wording before `2d96c95`. | Cancelled after 07:34, still in the investigation: no result. |
| 2026-10-10 | `2d330db` | `run_2a95ffc92c7a65bc` (`reh_875707acab2ce734`) | The same courier change on `main`, on top of fast typed extraction (`b8f3228`) and free instead of physical stock (`2d96c95`). | **Finished eligible at quality 100 in 12:24, $0.36.** No open question left after 500 s; the courier returned the code in 3 calls (14 s); the checklist reported READY at once and the receipt was read in code. Against the 98.7 run the one corrected field is a lead time, which follows from the free-stock figure. The coverage gate held back one premature "absent" that would not have changed the bid; the other new checks did not trigger. One run only: repeat it before relying on it. |

Local validation for `b8f3228`: `uv run --no-sync python -m unittest discover tests -v` passed all 239 tests. Focused case-file and preflight tests also passed after the extraction-speed change.

Use `atira status` to find a run ID, `atira logs <run-id> --follow` for its
console trace, and `atira package <run-id>` to inspect exactly what the sandbox
received. Keep the platform's score/breakdown and the next decision in the last
column after it finishes.
