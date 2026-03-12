"""User-related tools for Pararam.io."""

import logging

import httpx
from fastmcp import FastMCP
from pararamio_aio._core import (
    PararamioAuthenticationError,
    PararamioHTTPRequestError,
    PararamioRequestError,
    PararamioValidationError,
)

from pararam_nexus_mcp.client import get_client
from pararam_nexus_mcp.helpers import error_response, success_response
from pararam_nexus_mcp.models import (
    GetUserInfoPayload,
    GetUserTeamStatusPayload,
    SearchUsersPayload,
    TeamStatus,
    ToolResponse,
    UserInfo,
)

logger = logging.getLogger(__name__)


def register_user_tools(mcp: FastMCP[None]) -> None:
    """Register user-related tools with the MCP server."""

    @mcp.tool()
    async def search_users(
        query: str,
        limit: int = 20,
    ) -> ToolResponse[SearchUsersPayload | None]:
        """
        Search for users by name or unique name.

        Args:
            query: Search query string (name or unique_name)
            limit: Maximum number of results to return (default: 20)

        Returns:
            ToolResponse with SearchUsersPayload containing list of users including id, name,
            unique_name, and team memberships
        """
        try:
            client = await get_client()

            logger.info(f'Searching users with query: {query}')

            # Search users
            users = await client.client.search_users(query)

            if not users:
                return success_response(
                    message=f'No users found matching query: {query}',
                    payload=SearchUsersPayload(
                        query=query,
                        count=0,
                        users=[],
                    ),
                )

            # Apply limit
            users = users[:limit]

            # Format results — use _data dict directly to avoid PararamModelNotLoadedError
            # when optional fields are missing from search API response
            formatted_users = [
                UserInfo(
                    id=user._data.get('id', 0),
                    name=user._data.get('name', ''),
                    unique_name=user._data.get('unique_name', ''),
                    is_bot=user._data.get('is_bot', False),
                    pm_chat_id=user._data.get('pm_thread_id'),
                )
                for user in users
            ]

            message_text = f"Found {len(formatted_users)} users matching '{query}'"

            return success_response(
                message=message_text,
                payload=SearchUsersPayload(
                    query=query,
                    count=len(formatted_users),
                    users=formatted_users,
                ),
            )

        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while searching users: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while searching users: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while searching users: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while searching users: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while searching users: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )

    @mcp.tool()
    async def get_user_info(
        user_id: str,
    ) -> ToolResponse[GetUserInfoPayload | None]:
        """
        Get detailed information about a specific user.

        Args:
            user_id: User ID

        Returns:
            ToolResponse with GetUserInfoPayload containing user details including id, name,
            unique_name, and team memberships
        """
        try:
            client = await get_client()

            logger.info(f'Getting user info for user_id: {user_id}')

            # Get user by ID
            user = await client.client.get_user_by_id(int(user_id))
            if not user:
                return error_response(
                    message=f'User {user_id} not found',
                    error='User not found',
                )

            await user.load()

            message_text = f"Retrieved information for user '{user.name}' (ID: {user.id})"

            return success_response(
                message=message_text,
                payload=GetUserInfoPayload(
                    id=user.id,
                    name=user.name,
                    unique_name=user.unique_name,
                    active=user.active,
                    is_bot=user.is_bot,
                    time_created=str(user.time_created),
                    time_updated=str(user.time_updated),
                    timezone_offset_minutes=user.timezone_offset_minutes,
                    organizations=user.organizations,
                ),
            )

        except ValueError as e:
            logger.error('Invalid user_id: %s', e)
            return error_response(
                message='Invalid user ID',
                error=f'Invalid user_id: {e!s}',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while getting user info: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while getting user info: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while getting user info: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while getting user info: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while getting user info: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )

    @mcp.tool()
    async def get_user_team_status(
        user_id: str,
        team_id: str | None = None,
    ) -> ToolResponse[GetUserTeamStatusPayload | None]:
        """
        Get user's status in teams (member, admin, guest, or not in team).

        Args:
            user_id: User ID to check
            team_id: Optional team ID to check status in specific team. If not provided, returns status in all teams.

        Returns:
            ToolResponse with GetUserTeamStatusPayload containing team membership status
            including is_member, is_admin, is_guest, and state
        """
        try:
            client = await get_client()
            user_id_int = int(user_id)

            logger.info(f'Getting team status for user_id: {user_id}, team_id: {team_id}')

            # Get teams to check
            if team_id:
                teams = await client.client.get_teams_by_ids([int(team_id)])
            else:
                # Get all user's teams
                teams = await client.client.get_my_teams()

            if not teams:
                return error_response(
                    message='No teams found',
                    error='No teams found',
                )

            # Check user status in each team
            team_statuses = []
            for team in teams:
                is_member = user_id_int in team.users
                is_admin = user_id_int in team.admins
                is_guest = user_id_int in team.guests

                team_statuses.append(
                    TeamStatus(
                        team_id=team.id,
                        team_title=team.title,
                        team_slug=team.slug,
                        is_member=is_member,
                        is_admin=is_admin,
                        is_guest=is_guest,
                        in_team=is_member or is_guest,
                    )
                )

            # Count teams where user is a member
            teams_member_count = sum(1 for status in team_statuses if status.in_team)
            message_text = (
                f'User {user_id} is a member of {teams_member_count} out of {len(team_statuses)} teams checked'
            )

            return success_response(
                message=message_text,
                payload=GetUserTeamStatusPayload(
                    user_id=user_id,
                    teams_checked=len(team_statuses),
                    team_statuses=team_statuses,
                ),
            )

        except ValueError as e:
            logger.error('Invalid user_id or team_id: %s', e)
            return error_response(
                message='Invalid input',
                error=f'Invalid input: {e!s}',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while getting team status: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while getting team status: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while getting team status: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while getting team status: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while getting team status: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )
