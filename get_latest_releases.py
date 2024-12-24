#!/usr/bin/env python3
"""
GitHub Release Notes Fetcher

This script fetches the latest stable and pre-release information from specified GitHub repositories
and saves the release notes as markdown files in an organized directory structure. Automatically
detects and organizes releases for monorepos and single repositories.

Configuration Priority (highest to lowest):
1. Environment Variables
2. Command Line Arguments
3. Configuration File (repos.cfg)
4. Default Values

Environment Variables:
    GITHUB_TOKEN="your_github_token"  # Strongly recommended to avoid rate limits
    GITHUB_REPOS="owner1/repo1,owner2/repo2"
    ARTIFACTS_PATH="/path/to/artifacts"
    ARTIFACT_HISTORY="true"           # Fetch all historical releases
    GITHUB_RELEASES_DEBUG="true"      # Enable debug logging

Command Line Arguments:
    --repos owner1/repo1,owner2/repo2
    --artifacts-path /path/to/artifacts
    --history                         # Fetch all historical releases
    --debug                           # Enable debug logging

Configuration File (repos.cfg):
    [repositories]
    repos = owner1/repo1,owner2/repo2
    
    [artifacts]
    path = /path/to/artifacts
    history = true                    # Fetch all historical releases

    [settings]
    debug = true                      # Enable debug logging

Default Values:
    artifacts.path = "artifacts"
    artifacts.history = false         # Only fetch latest releases by default
    debug = false                     # Debug logging disabled by default

Output Structure:
    {artifacts_path}/
        {owner}/
            {repo}/
                {artifact}/           # Created automatically for monorepo releases
                    {tag}.md

Example Usage:
    # Using environment variables:
    export GITHUB_REPOS="ethereum-optimism/optimism"
    export ARTIFACTS_PATH="./release-notes"
    python get_latest_releases.py

    # Using command line:
    python get_latest_releases.py \\
        --repos ethereum-optimism/optimism \\
        --artifacts-path ./release-notes

    # Using config file:
    # Create repos.cfg with configuration and run:
    python get_latest_releases.py

Dependencies:
    pip install requests

Notes:
    - GitHub API rate limits are strict without authentication:
      * Authenticated: 5,000 requests per hour
      * Unauthenticated: 60 requests per hour
    - Set GITHUB_TOKEN environment variable to avoid rate limiting:
      export GITHUB_TOKEN="ghp_your_token_here"
    - Monorepo artifacts are automatically detected from release tags
      Example: "op-node/v1.10.2" creates artifacts/owner/repo/op-node/v1.10.2.md
    - Release notes are saved in markdown format with release type clearly indicated
"""

import os
import sys
import requests
import argparse
import configparser
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Constants
GITHUB_API_BASE = "https://api.github.com"
ENV_VAR_NAME = "GITHUB_REPOS"
CONFIG_FILE_NAMES = ["repos.cfg", "repos.conf"]
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
}
DEBUG_ENV_VAR = "GITHUB_RELEASES_DEBUG"

# Add your GitHub token here or use environment variable GITHUB_TOKEN
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

class ReleaseInfo:
    def __init__(self, tag: str, body: str, is_prerelease: bool):
        self.tag = tag
        self.body = body
        self.is_prerelease = is_prerelease

