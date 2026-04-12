# Trainer Loop Contract

Use the repository trainer loop for the selected target without relying on repo-local helper scripts outside the selected repository checkout.

## Workspace Contract

1. Derive `<prompt-name>` from the selected file path by stripping `.prompty` entirely, or otherwise stripping only the final extension.
2. Use the local workspace root `<target-dir>/.trainer-workspace/<prompt-name>/`.
3. Keep all trainer artifacts under that local workspace. Never use repo-root `*-workspace` directories for this workflow.
4. Before any trainer stage runs, ensure the workspace contains:
   - `engineer-prompt/`
   - `inputs/source/`
   - `iterations/`
5. Copy the current source file to `inputs/source/<basename>` if that snapshot does not already exist.
6. Ensure `engineer-prompt/review.md` exists. If it is missing, create a concise review artifact that records the target goal, likely failure modes, dataset gaps, validation plan, and the next optimization hypothesis.
7. Maintain `workflow-status.json` at the workspace root with these fields:
   - `target_file`
   - `workspace_root`
   - `prompt_name`
   - `workflow_state`
   - `updated_at`
   - `required_artifacts`
8. Use only these workflow states: `pending_engineer_prompt`, `pending_training`, `training`, and `complete`.
9. When training starts, set `workflow_state` to `training`, create the next `iterations/iteration-N/` directory, and create these subdirectories inside it:
   - `research/`
   - `synthesize/`
   - `optimize/`
   - `election/`
   - `candidates/`
   - `steering/`
   - `validation/`
10. Keep `required_artifacts` updated for:
    - `engineer_prompt_review`
    - `source_snapshot`
    - `latest_iteration_dir`
    - `train_dataset`
    - `val_dataset`
    - `eval_manifest`
    - `optimize_report`
    - `candidate_dir`
    - `candidate_manifest`
    - `latest_steering_turn`
    - `steering_summary_dir`
    - `validation_log`
    - `decision_summary`
11. On success, set `workflow_state` to `complete`, update `latest_iteration_dir`, point `decision_summary` to the final rollup artifact, and record whichever optimize report exists for the active iteration.
12. After each trainer stage finishes or fails, leave `workflow-status.json`, `required_artifacts`, and any stage output directories in a checkpointable state so the workflow can upload them to GitHub artifacts for downstream jobs and future resumption.

## Skill Execution Contract

1. The `trainer` agent uses the `researcher` agent for research-stage work and the `agent-skills` MCP server as the execution path for the remaining `trainer-*` skills.
2. Before each non-research stage, call `find_agent_skill` to locate the exact skill.
3. Call `load_agent_skill` before first use of a stage and again if the stage context changes materially.
4. Call `run_agent_skill` to execute the chosen stage.
5. When required support data is missing, the default stage order is `researcher` -> `trainer-synthesize` -> `trainer-optimize`.
6. Require at least one `trainer-optimize` pass for the selected target.
7. If multiple optimize outputs require comparison, run `trainer-election` as a separate step rather than assuming optimize performs leader selection.
8. Treat `research/`, `synthesize/`, `optimize/`, `election/`, `candidates/`, `steering/`, and `validation/` under the active iteration as the canonical stage checkpoint directories that later jobs may inspect after artifact download.

## Collaboration Contract

1. The `trainer` agent owns trainer-skill execution, workspace coordination, and the sequencing of any teacher/student/adversary loop work.
2. The `researcher` agent owns public-source discovery, source triage, and blocker reporting when grounded source material is missing.
3. The `teacher` agent only reviews supplied optimization artifacts or user-provided context to recommend what should improve next, and must forecast likely student mistakes itself before using any student handoff.
4. The `student` agent applies targeted revisions when the trainer requests implementation help, then returns the reasoning trajectory, plan, and justification behind the chosen response.
5. The `adversary` agent stress-tests pending changes before finalization by generating several distinct exploit or judge-gaming artifacts intended to trick the judge, rather than only reporting a single failure mode.
6. The adversary should model the judge's likely response to each exploit candidate, recursively reflect on that forecast, and persist per-turn exploit artifacts such as `candidate.md`, `description.md`, `predicted-judge-response.md`, and `reflection.md` alongside the staged candidate until it converges on the strongest exploit attempt or exhausts the search.
7. The `teacher` and `student` agents may hand off to each other in a bounded multi-turn loop, but within a teacher turn the teacher should finalize steering first and use any student handoff only at the end to elicit a concrete response or solution. End that loop when the teacher predicts the student will improve no further, the student predicts teacher approval, or another explicit exit criterion applies.

