# Demosat EHA and EVR DataFrame Specification

## Problem Statement

Demosat simulation output already contains EHA and EVR CSV records, but the `demosat_data_utils` repository only partially exposes them through the modern `TtsDataFrame` architecture.

The repository already contains `DemosatEvrFrame` and `DemosatEvrRowSeries`, added on top of the shared `AmpcsEvrFrame` seam. That work is a useful starting point, not a complete implementation of this specification. The repository does not yet contain the corresponding Demosat telemetry DataFrame, and the existing EVR frame lacks complete fixture-backed tests, public exports, and explicit integration verification.

The deliverable is a coherent Demosat EHA/EVR DataFrame layer that follows the repository's actual vocabulary and shared abstractions:

- `DemosatChannelFrame` is the Demosat EHA/telemetry frame.
- `DemosatEvrFrame` is the Demosat event-record frame and already exists in partial form.
- `AmpcsEhaFrame` and `AmpcsEvrFrame` are the shared Teamtools extension seams.
- Legacy `DataContainer`/`DataItem` classes remain available for compatibility unless a separate approved migration explicitly changes them.

This specification is intentionally narrower than the broader repository migration effort. Command and sequence DataFrames are out of scope here.

## Solution

Complete the Demosat EHA/EVR DataFrame layer in four coordinated areas:

1. Add `DemosatChannelFrame` as a Demosat-specific subclass of the shared AMPCS EHA frame, with the actual Demosat CSV columns, permissive data handling, alarm-aware row behavior, and latest-available-data selection.
2. Complete and verify the existing `DemosatEvrFrame` and `DemosatEvrRowSeries` implementation without recreating a second EVR frame abstraction.
3. Export the modern frame classes through the package's established public API while preserving the legacy EVR classes until their separate deprecation work is completed.
4. Add focused tests using the actual Demosat simulation output and edge-case in-memory data, then run the full repository verification suite.

The highest test seam is the public DataFrame API: construct each frame, load the simulation CSV, exercise pandas operations, inspect row styles, and call the public domain methods.

## User Stories

