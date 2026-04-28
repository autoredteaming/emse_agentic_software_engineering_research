# RQ4 — Top-20 High-Damage Case Study Package

The following PRs are ranked by predicted composite damage score on the RQ4 test set. A human author should read 5 of them in detail and extract qualitative insights about WHAT KIND of damage agent PRs introduce (logic edge cases? hidden coupling? API mis-use? test gaps?).


## Case 1 — PR #1883 (Claude_Code)
- **Repo**: `mendableai/firecrawl`
- **Task type**: `fix`
- **Language**: TypeScript
- **Damage score**: 10.371
- **Signals**: text_strict=0, refs=3, followups_30pct=0
- **Size**: +6/-0 LOC, 1 files, tests-in-PR=0
- **Review**: 1 reviews, merge in 0.18h
- **URL**: https://github.com/mendableai/firecrawl/pull/1883
- **Title**: fix(go): add mutex to prevent concurrent access issues in html-to-markdown

<details><summary>PR body (first 800 chars)</summary>


Adds global mutex to serialize all calls to ConvertHTMLToMarkdown function
to prevent race conditions and heap corruption that was causing runtime panics.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
    
<!-- This is an auto-generated description by cubic. -->
---

## Summary by cubic
Added a global mutex to the ConvertHTMLToMarkdown function to prevent race conditions and runtime panics caused by concurrent access.

- **Bug Fixes**
  - Serializes all calls to ConvertHTMLToMarkdown to avoid heap corruption.

<!-- End of auto-generated description by cubic. -->



</details>

**Top files modified**:
  - `apps/api/sharedLibs/go-html-to-md/html-to-markdown.go` (+6/-0)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 2 — PR #276 (Devin)
- **Repo**: `enzonotario/vitepress-openapi`
- **Task type**: `docs`
- **Language**: TypeScript
- **Damage score**: 7.106
- **Signals**: text_strict=1, refs=4, followups_30pct=0
- **Size**: +508/-345 LOC, 4 files, tests-in-PR=0
- **Review**: 0 reviews, merge in 94.59h
- **URL**: https://github.com/enzonotario/vitepress-openapi/pull/276
- **Title**: docs: add component API documentation for OASpec and OAOperation

<details><summary>PR body (first 800 chars)</summary>


# feat: add comprehensive component API documentation for OASpec and OAOperation

## Summary

This PR resolves issue #275 by adding complete component API documentation for the `OASpec` and `OAOperation` components. The documentation includes:

- **New Components section** in the documentation sidebar with overview and individual component pages
- **Comprehensive prop tables** with types, defaults, and descriptions for all component properties
- **Event and slot documentation** covering all available customization points
- **Usage examples** showing local vs remote spec patterns with `ScopeConfigurationTabs`
- **Best practices guidance** for performance, error handling, and VitePress integration
- **Clear explanation** of the difference between `spec` and `spec-url` props

The documentatio

</details>

**Top files modified**:
  - `docs/components/oa-operation.md` (+238/-0)
  - `docs/components/oa-spec.md` (+201/-0)
  - `docs/components/oa-operation.md` (+2/-188)
  - `docs/components/oa-spec.md` (+4/-156)
  - `docs/components/index.md` (+41/-0)
  - `docs/.vitepress/config.mts` (+21/-0)
  - `docs/components/index.md` (+1/-1)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 3 — PR #10624 (Copilot)
- **Repo**: `dotnet/aspire`
- **Task type**: `fix`
- **Language**: C#
- **Damage score**: 7.106
- **Signals**: text_strict=1, refs=3, followups_30pct=1
- **Size**: +41/-0 LOC, 2 files, tests-in-PR=1
- **Review**: 3 reviews, merge in 0.57h
- **URL**: https://github.com/dotnet/aspire/pull/10624
- **Title**: Fix GitHubModels health check dependency on IHttpClientFactory

<details><summary>PR body (first 800 chars)</summary>


The GitHubModels health check was failing when `IHttpClientFactory` was not explicitly registered by the user, causing the following exception:

```
System.InvalidOperationException: No service for type 'System.Net.Http.IHttpClientFactory' has been registered.
   at Microsoft.Extensions.DependencyInjection.ServiceProviderServiceExtensions.GetRequiredService(IServiceProvider provider, Type serviceType)
   at Aspire.Hosting.GitHubModelsExtensions.<>c__DisplayClass2_0.<WithHealthCheck>b__0(IServiceProvider sp)
```

## Root Cause
The `WithHealthCheck` method in `GitHubModelsExtensions.cs` was calling `sp.GetRequiredService<IHttpClientFactory>()` without ensuring that the HTTP client services were registered first.

