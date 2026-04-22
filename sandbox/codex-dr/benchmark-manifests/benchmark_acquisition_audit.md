# Codex-DR Benchmark Acquisition Audit

Status: active acquisition audit for `alexandriacleanroom-91.1.2`
Date: 2026-04-22
Workspace: `sandbox/codex-dr/`
Internet evidence checked: 2026-04-22

## Purpose

This audit calibrates the Codex-DR sandbox target against public benchmark
reality without executing benchmarks, running terminal agents, or spending
provider/model tokens.

Benchmark acquisition does not authorize benchmark execution. Execution remains
blocked until the provider-off bootstrap implementation bead
`alexandriacleanroom-91.1.4.1` passes, the harness contracts exist, and a
run-specific token manifest has been approved.

## Governing Posture

- The sandbox target is Grep-style recursive deep-research parity pressure, not
  a local demo.
- Public benchmark artifacts may define target calibration, evaluator shape,
  data-access constraints, and blocked claims.
- Public Grep/Parcha score publications are donor evidence, not Alexandria
  proof.
- Root Program 80/90 artifacts are historical proof surfaces for this lane.
- Raw private benchmark data, paid corpora, secrets, provider transcripts, and
  large benchmark payloads must not enter git.

## Protocol Receipts

### Center Of Gravity

- Intended system: an inspectable terminal-agent deep-research sandbox that can
  eventually plan, branch, deepen, synthesize, review, re-enter, report, score,
  and emit allowed claims.
- Current center: bootstrap doctrine and benchmark acquisition, not root
  runtime code or Program 90.
- Missing center this audit supports: the benchmark-and-claim boundary that
  future parity and harness contracts must respect.
- False closure: treating public Grep/Parcha scores, dataset availability, or a
  copied scorer command as Alexandria parity.

### Teleology

- Completion object: a benchmark acquisition artifact future parity-contract
  work can cite without chat context.
- Binding constraint: acquisition may permit dataset-readiness claims only; it
  may not permit execution, performance, or parity claims.
- `teleological-pre-inference` and `teleology-preserving-planning` were followed
  from local protocol files because the named skills were not advertised in the
  skill catalog for this session.

### Evidence-First Backpressure

- Acquisition claim gate: PROCEED where public metadata or repo-local snapshots
  identify source, version, license/access, case count, and evaluator shape.
- Execution claim gate: PROVE FIRST for every benchmark run, score, parity, or
  leaderboard comparison claim.
- Provider claim gate: PROVE FIRST for any use of Gemini, Jina, browser/search,
  SDK, or terminal-agent behavior.

### Spec Interface Audit

Upstream interfaces satisfied:

- `sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md`: benchmark acquisition
  calibrates the target and does not authorize execution.
- `sandbox/codex-dr/docs/ARCHITECT_HANDOFF.md`: audit covers DRACO,
  DeepSearchQA, DeepResearch Bench, and Parcha-published benchmark material.
- `docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`: benchmark
  claims require acquired datasets, recorded versions, evaluator shape, and
  reproducible scores.

Downstream obligations created:

- `alexandriacleanroom-91.1.3` parity contract must cite this file's claim
  classes.
- `alexandriacleanroom-91.1.4.1` provider-off bootstrap implementation remains
  the execution blocker.
- Any future benchmark execution bead must produce a token manifest, case
  manifest, scorer manifest, run bundle, and allowed-claims output.

No round-trip execution interface is introduced here. This is an acquisition
contract, not an implementation contract.

## Claim Classes

| Class | Meaning | Status after this audit |
| --- | --- | --- |
| Permitted | Claim may be made from this audit alone. | Public acquisition metadata and target-calibration statements only. |
| Blocked | Claim cannot be made until a later proof artifact exists. | Any Alexandria score, Grep parity, leaderboard rank, product readiness, or benchmark-execution success. |
| Evidence-pending | Plausible but not settled from public/local evidence checked here. | Exact private Grep/Parcha setup, judge reproducibility, hidden prompts/configs, API versions, and private rerun conditions. |

## Source Inventory

| Artifact | URL | Version or snapshot observed | License/access observed | Notes |
| --- | --- | --- | --- | --- |
| DRACO paper | https://arxiv.org/abs/2602.11685 | arXiv v1, submitted 2026-02-12 | arXiv paper license link present | Primary public paper. |
| DRACO dataset | https://huggingface.co/datasets/perplexity-ai/draco | HF API sha `ce076749809027649ebd331bcb70f42bf720d387`, last modified 2026-02-20 | MIT, public, ungated | Metadata only inspected; raw dataset not downloaded into repo. |
| Perplexity DRACO article | https://research.perplexity.ai/articles/evaluating-deep-research-performance-in-the-wild-with-the-draco-benchmark | Public article, crawled current by web search | Public web | Secondary method/positioning source from benchmark owner. |
| DeepSearchQA paper | https://arxiv.org/abs/2601.20975 | arXiv v1, submitted 2026-01-28 | arXiv paper license link present | Primary public paper. |
| DeepSearchQA HF mirror | https://huggingface.co/datasets/google/deepsearchqa | HF API sha `b2623f8653065c2672de6d941fc5434cd652376c`, last modified 2025-12-17 | Apache-2.0, public, ungated | Metadata only inspected; raw CSV not downloaded into repo. |
| DeepSearchQA Kaggle | https://www.kaggle.com/datasets/googleai/deepsearchqa | Linked by paper/HF card | Kaggle access required for leaderboard/starter notebook | External auth/terms may apply; not accessed here beyond public links. |
| DeepResearch Bench paper | https://arxiv.org/abs/2506.11763 | arXiv v1, submitted 2025-06-13 | arXiv paper license link present | Primary public paper. |
| DeepResearch Bench repo | https://github.com/Ayanami0730/deep_research_bench | Public GitHub repo, 37 commits observed in web view | Apache-2.0 license shown | Contains code, prompts, data structure, and submission requirements. |
| DeepResearch Bench HF dataset | https://huggingface.co/datasets/muset-ai/DeepResearch-Bench-Dataset | HF API sha `f7d27cdd3930dd1eaf67a217821e616cc62e9f8e`, last modified 2025-11-17 | Apache-2.0, public, ungated | Metadata only inspected; generated reports not downloaded into repo. |
| DeepResearch Bench leaderboard | https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard | Dynamic public leaderboard | Public web; submission requires materials | Current ranking may change; cite only with date. |
| Parcha/Grep benchmarks repo | https://github.com/Parcha-ai/benchmarks | GitHub API main commit `82ffb84dbd61833932936b5bc3c2afeb8536d6fb`, created/pushed 2026-04-07 | Public repo; GitHub API reported `license: null` | Public score/results material. No explicit repo license observed. |
| Grep architecture article | https://grep.ai/blog/building-grep-deep-research | Repo-local snapshot captured as `docs/references/grep_building_grep_deep_research_2026_03_16.md` | Public article snapshot | Donor architecture and Grep score claims; not Alexandria proof. |
| Parcha "Claude in a Box" article | https://blog.parcha.dev/blog/claude-in-a-box | Repo-local snapshot checked 2026-04-21 | Public article snapshot | Donor harness/agent-box structure; not a benchmark source. |

## Benchmark Family Records

### DRACO