1. As a Demosat data consumer, I want to construct a `DemosatChannelFrame` from tabular telemetry records, so that I can analyze EHA data using pandas.
2. As a Demosat data consumer, I want to construct a `DemosatEvrFrame` from tabular event records, so that I can analyze EVRs using pandas.
3. As a Demosat data consumer, I want both frames to use the shared `TtsDataFrame` architecture, so that pandas operations and Teamtools integrations work consistently.
4. As a Demosat data consumer, I want telemetry to use the established `DemosatChannelFrame` name, so that the public API matches the repository roadmap and shared AMPCS vocabulary.
5. As a Demosat data consumer, I want the existing `DemosatEvrFrame` completed rather than replaced, so that prior work and downstream references remain coherent.
6. As a Demosat data consumer, I want the real Demosat EHA simulation CSV to load without column renaming, so that simulator output is directly usable.
7. As a Demosat data consumer, I want the real Demosat EVR simulation CSV to load without column renaming, so that simulator output is directly usable.
8. As a Demosat data consumer, I want all EHA columns retained, so that telemetry values, alarm state, and session context remain available.
9. As a Demosat data consumer, I want all EVR columns retained, so that event values, metadata, and session context remain available.
10. As a Demosat data consumer, I want Demosat field names preserved, so that this mission layer remains independent from Oxus naming.
11. As a Demosat data consumer, I want missing optional values accepted, so that partially populated simulation records load successfully.
12. As a Demosat data consumer, I want numeric and enumerated EHA values preserved, so that channels such as `TX_POWER_STATE`, `VCDU_NO`, and `SC_MODE` remain meaningful.
13. As a Demosat data consumer, I want `status` treated as channel status rather than alarm state, so that enumerated values are not misclassified.
14. As a Demosat data consumer, I want `dnAlarmState` and `euAlarmState` retained independently, so that raw and engineering-unit alarms remain inspectable.
15. As an operations user, I want an EHA row to show an alarm style when either alarm state is red, so that severe conditions are visible immediately.
16. As an operations user, I want an EHA row to show a warning style when no alarm is red but an alarm is yellow, so that caution conditions remain visible.
17. As an operations user, I want red to take precedence over yellow, so that styling never understates the worst condition.
18. As an operations user, I want alarm styling to work regardless of ordinary case differences in incoming alarm values, so that `red` and `RED` have consistent meaning.
19. As an operations user, I want unalarmed EHA rows to use a stable neutral style, so that all rows render predictably.
20. As an operations user, I want EVR styles to use the shared `EvrPalette` semantics, so that Demosat displays follow Teamtools conventions.
21. As an operations user, I want every severity present in Demosat simulation output styled correctly, so that diagnostic, command, activity, warning, fatal, and simulator-error events are distinguishable.
22. As a Demosat data consumer, I want missing or unknown EVR levels to render safely, so that one malformed event does not break a table.
23. As a Demosat data consumer, I want `scet` to be the default time axis for both frames, so that time-based operations use spacecraft event time consistently.
24. As a Demosat data consumer, I want Demosat day-of-year timestamps interpreted correctly, so that values such as `2024-033T00:00:00.000000` work in time operations.
25. As a Demosat data consumer, I want `rct` and `lst` retained as optional fields without prematurely defining them as supported time axes, so that current simulator output remains compatible.
26. As a Demosat data consumer, I want `sclk` retained as a numeric spacecraft-clock value, so that it remains available for correlation.
27. As a Demosat data consumer, I want `DemosatChannelFrame.lad()` to return the latest sample per `channelId`, so that I can inspect the latest available telemetry state.
28. As a Demosat data consumer, I want LAD to work on unsorted input, so that correctness does not depend on CSV ordering.
29. As a Demosat data consumer, I want LAD results to remain `DemosatChannelFrame` objects, so that pandas operations can be chained.
30. As an operations user, I want to filter EVRs by one or more levels using the shared log-frame filtering vocabulary, so that I can create focused event views.
31. As a Demosat data consumer, I want EVR filtering to preserve source order, so that event chronology remains intact.
32. As a Demosat data consumer, I want EVR filtering results to remain `DemosatEvrFrame` objects, so that filtering composes with the DataFrame API.
33. As a Demosat data consumer, I want ordinary pandas filtering, sorting, copying, `.loc`, and `.iloc` operations to preserve the specialized frame type where supported, so that frame behavior is not lost during analysis.
34. As a UI consumer, I want row styling exposed through the shared row-series mechanism, so that `iterrows()` and `power_table()` use the same style behavior.
35. As a maintainer, I want tests based on the checked-in Demosat simulation outputs, so that behavior is verified against real project data.
36. As a maintainer, I want focused edge tests for alarms, missing timestamps, severity fallbacks, and mixed values, so that regressions are explicit.
37. As a maintainer, I want the legacy EVR classes preserved while their separate deprecation issue is handled, so that existing consumers are not broken by this feature.
38. As an autonomous agent, I want objective completion gates covering implementation, tests, exports, and compatibility, so that I cannot finish with only placeholder classes or an import-only smoke test.

## Implementation Decisions

### Repository vocabulary and existing seams

- The telemetry class is `DemosatChannelFrame`, not `EhaDataFrame`.
- The event class is `DemosatEvrFrame`, which already exists and must be completed and tested rather than duplicated.
- `DemosatChannelFrame` should extend `AmpcsEhaFrame`.
- `DemosatEvrFrame` should continue extending `AmpcsEvrFrame`.
- Mission-specific row classes should extend the appropriate shared row-series classes.
- The shared `TtsDataFrame`, `AmpcsEhaFrame`, `AmpcsEvrFrame`, `TtsLogFrame`, and `EvrPalette` implementations are the source of truth for extension behavior.
- Do not migrate command, sequence, ephemeris, orbit-event, communication-window, or ground-station models as part of this specification.

### Legacy compatibility

- Keep the existing `EvrContainer` and `EvrItem` classes intact during this work.
- Do not remove or silently change their behavior.
- The separate deprecation task may add warnings later, but this specification must not make that unrelated change implicit.
- The final report must state how the modern and legacy EVR APIs coexist.

### EHA frame contract

`DemosatChannelFrame` must retain the complete Demosat EHA row shape:

- `recordType`
- `sessionId`
- `sessionHost`
- `channelId`
- `dssId`
- `vcid`
- `name`
- `module`
- `ert`
- `scet`
- `rct`
- `lst`
- `sclk`
- `dn`
- `dnStr`
- `eu`
- `status`
- `dnAlarmState`
- `euAlarmState`
- `realtime`
- `type`

