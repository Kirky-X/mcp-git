"""
Git operations service implementation.

This module provides the Git operations service for the microservices architecture.
"""

from typing import Any
from uuid import UUID

from loguru import logger

from mcp_git.services.service_interface import GitServiceInterface
from mcp_git.service.facade import GitServiceFacade


class GitService(GitServiceInterface):
    """
    Git operations service.

    This service handles all Git-related operations including clone, commit,
    push, pull, and status checks.
    """

    def __init__(self, facade: GitServiceFacade):
        """
        Initialize the Git service.

        Args:
            facade: Git service facade for Git operations
        """
        self.facade = facade

    async def clone(
        self,
        url: str,
        workspace_id: UUID,
        branch: str | None = None,
        depth: int | None = None,
    ) -> dict[str, Any]:
        """
        Clone a repository.

        Args:
            url: Repository URL
            workspace_id: Workspace ID
            branch: Branch to clone
            depth: Clone depth

        Returns:
            Clone result
        """
        logger.info("Cloning repository", url=url, workspace_id=str(workspace_id))

        result = await self.facade.clone(
            url=url,
            workspace_id=workspace_id,
            branch=branch,
            depth=depth,
        )

        logger.info("Clone completed", workspace_id=str(workspace_id))
        return result

    async def commit(
        self,
        workspace_id: UUID,
        message: str,
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> str:
        """
        Create a commit.

        Args:
            workspace_id: Workspace ID
            message: Commit message
            author_name: Author name
            author_email: Author email

        Returns:
            Commit OID
        """
        logger.info("Creating commit", workspace_id=str(workspace_id))

        oid = await self.facade.create_commit(
            workspace_id=workspace_id,
            message=message,
            author_name=author_name,
            author_email=author_email,
        )

        logger.info("Commit created", workspace_id=str(workspace_id), commit_id=oid)
        return oid

    async def push(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        branch: str | None = None,
        force: bool = False,
    ) -> None:
        """
        Push changes to remote.

        Args:
            workspace_id: Workspace ID
            remote: Remote name
            branch: Branch to push
            force: Force push
        """
        logger.info("Pushing changes", workspace_id=str(workspace_id), remote=remote)

        await self.facade.push(
            workspace_id=workspace_id,
            remote=remote,
            branch=branch,
            force=force,
        )

        logger.info("Push completed", workspace_id=str(workspace_id))

    async def pull(
        self,
        workspace_id: UUID,
        remote: str = "origin",
        branch: str | None = None,
        rebase: bool = False,
    ) -> None:
        """
        Pull changes from remote.

        Args:
            workspace_id: Workspace ID
            remote: Remote name
            branch: Branch to pull
            rebase: Use rebase
        """
        logger.info("Pulling changes", workspace_id=str(workspace_id), remote=remote)

        await self.facade.pull(
            workspace_id=workspace_id,
            remote=remote,
            branch=branch,
            rebase=rebase,
        )

        logger.info("Pull completed", workspace_id=str(workspace_id))

    async def get_status(self, workspace_id: UUID) -> dict[str, Any] | None:
        """
        Get repository status.

        Args:
            workspace_id: Workspace ID

        Returns:
            Repository status
        """
        logger.debug("Getting repository status", workspace_id=str(workspace_id))

        status = await self.facade.get_status(workspace_id)

        return status