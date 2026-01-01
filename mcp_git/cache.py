"""
Repository metadata cache for mcp-git.

Caches repository metadata like branch list, tag list, and file tree
to improve performance for frequently accessed repositories.
"""

import asyncio
import hashlib
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from mcp_git.metrics import metrics, repository_metadata_cache

UTC = timezone.utc


@dataclass
class RepoMetadata:
    """Cached repository metadata."""

    # Identity
    repo_url: str
    cache_key: str

    # Content
    branches: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    default_branch: str = "main"
    head_commit: str | None = None

    # File tree (optional, can be large)
    root_files: list[str] = field(default_factory=list)
    root_dirs: list[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    size_bytes: int = 0

    # Validity
    ttl_seconds: int = 7200  # 2 hours

    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        age = datetime.now(UTC) - self.last_updated
        return age < timedelta(seconds=self.ttl_seconds)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repo_url": self.repo_url,
            "cache_key": self.cache_key,
            "branches": self.branches,
            "tags": self.tags,
            "default_branch": self.default_branch,
            "head_commit": self.head_commit,
            "root_files": self.root_files,
            "root_dirs": self.root_dirs,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "size_bytes": self.size_bytes,
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepoMetadata":
        """Create from dictionary."""
        return cls(
            repo_url=data["repo_url"],
            cache_key=data["cache_key"],
            branches=data.get("branches", []),
            tags=data.get("tags", []),
            default_branch=data.get("default_branch", "main"),
            head_commit=data.get("head_commit"),
            root_files=data.get("root_files", []),
            root_dirs=data.get("root_dirs", []),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(UTC)),
            last_updated=datetime.fromisoformat(data["last_updated"])
            if isinstance(data.get("last_updated"), str)
            else data.get("last_updated", datetime.now(UTC)),
            size_bytes=data.get("size_bytes", 0),
            ttl_seconds=data.get("ttl_seconds", 7200),
        )


