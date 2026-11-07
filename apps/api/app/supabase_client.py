"""Supabase client for real-time features and storage"""
from supabase import create_client, Client
from app.config import settings
from functools import lru_cache

@lru_cache()
def get_supabase_client() -> Client:
    """Get Supabase client instance"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise ValueError("Supabase credentials not configured")
    
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY
    )

def get_supabase_publishable_client() -> Client:
    """Get a Supabase client configured with the publishable key."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_PUBLISHABLE_KEY:
        raise ValueError("Supabase credentials not configured")
    
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_PUBLISHABLE_KEY
    )
