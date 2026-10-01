# Rules

There are two sets. The **repository rules** define how participants manage their individual Round 2 work, and the **engineering rules** are part of what you are assessed on.

## Repository rules

| #  | Rule                                                                                                        | How it's enforced                                               |
| -- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| R1 | Round 2 is an **individual build**.                                                                         | Participant responsibility                                      |
| R2 | Each participant must work in their **own GitHub fork** of this repository.                                 | Participant responsibility                                      |
| R3 | Your fork is your Round 2 development and final submission repository.                                      | Participant responsibility                                      |
| R4 | All code commits forming your Round 2 submission must be made during the **authorised build phase**.        | Repository history / evaluation                                 |
| R5 | Do not continue making Round 2 code changes after the build phase ends.                                     | Repository history / evaluation                                 |
| R6 | No secrets in the repo: API keys, tokens, passwords, `.env` files.                                          | You. A leaked key is revoked, and it may affect the submission. |
| R7 | Do not edit, delete or interfere with the organiser's official repository or another participant's work.    | Participant responsibility                                      |
| R8 | Once the official submission form is submitted, the submission is **final**. No resubmissions are accepted. | Submission process                                              |

The official repository, shared `data/` files and top-level documentation are provided as reference resources. Build your solution in **your own fork**.

If any shared documentation or data appears incorrect or contradictory, raise it with the organisers rather than silently modifying the official repository.

### Round 2 timeline

* **Build phase begins:** 25 September 2026 · 9:00 AM IST
* **Submissions open:** 27 September 2026
* **Final submission deadline:** 1 October 2026 · 6:00 PM IST

The submission form closes permanently at the final deadline.

**There is no reopening and no resubmission.**

## Engineering rules (not negotiable)

These are the craft part of the assessment. Each one is cheap to follow now and expensive to retrofit.

### 1. Tenancy isolation before any feature

Every table gets row-level security scoped to the organisation, **enabled and forced**. Test that a second organisation sees zero rows, and that it can't fetch another organisation's image by guessing a key. Row isolation with a shared, guessable image path is a leak that looks green.

*The sample data has two orgs (`org_demo_alpha`, `org_demo_bravo`) for exactly this test.*

### 2. Batch your model calls

Make **one** call per unit carrying all checks, never one call per check. At prep volumes that is the difference between a 90% gross margin and none.

### 3. Fail open

A model error or timeout still saves the capture and still produces a record, marked `pending`. Nothing blocks the operator. Anything that makes a warehouse line wait gets worked around within a day of deployment.

### 4. Uncertain is a valid verdict

It isn't a low-confidence pass. A model that declines to judge a bad photo is more credible to an operations person than one that is confidently wrong. Build it as a first-class outcome and show it in the interface.

*The sample data uses `uncertain` and `pending_review` as values on purpose.*

### 5. Look authoritative rules up

Where the channel publishes the requirement, retrieve it. Don't let a model recall it from memory, and don't infer it from examples. **That includes the sample CSVs in this repo.** Their requirement flags and fee amounts are dummy values.

## Honesty rules (assessed)

* **Say what you built, not what it sounds like.** You have a content hash. You don't have a tamper-evident, immutable or anchored record, unless you actually built one and can show it.
* **Overrides are data.** When an operator disagrees with the agent, capture the original verdict, the new verdict and a reason. Never discard those rows silently.
* **"It works well" isn't a result.** Report a number per check, with false positives and false negatives separately and the method written down. An honest 61% you can break down beats a 95% you can't.
* **Contradictions are findings.** Where the background documents disagree, raise it. Don't silently pick one side.
