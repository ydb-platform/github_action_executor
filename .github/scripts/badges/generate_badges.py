#!/usr/bin/env python3
"""
Universal GitHub Actions Badge Generator

This module provides utilities for generating workflow trigger badges
that can be used in PR comments, README files, or documentation.

Usage:
    from generate_badges import BadgeGenerator
    
    generator = BadgeGenerator(
        app_domain="https://your-app.com",
        repo_owner="owner",
        repo_name="repo",
        pr_number=123
    )
    
    # 1. Generate a single badge (direct or UI)
    direct_badge = generator.create_badge(
        text="Run Tests",
        workflow_id="test.yml",
        link_type="direct",
        inputs={"test_type": "all"}
    )
    
    ui_badge = generator.create_badge(
        text="Run Tests",
        workflow_id="test.yml",
        link_type="ui",
        inputs={"test_type": "all"}
    )
    
    # 2. Generate a badge pair (direct + UI together)
    badge_pair = generator.create_badge_pair(
        text="Run Tests",
        workflow_id="test.yml",
        inputs={"test_type": "all"}
    )
    
    # 3. Generate a table with different values
    rows = [
        {"branch": "release/v1.0", "workflow_id": "backport.yml", "inputs": {...}},
        {"branch": "stable", "workflow_id": "backport.yml", "inputs": {...}}
    ]
    
    def formatter(row, gen):
        branch = row["branch"]
        badges = gen.create_badge_pair("Backport", row["workflow_id"], inputs=row["inputs"])
        return [f"`{branch}`", badges]
    
    table = generator.create_table(
        rows=rows,
        column_headers=["Branch", "Actions"],
        row_formatter=formatter
    )
    
    # 4. High-level helpers (optional):
    #    - create_backport_table() - convenience wrapper for backport use case
    #    - generate_comment() - generate complete PR comment
"""

import json
import os
import sys
from urllib.parse import urlencode, quote
from typing import Dict, List, Optional, Literal


