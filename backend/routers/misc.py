from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form, Header, Query
from fastapi.responses import StreamingResponse
from core import *
from models import *

router = APIRouter()

@router.post("/contact")
async def contact(inp: ContactInput):
    await db.contact_messages.insert_one({
        "name": inp.name, "email": inp.email.lower(), "message": inp.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}

@router.get("/")
async def root():
    return {"message": "CEO AI online"}