## Solution
Modified the `WithHealthCheck` method to automatically call `builde

</details>

**Top files modified**:
  - `tests/Aspire.Hosting.GitHub.Models.Tests/GitHubModelsExtensionTests.cs` (+20/-0)
  - `tests/Aspire.Hosting.GitHub.Models.Tests/GitHubModelsExtensionTests.cs` (+18/-0)
  - `src/Aspire.Hosting.GitHub.Models/GitHubModelsExtensions.cs` (+3/-0)
  - `None` (+0/-0)

**Linked issues**:
  - [closed] Health check for GitHubModels fails when IHttpClientFactory is not registered

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #10626 [fix] [release/9.4] Fix GitHubModels health check dependency on IHttpClientFactory (overlap 1.00)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 4 — PR #5660 (Cursor)
- **Repo**: `elizaOS/eliza`
- **Task type**: `fix`
- **Language**: TypeScript
- **Damage score**: 6.446
- **Signals**: text_strict=1, refs=2, followups_30pct=0
- **Size**: +10/-5 LOC, 2 files, tests-in-PR=0
- **Review**: 0 reviews, merge in 0.02h
- **URL**: https://github.com/elizaOS/eliza/pull/5660
- **Title**: Prevent undefined model use restoration

<details><summary>PR body (first 800 chars)</summary>


```
<!-- Use this template by filling in information and copying and pasting relevant items out of the HTML comments. -->

# Relates to

<!-- LINK TO ISSUE OR TICKET -->
None

# Risks

<!--
Low, medium, large. List what kind of risks and what could be affected.
-->
Low. This PR adds validation and error handling, preventing a runtime issue.

# Background

## What does this PR do?

This PR adds validation to the `SimpleReasoningService` to ensure `runtime.useModel` is a valid function during construction and before it's restored in the `disable()` method.

## What kind of change is this?

<!--
Bug fixes (non-breaking change which fixes an issue)
Improvements (misc. changes to existing features)
Features (non-breaking change which adds functionality)
Updates (new versions of included code)
-

</details>

**Top files modified**:
  - `packages/plugin-training/src/mvp/simple-reasoning-service.ts` (+8/-0)
  - `packages/plugin-training/src/cli/commands/test-fine-tuned.ts` (+2/-5)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 5 — PR #662 (Devin)
- **Repo**: `antiwork/gumroad`
- **Task type**: `chore`
- **Language**: Ruby
- **Damage score**: 6.416
- **Signals**: text_strict=1, refs=2, followups_30pct=1
- **Size**: +1/-1 LOC, 1 files, tests-in-PR=0
- **Review**: 1 reviews, merge in 0.05h
- **URL**: https://github.com/antiwork/gumroad/pull/662
- **Title**: Update S3 presigned URL expiry from 1 week to 1 year in GenerateSalesReportJob

<details><summary>PR body (first 800 chars)</summary>


# Update S3 presigned URL expiry from 1 week to 1 year in GenerateSalesReportJob

## Summary

Updated the S3 presigned URL expiry time in `GenerateSalesReportJob` from 1 week to 1 year. This change extends the validity of download links for sales reports that are generated and sent via Slack notifications from 7 days to 365 days.

**Files changed:**
- `app/sidekiq/generate_sales_report_job.rb` - Changed line 51 from `expires_in: 1.week.to_i` to `expires_in: 1.year.to_i`

## Review & Testing Checklist for Human

- [ ] **Verify requirement accuracy**: Confirm 1 year is the correct expiry time (not 1 month, 6 months, etc.)
- [ ] **Security review**: Assess security implications of longer-lived download URLs (365 days vs 7 days)
- [ ] **End-to-end testing**: Generate a sales report and verify 

</details>

**Top files modified**:
  - `app/sidekiq/generate_sales_report_job.rb` (+1/-1)

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #665 [fix] Remove expires_in parameter from S3 presigned URL in GenerateSalesReportJob (overlap 1.00)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 6 — PR #10453 (Copilot)
- **Repo**: `dotnet/aspire`
- **Task type**: `refactor`
- **Language**: C#
- **Damage score**: 6.377
- **Signals**: text_strict=1, refs=3, followups_30pct=0
- **Size**: +225/-277 LOC, 13 files, tests-in-PR=1
- **Review**: 2 reviews, merge in 13.23h
- **URL**: https://github.com/dotnet/aspire/pull/10453
- **Title**: Remove deprecated parameterless GetDashboardUrlsAsync method from AppHostRpcTarget

<details><summary>PR body (first 800 chars)</summary>


## Description

This PR removes the deprecated parameterless `GetDashboardUrlsAsync()` method from the `AppHostRpcTarget` class as requested in the issue. This method was an old API that is no longer used and should be cleaned up.

