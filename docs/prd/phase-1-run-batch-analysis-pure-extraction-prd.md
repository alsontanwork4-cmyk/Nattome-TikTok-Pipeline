# Phase 1 Run Batch Analysis Pure Extraction PRD

## Problem Statement

The Batch Analysis Run implementation has grown into one large Python file that mixes command-line parsing, runtime configuration, candidate loading, Viral Relevance Selection, Run Folder orchestration, Evidence Bundle creation, Tool Stack execution, output writing, Telegram Delivery, cleanup, and error handling.

This makes the logic flow hard to understand and increases the risk that future changes will bloat the same file further. The current command-line workflow still works and is used by Codex, tests, and automation, so the first improvement must reduce file size and improve Module shape without changing behavior.

The immediate user need is to compact the Batch Analysis Run codebase through pure extraction. The CLI Interface must stay exactly the same so existing commands, tests, skills, and Scheduled Analysis Run prompts continue to work.

## Solution

Phase 1 will convert the current Batch Analysis Run script into a thin CLI Adapter while moving stable, domain-shaped logic into importable Batch Analysis modules.

The CLI Adapter will keep the same command, flags, return codes, and user-visible output. It will parse command-line arguments, call the Batch Analysis Run Module, report errors the same way, and print the same success message.

The first extraction will focus on low-risk, high-clarity areas:

- runtime configuration loading and merging
- candidate file loading
- candidate timestamp parsing and metric extraction
- weighted engagement scoring
- Nattome relevance scoring
- Minimum Eligibility Filter behavior
- Viral Relevance Selection
- candidate normalization
- Batch Analysis Run orchestration entrypoint

This phase will not intentionally fix existing behavior, rename flags, redesign output files, split tests, change schemas, enforce new validation, or alter the Evidence-First Analysis behavior. Known issues found during extraction should be documented for later phases rather than fixed inside Phase 1 unless they are extraction blockers.

## User Stories

1. As a Codex user, I want to run the same Batch Analysis Run command after extraction, so that my existing workflow does not break.
2. As a Codex user, I want the same flags to keep working, so that scheduled prompts and manual commands remain valid.
3. As a Codex user, I want the same success message after a run, so that downstream expectations and tests do not change.
4. As a Codex user, I want the same error messages and return codes for invalid input, so that failures remain predictable.
5. As a maintainer, I want the command-line script to become a thin CLI Adapter, so that it has one clear job.
6. As a maintainer, I want configuration logic extracted into its own Module, so that runtime settings have better Locality.
7. As a maintainer, I want candidate loading extracted into its own Module, so that JSON shape handling is easier to inspect.
8. As a maintainer, I want candidate scoring extracted into its own Module, so that Viral Relevance Selection has a clear Interface.
9. As a maintainer, I want Minimum Eligibility Filter behavior extracted without changing it, so that the refactor remains safe.
10. As a maintainer, I want candidate normalization extracted, so that schema handling does not keep bloating the CLI Adapter.
11. As a maintainer, I want Batch Analysis Run orchestration callable from an importable Module, so that future tests and scheduled runners do not have to import a script by path.
12. As a maintainer, I want current CLI-scale tests to keep passing, so that pure extraction has a clear safety net.
13. As a maintainer, I want no output schema changes in Phase 1, so that existing Run Folder artifacts remain compatible.
14. As a maintainer, I want no Report Form changes in Phase 1, so that Video Evidence Reports are not affected by structural extraction.
15. As a maintainer, I want no Cross-Video Pattern Summary changes in Phase 1, so that weekly interpretation remains stable.
16. As a maintainer, I want no Telegram Delivery changes in Phase 1, so that delivery behavior is not mixed with extraction risk.
17. As a maintainer, I want no Tool Stack behavior changes in Phase 1, so that FFmpeg, OCR, transcription, and download behavior stay stable.
18. As a maintainer, I want future extraction phases to have clearer seams, so that Evidence Bundle capture and output generation can be tackled later.
19. As a maintainer, I want known behavior issues documented separately, so that pure extraction does not become a hidden feature change.
20. As a maintainer, I want the extracted Modules to be domain-shaped, so that the code becomes easier to navigate for humans and AI agents.
21. As a maintainer, I want the extracted Modules to be deep enough to hide messy implementation details, so that callers get more Leverage from smaller Interfaces.
22. As a maintainer, I want raw dictionary conventions concentrated in candidate handling where possible, so that schema drift has better Locality.
23. As a maintainer, I want the Run Folder orchestration entrypoint isolated, so that later phases can reduce orchestration complexity without touching CLI parsing.
24. As a maintainer, I want the first extraction to be small enough to review confidently, so that future extraction work can build on a trusted checkpoint.
25. As a maintainer, I want tests to prove behavior stayed the same, so that I can separate extraction regressions from later design changes.