| Field | Audit finding |
| --- | --- |
| Canonical public source | Paper: https://arxiv.org/abs/2602.11685. Dataset: https://huggingface.co/datasets/perplexity-ai/draco. |
| Version observed | arXiv v1 submitted 2026-02-12. HF sha `ce076749809027649ebd331bcb70f42bf720d387`, last modified 2026-02-20. |
| License/use restrictions | HF dataset metadata says MIT. Paper page exposes an arXiv license link. No private access needed for dataset viewing. |
| Access constraints | Public and ungated on HF. Dataset is small by HF category (`n<1K`), but raw data must not be copied into git unless a future case-manifest bead explicitly allows a minimal pointer-only wrapper. |
| Case count | 100 test rows across 10 domains. |
| Evaluator shape | Long-form answer judged against task-specific rubrics across factual accuracy, breadth/depth, presentation quality, and citation quality. HF card describes about 40 criteria per task; observed DRACO card names 3,934 criteria across all tasks. |
| Scoring/rubric notes | Weighted criteria include positive and negative weights. Severe negative penalties exist for harmful content. Comparability depends on consistent judge model, prompt, temperature/reasoning settings, and scoring implementation. |
| Local reproduction notes | Acquisition can point to HF dataset sha and source URL. Execution would need an answer generation harness, judge configuration, scoring implementation, and custody bundle. No run authorized here. |
| Public/private gap | Grep/Parcha public claims report 78.6 percent on DRACO, but exact private run transcripts, provider versions, prompts, and any selection/rerun policy are not established by this audit. |
| Claim class | Permitted: DRACO has a public, small, MIT-licensed dataset and defined rubric axes suitable for future target calibration. Blocked: any Alexandria DRACO score or Grep-parity comparison. Evidence-pending: exact comparability to Grep/Parcha's private evaluation setup. |

### DeepSearchQA

| Field | Audit finding |
| --- | --- |
| Canonical public source | Paper: https://arxiv.org/abs/2601.20975. HF mirror: https://huggingface.co/datasets/google/deepsearchqa. Kaggle dataset/leaderboard/starter code linked from paper and HF card. |
| Version observed | arXiv v1 submitted 2026-01-28. HF sha `b2623f8653065c2672de6d941fc5434cd652376c`, last modified 2025-12-17. |
| License/use restrictions | HF metadata says Apache-2.0. Kaggle access and leaderboard/starter notebook may carry Kaggle terms and authentication requirements. |
| Access constraints | HF dataset is public and ungated. Kaggle leaderboard and starter code require external site access and may require login. |
| Case count | Public HF card says 900 rows. Parcha/Grep material reports a 896-question scored subset with adjusted factual-correctness accounting; the 900-vs-896 difference must be treated as evidence-pending until the exact exclusion/adjustment rule is reproduced. |
| Evaluator shape | Web-access QA agent produces answer(s). Autorater compares outputs against gold answers. HF card states `gemini-2.5-flash` and the Kaggle starter notebook grading prompt should be used for official-style grading. |
| Scoring/rubric notes | Factual correctness and F1-style scoring for single/set answers. Outcomes are black-box; trajectory adequacy is not directly assessed by the public benchmark. |
| Local reproduction notes | Acquisition can record HF sha and Kaggle links. Execution would require web-enabled answer generation, locked inference-time hiding of `answer_type`, the Kaggle grading prompt, `gemini-2.5-flash` access, and a scorer manifest. |
| Public/private gap | Grep/Parcha public claim is 84.5 percent adjusted FC over 896 cases. The public benchmark has 900 rows; exact adjusted FC rule, removed cases, and private run traces remain unverified here. |
| Claim class | Permitted: DeepSearchQA is public, Apache-2.0 on HF, and contains 900 prompts across 17 fields. Blocked: Alexandria pass@1, FC, F1, or Grep comparison. Evidence-pending: 896-case subset and exact Parcha/Grep adjustment logic. |

### DeepResearch Bench

| Field | Audit finding |
| --- | --- |
| Canonical public source | Paper: https://arxiv.org/abs/2506.11763. Repo: https://github.com/Ayanami0730/deep_research_bench. HF dataset: https://huggingface.co/datasets/muset-ai/DeepResearch-Bench-Dataset. |
| Version observed | arXiv v1 submitted 2025-06-13. HF dataset sha `f7d27cdd3930dd1eaf67a217821e616cc62e9f8e`, last modified 2025-11-17. Public repo observed with Apache-2.0 license and 37 commits in GitHub web view. |
| License/use restrictions | Repo and HF dataset indicate Apache-2.0. Official leaderboard submission requires raw generated reports, reproducibility link, metadata, and a temporary Gemini-2.5-Pro-accessible key. |
| Access constraints | Public repo and HF dataset are reachable. Official submission requires email coordination and provider key material. Local FACT evaluation also requires web scraping/Jina-style access according to public repo prerequisites. |
| Case count | 100 PhD-level tasks, 50 Chinese and 50 English, across 22 fields. |
| Evaluator shape | RACE evaluates long-form reports with adaptive criteria and reference-based scoring across comprehensiveness, insight/depth, instruction following, and readability. FACT evaluates factual/citation support through statement-source extraction and verification. |
| Scoring/rubric notes | RACE uses Gemini-2.5-Pro in the public repo's current setup. FACT uses scraping plus LLM judgment. Both are provider-backed and therefore blocked until token and provider-off gates pass. |
| Local reproduction notes | Acquisition can cite repo/HF/paper. Execution would require generated articles in the expected raw-data format, official scripts, provider keys, web-scrape key/config where used, scorer manifest, repeated-run policy, and custody bundle. |
| Public/private gap | Public leaderboard entries and Parcha/Grep published results can be cited as external claims only. Exact Grep report-generation setup, best-of-N policy, rewrite strategy, and verification run materials are not established as Alexandria proof. |
| Claim class | Permitted: DeepResearch Bench has public Apache-2.0 code/data surfaces and a defined 100-task RACE/FACT evaluation shape. Blocked: any Alexandria RACE/FACT score or leaderboard claim. Evidence-pending: exact official leaderboard reproducibility for Parcha/Grep and judge variance under Alexandria's future runner. |

### Parcha-Published Benchmark Material

| Field | Audit finding |
| --- | --- |
| Canonical public source | https://github.com/Parcha-ai/benchmarks plus Grep article snapshot in `docs/references/grep_building_grep_deep_research_2026_03_16.md`. |
| Version observed | GitHub API main commit `82ffb84dbd61833932936b5bc3c2afeb8536d6fb`; commit date 2026-04-07; web page shows one commit and no releases. |
| License/use restrictions | Public repo. GitHub API reported no repository license. Treat code/data reuse as evidence-pending until a license is added or explicit permission is obtained. |
| Access constraints | Public GitHub repository. Raw Grep-generated benchmark outputs may exist in repo subdirectories, but this audit did not download or import them. |
| Case count | Parcha README reports DRACO 100 tasks, DeepSearchQA 896 scored questions, and DeepResearch Bench 100 queries. |
| Evaluator shape | Parcha README reports Gemini-2.5-Pro for DRACO/DeepResearch Bench and DeepSearchQA adjusted FC/pass@1 plus automated FC and concise F1. |
| Scoring/rubric notes | Parcha material is an external score publication, not a neutral benchmark definition. It is useful for target calibration and gap analysis, not for Alexandria claims. |
| Local reproduction notes | Future work may cite commit `82ffb84...` as an external score snapshot. Do not import Parcha raw outputs into git unless license/permission and data policy are resolved. |
| Public/private gap | The public repo gives summarized scores and some artifacts. It does not settle private Grep/Parcha prompts, model/provider versions, tool access, branch traces, token budgets, selection policy, or full custody chain. DeepResearch Bench leaderboard rank is dynamic; public benchmark-owner materials observed during this audit include later April 2026 leaderboard updates after earlier Grep/Parcha rank claims. |
| Claim class | Permitted: Parcha/Grep publicly published benchmark score claims exist at the cited repo and article. Blocked: endorsing those claims as Alexandria proof. Evidence-pending: reuse license and exact reproduction conditions. |

## Local Reproduction Boundary

No benchmark case should enter a runnable harness until all of the following
exist:

