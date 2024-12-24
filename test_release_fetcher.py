import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from get_latest_releases import GitHubReleaseFetcher, ReleaseInfo

# Test data
MOCK_RELEASES = [
    # Regular repository release
    {
        'tag_name': 'v1.0.0',
        'name': 'Version 1.0.0',
        'body': 'Regular release notes',
        'draft': False,
        'prerelease': False
    },
    # Monorepo release
    {
        'tag_name': 'op-node/v1.10.2',
        'name': 'op-node v1.10.2',
        'body': 'Monorepo release notes',
        'draft': False,
        'prerelease': False
    },
    # Pre-release
    {
        'tag_name': 'v2.0.0-rc1',
        'name': 'Version 2.0.0-rc1',
        'body': 'Pre-release notes',
        'draft': False,
        'prerelease': True
    },
    # Draft release (should be skipped)
    {
        'tag_name': 'v3.0.0',
        'name': 'Draft Release',
        'body': 'Draft notes',
        'draft': True,
        'prerelease': False
    }
]

@pytest.fixture
def mock_session():
    """Create a mock session with predefined responses."""
    with patch('requests.Session') as mock:
        session = Mock()
        
        # Mock rate limit response
        rate_limit_response = Mock()
        rate_limit_response.json.return_value = {
            'resources': {
                'core': {
                    'limit': 5000,
                    'remaining': 4999,
                    'reset': 1234567890
                }
            }
        }
        rate_limit_response.raise_for_status.return_value = None
        
        # Mock releases response
        releases_response = Mock()
        releases_response.json.return_value = MOCK_RELEASES
        releases_response.raise_for_status.return_value = None
        releases_response.headers = {'X-RateLimit-Remaining': '4999'}
        
        session.get.side_effect = [rate_limit_response, releases_response]
        mock.return_value = session
        yield mock

@pytest.fixture
def temp_artifacts_dir(tmp_path):
    """Create a temporary directory for artifacts."""
    return tmp_path / "artifacts"

@pytest.fixture
def fetcher(temp_artifacts_dir, mock_session):
    """Create a GitHubReleaseFetcher instance with mocked session."""
    with patch.dict(os.environ, {
        'ARTIFACTS_PATH': str(temp_artifacts_dir),
        'GITHUB_TOKEN': 'fake_token'
    }):
        return GitHubReleaseFetcher()

def test_initialization(fetcher, temp_artifacts_dir):
    """Test fetcher initialization."""
    assert fetcher.artifacts_root == str(temp_artifacts_dir)
    assert not fetcher.debug
    assert not fetcher.fetch_history

def test_get_latest_releases(fetcher):
    """Test fetching latest releases."""
    releases = fetcher.get_latest_releases("test/repo")
    
    # Check regular release
    assert '' in releases
    stable, pre = releases['']
    assert stable.tag == 'v1.0.0'
    assert not stable.is_prerelease
    
    # Check monorepo release was detected
    assert 'op-node' in releases
    stable, pre = releases['op-node']
    assert stable.tag == 'op-node/v1.10.2'
    assert not stable.is_prerelease

def test_save_release_notes(fetcher, temp_artifacts_dir):
    """Test saving release notes to files."""
    release = ReleaseInfo('v1.0.0', 'Test release notes', False)
    
    # Save regular release
    result = fetcher.save_release_notes('owner', 'repo', '', release)
    assert result
    
    # Check file was created
    filepath = temp_artifacts_dir / 'owner' / 'repo' / 'v1.0.0.md'
    assert filepath.exists()
    content = filepath.read_text()
    assert 'owner/repo' in content
    assert 'v1.0.0' in content
    assert 'Test release notes' in content

def test_save_monorepo_release_notes(fetcher, temp_artifacts_dir):
    """Test saving monorepo release notes."""
    release = ReleaseInfo('op-node/v1.0.0', 'Test monorepo notes', False)
    
    # Save monorepo release
    result = fetcher.save_release_notes('owner', 'repo', 'op-node', release)
    assert result
    
    # Check file was created with correct structure
    filepath = temp_artifacts_dir / 'owner' / 'repo' / 'op-node' / 'v1.0.0.md'
    assert filepath.exists()
    content = filepath.read_text()
    assert 'owner/repo/op-node' in content
    assert 'op-node/v1.0.0' in content

def test_skip_existing_files(fetcher, temp_artifacts_dir):
    """Test that existing files are not overwritten."""
    release = ReleaseInfo('v1.0.0', 'Test release notes', False)
    
    # Save file first time
    result1 = fetcher.save_release_notes('owner', 'repo', '', release)
    assert result1
    
    # Try to save same file again
    result2 = fetcher.save_release_notes('owner', 'repo', '', release)
    assert not result2  # Should return False for skipped file

def test_process_repository(fetcher, temp_artifacts_dir):
    """Test processing an entire repository."""
    fetcher.process_repository('test/repo')
    
    # Check regular release was saved
    assert (temp_artifacts_dir / 'test' / 'repo' / 'v1.0.0.md').exists()
    
    # Check monorepo release was saved
    assert (temp_artifacts_dir / 'test' / 'repo' / 'op-node' / 'v1.10.2.md').exists()

def test_history_mode(fetcher):
    """Test fetching all historical releases."""
    fetcher.fetch_history = True
    releases = fetcher.get_latest_releases("test/repo")
    
    # Check all non-draft releases were collected
    assert len(releases['']) == 2  # v1.0.0 and v2.0.0-rc1
    assert len(releases['op-node']) == 1  # op-node/v1.10.2

@pytest.mark.parametrize("tag,artifact,expected", [
    ('v1.0.0', '', 'v1.0.0'),  # Regular release
    ('op-node/v1.0.0', 'op-node', 'v1.0.0'),  # Monorepo release
    ('v2.0.0-rc1', '', 'v2.0.0-rc1'),  # Pre-release
])
def test_tag_cleanup(fetcher, temp_artifacts_dir, tag, artifact, expected):
    """Test tag name cleanup for different formats."""
    release = ReleaseInfo(tag, 'Test notes', False)
    fetcher.save_release_notes('owner', 'repo', artifact, release)
    
    if artifact:
        base_path = temp_artifacts_dir / 'owner' / 'repo' / artifact
    else:
        base_path = temp_artifacts_dir / 'owner' / 'repo'
    
    assert (base_path / f"{expected}.md").exists() 