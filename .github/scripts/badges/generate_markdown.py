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


def replace_placeholders(text: str, pr_branch: str, pr_number: int, base_branch: str) -> str:
    """Replace placeholders in text with actual values"""
    if not isinstance(text, str):
        return text
    return (text
            .replace("{pr_branch}", pr_branch)
            .replace("{pr_number}", str(pr_number))
            .replace("{base_branch}", base_branch))


def load_json_file(file_path: str, config_dir: str, data_key: str = None):
    """
    Load JSON data from file, resolving path relative to config_dir or current directory.
    
    Returns:
        - If data_key is None: returns the file content as-is (dict or list)
        - If data_key is provided: returns file_data[data_key] if file_data is dict, else file_data
    """
    # Try relative to config directory first
    full_path = os.path.join(config_dir, file_path)
    if not os.path.exists(full_path):
        # Try relative to current working directory
        if os.path.exists(file_path):
            full_path = file_path
        else:
            return None
    
    try:
        with open(full_path, 'r') as f:
            file_data = json.load(f)
            
        # Extract data using data_key if provided
        if data_key and isinstance(file_data, dict):
            return file_data.get(data_key)
        
        return file_data
    except Exception:
        return None


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
            
            # Replace placeholders in all input values
            for key, value in list(base_inputs.items()):
                base_inputs[key] = replace_placeholders(value, pr_branch, pr_number, base_branch)
            
            # Handle file-based input transforms from config
            input_transforms = block.get("input_transforms", [])
            config_dir = os.path.dirname(os.path.abspath(config_path))
            
            for transform in input_transforms:
                source_key = transform.get("source_key")
                target_key = transform.get("target_key")
                transform_type = transform.get("type", "comma_separated")
                data_key = transform.get("data_key")
                
                if not source_key or not target_key or source_key not in base_inputs:
                    continue
                
                file_path = base_inputs.pop(source_key)
                file_data = load_json_file(file_path, config_dir, data_key)
                
                if not isinstance(file_data, list):
                    continue
                
                # Transform based on type
                if transform_type == "json":
                    base_inputs[target_key] = json.dumps(file_data)
                else:  # comma_separated (default)
                    base_inputs[target_key] = ",".join(file_data)
            
            badge_color = block.get("badge_color")
            icon = block.get("icon")
            badge_type = block.get("badge_type")
            
            if not workflow_id:
                continue
            
            # Add section header (unless hide_title is set)
            if not block.get("hide_title", False):
                lines.append(f"### {title}")
            
            if badge_type == "table":
                # Generate table with multiple rows
                rows_data = block.get("rows", [])
                
                # If rows_data not provided, generate from items_file or items list
                if not rows_data:
                    items = []
                    items_file = block.get("items_file")
                    
                    if items_file:
                        config_dir = os.path.dirname(os.path.abspath(config_path))
                        items_data_key = block.get("items_data_key")
                        items = load_json_file(items_file, config_dir, items_data_key)
                        if not isinstance(items, list):
                            items = []
                    else:
                        items = block.get("items", [])
                    
                    # Generate rows_data from items
                    if items:
                        label_key = block.get("label_key")
                        if not label_key:
                            items = []  # Skip if required config missing
                        
                        badge_text = block.get("badge_text")
                        row_inputs_template = block.get("row_inputs_template", {})
                        input_key = block.get("input_key")
                        item_placeholder = block.get("item_placeholder", "{item}")
                        label_format = block.get("label_format")
                        
                        if not row_inputs_template and not input_key:
                            items = []  # Skip if no way to set inputs
                        
                        for item in items:
                            # Build row inputs
                            if row_inputs_template:
                                import copy
                                row_inputs = copy.deepcopy(row_inputs_template)
                                for key, value in row_inputs.items():
                                    # Replace item placeholder first, then other placeholders
                                    replaced = str(value).replace(item_placeholder, str(item))
                                    row_inputs[key] = replace_placeholders(replaced, pr_branch, pr_number, base_branch)
                            else:
                                row_inputs = {input_key: item}
                            
                            # Build row data
                            formatted_label = (label_format.replace("{value}", str(item)) 
                                             if label_format else str(item))
                            
                            row_data = {
                                label_key: formatted_label,
                                "inputs": {**base_inputs, **row_inputs}
                            }
                            if badge_text:
                                row_data["badge_text"] = badge_text
                            rows_data.append(row_data)
                
                column_headers = block.get("column_headers")
                label_key = block.get("label_key")
                
                if rows_data:
                    if not column_headers or not label_key:
                        continue  # Skip if required config missing
                    
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
                    badge_text_template = block.get("badge_text_template")
                    label_format_table = block.get("label_format_table")
                    
                    def formatter(row, gen):
                        label = row["label"]
                        
                        # Generate badge text
                        badge_text = (row.get("badge_text") or 
                                    (badge_text_template.replace("{label}", label) if badge_text_template else label))
                        
                        # Format label for display
                        label_formatted = (label_format_table.replace("{label}", label) 
                                         if label_format_table else label)
                        
                        badges = gen.create_badge_pair(
                            text=badge_text,
                            workflow_id=row["workflow_id"],
                            ref=row["ref"],
                            inputs=row["inputs"],
                            return_url=row["return_url"],
                            direct_color=row["badge_color"],
                            icon=row["icon"]
                        )
                        
                        return [label_formatted, badges]
                    
                    table = generator.create_table(
                        rows=rows,
                        column_headers=column_headers,
                        row_formatter=formatter
                    )
                    lines.append(table)
            else:
                # Generate badge pair (or single UI badge if only_ui is specified)
                badge_text = block.get("badge_text")
                if not badge_text:
                    # Derive from title: remove markdown headers and emoji prefixes
                    badge_text = title.replace("### ", "").strip()
                    emoji_prefixes = block.get("emoji_prefixes", [])
                    for prefix in emoji_prefixes:
                        if badge_text.startswith(prefix):
                            badge_text = badge_text[len(prefix):].strip()
                            break
                
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
    parser.add_argument("--vars", required=True, help="Path to JSON file or JSON string with variables: app_domain, repo_owner, repo_name, pr_number, pr_branch, base_branch")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    
    args = parser.parse_args()
    
    # Load vars - either from file or parse as JSON string
    vars_data = args.vars
    # If it looks like JSON (starts with { or [), parse directly
    if vars_data.strip().startswith(('{', '[')):
        try:
            vars_dict = json.loads(vars_data)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON string in --vars", file=sys.stderr)
            sys.exit(1)
    elif os.path.exists(vars_data):
        # It's a file path
        with open(vars_data, 'r') as f:
            vars_dict = json.load(f)
    else:
        # Try to parse as JSON string anyway
        try:
            vars_dict = json.loads(vars_data)
        except json.JSONDecodeError:
            print(f"Error: --vars must be either a path to JSON file or valid JSON string", file=sys.stderr)
            sys.exit(1)
    
    # Extract required variables
    required_vars = ["app_domain", "repo_owner", "repo_name", "pr_number", "pr_branch", "base_branch"]
    missing_vars = [var for var in required_vars if var not in vars_dict]
    if missing_vars:
        print(f"Error: Missing required variables in --vars: {', '.join(missing_vars)}", file=sys.stderr)
        sys.exit(1)
    
    markdown = generate_markdown(
        config_path=args.config,
        app_domain=vars_dict["app_domain"],
        repo_owner=vars_dict["repo_owner"],
        repo_name=vars_dict["repo_name"],
        pr_number=int(vars_dict["pr_number"]),
        pr_branch=vars_dict["pr_branch"],
        base_branch=vars_dict["base_branch"]
    )
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(markdown)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
