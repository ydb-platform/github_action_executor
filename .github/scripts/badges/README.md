# Badge Generator Scripts

Universal Python module for generating GitHub Actions workflow trigger badges.

## 📁 File Structure

```
.github/scripts/badges/
├── generate_badges.py          # Core module (low-level API) - REQUIRED
├── generate_markdown.py          # Markdown generator script - REQUIRED
├── README.md                   # This file
├── configs/
│   └── badge_config.json       # Main badge configuration
├── preview/
│   └── preview_config.py      # Preview JSON config as markdown
└── examples/
    ├── example_config.json     # Example configuration
    └── example_config.md       # Visualization of example config
```

## 🎯 Quick Start

### Option 0: Preview Your Config (Simplest)

Edit your JSON config in `.github/scripts/badges/configs/badge_config.json` and preview markdown:

```bash
# Simple: config -> markdown (prints to stdout, uses defaults)
python3 .github/scripts/badges/preview/preview_config.py configs/badge_config.json

# Save to file
python3 .github/scripts/badges/preview/preview_config.py configs/badge_config.json --output preview.md

# With custom parameters
python3 .github/scripts/badges/preview/preview_config.py configs/badge_config.json \
  --app-domain https://my-app.com \
  --repo-owner owner \
  --repo-name repo \
  --pr-number 123
```

### Option 1: JSON Configuration (For GitHub Actions)

Create a JSON config file (see `configs/badge_config.json` for reference) and use `generate_markdown.py` in your workflow.

### Option 1: JSON Configuration (For GitHub Actions)

Create a JSON config file (see `examples/example_config.json` for reference):

```json
{
  "workflows": [
    {
      "title": "🧪 Run Tests",
      "type": "table",
      "workflow_id": "test.yml",
      "rows": [...]
    }
  ],
  "backport_branches": ["release/v1.0"],
  "legend": {...}
}
```

Then use `generate_markdown.py`:

```bash
    python3 .github/scripts/badges/generate_markdown.py \
  --config badge_config.json \
  --app-domain "https://your-app.com" \
  --repo-owner "owner" \
  --repo-name "repo" \
  --pr-number 123 \
  --pr-branch "feature" \
  --base-branch "main" \
  --output comment.txt
```

## 📚 Architecture

### Core Module (`generate_badges.py`) - **CORE, REQUIRED**

**Low-Level Functions (Core API):**
- `BadgeGenerator` class - Main generator
- `create_badge()` - Generate a single badge (direct or UI)
- `create_badge_pair()` - Generate a pair of badges (direct + UI)
- `create_table()` - Generate a markdown table with custom row formatter

**High-Level Helpers (Optional):**
- `create_backport_table()` - Convenience wrapper for backport tables
- `generate_comment()` - Generate complete PR comment

**Purpose:** Foundation for all badge generation. Used by other modules.

### Markdown Generator Script (`generate_markdown.py`) - **REQUIRED for GitHub Actions**

Wrapper script used in GitHub Actions workflows:
- Reads JSON config file
- Uses `BadgeGenerator` from `generate_badges.py`
- Generates complete PR comment
- Used in `.github/workflows/pr-badges.yml`

**Purpose:** Entry point for GitHub Actions workflows. Reads JSON config and generates markdown.

### Preview Script (`preview_config.py`) - **For previewing configs**

Simple script to preview your JSON config as markdown:
- Uses sensible defaults (no need to specify all parameters)
- Can customize all parameters via command-line flags
- Perfect for editing JSON and seeing the result

**Purpose:** Quick preview tool for editing and testing badge configurations.

**Usage:**
```bash
# Simple: just config path (uses defaults)
python3 .github/scripts/badges/preview/preview_config.py configs/badge_config.json

# Save to file
python3 .github/scripts/badges/preview/preview_config.py configs/badge_config.json --output preview.md

# With custom parameters
python3 .github/scripts/badges/preview/preview_config.py configs/badge_config.json \
  --app-domain https://my-app.com \
  --repo-owner owner \
  --repo-name repo \
  --pr-number 123
```

## 📖 Examples

- **`examples/example_config.json`** - Complete example configuration
- **`examples/example_config.md`** - Visualization of what the example config generates

## 🔧 Configuration Format

### Simple Badge Pair

```json
{
  "workflows": [
    {
      "title": "🔨 Build",
      "type": "pair",
      "workflow_id": "build.yml",
      "ref": "main",
      "inputs": {"build_type": "release"},
      "badge_color": "2196f3",
      "icon": "🔨"
    }
  ]
}
```

### Table with Multiple Rows

```json
{
  "workflows": [
    {
      "title": "🧪 Run Tests",
      "type": "table",
      "workflow_id": "test.yml",
      "column_headers": ["Sanitizer", "Actions"],
      "label_key": "sanitizer",
      "rows": [
        {
          "sanitizer": "Address",
          "badge_color": "4caf50",
          "inputs": {"sanitizer": "address"}
        },
        {
          "sanitizer": "Memory",
          "badge_color": "2196f3",
          "inputs": {"sanitizer": "memory"}
        }
      ]
    }
  ]
}
```

### Legend Configuration

```json
{
  "legend": {
    "enabled": true,
    "direct_text": "▶ - immediately runs the workflow with default parameters.",
    "ui_text": "⚙️ - opens UI to review and modify parameters before running."
  }
}
```

## 🚀 Integration

### Copy to Your Repository

```bash
mkdir -p .github/scripts/badges
cp generate_badges.py generate_markdown.py .github/scripts/badges/
```

### Use in GitHub Actions

```yaml
- name: Generate badges
  run: |
    python3 .github/scripts/badges/generate_markdown.py \
      --config badge_config.json \
      --app-domain "${{ vars.APP_DOMAIN }}" \
      --repo-owner "${{ github.repository_owner }}" \
      --repo-name "${{ github.event.repository.name }}" \
      --pr-number ${{ github.event.pull_request.number }} \
      --pr-branch "${{ github.event.pull_request.head.ref }}" \
      --base-branch "${{ github.event.pull_request.base.ref }}" \
      --output comment.txt
```

## 📝 API Reference

### BadgeGenerator (Core Module)

```python
from generate_badges import BadgeGenerator

gen = BadgeGenerator(
    app_domain="https://your-app.com",
    repo_owner="owner",
    repo_name="repo",
    pr_number=123
)

# Low-level functions
badge = gen.create_badge("Run Tests", "test.yml", link_type="direct")
pair = gen.create_badge_pair("Run Tests", "test.yml")
table = gen.create_table(rows, headers, formatter)
```


## 📄 License

This script is part of the GitHub Action Executor project.