The frame must use `channelId` as its semantic label and `eu` as its primary value where the shared AMPCS frame contract requires those settings.

Schema handling must be permissive. Missing optional fields and mixed numeric/enumerated values must be accepted. `status` must remain distinct from alarm state.

### EVR frame contract

`DemosatEvrFrame` must retain the complete Demosat EVR row shape:

- `recordType`
- `sessionId`
- `sessionHost`
- `name`
- `module`
- `level`
- `eventId`
- `vcid`
- `dssId`
- `fromSse`
- `realtime`
- `sclk`
- `scet`
- `ert`
- `rct`
- `lst`
- `message`
- `metadataKeywordList`
- `metadataValuesList`
- `metadata`

The existing Demosat level vocabulary remains authoritative:

- `DIAGNOSTIC`
- `COMMAND`
- `ACTIVITY_LO`
- `ACTIVITY_HI`
- `WARNING_LO`
- `WARNING_HI`
- `FATAL`
- `SIM_ERROR`

The frame must use `name` as its label, `message` as its value, and `scet` as its default time label consistently with the shared AMPCS EVR frame.

### Time behavior

- Both frames use `DEFAULT_TIME_LABEL = "scet"`.
- Demosat timestamps use the year/day-of-year form `%Y-%jT%H:%M:%S.%f`.
- `rct` and `lst` remain retained optional columns, not supported default time axes.
- `ert` remains available as a data column.
- `sclk` remains numeric and does not replace `scet` as the default time axis.

### EHA alarm styling

Expose styles through the row-series mechanism used by `TtsDataFrame` rendering.

- Read `dnAlarmState` and `euAlarmState`; never use `status` as an alarm source.
- Treat alarm values case-insensitively, so lower- and upper-case representations have the same meaning.
- If either state is red, return the red/alarm style.
- Otherwise, if either state is yellow, return the yellow/warning style.
- Otherwise, return a stable neutral/nominal style.
- Red takes precedence over yellow.
- Empty, null, and pandas-missing values must not raise.

The implementation may reuse the shared AMPCS EHA alarm styling where its behavior matches this contract; mission-specific normalization or override is required where case handling or Demosat semantics differ.

### EVR styling and filtering

- Use the existing `EvrPalette` semantics for standard EVR levels.
- Preserve the Demosat-specific `SIM_ERROR` style behavior already established in the mission module.
- Unknown or missing levels must fall back safely without raising during rendering.
- Use the shared log-frame filtering vocabulary (`filter_level` and related methods) unless a Demosat-specific `filter_by_severity` alias is demonstrably needed by an existing consumer.
- Filtering must preserve row order and return the specialized frame type through the shared DataFrame machinery.

### LAD

Implement `DemosatChannelFrame.lad()` as a public DataFrame-native method:

- Return a `DemosatChannelFrame`.
- Return at most one row per `channelId`.
- Select the latest usable row by `scet`.
- Work correctly on unsorted input.
- Preserve all selected-row columns.
- Define deterministic behavior for missing or unusable `scet` values.

### Public API

- Export `DemosatChannelFrame` and `DemosatEvrFrame` through the package's established public import surface.
- Do not introduce `EhaDataFrame` or `EvrDataFrame` aliases unless an existing repository consumer requires them and the compatibility decision is documented.
- Keep legacy EVR exports available while the separate deprecation issue remains unresolved.

## Testing Decisions

Test the public DataFrame behavior at the highest existing seam. Tests should verify observable behavior rather than private helper names or incidental pandas implementation details.

### Required EHA tests

- Construction from records and a pandas DataFrame.
- Loading the real `simulated_eha.csv` fixture through the supported CSV path.
- Complete column retention.
- Missing optional fields.
- Mixed numeric and enumerated values.
- `DemosatChannelFrame` and `TtsDataFrame` identity.
- `channelId` label and `eu` value semantics.
- `scet` default time behavior and day-of-year parsing.
- Preservation through copy, filter, sort, `.loc`, `.iloc`, and row iteration where supported.
- No alarm, DN yellow, EU yellow, DN red, EU red, and red-over-yellow styling.
- Lowercase and uppercase alarm values.
- Confirmation that `status` does not drive alarm styling.
- LAD with unsorted duplicate channels, ties, missing timestamps, selected values, and result type.