## Changes Made

- Removed the `GetDashboardUrlsAsync()` method without parameters from `src/Aspire.Hosting/Backchannel/AppHostRpcTarget.cs` (lines 120-123)
- The method with `CancellationToken` parameter remains unchanged and continues to be used by all existing code

## Impact

- **No breaking changes**: All existing usage already calls the overload with `CancellationToken` parameter
- **No interface changes**: The `IAppHostBackchannel` interface only defines the version with `CancellationToken`
- **Clean removal**: No other code references the parameterless v

</details>

**Top files modified**:
  - `eng/Version.Details.xml` (+97/-97)
  - `eng/Versions.props` (+58/-57)
  - `Directory.Packages.props` (+26/-25)
  - `src/Components/Aspire.OpenAI/ConfigurationSchema.json` (+40/-0)
  - `tests/Aspire.Hosting.Tests/Backchannel/AppHostBackchannelTests.cs` (+0/-35)
  - `src/Aspire.Cli/Backchannel/ExtensionBackchannel.cs` (+0/-19)
  - `src/Aspire.Cli/Backchannel/AppHostBackchannel.cs` (+0/-16)
  - `tests/Aspire.Cli.Tests/TestServices/TestAppHostBackchannel.cs` (+0/-11)
  - `src/Aspire.Hosting/Backchannel/AppHostRpcTarget.cs` (+0/-7)
  - `src/Aspire.Hosting/Backchannel/AppHostRpcTarget.cs` (+0/-5)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 7 — PR #95356 (Cursor)
- **Repo**: `getsentry/sentry`
- **Task type**: `fix`
- **Language**: Python
- **Damage score**: 6.172
- **Signals**: text_strict=1, refs=3, followups_30pct=1
- **Size**: +3/-0 LOC, 1 files, tests-in-PR=0
- **Review**: 2 reviews, merge in 0.43h
- **URL**: https://github.com/getsentry/sentry/pull/95356
- **Title**: fix(detectors): TypeError

<details><summary>PR body (first 800 chars)</summary>


Fixes `TypeError: 'NoneType' object is not subscriptable` in `SQLInjectionDetector`.

This error occurred when `extract_request_data` encountered `None` or malformed entries in the request query parameters or body, leading to a crash when attempting to access `query_pair[1]`.

The fix adds a defensive check to skip `None` or insufficiently sized `query_pair` entries, making the detector more robust against unexpected input data.