## Judge Steering Contract

1. Keep Judge-owned agent files, skill contracts, scripts, templates, and local references (including any `references/` trees) immutable during trainer runs.
2. When the selected target is not `.github/agents/judge.agent.md`, do not write trainer output into `.github/agents/judge.agent.md`, `skills/judge-*/`, or any path under `.github/agents/.trainer-workspace/judge.agent/`. When `.github/agents/judge.agent.md` is the selected target, keep Judge-owned immutable content read-only but write any per-run artifacts only under `.github/agents/.trainer-workspace/judge.agent/iterations/iteration-N/`.
3. Publish iteration-scoped steering under the selected target's local `.trainer-workspace/<prompt-name>/iterations/iteration-N/steering/<agent>/turn-N/STEERING.md` path so every agent turn gets its own artifact.
4. Keep rolling steering summaries under `.trainer-workspace/<prompt-name>/iterations/iteration-N/steering/<agent>/summary.md` so each agent has an iteration-local summary for that prompt workspace.
5. Treat `required_artifacts.latest_iteration_dir` plus the active iteration's `steering/`, `optimize/`, `election/`, and `validation/` outputs as the iteration steering bundle.
6. Treat workspace-root `decision.md`, optional `benchmark.json`, `benchmark.md`, and `review.html` as the cross-run rollup steering bundle.
7. Populate `iterations/iteration-N/candidates/` with judge-ready entries for `original`, `student`, and `adversary`, where each entry contains the staged candidate plus companion artifacts such as `description.md`, `predicted-judge-response.md`, and `reflection.md`; adversary entries should represent concrete exploit attempts rather than risk summaries.
8. Treat `required_artifacts.candidate_dir` and `required_artifacts.candidate_manifest` as the canonical handoff for the staged judge candidate set when they are present. Prefer `candidates.json` as the manifest filename, and have it map each candidate source to its prompt artifact, description artifact, predicted judge response artifact, reflection artifact, and any selection notes.
9. If an adversary candidate wins or reveals a credible exploit, add extra steering guidance for later judge turns that explicitly blocks the newly identified exploit pattern.
   - Treat an exploit as credible when the adversary predicts the judge would rank it at or above the strongest student candidate.
   - Also treat an exploit as credible when it depends on a rubric or coverage gap the current judge bundle does not explicitly guard against.
10. If the old prompt wins, add extra steering guidance for the teacher that explains why the revised candidates regressed and what the student should learn before the next revision.
11. Judge agents and judge skills must read those steering bundles as external, read-only inputs at runtime.

## Dataset And Judge Mode Rules

1. Reuse existing train, validation, and authored eval assets when they already fit the selected target.
2. If any required train, validation, or authored eval assets are missing, call the `researcher` agent first and synthesize the missing assets before optimize.
3. Use `judge_mode=llm_judge` for rows that expose `reference` plus `criteria`, or explicitly set `scoring: llm_judge`.
4. Use `judge_mode=custom` for rows that expose `expected_json`, or use row-level scoring such as `normalized_match`, `json_schema`, or `custom_python`.
5. Keep `judge_mode=deterministic` only for exact-match `expected` tasks that do not require a richer scorer.

## Optimize Output Contract

1. Store optimizer outputs under `iterations/iteration-N/optimize/`.
2. For a normal optimize run, keep `optimized-prompt.md` and `optimize-report.json` together.
3. If optimize returns `mode=manual_followup`, save the JSON payload as `manual-followup-report.json`, answer the returned `model_prompt` yourself, save that answer as `optimized-prompt.md`, and continue using that candidate for the rest of the workflow.
4. Before judge review or election, stage the original prompt, the strongest student candidate, and the strongest adversary candidate under `candidates/original/`, `candidates/student/`, and `candidates/adversary/`.
5. Persist the chosen optimized content back to the selected source file only when the candidate is defensible and validation passes.
