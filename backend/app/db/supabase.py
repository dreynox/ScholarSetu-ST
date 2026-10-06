"""
Supabase client provider with public and privileged client singletons.
"""
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings
from app.utils.errors import AppException


class SupabaseManager:
    """
    Manages cached singleton instances of Supabase clients.
    """
    _anon_client: Optional[Client] = None
    _service_client: Optional[Client] = None

    @classmethod
    def get_anon_client(cls) -> Client:
        """
        Returns the public/normal client initialized with SUPABASE_ANON_KEY.
        Used for normal user-scoped and authentication operations.
        """
        if cls._anon_client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
                raise AppException(
                    status_code=500,
                    code="SUPABASE_CONFIG_MISSING",
                    message="Supabase URL or Anonymous Key is not configured."
                )
            cls._anon_client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_ANON_KEY
            )
        return cls._anon_client

    @classmethod
    def get_service_client(cls) -> Client:
        """
        Returns the backend privileged client initialized with SUPABASE_SERVICE_ROLE_KEY.
        Used ONLY inside the backend when a privileged server-side operation is genuinely required.
        NEVER expose this client or its credentials to the frontend.
        """
        if cls._service_client is None:
            key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
            if not settings.SUPABASE_URL or not key:
                raise AppException(
                    status_code=500,
                    code="SUPABASE_CONFIG_MISSING",
                    message="Supabase URL or Service Role Key is not configured."
                )
            cls._service_client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=key
            )
        return cls._service_client

    @classmethod
    def get_user_client(cls, token: str) -> Client:
        """
        Creates a client scoped with the user's access token for strict RLS enforcement.
        """
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise AppException(
                status_code=500,
                code="SUPABASE_CONFIG_MISSING",
                message="Supabase URL or Anonymous Key is not configured."
            )
        client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_ANON_KEY
        )
        client.postgrest.auth(token)
        return client


def get_supabase_client() -> Client:
    """Dependency/Helper to get anonymous client."""
    return SupabaseManager.get_anon_client()


def get_supabase_service_client() -> Client:
    """Dependency/Helper to get privileged service-role client."""
    return SupabaseManager.get_service_client()


def get_supabase_user_client(token: str) -> Client:
    """Helper to get user-scoped client."""
    return SupabaseManager.get_user_client(token)