class BadgeGenerator:
    """Generator for GitHub Actions workflow trigger badges"""
    
    def __init__(
        self,
        app_domain: str,
        repo_owner: str,
        repo_name: str,
        pr_number: Optional[int] = None,
        pr_branch: Optional[str] = None,
        base_branch: Optional[str] = None
    ):
        """
        Initialize badge generator
        
        Args:
            app_domain: Base URL of the workflow executor app (e.g., "https://app.example.com")
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: Optional PR number (for generating return_url)
            pr_branch: Optional PR branch name
            base_branch: Optional base branch name
        """
        self.app_domain = app_domain.rstrip('/')
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.pr_branch = pr_branch
        self.base_branch = base_branch or "main"
        
        # Generate return_url if pr_number is provided
        self.return_url = None
        if pr_number:
            self.return_url = f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}"
    
    def build_workflow_url(
        self,
        workflow_id: str,
        link_type: Literal["direct", "ui"] = "direct",
        ref: Optional[str] = None,
        inputs: Optional[Dict[str, str]] = None,
        return_url: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Build workflow trigger URL
        
        Args:
            workflow_id: Workflow file name (e.g., "test.yml")
            link_type: "direct" for immediate execution, "ui" for form preview
            ref: Branch or tag name (defaults to base_branch)
            inputs: Dictionary of workflow input parameters
            return_url: URL to return to after workflow execution
            **kwargs: Additional query parameters
            
        Returns:
            Complete workflow trigger URL
        """
        ref = ref or self.base_branch
        inputs = inputs or {}
        
        # Base parameters
        params = {
            "owner": self.repo_owner,
            "repo": self.repo_name,
            "workflow_id": workflow_id,
            "ref": ref
        }
        
        # Add workflow inputs
        params.update(inputs)
        
        # Add return_url if provided
        if return_url:
            params["return_url"] = return_url
        elif self.return_url:
            params["return_url"] = self.return_url
        
        # Add UI flag if needed
        if link_type == "ui":
            params["ui"] = "true"
        
        # Add any additional parameters
        params.update(kwargs)
        
        # Build URL
        query_string = urlencode(params, doseq=True)
        return f"{self.app_domain}/workflow/trigger?{query_string}"
    
    def create_badge(
        self,
        text: str,
        workflow_id: str,
        link_type: Literal["direct", "ui"] = "direct",
        ref: Optional[str] = None,
        inputs: Optional[Dict[str, str]] = None,
        return_url: Optional[str] = None,
        badge_color: str = "2196f3",
        badge_style: str = "flat-square",
        icon: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Create a single badge markdown link
        
        Args:
            text: Badge text to display
            workflow_id: Workflow file name
            link_type: "direct" or "ui"
            ref: Branch name
            inputs: Workflow input parameters
            return_url: Return URL
            badge_color: Badge color (hex without #)
            badge_style: Badge style (flat-square, flat, plastic, etc.)
            icon: Optional icon emoji or text prefix
            **kwargs: Additional URL parameters
            
        Returns:
            Markdown badge link
        """
        url = self.build_workflow_url(
            workflow_id=workflow_id,
            link_type=link_type,
            ref=ref,
            inputs=inputs,
            return_url=return_url,
            **kwargs
        )
        
        # Prepare badge text
        badge_text = f"{icon} {text}".strip() if icon else text
        # Replace spaces with underscores for badge URL
        badge_text_encoded = badge_text.replace(" ", "_")
        
        # Build shields.io badge URL
        badge_url = (
            f"https://img.shields.io/badge/{quote(badge_text_encoded)}-{badge_color}"
            f"?style={badge_style}"
        )
        
        return f"[![{badge_text}]({badge_url})]({url})"
    
    def create_badge_pair(
        self,
        text: str,
        workflow_id: str,
        ref: Optional[str] = None,
        inputs: Optional[Dict[str, str]] = None,
        return_url: Optional[str] = None,
        direct_color: str = "4caf50",
        ui_color: str = "ff9800",
        badge_style: str = "flat-square",
        icon: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Create a pair of badges (direct + UI)
        
        Args:
            text: Badge text
            workflow_id: Workflow file name
            ref: Branch name
            inputs: Workflow inputs
            return_url: Return URL
            direct_color: Color for direct badge
            ui_color: Color for UI badge
            badge_style: Badge style
            icon: Optional icon
            **kwargs: Additional parameters
            
        Returns:
            Two badges separated by space
        """
        direct_badge = self.create_badge(
            text=text,
            workflow_id=workflow_id,
            link_type="direct",
            ref=ref,
            inputs=inputs,
            return_url=return_url,
            badge_color=direct_color,
            badge_style=badge_style,
            icon=icon,
            **kwargs
        )
        
        ui_badge = self.create_badge(
            text="⚙️",
            workflow_id=workflow_id,
            link_type="ui",
            ref=ref,
            inputs=inputs,
            return_url=return_url,
            badge_color=ui_color,
            badge_style=badge_style,
            **kwargs
        )
        
        return f"{direct_badge} {ui_badge}"
    
    def create_table(
        self,
        rows: List[Dict],
        column_headers: List[str],
        row_formatter: callable,
        return_url: Optional[str] = None
    ) -> str:
        """
        Create a markdown table with badges for different row values
        
        Args:
            rows: List of dictionaries, each representing a table row
            column_headers: List of column header names
            row_formatter: Function that takes (row_data, generator) and returns list of cell markdown strings
            return_url: Return URL
            
        Returns:
            Markdown table string
            
        Example:
            rows = [
                {"branch": "release/v1.0", "workflow_id": "backport.yml", "inputs": {...}},
                {"branch": "stable", "workflow_id": "backport.yml", "inputs": {...}}
            ]
            
            def formatter(row, gen):
                branch = row["branch"]
                inputs = row["inputs"]
                workflow_id = row["workflow_id"]
                badges = gen.create_badge_pair("Backport", workflow_id, inputs=inputs)
                return [f"`{branch}`", badges]
            
            table = generator.create_table(
                rows=rows,
                column_headers=["Branch", "Actions"],
                row_formatter=formatter
            )
        """
        if not rows:
            return ""
        
        # Build header
        header = "| " + " | ".join(column_headers) + " |\n"
        separator = "|" + "|".join(["--------" for _ in column_headers]) + "|\n"
        table = header + separator
        
        # Build rows
        for row in rows:
            cells = row_formatter(row, self)
            if len(cells) != len(column_headers):
                raise ValueError(f"Row formatter returned {len(cells)} cells, expected {len(column_headers)}")
            table += "| " + " | ".join(cells) + " |\n"
        
        return table
    
    # ============================================================================
    # HIGH-LEVEL HELPERS (Optional convenience functions)
    # ============================================================================
    
    def create_backport_table(
        self,
        workflow_id: str,
        source_branch: Optional[str] = None,
        target_branches: List[str] = None,
        return_url: Optional[str] = None,
        direct_color: str = "2196f3",
        ui_color: str = "ff9800",
        badge_style: str = "flat-square",
        **kwargs
    ) -> str:
        """
        Create a markdown table with backport badges for multiple branches
        
        HIGH-LEVEL HELPER: This is a convenience wrapper around create_table() 
        for the specific backport use case. For other use cases, use create_table() directly.
        
        Args:
            workflow_id: Workflow file name (e.g., "backport.yml")
            source_branch: Source branch to backport from
            target_branches: List of target branches
            return_url: Return URL
            direct_color: Color for direct badges
            ui_color: Color for UI badges
            badge_style: Badge style
            **kwargs: Additional workflow inputs
            
        Returns:
            Markdown table string
        """
        if not target_branches:
            return ""
        
        source_branch = source_branch or self.pr_branch or self.base_branch
        
        # Prepare rows
        rows = []
        for target_branch in target_branches:
            rows.append({
                "branch": target_branch,
                "workflow_id": workflow_id,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "return_url": return_url or self.return_url,
                "direct_color": direct_color,
                "ui_color": ui_color,
                "badge_style": badge_style,
                "base_branch": self.base_branch,
                **kwargs
            })
        
        # Formatter function
        def formatter(row, gen):
            branch = row["branch"]
            workflow_id = row["workflow_id"]
            inputs = {
                "source_branch": row["source_branch"],
                "target_branch": row["target_branch"],
                **{k: v for k, v in row.items() if k not in [
                    "branch", "workflow_id", "source_branch", "target_branch",
                    "return_url", "direct_color", "ui_color", "badge_style", "base_branch"
                ]}
            }
            badges = gen.create_badge_pair(
                text="▶ Backport",
                workflow_id=workflow_id,
                ref=row["base_branch"],
                inputs=inputs,
                return_url=row["return_url"],
                direct_color=row["direct_color"],
                ui_color=row["ui_color"],
                badge_style=row["badge_style"]
            )
            return [f"`{branch}`", badges]
        
        return self.create_table(
            rows=rows,
            column_headers=["Branch", "Actions"],
            row_formatter=formatter,
            return_url=return_url
        )
    
    def generate_comment(
        self,
        workflows: List[Dict],
        backport_branches: Optional[List[str]] = None,
        backport_workflow_id: str = "backport.yml",
        header: str = "## 🚀 Quick Actions",
        footer: Optional[str] = None,
        show_legend: bool = True
    ) -> str:
        """
        Generate a complete PR comment with badges (OPTIONAL high-level helper)
        
        Note: This is a convenience function. For more control, use low-level
        functions (create_badge, create_badge_pair, create_table) directly
        or use generate_markdown.py wrapper script.
        
        Args:
            workflows: List of workflow configurations, each with:
                - title: Section title
                - workflow_id: Workflow file name
                - ref: Branch name (optional)
                - inputs: Workflow inputs (optional)
                - badge_color: Badge color (optional)
                - icon: Icon emoji (optional)
            backport_branches: List of branches for backport table
            backport_workflow_id: Workflow ID for backport
            header: Comment header text
            footer: Optional footer text
            show_legend: Whether to show badge legend
            
        Returns:
            Complete markdown comment
        """
        lines = [header, ""]
        
        # Add workflows
        for workflow_config in workflows:
            title = workflow_config.get("title", "Workflow")
            workflow_id = workflow_config.get("workflow_id")
            ref = workflow_config.get("ref", self.base_branch)
            inputs = workflow_config.get("inputs", {})
            badge_color = workflow_config.get("badge_color", "4caf50")
            icon = workflow_config.get("icon", "▶")
            
            if not workflow_id:
                continue
            
            lines.append(f"### {title}")
            
            badge_pair = self.create_badge_pair(
                text=title.replace("### ", "").strip(),
                workflow_id=workflow_id,
                ref=ref,
                inputs=inputs,
                return_url=self.return_url,
                direct_color=badge_color,
                icon=icon
            )
            
            lines.append(badge_pair)
            lines.append("")
        
        # Add backport table if branches provided
        if backport_branches:
            lines.append("### 📦 Backport")
            lines.append("")
            backport_table = self.create_backport_table(
                workflow_id=backport_workflow_id,
                source_branch=self.pr_branch,
                target_branches=backport_branches,
                return_url=self.return_url
            )
            lines.append(backport_table)
            lines.append("")
        
        # Add legend
        if show_legend:
            lines.append(
                "▶ - immediately runs the workflow with default parameters.\n"
                "⚙️ - opens UI to review and modify parameters before running.\n"
            )
        
        # Add footer
        if footer:
            lines.append("---")
            lines.append(footer)
        else:
            lines.append("---")
            lines.append("*These links will automatically comment on this PR with the workflow results.*")
            lines.append("")
            lines.append("*Tip: To open links in a new tab, use Ctrl+Click (Windows/Linux) or Cmd+Click (macOS).*")
        
        return "\n".join(lines)


def main():
    """
    CLI interface for badge generation (OPTIONAL)
    
    Note: For GitHub Actions workflows, use generate_markdown.py instead.
    This CLI is provided for convenience and uses the high-level generate_comment() helper.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate GitHub Actions workflow badges")
    parser.add_argument("--app-domain", required=True, help="Base URL of workflow executor app")
    parser.add_argument("--repo-owner", required=True, help="Repository owner")
    parser.add_argument("--repo-name", required=True, help="Repository name")
    parser.add_argument("--pr-number", type=int, help="PR number (for return_url)")
    parser.add_argument("--pr-branch", help="PR branch name")
    parser.add_argument("--base-branch", default="main", help="Base branch name")
    parser.add_argument("--config", help="Path to JSON config file")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    
    args = parser.parse_args()
    
    # Load config if provided
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Initialize generator
    generator = BadgeGenerator(
        app_domain=args.app_domain,
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        pr_number=args.pr_number or config.get("pr_number"),
        pr_branch=args.pr_branch or config.get("pr_branch"),
        base_branch=args.base_branch or config.get("base_branch", "main")
    )
    
    # Generate comment
    workflows = config.get("workflows", [])
    backport_branches = config.get("backport_branches", [])
    backport_workflow_id = config.get("backport_workflow_id", "backport.yml")
    
    comment = generator.generate_comment(
        workflows=workflows,
        backport_branches=backport_branches,
        backport_workflow_id=backport_workflow_id
    )
    
    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == "__main__":
    main()

