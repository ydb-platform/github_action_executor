# Example Config Visualization

This document shows what the `example_config.json` configuration generates.

## Configuration Overview

The example config creates a PR comment with:
- **Run Tests** section with a table of 4 sanitizers (each with different colors)
- **Build** section with a simple badge pair
- **Backport** section with a table of branches
- **Legend** explaining the badge icons

## Generated PR Comment

### 🧪 Run Tests

| Sanitizer | Actions |
|-----------|---------|
| **Address** | [![▶ Run Address](https://img.shields.io/badge/▶_Run_Address-4caf50?style=flat-square)](...) [![⚙️](https://img.shields.io/badge/⚙️-ff9800?style=flat-square)](...) |
| **Memory** | [![▶ Run Memory](https://img.shields.io/badge/▶_Run_Memory-2196f3?style=flat-square)](...) [![⚙️](https://img.shields.io/badge/⚙️-ff9800?style=flat-square)](...) |
| **Undefined Behavior** | [![▶ Run Undefined Behavior](https://img.shields.io/badge/▶_Run_Undefined_Behavior-ff9800?style=flat-square)](...) [![⚙️](https://img.shields.io/badge/⚙️-ff9800?style=flat-square)](...) |
| **Thread** | [![▶ Run Thread](https://img.shields.io/badge/▶_Run_Thread-9c27b0?style=flat-square)](...) [![⚙️](https://img.shields.io/badge/⚙️-ff9800?style=flat-square)](...) |

### 🔨 Build

[![🔨 Build](https://img.shields.io/badge/🔨_Build-2196f3?style=flat-square)](...) [![⚙️](https://img.shields.io/badge/⚙️-ff9800?style=flat-square)](...)

### 📦 Backport

| Branch | Actions |
|--------|---------|
| `release/v1.0` | [![▶ Backport](https://img.shields.io/badge/▶_Backport-2196f3?style=flat-square)](...) [![⚙️](https://img.shields.io/badge/⚙️-ff9800?style=flat-square)](...) |
| `release/v2.0` | [![▶ Backport](https://img.shields.io/badge/▶_Backport-2196f3?style=flat-square)](...) [![⚙️](https://img.shields.io/badge/⚙️-ff9800?style=flat-square)](...) |
| `stable` | [![▶ Backport](https://img.shields.io/badge/▶_Backport-2196f3?style=flat-square)](...) [![⚙️](https://img.shields.io/badge/⚙️-ff9800?style=flat-square)](...) |

▶ - immediately runs the workflow with default parameters.
⚙️ - opens UI to review and modify parameters before running.

---

*These links will automatically comment on this PR with the workflow results.*

*Tip: To open links in a new tab, use Ctrl+Click (Windows/Linux) or Cmd+Click (macOS).*

## Configuration Breakdown

### Run Tests Table

- **Type**: `table` - creates a markdown table
- **Column Headers**: `["Sanitizer", "Actions"]`
- **Label Key**: `sanitizer` - field name in row data for the label
- **Base Inputs**: Applied to all rows
  - `pr_branch`: PR branch name
  - `test_type`: "all"
  - `from_pr`: PR number
- **Rows**: 4 sanitizers with different colors
  - Address (green: `4caf50`)
  - Memory (blue: `2196f3`)
  - Undefined Behavior (orange: `ff9800`)
  - Thread (purple: `9c27b0`)

### Build Pair

- **Type**: `pair` (default) - creates a simple badge pair
- **Workflow**: `build.yml`
- **Color**: Blue (`2196f3`)
- **Icon**: 🔨

### Backport Table

- **Workflow**: `backport.yml`
- **Branches**: `release/v1.0`, `release/v2.0`, `stable`
- Automatically generates table with badges for each branch

### Legend

- **Enabled**: `true`
- **Direct Text**: Explains ▶ badge
- **UI Text**: Explains ⚙️ badge

## Color Reference

- `4caf50` - Green (Address sanitizer)
- `2196f3` - Blue (Memory sanitizer, Build)
- `ff9800` - Orange (Undefined Behavior sanitizer, UI badges)
- `9c27b0` - Purple (Thread sanitizer)

## Testing the Config

To test this config locally:

```bash
python3 .github/scripts/badges/generate_markdown.py \
  --config .github/scripts/example_config.json \
  --app-domain "https://your-app.com" \
  --repo-owner "owner" \
  --repo-name "repo" \
  --pr-number 123 \
  --pr-branch "feature-branch" \
  --base-branch "main" \
  --output /tmp/test_comment.md
```

Then view `/tmp/test_comment.md` to see the generated comment.