## Implementation Decisions

- Phase 1 is pure extraction only.
- The command-line Interface must be preserved exactly.
- The script will become a thin CLI Adapter.
- The Batch Analysis Run orchestration will move behind an importable Module Interface.
- Runtime configuration loading and recursive configuration merging will move into a dedicated configuration Module.
- Candidate JSON loading, metric parsing, timestamp parsing, relevance scoring, engagement scoring, filtering, ranking, and normalization will move into a dedicated candidate Module.
- The first phase will use domain-shaped Modules rather than one large extracted file.
- Existing behavior must be preserved even where a later design improvement is obvious.
- The known downloadable-video eligibility gap will not be fixed in Phase 1 unless the extraction cannot proceed without touching it.
- The existing Run Folder layout will not change.
- The existing Batch Output Set will not change.
- The existing Evidence Bundle contents will not change.
- The existing Video Evidence Report Report Form will not change.
- The existing Cross-Video Pattern Summary output will not change.
- The existing Structured JSON Output and Spreadsheet Summary Output will not change.
- The existing Telegram Delivery behavior will not change.
- The existing cleanup behavior will not change.
- The existing Tool Stack execution behavior will not change.
- Existing broad CLI tests will remain the primary regression safety net for Phase 1.
- Focused tests for the extracted Modules are desirable after Phase 1 but are not required during the first extraction unless import behavior becomes risky.
- Any new Module Interface should be simple enough for future callers to use without knowing command-line parsing details.
- Any extracted Module should keep domain vocabulary aligned with the project glossary: Batch Analysis Run, Run Folder, Minimum Eligibility Filter, Viral Relevance Selection, Default Batch, Evidence Bundle, and Batch Output Set.

## Testing Decisions

- Tests should validate external behavior, not the internal file movement.
- Existing tests should remain in place for Phase 1.
- The current CLI behavior should continue to be tested through the same command-style paths.
- Existing tests should confirm that a timestamped Run Folder is still created.
- Existing tests should confirm invalid configuration still fails before creating a Run Folder.
- Existing tests should confirm candidates are still filtered, ranked, selected, and written the same way.
- Existing tests should confirm Evidence Bundles and downstream outputs still appear when candidates are supplied.
- Existing tests should confirm missing tooling is still recorded honestly rather than fabricated.
- Existing tests should confirm Telegram Delivery still skips when credentials are missing.
- Existing tests should confirm cleanup and refinement hooks are unaffected.
- New focused tests may be added later for configuration merging and candidate selection once Phase 1 is stable.
- A good Phase 1 test result is that all existing tests pass with no expected output changes.
- A bad Phase 1 test result is any output difference caused only by moving code.

## Out of Scope

- Fixing candidate schema mismatches between Daily Discovery and Batch Analysis Run is out of scope.
- Enforcing downloadable video eligibility is out of scope for Phase 1.
- Splitting Evidence Bundle capture into its own Module is out of scope for Phase 1.
- Extracting Tool Stack Adapters is out of scope for Phase 1.
- Extracting output writers or a Batch Output Set read model is out of scope for Phase 1.
- Extracting Telegram Delivery into a shared Module is out of scope for Phase 1.
- Redesigning tests into focused test files is out of scope for Phase 1.
- Changing the Run Folder layout is out of scope.
- Changing markdown, JSON, or spreadsheet schemas is out of scope.
- Changing the Report Form is out of scope.
- Changing scoring thresholds or ranking formulas is out of scope.
- Adding new product features is out of scope.

## Further Notes

- This PRD is intentionally narrower than the full Nattome TikTok OCR Video Evidence Pipeline PRD.
- The goal is to create a stable checkpoint before deeper extraction phases.
- The recommended next PRD after Phase 1 should cover Evidence Bundle capture as a deep Module.
- The current broad test suite is not the final desired test shape, but it is the right safety net for pure extraction.
- The extraction should reduce future bloating by making the CLI Adapter boring and small.
