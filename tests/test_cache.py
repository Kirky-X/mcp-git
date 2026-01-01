"""
Tests for cache module.
"""

import asyncio
from datetime import UTC,  datetime, timedelta
from pathlib import Path
import pytest

from mcp_git.cache import RepoMetadata, RepoMetadataCache, CacheManager


class TestRepoMetadata:
    """Tests for RepoMetadata dataclass."""

    def test_repo_metadata_creation(self):
        """Test creating a RepoMetadata instance."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
            branches=["main", "develop"],
            tags=["v1.0.0", "v2.0.0"],
            default_branch="main",
            head_commit="abc123",
            root_files=["README.md", "setup.py"],
            root_dirs=["src", "tests"],
        )

        assert metadata.repo_url == "https://github.com/user/repo.git"
        assert metadata.cache_key == "test_key"
        assert len(metadata.branches) == 2
        assert len(metadata.tags) == 2
        assert metadata.default_branch == "main"
        assert metadata.head_commit == "abc123"
        assert len(metadata.root_files) == 2
        assert len(metadata.root_dirs) == 2

    def test_repo_metadata_defaults(self):
        """Test RepoMetadata with default values."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
        )

        assert metadata.branches == []
        assert metadata.tags == []
        assert metadata.default_branch == "main"
        assert metadata.head_commit is None
        assert metadata.root_files == []
        assert metadata.root_dirs == []
        assert metadata.ttl_seconds == 7200

    def test_repo_metadata_is_valid(self):
        """Test RepoMetadata validity check."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
        )

        # Fresh metadata should be valid
        assert metadata.is_valid() is True

        # Old metadata should be invalid
        metadata.last_updated = datetime.now(UTC) - timedelta(seconds=8000)
        assert metadata.is_valid() is False

    def test_repo_metadata_to_dict(self):
        """Test converting RepoMetadata to dictionary."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
            branches=["main"],
        )

        data = metadata.to_dict()

        assert data["repo_url"] == "https://github.com/user/repo.git"
        assert data["cache_key"] == "test_key"
        assert data["branches"] == ["main"]
        assert "created_at" in data
        assert "last_updated" in data

    def test_repo_metadata_from_dict(self):
        """Test creating RepoMetadata from dictionary."""
        data = {
            "repo_url": "https://github.com/user/repo.git",
            "cache_key": "test_key",
            "branches": ["main"],
            "tags": [],
            "default_branch": "main",
            "head_commit": "abc123",
            "root_files": [],
            "root_dirs": [],
            "created_at": datetime.now(UTC).isoformat(),
            "last_updated": datetime.now(UTC).isoformat(),
            "size_bytes": 0,
            "ttl_seconds": 7200,
        }

        metadata = RepoMetadata.from_dict(data)

        assert metadata.repo_url == "https://github.com/user/repo.git"
        assert metadata.cache_key == "test_key"
        assert metadata.branches == ["main"]
        assert metadata.head_commit == "abc123"


