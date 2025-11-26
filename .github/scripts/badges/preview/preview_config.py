#!/usr/bin/env python3
"""
Preview badge configuration

Simple script to preview how your JSON config will look as markdown.
Uses sensible defaults so you can just edit JSON and preview it.
"""

import json
import sys
import argparse
from pathlib import Path

# Add badges directory to path (parent of preview)
badges_dir = Path(__file__).parent.parent
sys.path.insert(0, str(badges_dir))

from generate_markdown import generate_markdown


def main():
    parser = argparse.ArgumentParser(
        description="Preview badge configuration markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview with defaults (for quick testing)
  python3 preview_config.py my_config.json
  
  # Preview with custom app domain
  python3 preview_config.py my_config.json --app-domain https://my-app.com
  
  # Save preview to file
  python3 preview_config.py my_config.json --output preview.md
  
  # Full customization
  python3 preview_config.py my_config.json \\
    --app-domain https://my-app.com \\
    --repo-owner owner \\
    --repo-name repo \\
    --pr-number 123 \\
    --pr-branch feature \\
    --base-branch main
        """
    )
    
    parser.add_argument(
        "config",
        help="Path to JSON config file"
    )
    parser.add_argument(
        "--app-domain",
        default="https://ydb-tech-qa.duckdns.org",
        help="Base URL of workflow executor app (default: https://your-app.com)"
    )
    parser.add_argument(
        "--repo-owner",
        default="owner",
        help="Repository owner (default: owner)"
    )
    parser.add_argument(
        "--repo-name",
        default="repo",
        help="Repository name (default: repo)"
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        default=123,
        help="PR number (default: 123)"
    )
    parser.add_argument(
        "--pr-branch",
        default="feature-branch",
        help="PR branch name (default: feature-branch)"
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch name (default: main)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: print to stdout)"
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        return 1
    
    # Validate JSON
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        return 1
    
    # Generate markdown
    try:
        markdown = generate_markdown(
            config_path=str(config_path),
            app_domain=args.app_domain,
            repo_owner=args.repo_owner,
            repo_name=args.repo_name,
            pr_number=args.pr_number,
            pr_branch=args.pr_branch,
            base_branch=args.base_branch
        )
    except Exception as e:
        print(f"Error generating markdown: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(markdown, encoding='utf-8')
        print(f"✓ Preview saved to: {output_path}", file=sys.stderr)
        print(f"✓ Preview length: {len(markdown)} characters", file=sys.stderr)
    else:
        print(markdown)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