class GitHubReleaseFetcher:
    def __init__(self):
        self.session = requests.Session()
        if not GITHUB_TOKEN:
            print("Warning: No GITHUB_TOKEN found. API rate limits will be restricted.")
            print("Set GITHUB_TOKEN environment variable to increase rate limits.")
        self.session.headers.update(HEADERS)
        self.artifacts_root = self.get_artifacts_path()
        self.debug = self.get_debug_setting()
        self.fetch_history = self.get_history_setting()
        self.check_rate_limit()

    def check_rate_limit(self):
        """Check and display current rate limit status."""
        try:
            response = self.session.get(f"{GITHUB_API_BASE}/rate_limit")
            response.raise_for_status()
            data = response.json()
            rate = data['resources']['core']
            
            self.debug_print(f"GitHub API Rate Limit Status:")
            self.debug_print(f"  Remaining: {rate['remaining']}/{rate['limit']}")
            if rate['remaining'] < 100:
                from datetime import datetime
                reset_time = datetime.fromtimestamp(rate['reset'])
                print(f"Warning: Only {rate['remaining']} API calls remaining. Resets at {reset_time}")
        except Exception as e:
            print(f"Warning: Could not check rate limit status: {str(e)}")

    def get_artifacts_path(self) -> str:
        """Get the root path for artifacts from environment, CLI, or config file."""
        # 1. Check environment variable
        env_path = os.getenv('ARTIFACTS_PATH')
        if env_path:
            return env_path

        # 2. Check command line arguments
        parser = argparse.ArgumentParser(description='Fetch GitHub release notes')
        parser.add_argument('--artifacts-path', help='Path to store artifact files')
        args, _ = parser.parse_known_args()  # Use known_args to not interfere with other arg parsing
        if args.artifacts_path:
            return args.artifacts_path

        # 3. Check config file
        for config_file in CONFIG_FILE_NAMES:
            if os.path.exists(config_file):
                config = configparser.ConfigParser()
                config.read(config_file)
                if 'artifacts' in config and 'path' in config['artifacts']:
                    return config['artifacts']['path']

        # 4. Default value
        return 'artifacts'

    def get_debug_setting(self) -> bool:
        """Get debug setting from environment, CLI, or config file."""
        # 1. Check environment variable
        env_debug = os.getenv(DEBUG_ENV_VAR)
        if env_debug is not None:
            return env_debug.lower() in ('true', '1', 'yes', 'on')

        # 2. Check command line arguments
        parser = argparse.ArgumentParser(description='Fetch GitHub release notes')
        parser.add_argument('--debug', action='store_true', help='Enable debug logging')
        args, _ = parser.parse_known_args()
        if args.debug:
            return True

        # 3. Check config file
        for config_file in CONFIG_FILE_NAMES:
            if os.path.exists(config_file):
                config = configparser.ConfigParser()
                config.read(config_file)
                if 'settings' in config and 'debug' in config['settings']:
                    return config['settings']['debug'].lower() in ('true', '1', 'yes', 'on')

        # 4. Default value
        return False

    def get_history_setting(self) -> bool:
        """Get history setting from environment, CLI, or config file."""
        # 1. Check environment variable
        env_history = os.getenv('ARTIFACT_HISTORY')
        if env_history is not None:
            return env_history.lower() in ('true', '1', 'yes', 'on')

        # 2. Check command line arguments
        parser = argparse.ArgumentParser(description='Fetch GitHub release notes')
        parser.add_argument('--history', action='store_true', help='Fetch all historical releases')
        args, _ = parser.parse_known_args()
        if args.history:
            return True

        # 3. Check config file
        for config_file in CONFIG_FILE_NAMES:
            if os.path.exists(config_file):
                config = configparser.ConfigParser()
                config.read(config_file)
                if 'artifacts' in config and 'history' in config['artifacts']:
                    return config['artifacts']['history'].lower() in ('true', '1', 'yes', 'on')

        # 4. Default value
        return False

    def debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"DEBUG: {message}")

    def get_repositories(self) -> List[str]:
        """Get repository list from environment variable, CLI, or config file."""
        # 1. Check environment variable
        repos = os.getenv(ENV_VAR_NAME)
        if repos:
            return repos.split(',')

        # 2. Check command line arguments
        parser = argparse.ArgumentParser(description='Fetch GitHub release notes')
        parser.add_argument('--repos', help='Comma-separated list of repositories (owner/repo)')
        args, _ = parser.parse_known_args()
        if args.repos:
            return args.repos.split(',')

        # 3. Check config file
        for config_file in CONFIG_FILE_NAMES:
            if os.path.exists(config_file):
                config = configparser.ConfigParser()
                config.read(config_file)
                if 'repositories' in config and 'repos' in config['repositories']:
                    return config['repositories']['repos'].split(',')

        print("Error: No repositories specified. Please use environment variable, config file, or --repos argument.")
        sys.exit(1)

    def get_monorepo_artifacts(self, repo: str) -> List[str]:
        """Get list of artifacts for a monorepo from environment, CLI, or config file."""
        # 1. Check environment variable
        env_artifacts = os.getenv(f'MONOREPO_ARTIFACTS_{repo.replace("/", "_").upper()}')
        if env_artifacts:
            return env_artifacts.split(',')

        # 2. Check command line arguments
        parser = argparse.ArgumentParser(description='Fetch GitHub release notes')
        parser.add_argument(f'--artifacts-{repo.replace("/", "-")}', 
                           help=f'Comma-separated list of artifacts for {repo}')
        args, _ = parser.parse_known_args()
        arg_name = f'artifacts_{repo.replace("/", "_")}'
        if hasattr(args, arg_name) and getattr(args, arg_name):
            return getattr(args, arg_name).split(',')

        # 3. Check config file
        for config_file in CONFIG_FILE_NAMES:
            if os.path.exists(config_file):
                config = configparser.ConfigParser()
                config.read(config_file)
                if 'monorepos' in config and repo in config['monorepos']:
                    return config['monorepos'][repo].split(',')

        # 4. Default value (empty string for non-monorepos)
        return ['']

    def get_latest_releases(self, repo: str) -> Dict[str, Union[List[ReleaseInfo], Tuple[Optional[ReleaseInfo], Optional[ReleaseInfo]]]]:
        """Fetch latest stable and pre-release for a repository, organized by artifact."""
        artifacts_releases = {}  # Dict to store releases by artifact
        page = 1
        per_page = 100  # GitHub's maximum items per page
        
        # Update the debug print to handle both modes
        def format_releases_debug(artifacts_releases):
            debug_info = []
            for k, v in artifacts_releases.items():
                if isinstance(v, list):
                    # History mode - show count and tags
                    tags = [r.tag for r in v]
                    debug_info.append((k, f"{len(v)} releases: {tags}"))
                else:
                    # Latest only mode - show stable and pre-release tags
                    stable, pre = v
                    debug_info.append((k, (
                        stable.tag if stable else None,
                        pre.tag if pre else None
                    )))
            return debug_info

        try:
            # Get configured artifacts
            configured_artifacts = self.get_monorepo_artifacts(repo)
            self.debug_print(f"Configured artifacts for {repo}: {configured_artifacts}")
            
            # Initialize releases dict for each artifact
            for artifact in configured_artifacts:
                if self.fetch_history:
                    artifacts_releases[artifact] = []  # List for all releases
                else:
                    artifacts_releases[artifact] = (None, None)  # Tuple for latest only

            while True:
                url = f"{GITHUB_API_BASE}/repos/{repo}/releases"
                params = {
                    'page': page,
                    'per_page': per_page
                }
                
                self.debug_print(f"Fetching page {page} for {repo}")
                response = self.session.get(url, params=params)
                
                # Handle rate limiting more gracefully
                if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
                    remaining = int(response.headers['X-RateLimit-Remaining'])
                    if remaining == 0:
                        from datetime import datetime
                        reset_time = datetime.fromtimestamp(int(response.headers['X-RateLimit-Reset']))
                        print(f"Error: GitHub API rate limit reached. Resets at {reset_time}")
                        if not GITHUB_TOKEN:
                            print("Tip: Set GITHUB_TOKEN environment variable to increase rate limits.")
                        return artifacts_releases

                response.raise_for_status()
                releases = response.json()

                if not releases:
                    if page == 1:
                        print(f"Warning: No releases found for {repo}")
                        return {'': (None, None)}
                    break  # No more releases to process

                for release in releases:
                    if release['draft']:
                        continue

                    # Determine which artifact this release belongs to
                    release_name = release['name'].lower() if release['name'] else ''
                    release_tag = release['tag_name'].lower()
                    release_body = release['body'].lower() if release['body'] else ''
                    
                    # First try to match with configured artifacts
                    matched_artifact = ''
                    for artifact in configured_artifacts:
                        if artifact and (
                            (artifact.lower() in release_name) or 
                            (artifact.lower() in release_tag) or 
                            (artifact.lower() in release_body)
                        ):
                            matched_artifact = artifact
                            self.debug_print(f"Matched release {release['tag_name']} to configured artifact {artifact}")
                            break
                    
                    # If no configured artifact matched, try to extract from tag
                    if not matched_artifact and '/' in release['tag_name']:
                        potential_artifact = release['tag_name'].split('/')[0]
                        self.debug_print(f"Extracted potential artifact {potential_artifact} from tag {release['tag_name']}")
                        matched_artifact = potential_artifact
                        # Initialize the new artifact based on history mode
                        if matched_artifact not in artifacts_releases:
                            if self.fetch_history:
                                artifacts_releases[matched_artifact] = []
                            else:
                                artifacts_releases[matched_artifact] = (None, None)
                    
                    release_info = ReleaseInfo(
                        release['tag_name'],
                        release['body'] or "No release notes provided.",
                        release['prerelease']
                    )

                    if self.fetch_history:
                        # Store all releases
                        artifacts_releases[matched_artifact].append(release_info)
                    else:
                        # Store only latest stable and pre-release
                        current_stable, current_pre = artifacts_releases.get(matched_artifact, (None, None))
                        if release['prerelease'] and not current_pre:
                            artifacts_releases[matched_artifact] = (current_stable, release_info)
                        elif not release['prerelease'] and not current_stable:
                            artifacts_releases[matched_artifact] = (release_info, current_pre)

                    # Stop condition changes based on history mode
                    if not self.fetch_history:
                        if all(stable and pre for stable, pre in artifacts_releases.values()):
                            self.debug_print("Found all needed releases, stopping pagination")
                            break

                # Check if we should continue to the next page
                if len(releases) < per_page:
                    break  # No more pages to fetch
                
                # Check rate limit
                if 'X-RateLimit-Remaining' in response.headers:
                    remaining = int(response.headers['X-RateLimit-Remaining'])
                    if remaining < 1:
                        reset_time = int(response.headers['X-RateLimit-Reset'])
                        print(f"Warning: GitHub API rate limit reached. Resets at timestamp {reset_time}")
                        break

                page += 1

            self.debug_print(f"Final artifacts_releases: {format_releases_debug(artifacts_releases)}")
            return artifacts_releases

        except requests.exceptions.RequestException as e:
            print(f"Error fetching releases for {repo}: {str(e)}")
            return {'': (None, None)}

    def save_release_notes(self, owner: str, repo: str, artifact: str, release: ReleaseInfo) -> bool:
        """
        Save release notes to a markdown file.
        Returns True if file was written, False if skipped.
        """
        try:
            # Create directory structure starting from artifacts root
            if artifact:  # Only include artifact in path if it exists
                base_path = Path(self.artifacts_root) / owner / repo / artifact
            else:
                base_path = Path(self.artifacts_root) / owner / repo
            
            self.debug_print(f"Creating directory structure at {base_path}")
            base_path.mkdir(parents=True, exist_ok=True)

            # Clean up tag name - remove artifact prefix if present
            tag = release.tag
            if artifact and tag.startswith(f"{artifact}/"):
                tag = tag[len(artifact)+1:]  # +1 for the '/'
            
            # Create filename
            filename = f"{tag}.md"
            filepath = base_path / filename

            # Check if file already exists
            if filepath.exists():
                self.debug_print(f"Skipping existing file: {filepath}")
                return False

            self.debug_print(f"Writing new file to {filepath}")

            # Prepare content
            release_type = "Pre-release" if release.is_prerelease else "Stable Release"
            full_path = f"{owner}/{repo}"
            if artifact:
                full_path += f"/{artifact}"
            content = f"""# {full_path} - {release.tag} ({release_type})

## Release Notes

{release.body}
"""

            # Write to file
            filepath.write_text(content, encoding='utf-8')
            self.debug_print(f"Saved release notes to: {filepath}")
            return True
        except Exception as e:
            print(f"Error saving release notes: {str(e)}")
            print(f"Debug info: owner={owner}, repo={repo}, artifact={artifact}, tag={release.tag}")
            return False

    def process_repository(self, repo: str):
        """Process a single repository and its artifacts."""
        try:
            owner, repo_name = repo.strip().split('/')
        except ValueError:
            print(f"Error: Invalid repository format '{repo}'. Expected format: owner/repo")
            return

        artifacts_releases = self.get_latest_releases(f"{owner}/{repo_name}")
        summary = {}  # Track written/skipped counts per artifact

        if self.fetch_history:
            # Process all historical releases
            for artifact, releases in artifacts_releases.items():
                written = skipped = 0
                for release in releases:
                    if self.save_release_notes(owner, repo_name, artifact, release):
                        written += 1
                    else:
                        skipped += 1
                summary[artifact] = {'written': written, 'skipped': skipped}
        else:
            # Process only latest releases
            for artifact, (stable_release, prerelease) in artifacts_releases.items():
                written = skipped = 0
                if stable_release:
                    if self.save_release_notes(owner, repo_name, artifact, stable_release):
                        written += 1
                    else:
                        skipped += 1
                if prerelease:
                    if self.save_release_notes(owner, repo_name, artifact, prerelease):
                        written += 1
                    else:
                        skipped += 1
                summary[artifact] = {'written': written, 'skipped': skipped}

        # Print summary for this repository
        print(f"\nSummary for {repo}:")
        for artifact, counts in summary.items():
            artifact_path = f"{artifact}/" if artifact else ""
            print(f"  {artifact_path}")
            print(f"    Files: {counts['written']} written, {counts['skipped']} unchanged")
            
            # Show latest releases for this artifact
            if self.fetch_history and artifacts_releases[artifact]:
                latest = artifacts_releases[artifact][0]  # Assuming sorted by date
                print(f"    Latest: {latest.tag}")
            elif not self.fetch_history:
                stable, pre = artifacts_releases[artifact]
                if stable:
                    print(f"    Latest stable: {stable.tag}")
                if pre:
                    print(f"    Latest pre-release: {pre.tag}")

def main():
    fetcher = GitHubReleaseFetcher()
    repositories = fetcher.get_repositories()

    for repo in repositories:
        print(f"\nProcessing repository: {repo}")
        fetcher.process_repository(repo)

if __name__ == "__main__":
    main() 