class RepoMetadataCache:
    """
    Cache for repository metadata using moka.

    Provides fast access to frequently accessed repository information
    like branches, tags, and file listings.
    """

    def __init__(
        self,
        max_entries: int = 200,
        default_ttl: int = 7200,
    ):
        """
        Initialize the repository metadata cache.

        Args:
            max_entries: Maximum number of cached repositories
            default_ttl: Default TTL in seconds (2 hours)
        """
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._cache: Any = None
        self._use_moka = False

        try:
            from moka import MokaCache  # type: ignore[import-untyped]

            self._cache = MokaCache(
                max_capacity=max_entries,
                time_to_live=default_ttl,
            )
            self._use_moka = True
            logger.info("Using moka for repository metadata cache")
        except ImportError:
            logger.warning("moka not installed, falling back to simple dict cache")
            self._cache = {}
            self._use_moka = False

    def _generate_cache_key(self, repo_url: str, path: Path | None = None) -> str:
        """Generate a cache key for a repository."""
        # Include path if provided for workspace-specific caching
        key_data = repo_url
        if path:
            key_data = f"{repo_url}:{str(path)}"

        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    async def get(
        self,
        repo_url: str,
        path: Path | None = None,
    ) -> RepoMetadata | None:
        """
        Get cached metadata for a repository.

        Args:
            repo_url: Repository URL
            path: Optional workspace path

        Returns:
            Cached metadata or None if not found/invalid
        """
        cache_key = self._generate_cache_key(repo_url, path)

        if self._use_moka:
            metadata = self._cache.get(cache_key)
            if metadata is not None and metadata.is_valid():
                metrics.record_cache_hit("repo_metadata")
                return metadata  # type: ignore[no-any-return]
            elif metadata is not None:
                # Expired, moka will handle it automatically
                metrics.record_cache_miss("repo_metadata")
                return None
            else:
                metrics.record_cache_miss("repo_metadata")
                return None
        else:
            # Fallback to simple dict cache
            async with self._lock:
                if cache_key in self._cache:
                    metadata = self._cache[cache_key]
                    if metadata.is_valid():
                        metrics.record_cache_hit("repo_metadata")
                        return metadata  # type: ignore[no-any-return]
                    else:
                        # Expired, remove from cache
                        del self._cache[cache_key]
                        metrics.record_cache_miss("repo_metadata")

        return None

    async def set(
        self,
        repo_url: str,
        metadata: RepoMetadata,
        path: Path | None = None,
    ) -> None:
        """
        Cache repository metadata.

        Args:
            repo_url: Repository URL
            metadata: Metadata to cache
            path: Optional workspace path
        """
        cache_key = self._generate_cache_key(repo_url, path)
        metadata.cache_key = cache_key
        # Only set TTL if not already set
        if metadata.ttl_seconds == 7200:  # Default value
            metadata.ttl_seconds = self._default_ttl

        if self._use_moka:
            self._cache.insert(cache_key, metadata)
            metrics.update_cache_size("repo_metadata", len(self._cache))
        else:
            # Fallback to simple dict cache
            async with self._lock:
                # Check if we need to evict entries
                if len(self._cache) >= self._max_entries:
                    self._evict_oldest()

                self._cache[cache_key] = metadata
                metrics.update_cache_size("repo_metadata", len(self._cache))

    async def invalidate(
        self,
        repo_url: str,
        path: Path | None = None,
    ) -> bool:
        """
        Invalidate cached metadata for a repository.

        Args:
            repo_url: Repository URL
            path: Optional workspace path

        Returns:
            True if entry was found and removed
        """
        cache_key = self._generate_cache_key(repo_url, path)

        if self._use_moka:
            entry = self._cache.get(cache_key)
            if entry is not None:
                self._cache.invalidate(cache_key)
                metrics.update_cache_size("repo_metadata", len(self._cache))
                return True
            return False
        else:
            # Fallback to simple dict cache
            async with self._lock:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    metrics.update_cache_size("repo_metadata", len(self._cache))
                    return True

        return False

    async def invalidate_all(self) -> int:
        """
        Invalidate all cached entries.

        Returns:
            Number of entries invalidated
        """
        if self._use_moka:
            count = len(self._cache)
            self._cache.invalidate_all()
            metrics.update_cache_size("repo_metadata", 0)
            return count
        else:
            # Fallback to simple dict cache
            async with self._lock:
                count = len(self._cache)
                self._cache.clear()
                metrics.update_cache_size("repo_metadata", 0)
                return count

    async def get_or_fetch(
        self,
        repo_url: str,
        path: Path | None,
        fetch_fn: Callable[..., Coroutine[Any, Any, RepoMetadata | None]],
    ) -> RepoMetadata | None:
        """
        Get cached metadata or fetch if not available.

        Args:
            repo_url: Repository URL
            path: Optional workspace path
            fetch_fn: Async function to fetch metadata if not cached

        Returns:
            Repository metadata
        """
        # Try to get from cache
        cached = await self.get(repo_url, path)
        if cached is not None:
            return cached

        # Fetch from source
        try:
            metadata = await fetch_fn(repo_url, path)
            if metadata is not None:
                await self.set(repo_url, metadata, path)
            return metadata  # type: ignore[no-any-return]
        except Exception as e:
            # If fetch fails, try to return stale data
            logger.warning(
                "Failed to fetch repository metadata, returning stale data if available",
                repo_url=repo_url,
                error=str(e),
            )
            return await self.get(repo_url, path)

    def _evict_oldest(self) -> None:
        """Remove the oldest entries to make room for new ones."""
        # Sort by last_updated and remove oldest
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_updated,
        )

        # Remove oldest 20%
        remove_count = max(1, int(self._max_entries * 0.2))
        for key, _ in sorted_entries[:remove_count]:
            del self._cache[key]

    @property
    def size(self) -> int:
        """Return the number of cached entries."""
        if self._use_moka:
            return len(self._cache)
        else:
            return len(self._cache)

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        if self._use_moka:
            # moka doesn't provide direct access to all entries
            # Return basic stats
            total_entries = len(self._cache)
            return {
                "total_entries": total_entries,
                "valid_entries": total_entries,  # moka handles TTL automatically
                "expired_entries": 0,
                "max_entries": self._max_entries,
                "backend": "moka",
            }
        else:
            # Fallback to simple dict cache
            valid_count = sum(1 for m in self._cache.values() if m.is_valid())
            return {
                "total_entries": len(self._cache),
                "valid_entries": valid_count,
                "expired_entries": len(self._cache) - valid_count,
                "max_entries": self._max_entries,
                "backend": "dict",
            }


# Global repository metadata cache instance
repo_metadata_cache = RepoMetadataCache()


class CacheManager:
    """Manager for all cache types in mcp-git."""

    def __init__(self) -> None:
        self.task_state_cache = repository_metadata_cache
        self.git_cache = repository_metadata_cache
        self.repo_metadata = repo_metadata_cache

    async def clear_all(self) -> dict[str, int]:
        """
        Clear all caches.

        Returns:
            Dictionary with counts of cleared entries per cache type
        """
        cleared = {
            "task_state": 0,
            "git": 0,
            "repo_metadata": 0,
        }

        cleared["repo_metadata"] = await self.repo_metadata.invalidate_all()

        return cleared

    async def get_all_stats(self) -> dict[str, Any]:
        """
        Get statistics for all caches.

        Returns:
            Dictionary with statistics for each cache
        """
        return {
            "task_state": self.task_state_cache.stats
            if hasattr(self.task_state_cache, "stats")
            else {"size": 0},
            "git": self.git_cache.stats if hasattr(self.git_cache, "stats") else {"size": 0},
            "repo_metadata": self.repo_metadata.stats,
        }