1. Provider-off bootstrap implementation bead `alexandriacleanroom-91.1.4.1`
   passes with custody, re-entry, compaction, claim ledger, and allowed-claims
   validation.
2. A parity contract cites this audit and narrows the intended benchmark claim.
3. A case manifest records dataset source URL, immutable version/sha, license,
   permitted local storage mode, and exact selected case IDs.
4. A scorer manifest records judge model, provider, prompt, parameters, retry
   rules, scorer code version, and expected output schema.
5. A token manifest records budget, stop conditions, input sources, data
   policy, transcript capture path, compaction policy, allowed claims, and
   non-claims.
6. Raw private, paid, or large public benchmark payloads remain outside git,
   with committed files holding pointers, checksums, and policy notes only.

## Permitted Claims After This Audit

- The Codex-DR sandbox has a benchmark acquisition audit covering DRACO,
  DeepSearchQA, DeepResearch Bench, and Parcha-published benchmark material.
- DRACO is publicly available as a small MIT-licensed HF dataset with 100 test
  rows and task-specific rubrics.
- DeepSearchQA is publicly available as a small Apache-2.0 HF dataset with 900
  rows; official-style grading depends on Kaggle starter materials and
  `gemini-2.5-flash`.
- DeepResearch Bench has public Apache-2.0 code/data surfaces and a 100-task
  RACE/FACT-style evaluation shape; official-style scoring requires provider
  keys and raw generated reports.
- Parcha/Grep have published external score claims for the three benchmark
  families, but their repo lacks an explicit license as observed here and does
  not constitute Alexandria proof or a stable current-rank claim.

## Blocked Claims

- Alexandria has run any of these benchmarks.
- Alexandria has reproduced any Grep/Parcha score.
- Alexandria has achieved DRACO, DeepSearchQA, DeepResearch Bench, or overall
  Grep parity.
- Alexandria has a comparable leaderboard entry.
- The public Parcha/Grep scores are independently verified by this repo.
- The sandbox is product-runtime ready.
- Provider-backed execution is safe before `alexandriacleanroom-91.1.4.1` and
  token-manifest gates pass.

## Evidence-Pending Claims

- Exact private Grep/Parcha model versions, tool stack, prompts, effort levels,
  branch traces, rerun policies, and selection rules.
- DeepSearchQA 896-case adjusted subset and exclusion policy.
- DRACO judge-model equivalence and scorer implementation details sufficient
  for apples-to-apples comparison.
- DeepResearch Bench official leaderboard reproducibility for Parcha/Grep
  beyond public materials.
- Current DeepResearch Bench rank for Grep/Parcha at any future date; the
  leaderboard is dynamic and must be checked at claim time.
- Whether Parcha-published benchmark repo artifacts may be reused in Alexandria
  under a license acceptable for committed fixtures.
- Whether future benchmark execution can avoid raw private/paid corpora while
  still producing strong enough parity evidence.

## Acquisition-To-Harness Guidance

The next parity-contract bead should use this audit as follows:

- Treat DRACO as the clearest first public target because dataset metadata,
  rows, rubric shape, and MIT license are public and compact.
- Treat DeepSearchQA as accessible but scorer-sensitive because official-style
  grading depends on Kaggle starter code and `gemini-2.5-flash`.
- Treat DeepResearch Bench as high-signal but expensive because RACE/FACT are
  provider-backed and official submission requires raw reports plus a temporary
  Gemini key.
- Treat Parcha/Grep published scores as target-pressure anchors and gap
  evidence, not as acquired ground truth or reusable licensed fixtures.

## Data Policy

This audit intentionally stores only source URLs, versions, metadata, and
claim-boundary notes. It does not commit raw benchmark rows, generated reports,
private corpora, provider transcripts, API keys, or paid data.

Future work may create tiny pointer manifests or local fixture wrappers only
when the license and data-policy question is explicit and the file does not
contain raw private/paid/large benchmark data.
