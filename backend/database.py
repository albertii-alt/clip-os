from supabase import create_client, Client
from supabase.client import ClientOptions
import httpx
from config import settings

# Force HTTP/1.1 to avoid Windows HTTP/2 socket read errors under concurrent requests
custom_httpx_client = httpx.Client(http2=False)

supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key,
    options=ClientOptions(httpx_client=custom_httpx_client)
)