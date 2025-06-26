from fastapi import HTTPException, Header
from supabase import create_client
import os

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

async def get_current_user(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    result = supabase.auth.get_user(token)
    if not result.user:
        raise HTTPException(401, "Unauthorized")
    return result.user
