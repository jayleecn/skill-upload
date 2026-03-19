"""Packager module for creating zip archives from local dirs or GitHub repos."""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import urllib.request
import json


class Packager:
    """Create zip archives from local directories or GitHub repositories."""

    @staticmethod
    def from_local(directory: str, output_path: Optional[str] = None) -> str:
        """
        Create zip from local directory.

        Args:
            directory: Path to local directory
            output_path: Optional output zip path (default: /tmp/{dirname}.zip)

        Returns:
            Path to created zip file
        """
        src_path = Path(directory).expanduser().resolve()

        if not src_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not src_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")

        # Default output path
        if output_path is None:
            output_path = f"/tmp/{src_path.name}.zip"

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Use git archive if it's a git repo, otherwise use zip command
        git_dir = src_path / ".git"
        if git_dir.exists():
            # Use git archive for clean exports
            result = subprocess.run(
                ["git", "archive", "--format=zip", f"--output={output}", "HEAD"],
                cwd=str(src_path),
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"git archive failed: {result.stderr}")
        else:
            # Use zip command for non-git directories
            result = subprocess.run(
                ["zip", "-r", str(output), "."],
                cwd=str(src_path),
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"zip failed: {result.stderr}")

        return str(output)

    @staticmethod
    def from_github(repo_url: str, output_path: Optional[str] = None, branch: str = "main") -> str:
        """
        Download zip from GitHub repository.

        Args:
            repo_url: GitHub repo URL (e.g., https://github.com/user/repo)
            output_path: Optional output zip path
            branch: Branch to download (default: main)

        Returns:
            Path to downloaded zip file
        """
        # Normalize URL
        url = repo_url.rstrip('/').replace('.git', '')

        # Extract repo name
        repo_name = url.split('/')[-1]

        # Default output path
        if output_path is None:
            output_path = f"/tmp/{repo_name}.zip"

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Try archive URL first (smaller, no .git history)
        archive_url = f"{url}/archive/refs/heads/{branch}.zip"

        try:
            urllib.request.urlretrieve(archive_url, str(output))
        except Exception as e:
            # Fallback to raw zip if archive fails
            raise RuntimeError(f"Failed to download from GitHub: {e}")

        return str(output)

    @staticmethod
    def get_github_info(repo_url: str) -> dict:
        """
        Get information about a GitHub repository.

        Args:
            repo_url: GitHub repo URL

        Returns:
            dict with repo info
        """
        # Normalize URL
        url = repo_url.rstrip('/').replace('.git', '')

        # Convert to API URL
        # https://github.com/user/repo -> https://api.github.com/repos/user/repo
        parts = url.replace('https://github.com/', '').split('/')
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

        owner, repo = parts[0], parts[1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            with urllib.request.urlopen(api_url) as response:
                data = json.loads(response.read().decode())
                return {
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "default_branch": data.get("default_branch", "main"),
                    "updated_at": data.get("updated_at"),
                    "stars": data.get("stargazers_count"),
                    "url": data.get("html_url")
                }
        except Exception as e:
            return {"error": str(e), "url": repo_url}
