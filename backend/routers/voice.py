from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from core import *
from models import *
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech
import io, tempfile, os as _os

router = APIRouter()

VOICE_HINT = ("(Estás numa conversa por VOZ. Responde de forma falada, natural, calorosa e concisa — "
              "como se estivesses a falar ao telefone com o empresário. Evita listas e formatação; frases curtas. "
              "Máximo 4-6 frases.)")

@router.post("/voice/chat")
async def voice_chat(file: UploadFile = File(...), session_id: str = Form(None), user: dict = Depends(get_current_user)):
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Áudio vazio")
    suffix = "." + (file.filename.split(".")[-1] if file.filename and "." in file.filename else "webm")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(audio); tmp.flush(); tmp.close()
        stt = OpenAISpeechToText(api_key=EMERGENT_KEY)
        with open(tmp.name, "rb") as af:
            tr = await stt.transcribe(file=af, model="whisper-1", language="pt", response_format="json")
        user_text = (getattr(tr, "text", "") or "").strip()
    except Exception as e:
        logger.error(f"stt error: {e}")
        raise HTTPException(500, "Não consegui perceber o áudio")
    finally:
        try: _os.unlink(tmp.name)
        except Exception: pass

    if not user_text:
        raise HTTPException(422, "Não percebi nada. Tenta falar outra vez.")

    sid = session_id
    if not sid:
        sid = str(uuid.uuid4())
        await db.chat_sessions.insert_one({"session_id": sid, "user_id": user["id"],
            "title": user_text[:50], "created_at": datetime.now(timezone.utc).isoformat()})
    history = await db.chat_messages.find({"session_id": sid, "user_id": user["id"]}).sort("created_at", 1).to_list(1000)
    await db.chat_messages.insert_one({"session_id": sid, "user_id": user["id"], "role": "user",
        "content": user_text, "created_at": datetime.now(timezone.utc).isoformat()})

    chat_obj = await get_chat(user["id"], user.get("name", ""), sid)
    context = f"{VOICE_HINT}\n\n{user_text}"
    if history:
        hist_txt = "\n".join(f"{h['role']}: {h['content']}" for h in history[-8:])
        context = f"{VOICE_HINT}\n\n[Histórico]\n{hist_txt}\n\n[Nova mensagem falada]\n{user_text}"
    try:
        reply = await chat_obj.send_message(UserMessage(text=context))
        reply = (reply if isinstance(reply, str) else str(reply)).strip()
    except Exception as e:
        logger.error(f"voice chat llm error: {e}")
        raise HTTPException(500, "O CEO não conseguiu responder agora")

    await db.chat_messages.insert_one({"session_id": sid, "user_id": user["id"], "role": "assistant",
        "content": reply, "created_at": datetime.now(timezone.utc).isoformat()})

    audio_b64 = ""
    try:
        tts = OpenAITextToSpeech(api_key=EMERGENT_KEY)
        audio_b64 = await tts.generate_speech_base64(text=reply[:4096], model="tts-1", voice="alloy", speed=1.0)
    except Exception as e:
        logger.error(f"tts error: {e}")

    return {"session_id": sid, "user_text": user_text, "reply_text": reply, "audio_base64": audio_b64}
