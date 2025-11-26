#!/usr/bin/env python3
"""
Generate markdown text with badges

This script uses the low-level BadgeGenerator functions to build
markdown content with badges. Can be used for PR comments, issue bodies,
or any other markdown content.
"""

import json
import sys
import os
from pathlib import Path

# Add badges directory to path for imports
badges_dir = Path(__file__).parent
sys.path.insert(0, str(badges_dir))

from generate_badges import BadgeGenerator


def generate_markdown(config_path: str, app_domain: str, repo_owner: str, repo_name: str,
                      pr_number: int, pr_branch: str, base_branch: str) -> str:
    """
    Generate markdown text with workflow trigger badges
    
    Args:
        config_path: Path to JSON config file
        app_domain: Base URL of workflow executor app
        repo_owner: Repository owner
        repo_name: Repository name
        pr_number: PR number (used for return_url)
        pr_branch: PR branch name (used for workflow inputs)
        base_branch: Base branch name (used as default ref)
        
    Returns:
        Complete markdown text with badges
    """
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Initialize generator
    generator = BadgeGenerator(
        app_domain=app_domain,
        repo_owner=repo_owner,
        repo_name=repo_name,
        pr_number=pr_number,
        pr_branch=pr_branch,
        base_branch=base_branch
    )
    
    # Build markdown sections
    lines = []
    
    # Get blocks from config
    blocks = config.get("blocks", [])
    
    if not blocks:
        return ""
    
    # Set default order and type for blocks
    for block in blocks:
        if "order" not in block:
            block["order"] = 100  # Default order
        
        if "type" not in block:
            block["type"] = "text"  # Default type
    
    # Sort all blocks by order
    blocks.sort(key=lambda x: x.get("order", 100))
    
    # Process all blocks in order
    for block in blocks:
        if not block.get("enabled", True):
            continue
        
        block_type = block.get("type", "text")
        
        if block_type == "text":
            # Text block
            if block.get("separator", False):
                lines.append("---")
            
            block_text = block.get("text", [])
            if block_text:
                if isinstance(block_text, list):
                    lines.extend(block_text)
                else:
                    lines.append(block_text)
                lines.append("")
        
        elif block_type == "badge":
            # Badge block
            title = block.get("title", "Workflow")
            workflow_id = block.get("workflow_id")
            ref = block.get("ref", base_branch)
            base_inputs = block.get("inputs", {}).copy()  # Copy to avoid modifying original
            
            # Replace dynamic values in inputs
            if "pr_branch" in base_inputs:
                base_inputs["pr_branch"] = pr_branch
            if "from_pr" in base_inputs:
                base_inputs["from_pr"] = str(pr_number)
            
            # Handle preset_branches - load branches from file and add to inputs
            if "preset_branches" in base_inputs:
                preset_branches_file = base_inputs.pop("preset_branches")  # Remove from inputs
                # Load branches from file
                config_dir = os.path.dirname(os.path.abspath(config_path))
                branches_file_path = os.path.join(config_dir, preset_branches_file)
                if os.path.exists(branches_file_path):
                    with open(branches_file_path, 'r') as f:
                        branches = json.load(f)
                        if isinstance(branches, dict):
                            branches = branches.get("branches", [])
                        # Add branches as comma-separated string for URL
                        if branches:
                            base_inputs["available_branches"] = ",".join(branches)
                else:
                    # Try relative to current working directory
                    if os.path.exists(preset_branches_file):
                        with open(preset_branches_file, 'r') as f:
                            branches = json.load(f)
                            if isinstance(branches, dict):
                                branches = branches.get("branches", [])
                            if branches:
                                base_inputs["available_branches"] = ",".join(branches)
            
            badge_color = block.get("badge_color", "4caf50")
            icon = block.get("icon", "▶")
            badge_type = block.get("badge_type", "pair")  # "pair" or "table"
            
            if not workflow_id:
                continue
            
            # Add section header (unless hide_title is set)
            if not block.get("hide_title", False):
                lines.append(f"### {title}")
            
            if badge_type == "table":
                # Generate table with multiple rows
                rows_data = block.get("rows", [])
                branches = block.get("branches", [])
                branches_file = block.get("branches_file")
                
                # Load branches from file if specified
                if branches_file and not rows_data:
                    config_dir = os.path.dirname(os.path.abspath(config_path))
                    branches_file_path = os.path.join(config_dir, branches_file)
                    if os.path.exists(branches_file_path):
                        with open(branches_file_path, 'r') as f:
                            branches = json.load(f)
                            # Support both array of strings and object with branches array
                            if isinstance(branches, dict):
                                branches = branches.get("branches", [])
                    else:
                        # Try relative to current working directory
                        if os.path.exists(branches_file):
                            with open(branches_file, 'r') as f:
                                branches = json.load(f)
                                if isinstance(branches, dict):
                                    branches = branches.get("branches", [])
                
                # If branches is specified, auto-generate rows
                if branches and not rows_data:
                    label_key = block.get("label_key", "branch")
                    badge_text = block.get("badge_text", "Backport")
                    for branch in branches:
                        branch_inputs = {
                            "source_branch": pr_branch,
                            "target_branch": branch
                        }
                        # Merge with base inputs
                        branch_inputs = {**base_inputs, **branch_inputs}
                        rows_data.append({
                            label_key: f"`{branch}`",
                            "badge_text": badge_text,
                            "inputs": branch_inputs
                        })
                
                column_headers = block.get("column_headers", ["Type", "Actions"])
                label_key = block.get("label_key", "label")
                
                if rows_data:
                    lines.append("")
                    
                    # Prepare rows for create_table
                    rows = []
                    for row_data in rows_data:
                        row_inputs = {**base_inputs, **row_data.get("inputs", {})}
                        row_badge_color = row_data.get("badge_color", badge_color)
                        row_icon = row_data.get("icon", icon)
                        
                        rows.append({
                            "label": row_data.get(label_key, ""),
                            "workflow_id": workflow_id,
                            "ref": ref,
                            "inputs": row_inputs,
                            "badge_color": row_badge_color,
                            "icon": row_icon,
                            "return_url": generator.return_url,
                            "badge_text": row_data.get("badge_text")
                        })
                    
                    # Formatter function
                    def formatter(row, gen):
                        label = row["label"]
                        badge_text = row.get("badge_text") or f"Run {label}"
                        badges = gen.create_badge_pair(
                            text=badge_text,
                            workflow_id=row["workflow_id"],
                            ref=row["ref"],
                            inputs=row["inputs"],
                            return_url=row["return_url"],
                            direct_color=row["badge_color"],
                            icon=row["icon"]
                        )
                        label_formatted = label
                        if not label.startswith("`") and not label.startswith("**"):
                            label_formatted = f"**{label}**"
                        return [label_formatted, badges]
                    
                    table = generator.create_table(
                        rows=rows,
                        column_headers=column_headers,
                        row_formatter=formatter
                    )
                    lines.append(table)
            else:
                # Generate badge pair (or single UI badge if only_ui is specified)
                badge_text = title.replace("### ", "").replace("🧪 ", "").replace("🔨 ", "").replace("📦 ", "").strip()
                only_ui = block.get("only_ui", False)
                
                if only_ui:
                    # Create only UI badge
                    ui_badge = generator.create_badge(
                        text=badge_text,
                        workflow_id=workflow_id,
                        link_type="ui",
                        ref=ref,
                        inputs=base_inputs,
                        return_url=generator.return_url,
                        badge_color=badge_color,
                        icon=icon
                    )
                    lines.append(ui_badge)
                else:
                    # Create badge pair (direct + UI)
                    badge_pair = generator.create_badge_pair(
                        text=badge_text,
                        workflow_id=workflow_id,
                        ref=ref,
                        inputs=base_inputs,
                        return_url=generator.return_url,
                        direct_color=badge_color,
                        icon=icon
                    )
                    lines.append(badge_pair)
            
            lines.append("")
    
    return "\n".join(lines)


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate markdown text with badges")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--app-domain", required=True, help="Base URL of workflow executor app")
    parser.add_argument("--repo-owner", required=True, help="Repository owner")
    parser.add_argument("--repo-name", required=True, help="Repository name")
    parser.add_argument("--pr-number", type=int, required=True, help="PR number")
    parser.add_argument("--pr-branch", required=True, help="PR branch name")
    parser.add_argument("--base-branch", required=True, help="Base branch name")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    
    args = parser.parse_args()
    
    markdown = generate_markdown(
        config_path=args.config,
        app_domain=args.app_domain,
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        pr_number=args.pr_number,
        pr_branch=args.pr_branch,
        base_branch=args.base_branch
    )
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(markdown)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
