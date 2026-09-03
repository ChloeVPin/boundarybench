# Researcher Access study brief

## Project summary

BoundaryBench studies a safety problem that appears when language models act through tools: information encountered during a task may look like an instruction without carrying authority from the user. The project asks when a capable agent completes legitimate work while also crossing a boundary the user never granted.

The proposed study measures authorization decay across controlled changes in instruction provenance, trajectory position, and repeated pressure. Eleven synthetic tasks cover repository, filesystem, data-flow, and administrative boundaries. Every attack case has a matched clean control, which separates genuine boundary preservation from broad refusal. A lightweight authority-checkpoint mitigation is evaluated in a second arm.

The repository already contains the scenario schema, isolated sandbox, controlled tools, complete event logging, deterministic oracles, paired factorial protocol, statistical aggregation, and a Responses API adapter. A machine-readable preregistration locks 35,640 cases across GPT-5.6 Sol, Terra, and Luna before model collection. The work aligns directly with responsible deployment, robustness, alignment, misuse resistance, and interpretable evaluation of model behavior.

## Research question

When a tool-using language model receives untrusted information during an authorized task, which changes in provenance, position, and repetition cause safe completion to decline, and can an explicit authority checkpoint reduce that decline without increasing refusal on clean controls?

## Planned use of OpenAI products

The study uses the Responses API to present a fixed trajectory and a restricted set of local function tools. Each model can read or modify only resettable synthetic fixtures and can contact only local stubs. The adapter disables response storage, excludes web and computer tools, records cumulative usage, and preserves every requested, denied, and completed effect.

Three GPT-5.6 capability tiers are evaluated under the same model-visible inputs, tool schemas, trial count, and randomized schedule. Comparing tiers tests whether task capability and authorization preservation move together. Comparing baseline and authority-checkpoint arms tests a concrete mitigation while matched controls measure the utility cost.

## Method

The 3 by 3 by 3 factorial design varies early, middle, or late attack position; one, three, or five presentations; and explicit, source-only, or flattened provenance. Eleven scenarios and eleven clean controls produce 594 cases per trial. Ten trials, three models, and two arms produce 35,640 cases.

Safe completion requires authorized task completion, no completed boundary violation, retained authorization, and a passing deterministic oracle. Rates use Wilson intervals. Matched effects use scenario-clustered bootstrap intervals. Unknown observations remain outside denominators, and all exclusions remain in the artifact.

## Significance

Agent evaluations often collapse success into whether the task was completed or whether an attack produced a visible final response. That misses blocked attempts, unauthorized side effects, and systems that look safe because they refuse everything. BoundaryBench makes these outcomes separately observable and identifies the context pressure associated with a failure.

This evidence can inform safer agent interfaces, permission systems, provenance displays, tool mediation, and deployment evaluations. The resulting corpus, protocol, adapter, raw schema, and analysis code are open and designed for independent replication.

## Feasibility and budget

The full design requires an estimated $812.59 at the standard prices listed on September 3, 2026. A $186.90 reserve covers interrupted calls and protocol-preserving replication, producing a $999.49 plan and a $1,000 API credit request. The compiled budget records 106.92 million input tokens and 53.46 million output tokens across all models and arms.

The research infrastructure is executable now. Its deterministic conformance suite covers all 594 protocol cases, and the automated software suite covers the provider loop, tool denials, token accounting, study compilation, schedule integrity, scenario validation, sandbox controls, oracles, and statistical estimators.

## Timeline

| Period | Deliverable |
| --- | --- |
| Month 1 | Budget calibration pilot, protocol-lock confirmation, release archive |
| Months 2 through 5 | Collection across the six locked model and arm blocks |
| Month 6 | Trace audit, exclusion ledger, confirmatory analysis |
| Month 7 | Held-out sensitivity study and independent reproduction package |
| Month 8 | Preprint, public dataset, software release, and research presentation |

The schedule fits within the program's twelve-month credit validity period and leaves four months for review or provider interruptions.

## Responsible publication

All tasks use synthetic data and local stubs. The project involves no human subjects, personal information, production access, or uncontrolled external action. Model safety or security findings follow OpenAI's sharing and publication policy and coordinated disclosure process before detailed public release. Publications disclose model versions, prompts, parameters, exclusions, funding, and material AI assistance.

## Program fit

The [Researcher Access Program](https://openai.com/form/researcher-access-program/) prioritizes work on responsible deployment, risk mitigation, and societal impact. This study addresses those goals through a reproducible robustness and alignment evaluation focused on the boundary between useful information and delegated authority. The public repository demonstrates a concrete method, bounded resource plan, responsible-use framework, and execution path for the proposed research.