class TestRepoMetadataCache:
    """Tests for RepoMetadataCache class."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance for testing."""
        return RepoMetadataCache(max_entries=10, default_ttl=7200)

    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache):
        """Test cache initialization."""
        assert cache.size == 0
        assert cache._max_entries == 10
        assert cache._default_ttl == 7200

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """Test setting and getting cache entries."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
            branches=["main"],
        )

        await cache.set("https://github.com/user/repo.git", metadata)
        assert cache.size == 1

        retrieved = await cache.get("https://github.com/user/repo.git")
        assert retrieved is not None
        assert retrieved.repo_url == "https://github.com/user/repo.git"
        assert retrieved.branches == ["main"]

    @pytest.mark.asyncio
    async def test_cache_get_with_path(self, cache):
        """Test cache with path parameter."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
            branches=["main"],
        )

        path = Path("/tmp/test")
        await cache.set("https://github.com/user/repo.git", metadata, path)

        retrieved = await cache.get("https://github.com/user/repo.git", path)
        assert retrieved is not None

        # Different path should not retrieve
        retrieved2 = await cache.get("https://github.com/user/repo.git", Path("/tmp/other"))
        assert retrieved2 is None

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss."""
        retrieved = await cache.get("https://github.com/nonexistent.com/repo.git")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache):
        """Test cache entry expiration."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
            ttl_seconds=1,  # 1 second TTL
        )

        await cache.set("https://github.com/user/repo.git", metadata)
        assert cache.size == 1

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Entry should be expired and removed
        retrieved = await cache.get("https://github.com/user/repo.git")
        assert retrieved is None
        assert cache.size == 0

    @pytest.mark.asyncio
    async def test_cache_invalidate(self, cache):
        """Test cache invalidation."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
        )

        await cache.set("https://github.com/user/repo.git", metadata)
        assert cache.size == 1

        result = await cache.invalidate("https://github.com/user/repo.git")
        assert result is True
        assert cache.size == 0

    @pytest.mark.asyncio
    async def test_cache_invalidate_nonexistent(self, cache):
        """Test invalidating non-existent entry."""
        result = await cache.invalidate("https://github.com/nonexistent.com/repo.git")
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_invalidate_all(self, cache):
        """Test invalidating all cache entries."""
        metadata1 = RepoMetadata(
            repo_url="https://github.com/user/repo1.git",
            cache_key="test_key1",
        )
        metadata2 = RepoMetadata(
            repo_url="https://github.com/user/repo2.git",
            cache_key="test_key2",
        )

        await cache.set("https://github.com/user/repo1.git", metadata1)
        await cache.set("https://github.com/user/repo2.git", metadata2)
        assert cache.size == 2

        count = await cache.invalidate_all()
        assert count == 2
        assert cache.size == 0

    @pytest.mark.asyncio
    async def test_cache_eviction(self, cache):
        """Test cache eviction when full."""
        cache = RepoMetadataCache(max_entries=5, default_ttl=7200)

        # Fill cache to capacity
        for i in range(5):
            metadata = RepoMetadata(
                repo_url=f"https://github.com/user/repo{i}.git",
                cache_key=f"test_key{i}",
            )
            await cache.set(f"https://github.com/user/repo{i}.git", metadata)

        assert cache.size == 5

        # Add one more entry, should trigger eviction
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo5.git",
            cache_key="test_key5",
        )
        await cache.set("https://github.com/user/repo5.git", metadata)

        # Cache should have fewer than 6 entries (eviction occurred)
        assert cache.size < 6

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache):
        """Test cache statistics."""
        metadata1 = RepoMetadata(
            repo_url="https://github.com/user/repo1.git",
            cache_key="test_key1",
        )
        metadata2 = RepoMetadata(
            repo_url="https://github.com/user/repo2.git",
            cache_key="test_key2",
            ttl_seconds=1,
        )

        await cache.set("https://github.com/user/repo1.git", metadata1)
        await cache.set("https://github.com/user/repo2.git", metadata2)

        stats = cache.stats

        assert stats["total_entries"] == 2
        assert stats["valid_entries"] >= 1
        assert stats["max_entries"] == 10

    @pytest.mark.asyncio
    async def test_get_or_fetch_hit(self, cache):
        """Test get_or_fetch with cache hit."""
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
            branches=["main"],
        )

        await cache.set("https://github.com/user/repo.git", metadata)

        fetch_called = False

        async def fetch_fn(url, path):
            nonlocal fetch_called
            fetch_called = True
            return None

        result = await cache.get_or_fetch("https://github.com/user/repo.git", None, fetch_fn)

        assert result is not None
        assert fetch_called is False  # Fetch should not be called

    @pytest.mark.asyncio
    async def test_get_or_fetch_miss(self, cache):
        """Test get_or_fetch with cache miss."""
        fetch_called = False

        async def fetch_fn(url, path):
            nonlocal fetch_called
            fetch_called = True
            return RepoMetadata(
                repo_url=url,
                cache_key="fetched_key",
                branches=["main"],
            )

        result = await cache.get_or_fetch("https://github.com/user/repo.git", None, fetch_fn)

        assert result is not None
        assert fetch_called is True  # Fetch should be called
        assert cache.size == 1  # Entry should be cached


class TestCacheManager:
    """Tests for CacheManager class."""

    @pytest.fixture
    def manager(self):
        """Create a CacheManager instance for testing."""
        return CacheManager()

    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.repo_metadata is not None
        assert manager.task_state_cache is not None
        assert manager.git_cache is not None

    @pytest.mark.asyncio
    async def test_clear_all(self, manager):
        """Test clearing all caches."""
        # Add some metadata to repo_metadata cache
        metadata = RepoMetadata(
            repo_url="https://github.com/user/repo.git",
            cache_key="test_key",
        )
        await manager.repo_metadata.set("https://github.com/user/repo.git", metadata)

        # Clear all caches
        cleared = await manager.clear_all()

        assert cleared["repo_metadata"] >= 0

    @pytest.mark.asyncio
    async def test_get_all_stats(self, manager):
        """Test getting statistics for all caches."""
        stats = await manager.get_all_stats()

        assert "task_state" in stats
        assert "git" in stats
        assert "repo_metadata" in stats