### Required EVR tests

- Construction from records and a pandas DataFrame.
- Loading the real `simulated_evrs.csv` fixture through the supported CSV path.
- Complete column retention, including the JSON-like `metadata` field.
- `DemosatEvrFrame` and `TtsDataFrame` identity.
- `name` label, `message` value, and `scet` default time semantics.
- All Demosat level values, including `SIM_ERROR`.
- `EvrPalette`-based styling and safe unknown/missing-level fallback.
- Existing shared filtering behavior for one and multiple levels.
- Source-order preservation and specialized result type.
- Public import behavior.
- Confirmation that legacy `EvrContainer` and `EvrItem` remain available and unchanged by this feature.

### Integration verification

Use the checked-in Demosat simulation outputs as fixtures without mutating them:

- `demosat_seq/examples/sim_outputs/simulated_eha.csv`
- `demosat_seq/examples/sim_outputs/simulated_evrs.csv`

If tests run from the standalone repository and cannot resolve the sibling fixture paths, use a test-local fixture strategy that preserves the exact headers and representative values. Do not silently skip fixture coverage.

Run and report:

```bash
pytest
python -m compileall src
python -c "from demosat_data_utils.evr import DemosatEvrFrame"
```

The agent must report exact commands, results, and any environment-specific fixture handling.

## Out of Scope

- Creating `demosat_telemetry_store`.
- Creating `EhaDataFrame` or `EvrDataFrame` as the canonical names.
- Reimplementing or changing the shared `TtsDataFrame`, `AmpcsEhaFrame`, `AmpcsEvrFrame`, or `EvrPalette` infrastructure.
- Removing legacy `EvrContainer` or `EvrItem` classes.
- Adding deprecation warnings unless the separate deprecation issue is explicitly included.
- Implementing command, sequence, ephemeris, orbit-event, communication-window, or ground-station DataFrames.
- Implementing database ingestion, dictionary parsing, or Oxus compatibility.
- Defining `rct` or `lst` as supported time axes.
- Adding broad analytics beyond `lad()` and existing shared EVR filtering.

## Exit Conditions

The autonomous agent may mark this work complete only when all applicable gates pass.

### EHA gates

- [ ] `DemosatChannelFrame` exists and extends the shared AMPCS/TtsDataFrame EHA seam.
- [ ] The real EHA simulation fixture loads through the supported CSV construction path.
- [ ] All Demosat EHA columns remain available.
- [ ] Missing and mixed values are accepted.
- [ ] `channelId`, `eu`, and `scet` semantics are configured correctly.
- [ ] Alarm styling reads DN/EU alarm state, handles case differences, gives red precedence, and ignores `status`.
- [ ] `lad()` returns the latest row per channel from unsorted input and preserves the specialized frame type.

### EVR gates

- [ ] The existing `DemosatEvrFrame` remains the only modern Demosat EVR frame implementation.
- [ ] The real EVR simulation fixture loads through the supported CSV construction path.
- [ ] All Demosat EVR columns remain available.
- [ ] `name`, `message`, and `scet` semantics are configured correctly.
- [ ] All Demosat levels, including `SIM_ERROR`, have tested styling behavior.
- [ ] Unknown/missing levels render safely.
- [ ] Shared EVR filtering works and preserves order and specialized frame type.
- [ ] `DemosatEvrFrame` is publicly importable.
- [ ] Legacy EVR classes remain available and are not silently changed.

### Repository gates

- [ ] Focused EHA and EVR tests exist and exercise real fixtures plus edge cases.
- [ ] Full tests pass.
- [ ] Compilation and import smoke checks pass.
- [ ] No placeholder methods, import-only tests, debug code, skipped required tests, or unrelated edits remain.
- [ ] The final diff has been reviewed.
- [ ] The final report lists implemented classes and methods, fixture handling, style precedence/fallbacks, compatibility decisions, commands run, results, and every unmet condition if any.
- [ ] If a gate is unmet, the agent reports the work incomplete instead of claiming success.

## Further Notes

The repository currently declares `tts-data-utils` as a dependency and already relies on shared AMPCS frame classes. Verify `tts-html-utils` availability through the actual environment before changing dependencies. The existing Demosat EVR implementation and the shared AMPCS classes are the starting point; the agent must inspect them and implement only the missing, repository-valid behavior.
