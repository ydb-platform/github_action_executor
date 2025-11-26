# Badge Generator Scripts

Universal Python module for generating GitHub Actions workflow trigger badges.

## 📁 File Structure

```
.github/scripts/
├── generate_badges.py          # Core module (low-level API)
├── generate_markdown.py         # Markdown generator script
├── badge_config_builder.py     # Python API for building configs
├── example_config.json         # Example configuration
├── example_config.md           # Visualization of example config
├── example_builder_usage.py   # Example usage of BadgeConfigBuilder
└── README.md                   # This file
```

## 🎯 Quick Start

### Option 1: Programmatic Configuration (Recommended)

```python
from badge_config_builder import BadgeConfigBuilder

# 1. Create builder (creates temp config)
builder = BadgeConfigBuilder()

# 2. Add components
builder.add_workflow_table(
    title="🧪 Run Tests",
    workflow_id="test.yml",
    rows=[
        {"sanitizer": "Address", "badge_color": "4caf50", "inputs": {"sanitizer": "address"}},
        {"sanitizer": "Memory", "badge_color": "2196f3", "inputs": {"sanitizer": "memory"}}
    ],
    column_headers=["Sanitizer", "Actions"],
    label_key="sanitizer"
)

builder.add_workflow_pair("🔨 Build", "build.yml")
builder.set_backport(["release/v1.0", "stable"])

# 3. Save config
config_path = builder.save()

# 4. Generate markdown preview
markdown = builder.generate_markdown(
    app_domain="https://your-app.com",
    repo_owner="owner",
    repo_name="repo",
    pr_number=123,
    pr_branch="feature",
    base_branch="main",
    output_path="preview.md"
)
```

See `example_builder_usage.py` for a complete example.

### Option 2: Manual JSON Configuration

Create a JSON config file (see `example_config.json` for reference):

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

### Core Module (`generate_badges.py`)

**Low-Level Functions (Core API):**
- `create_badge()` - Generate a single badge (direct or UI)
- `create_badge_pair()` - Generate a pair of badges (direct + UI)
- `create_table()` - Generate a markdown table with custom row formatter

**High-Level Helpers (Optional):**
- `create_backport_table()` - Convenience wrapper for backport tables
- `generate_comment()` - Generate complete PR comment

### Markdown Generator Script (`generate_markdown.py`)

Wrapper script used in GitHub Actions workflows. Reads JSON config and generates PR comment.

### Config Builder (`badge_config_builder.py`)

Python API for programmatically building configurations:
- `BadgeConfigBuilder()` - Create/load config
- `add_workflow_pair()` - Add simple workflow
- `add_workflow_table()` - Add workflow with table
- `set_backport()` - Configure backport
- `set_legend()` - Configure legend
- `save()` - Save config to file
- `generate_markdown()` - Generate markdown preview

## 📖 Examples

- **`example_config.json`** - Complete example configuration
- **`example_config.md`** - Visualization of what the example config generates
- **`example_builder_usage.py`** - Example of using BadgeConfigBuilder programmatically

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
mkdir -p .github/scripts
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

### BadgeConfigBuilder

```python
from badge_config_builder import BadgeConfigBuilder

builder = BadgeConfigBuilder()
builder.add_workflow_pair("Build", "build.yml")
builder.add_workflow_table("Tests", "test.yml", rows=[...])
builder.set_backport(["release/v1.0"])
config_path = builder.save()
markdown = builder.generate_markdown(...)
```

## 📄 License

This script is part of the GitHub Action Executor project.