[SENTRY-FOR-SENTRY-5ZQH](https://sentry.my.sentry.io/organizations/sentry/issues/2313274/)

</details>

**Top files modified**:
  - `src/sentry/performance_issues/detectors/sql_injection_detector.py` (+3/-0)

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #95516 [fix] fix(issue): add padding to stack trace vars (overlap 1.00)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 8 — PR #95572 (Cursor)
- **Repo**: `getsentry/sentry`
- **Task type**: `feat`
- **Language**: Python
- **Damage score**: 6.088
- **Signals**: text_strict=1, refs=2, followups_30pct=0
- **Size**: +2/-2 LOC, 1 files, tests-in-PR=0
- **Review**: 1 reviews, merge in 20.08h
- **URL**: https://github.com/getsentry/sentry/pull/95572
- **Title**: Make log text wrapping configurable with white-space prop

<details><summary>PR body (first 800 chars)</summary>


resolves JAVASCRIPT-32A9

render line breaks (new lines) in log messages when a user expands the log item to view log item details.

<img width="1692" height="610" alt="image" src="https://github.com/user-attachments/assets/457d2b3f-31bf-4616-9c26-8d1b78fe030f" />

</details>

**Top files modified**:
  - `static/app/views/explore/logs/styles.tsx` (+2/-2)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 9 — PR #1219 (Claude_Code)
- **Repo**: `OpenAgentsInc/openagents`
- **Task type**: `feat`
- **Language**: TypeScript
- **Damage score**: 6.055
- **Signals**: text_strict=0, refs=6, followups_30pct=0
- **Size**: +4629/-362 LOC, 29 files, tests-in-PR=1
- **Review**: 0 reviews, merge in 0.12h
- **URL**: https://github.com/OpenAgentsInc/openagents/pull/1219
- **Title**: feat: Complete 4-phase authentication integration - Remove duplication & add production hardening

<details><summary>PR body (first 800 chars)</summary>


## Summary
- Completed all 4 phases of authentication integration as outlined in #1215
- Removed all manual authentication duplication from the Convex Rust client
- Implemented production-ready JWT authentication with comprehensive monitoring and error recovery

## Test plan
- [x] Run `cargo test` - All 137 tests passing ✅
- [x] Verify no manual auth injection in `convex_impl.rs`
- [x] Confirm clean Tauri command signatures without auth parameters
- [x] Test token storage and retrieval functionality
- [x] Validate error recovery mechanisms
- [x] Check authentication monitoring integration

## Related Issues
Fixes #1215 - Integrate Enhanced Convex Rust Client with OpenAuth Authentication System

## Implementation Details

### Phase 1: Foundation & Analysis ✅
- Created comprehensive authenti

</details>

**Top files modified**:
  - `apps/desktop/src-tauri/src/claude_code/convex_impl.rs` (+602/-58)
  - `apps/desktop/src-tauri/src/claude_code/error_recovery.rs` (+633/-0)
  - `apps/desktop/CORS_CONFIGURATION.md` (+455/-0)
  - `apps/desktop/src-tauri/src/tests/jwt_integration_phase3.rs` (+366/-0)
  - `apps/desktop/src-tauri/src/claude_code/auth_metrics.rs` (+320/-0)
  - `apps/desktop/src-tauri/src/claude_code/token_storage.rs` (+320/-0)
  - `apps/desktop/src-tauri/src/claude_code/cors_utils.rs` (+292/-0)
  - `apps/desktop/src-tauri/src/tests/convex_auth_flow.rs` (+274/-0)
  - `apps/desktop/src-tauri/src/claude_code/convex_impl.rs` (+200/-22)
  - `apps/desktop/src-tauri/src/tests/auth_integration_baseline.rs` (+215/-0)

**Linked issues**:
  - [closed] Integrate Enhanced Convex Rust Client with OpenAuth Authentication System

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 10 — PR #4414 (Cursor)
- **Repo**: `acts-project/acts`
- **Task type**: `ci`
- **Language**: C++
- **Damage score**: 5.978
- **Signals**: text_strict=1, refs=2, followups_30pct=0
- **Size**: +2611/-1510 LOC, 63 files, tests-in-PR=1
- **Review**: 2 reviews, merge in 55.64h
- **URL**: https://github.com/acts-project/acts/pull/4414
- **Title**: ci: Add check for devcontainer configuration

<details><summary>PR body (first 800 chars)</summary>


Add a basic check that verifies the dev container can load, configure and build ACTS.

--- END COMMIT MESSAGE ---

Any further description goes here, @-mentions are ok here!

- Use a *conventional commits* prefix: [quick summary](https://www.conventionalcommits.org/en/v1.0.0/#summary)
  - We mostly use `feat`, `fix`, `refactor`, `docs`, `chore` and `build` types.
- A milestone will be assigned by one of the maintainers


</details>

**Top files modified**:
  - `Examples/Io/EDM4hep/src/EDM4hepSimInputConverter.cpp` (+554/-329)
  - `Plugins/Root/src/RootMaterialMapIo.cpp` (+476/-0)
  - `Plugins/Root/src/RootMaterialTrackIo.cpp` (+339/-0)
  - `Plugins/Root/src/RootMaterialTrackAccessor.cpp` (+0/-327)
  - `Examples/Io/Root/src/RootMaterialWriter.cpp` (+79/-186)
  - `Tests/UnitTests/Plugins/Root/RootMaterialMapIoTests.cpp` (+262/-0)
  - `Plugins/Root/include/Acts/Plugins/Root/RootMaterialTrackIo.hpp` (+205/-0)
  - `Plugins/Root/include/Acts/Plugins/Root/RootMaterialMapIo.hpp` (+196/-0)
  - `Plugins/Root/include/Acts/Plugins/Root/RootMaterialTrackAccessor.hpp` (+0/-185)
  - `Examples/Io/Root/src/RootMaterialDecorator.cpp` (+28/-156)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 11 — PR #95934 (Cursor)
- **Repo**: `getsentry/sentry`
- **Task type**: `feat`
- **Language**: Python
- **Damage score**: 5.929
- **Signals**: text_strict=1, refs=1, followups_30pct=2
- **Size**: +114/-63 LOC, 4 files, tests-in-PR=1
- **Review**: 3 reviews, merge in 0.47h
- **URL**: https://github.com/getsentry/sentry/pull/95934
- **Title**: Expose Sentry MCP configuration endpoint

<details><summary>PR body (first 800 chars)</summary>


<!-- Describe your PR here. -->
Exposes a `/.well-known/mcp.json` endpoint to provide configuration details for Sentry's MCP server.

This PR:
*   Adds a new endpoint at `/.well-known/mcp.json`.
*   Serves a JSON payload containing Sentry's MCP name, description, and endpoint.
*   Returns a 404 Not Found for self-hosted instances, mirroring the `security.txt` behavior.
*   Includes appropriate caching headers.
*   Adds tests to verify behavior in both SaaS and self-hosted modes.

<!--

  Sentry employees and contractors can delete or ignore the following.

-->

### Legal Boilerplate

Look, I get it. The entity doing business as "Sentry" was incorporated in the State of Delaware in 2015 as Functional Software, Inc. and is gonna need some rights from me in order to utilize 

</details>

**Top files modified**:
  - `MCP_IMPLEMENTATION_SUMMARY.md` (+61/-0)
  - `MCP_IMPLEMENTATION_SUMMARY.md` (+0/-61)
  - `tests/sentry/web/test_api.py` (+32/-0)
  - `src/sentry/web/api.py` (+14/-0)
  - `src/sentry/web/urls.py` (+5/-0)
  - `src/sentry/web/api.py` (+1/-1)
  - `tests/sentry/web/test_api.py` (+1/-1)

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #95516 [fix] fix(issue): add padding to stack trace vars (overlap 0.50)
  - #95780 [feat] feat(replay): Show CTA when org is not opted into gen ai features (overlap 0.50)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 12 — PR #1428 (OpenAI_Codex)
- **Repo**: `EricLBuehler/mistral.rs`
- **Task type**: `fix`
- **Language**: Rust
- **Damage score**: 5.903
- **Signals**: text_strict=1, refs=5, followups_30pct=1
- **Size**: +65/-64 LOC, 7 files, tests-in-PR=0
- **Review**: 2 reviews, merge in 2.74h
- **URL**: https://github.com/EricLBuehler/mistral.rs/pull/1428
- **Title**: Fix CUDA context switching, bind thread on CudaStorage drop

<details><summary>PR body (first 800 chars)</summary>


Related: https://github.com/EricLBuehler/candle/pull/82

Fixes #1406, #1401, #1399, #1394

## Summary
- add `set_cuda_context` helper to utils
- call helper in `Llama::forward_embeds` when switching devices
- document why context switching is needed

## Testing
- `cargo fmt` *(fails: rustfmt component not installed)*
- `cargo test --workspace --no-run` *(failed: build interrupted due to environment limits)*

------
https://chatgpt.com/codex/tasks/task_e_684063442160832289cdfb7840b2aac5

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->
## Summary by CodeRabbit

## Summary by CodeRabbit

- **Chores**
  - Updated internal dependencies to newer revisions for improved stability and compatibility.

- **Bug Fixes**
  - Improved device mapping log

</details>

**Top files modified**:
  - `mistralrs-core/src/utils/mod.rs` (+16/-0)
  - `mistralrs-core/src/pipeline/inputs_processor.rs` (+8/-8)
  - `mistralrs-core/src/utils/mod.rs` (+0/-16)
  - `Cargo.lock` (+6/-6)
  - `Cargo.lock` (+6/-6)
  - `mistralrs-core/src/models/llama.rs` (+8/-1)
  - `mistralrs-core/src/models/llama.rs` (+1/-8)
  - `Cargo.toml` (+4/-4)
  - `mistralrs-core/src/pipeline/inputs_processor.rs` (+4/-4)
  - `mistralrs-core/src/pipeline/inputs_processor.rs` (+4/-4)

**Linked issues**:
  - [closed] NV Cosmos Failing Device Local Storage

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #1427 [feat] Add tool callback support (overlap 0.71)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 13 — PR #40035 (Copilot)
- **Repo**: `microsoft/PowerToys`
- **Task type**: `fix`
- **Language**: C#
- **Damage score**: 5.827
- **Signals**: text_strict=1, refs=3, followups_30pct=0
- **Size**: +10/-4 LOC, 2 files, tests-in-PR=0
- **Review**: 3 reviews, merge in 117.68h
- **URL**: https://github.com/microsoft/PowerToys/pull/40035
- **Title**: Fix default browser detection for Windows 11 24H2 by checking UserChoiceLatest registry key

<details><summary>PR body (first 800 chars)</summary>


## Summary

This PR fixes an issue where PowerToys Web Search and PowerToys Run would always open Microsoft Edge instead of the user's default browser on Windows 11 24H2, even when a different browser like Firefox was set as the default.

## Root Cause

Windows 11 24H2 introduced a change where default browser associations are now stored in a new registry location:
- **New location**: `HKEY_CURRENT_USER\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoiceLatest`
- **Old location**: `HKEY_CURRENT_USER\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice`

PowerToys was only checking the old registry location, causing it to fail to find the default browser and fall back to Microsoft Edge.

## Changes Made

Updated both `DefaultBrowserInfo.cs`

</details>

**Top files modified**:
  - `src/modules/cmdpal/ext/Microsoft.CmdPal.Ext.WebSearch/Helpers/DefaultBrowserInfo.cs` (+5/-2)
  - `src/modules/launcher/Wox.Plugin/Common/DefaultBrowserInfo.cs` (+5/-2)
  - `None` (+0/-0)

**Linked issues**:
  - [closed] Web Search uses Microsoft Edge even though default is set to Firefox

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 14 — PR #895 (Copilot)
- **Repo**: `sysadminsmedia/homebox`
- **Task type**: `fix`
- **Language**: Go
- **Damage score**: 5.765
- **Signals**: text_strict=1, refs=1, followups_30pct=0
- **Size**: +142/-10 LOC, 2 files, tests-in-PR=1
- **Review**: 1 reviews, merge in 2.15h
- **URL**: https://github.com/sysadminsmedia/homebox/pull/895
- **Title**: Fix photo display issue when adding additional attachments to items

<details><summary>PR body (first 800 chars)</summary>


## Problem

When a photo is the first attachment added to an item, it displays correctly in the item card view. However, if any additional attachments (PDFs, manuals, receipts) are uploaded afterward, the photo disappears from the card view and shows the default Homebox pattern instead.

**Before fix:**
![Item with photo visible](https://github.com/user-attachments/assets/574124b3-5919-4179-a35f-f43d0b80fefe)

**After adding PDF (showing the bug):**
![Item showing default pattern instead of photo](https://github.com/user-attachments/assets/1667e077-42b0-4f66-8fd3-7cef109cc94b)

## Root Cause

The issue was in the backend attachment update logic in `repo_item_attachments.go`. When ANY attachment was updated, the code incorrectly removed the primary status from ALL other attachments, includi

</details>

**Top files modified**:
  - `backend/internal/data/repo/repo_item_attachments_test.go` (+129/-0)
  - `backend/internal/data/repo/repo_item_attachments.go` (+13/-10)
  - `None` (+0/-0)

**Linked issues**:
  - [closed] Adding an additional attachment to an item after a photo has already been added causes the photo no longer display in the item card

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 15 — PR #13499 (OpenAI_Codex)
- **Repo**: `hmislk/hmis`
- **Task type**: `feat`
- **Language**: HTML
- **Damage score**: 5.759
- **Signals**: text_strict=1, refs=0, followups_30pct=19
- **Size**: +191/-2 LOC, 3 files, tests-in-PR=0
- **Review**: 0 reviews, merge in 0.01h
- **URL**: https://github.com/hmislk/hmis/pull/13499
- **Title**: Add configurable transfer request receipt

<details><summary>PR body (first 800 chars)</summary>


## Summary
- add default configuration for Pharmacy Transfer Request Receipt
- implement a new composite receipt `pharmacy_transfer_request_receipt.xhtml`
- use new receipt on pharmacy transfer request page

## Testing
- `mvn test` *(fails: command not found)*

------
https://chatgpt.com/codex/tasks/task_e_686128089220832f9881076664a9d84f

</details>

**Top files modified**:
  - `src/main/webapp/resources/pharmacy/pharmacy_transfer_request_receipt.xhtml` (+128/-0)
  - `src/main/java/com/divudi/bean/common/ConfigOptionApplicationController.java` (+60/-0)
  - `src/main/webapp/pharmacy/pharmacy_transfer_request.xhtml` (+3/-2)

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #13681 [feat] 11966-selectivey-render-pharmacy-reports (overlap 0.33)
  - #13619 [feat] Add patient name capitalization options (overlap 0.33)
  - #13654 [feat] Add rate calculations on transfer request page (overlap 0.33)
  - #13660 [feat] show recent departments on transfer request page (overlap 0.33)
  - #13644 [feat] Implement save/finalize flow for transfer requests (overlap 0.33)
  - #13656 [feat] Enhance transfer request costing controls (overlap 0.33)
  - #13646 [feat] Add Transfer Request finalization flow (overlap 0.33)
  - #13657 [feat] Add qty and rate recalculation (overlap 0.33)
  - #13648 [fix] Fix variable name and remove debug prints (overlap 0.33)
  - #13507 [fix] Remove duplicated history column and unify prefix (overlap 0.67)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 16 — PR #13490 (OpenAI_Codex)
- **Repo**: `hmislk/hmis`
- **Task type**: `feat`
- **Language**: HTML
- **Damage score**: 5.757
- **Signals**: text_strict=1, refs=0, followups_30pct=19
- **Size**: +16/-3 LOC, 2 files, tests-in-PR=0
- **Review**: 0 reviews, merge in 0.00h
- **URL**: https://github.com/hmislk/hmis/pull/13490
- **Title**: Add item detail button to transfer request

<details><summary>PR body (first 800 chars)</summary>


## Summary
- add item history button to view selected item details in `pharmacy_transfer_request.xhtml`
- remove focus listener that previously loaded item details on focus
- support new button by implementing `displayItemDetails` in `TransferRequestController`

## Testing
- `mvn -q test` *(fails: `mvn` not found)*

------
https://chatgpt.com/codex/tasks/task_e_6860cb93dc54832fb30c6504411e7dae

</details>

**Top files modified**:
  - `src/main/webapp/pharmacy/pharmacy_transfer_request.xhtml` (+12/-3)
  - `src/main/java/com/divudi/bean/pharmacy/TransferRequestController.java` (+4/-0)

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #13654 [feat] Add rate calculations on transfer request page (overlap 1.00)
  - #13499 [feat] Add configurable transfer request receipt (overlap 0.50)
  - #13660 [feat] show recent departments on transfer request page (overlap 1.00)
  - #13496 [fix] Fix transfer request item history trigger (overlap 0.50)
  - #13644 [feat] Implement save/finalize flow for transfer requests (overlap 1.00)
  - #13656 [feat] Enhance transfer request costing controls (overlap 1.00)
  - #13646 [feat] Add Transfer Request finalization flow (overlap 1.00)
  - #13657 [feat] Add qty and rate recalculation (overlap 1.00)
  - #13648 [fix] Fix variable name and remove debug prints (overlap 1.00)
  - #13507 [fix] Remove duplicated history column and unify prefix (overlap 0.50)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 17 — PR #2621 (OpenAI_Codex)
- **Repo**: `strapi/documentation`
- **Task type**: `docs`
- **Language**: JavaScript
- **Damage score**: 5.752
- **Signals**: text_strict=0, refs=2, followups_30pct=0
- **Size**: +185/-172 LOC, 4 files, tests-in-PR=0
- **Review**: 2 reviews, merge in 0.23h
- **URL**: https://github.com/strapi/documentation/pull/2621
- **Title**: Improve GraphQL queries explanations (Flat vs. Relay-style)

<details><summary>PR body (first 800 chars)</summary>


This PR clarifies GraphQL queries (flat queries vs. Relay-style) and slightly improve the related migration documentation

</details>

**Top files modified**:
  - `docusaurus/docs/cms/migration/v4-to-v5/breaking-changes/graphql-api-updated.md` (+160/-160)
  - `docusaurus/docs/cms/migration/v4-to-v5/introduction-and-faq.md` (+6/-0)
  - `docusaurus/docs/cms/api/graphql.md` (+6/-0)
  - `docusaurus/docs/cms/migration/v4-to-v5/introduction-and-faq.md` (+0/-6)
  - `docusaurus/docs/cms/api/graphql.md` (+3/-2)
  - `docusaurus/docs/cms/migration/v4-to-v5/breaking-changes/graphql-api-updated.md` (+2/-2)
  - `docusaurus/docs/cms/migration/v4-to-v5/breaking-changes/graphql-api-updated.md` (+3/-0)
  - `docusaurus/docs/cms/migration/v4-to-v5/breaking-changes/graphql-api-updated.md` (+1/-1)
  - `docusaurus/docs/cms/migration/v4-to-v5/step-by-step.md` (+0/-1)
  - `docusaurus/docs/cms/migration/v4-to-v5/breaking-changes/graphql-api-updated.md` (+1/-0)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 18 — PR #93304 (Cursor)
- **Repo**: `getsentry/sentry`
- **Task type**: `feat`
- **Language**: Python
- **Damage score**: 5.732
- **Signals**: text_strict=1, refs=2, followups_30pct=3
- **Size**: +433/-52 LOC, 9 files, tests-in-PR=1
- **Review**: 2 reviews, merge in 16.02h
- **URL**: https://github.com/getsentry/sentry/pull/93304
- **Title**: feat(open-pr-comments): Add C# support

<details><summary>PR body (first 800 chars)</summary>


Adds Open PR Comment Support for C#

Built using Cursor Background Agent with some cleanup by me, pretty cool!

</details>

**Top files modified**:
  - `tests/sentry/integrations/source_code_management/test_language_parsers.py` (+252/-0)
  - `src/sentry/integrations/source_code_management/language_parsers.py` (+57/-0)
  - `tests/sentry/integrations/github/tasks/test_open_pr_comment.py` (+53/-0)
  - `src/sentry/integrations/source_code_management/language_parsers.py` (+18/-0)
  - `src/sentry/integrations/source_code_management/commit_context.py` (+11/-2)
  - `src/sentry/integrations/github/integration.py` (+11/-2)
  - `src/sentry/integrations/gitlab/integration.py` (+11/-2)
  - `src/sentry/integrations/github/integration.py` (+2/-9)
  - `src/sentry/integrations/gitlab/integration.py` (+2/-8)
  - `src/sentry/integrations/source_code_management/commit_context.py` (+1/-9)

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #95516 [fix] fix(issue): add padding to stack trace vars (overlap 0.56)
  - #94169 [feat] feat(platform): Add React Router Framework onboarding platform in FE (overlap 0.44)
  - #93402 [feat] feat(open-pr-comments): Golang Language Support (overlap 0.44)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 19 — PR #5489 (Claude_Code)
- **Repo**: `elizaOS/eliza`
- **Task type**: `feat`
- **Language**: TypeScript
- **Damage score**: 5.732
- **Signals**: text_strict=1, refs=1, followups_30pct=0
- **Size**: +1013/-340 LOC, 6 files, tests-in-PR=1
- **Review**: 1 reviews, merge in 0.00h
- **URL**: https://github.com/elizaOS/eliza/pull/5489
- **Title**: feat: add comprehensive test coverage for forms plugin

<details><summary>PR body (first 800 chars)</summary>


## Summary

This PR enhances the forms plugin with comprehensive test coverage including:
- Database persistence tests
- Zod validation tests
- Transaction safety tests
- Error handling improvements

## Changes

### 🧪 Test Coverage Enhancements
- **Database persistence tests** - Tests for graceful handling when database tables are missing and successful persistence when available
- **Zod validation tests** - Tests for field type validation and proper handling of falsy values (0, false, empty strings)
- **Transaction safety tests** - Tests for rollback behavior on database errors
- **Integration test fix** - Updated LLM error handling test to match actual behavior

### 🔧 Implementation Details
1. **Database Persistence Tests**:
   - Gracefully handles missing database tables
   - Continues 

</details>

**Top files modified**:
  - `packages/plugin-forms/src/services/forms-service.ts` (+387/-103)
  - `packages/plugin-forms/src/__tests__/forms-service.test.ts` (+267/-20)
  - `packages/plugin-forms/src/services/forms-service.ts` (+182/-35)
  - `packages/plugin-forms/src/__tests__/integration.test.ts` (+159/-17)
  - `bun.lock` (+6/-149)
  - `packages/plugin-forms/src/services/forms-service.ts` (+9/-11)
  - `packages/plugin-forms/package.json` (+2/-3)
  - `packages/plugin-forms/src/__tests__/integration.test.ts` (+1/-1)
  - `packages/plugin-forms/src/actions/cancel-form.ts` (+0/-1)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway:

## Case 20 — PR #2819 (OpenAI_Codex)
- **Repo**: `KomodoPlatform/komodo-wallet`
- **Task type**: `fix`
- **Language**: Dart
- **Damage score**: 5.730
- **Signals**: text_strict=1, refs=1, followups_30pct=7
- **Size**: +61/-29 LOC, 2 files, tests-in-PR=0
- **Review**: 0 reviews, merge in 0.01h
- **URL**: https://github.com/KomodoPlatform/komodo-wallet/pull/2819
- **Title**: fix(feedback): validate message not empty

<details><summary>PR body (first 800 chars)</summary>


## Summary
- add `feedbackMaxLength` constant
- validate feedback text isn't empty or too long
- show feedback validation errors in the UI

## Testing
- `dart format lib/shared/constants.dart lib/services/feedback/custom_feedback_form.dart`
- `flutter analyze` *(fails: requires Flutter SDK >=3.32.2)*

------
https://chatgpt.com/codex/tasks/task_e_685bf299429083268464bf4e13020cb7

</details>

**Top files modified**:
  - `lib/services/feedback/custom_feedback_form.dart` (+54/-26)
  - `lib/shared/constants.dart` (+7/-3)

**Follow-up PRs (within 180 days, file overlap ≥30%)**:
  - #2968 [fix] fix(ui): remove conflicting autofocus and add new focuses (overlap 0.50)
  - #2897 [fix] fix(trading): remove legacy fallback (overlap 0.50)
  - #2898 [refactor] refactor(feedback): adopt bloc pattern (overlap 0.50)
  - #2807 [feat] feat(feedback): require contact details for support (overlap 1.00)
  - #2899 [fix] fix(wallet): misc wallet page fixes (overlap 0.50)
  - #2750 [fix] bug: fix coin de-activation logic  (overlap 0.50)
  - #2893 [feat] feat(trading): integrate geo blocker api (overlap 0.50)

**Qualitative notes (to be filled by author)**:
- What did the agent change?
- Why is this PR high-risk (edge case? coupling? API? tests?)
- What did the follow-up PRs actually fix?
- Single-sentence takeaway: