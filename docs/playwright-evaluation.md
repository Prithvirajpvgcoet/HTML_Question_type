# Playwright evaluation scope

The LLM creates structured assertion definitions. It never evaluates candidate code, changes an assertion outcome, or awards points. Before publication, Playwright runs the generated assertions against the reference solution twice. Stable browser values become the stored expected values; failed or differing runs remain unpublished with `failed` or `flaky` validation status.

## Automatic scoring support

| Requirement | Support | Implementation |
| --- | --- | --- |
| Element presence/absence | Full | Locator count |
| Element count | Full | Locator count |
| Text and input-rendered text | Full | DOM text content |
| HTML attributes, IDs, classes | Full | Attribute and selector checks |
| Click, input, change, hover | Full | Playwright actions |
| Multi-step state changes | Full | Sequential groups with blocking |
| Computed CSS | Full | `getComputedStyle(...).getPropertyValue(...)` |
| Function presence | Full | Global function type check |
| Function invocation and resulting state | Full | `call_function` plus an observable check |
| Partial scoring | Full | Sum of points from passed assertions |
| Basic layout properties | Mostly | Deterministic computed CSS values |

Animations and transitions are disabled during evaluation. Assertions that rely on timers use bounded waits and polling. The browser runs with a fixed viewport, locale, timezone, device scale factor, clock, seeded `Math.random`, blocked service workers, and no network access. The Chromium version is pinned by the Playwright package/container image.

Screenshot similarity is not an automatic check in this version. `visual_region` is rejected by the schema and requires admin review until a deterministic image-diff contract is added. Accessibility can be checked through deterministic roles and ARIA attributes; full axe-core auditing is deferred.

Code quality, naming, readability, maintainability, and implementation technique are outside automatic scoring because they are not browser-observable requirements. The evaluator has a per-action timeout and a hard per-submission worker timeout; a hung candidate process is terminated and the submission is marked failed.
