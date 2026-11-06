import hmac
import logging
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from ask_sdk_model import RequestEnvelope
from ask_sdk_core.serialize import DefaultSerializer

from config import ENDPOINT_TOKEN, PORT, SKILL_ID
from skill import skill

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
serializer = DefaultSerializer()

TIMESTAMP_TOLERANCE_S = 150   # Alexa requires rejecting requests older than 150 s (replay protection)


def _application_id(envelope: RequestEnvelope) -> str | None:
    try:
        return envelope.context.system.application.application_id
    except AttributeError:
        return None


def _is_fresh(envelope: RequestEnvelope, now: datetime | None = None) -> bool:
    ts = getattr(envelope.request, "timestamp", None)
    if ts is None:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return abs(((now or datetime.now(timezone.utc)) - ts).total_seconds()) <= TIMESTAMP_TOLERANCE_S


@app.post("/alexa/{token}")
async def alexa_endpoint(token: str, request: Request) -> JSONResponse:
    # The endpoint controls the PC, so it must not answer anyone: the URL carries a secret token (404 otherwise),
    # the request must come from this skill and must be recent.
    if not hmac.compare_digest(token.encode(), ENDPOINT_TOKEN.encode()):
        raise HTTPException(status_code=404)
    body = await request.body()
    try:
        request_envelope = serializer.deserialize(body.decode("utf-8"), RequestEnvelope)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed request")
    if _application_id(request_envelope) != SKILL_ID:
        logger.warning("Rejected a request from another application id")
        raise HTTPException(status_code=403)
    if not _is_fresh(request_envelope):
        logger.warning("Rejected a stale or undated request")
        raise HTTPException(status_code=400, detail="Stale request")
    req = request_envelope.request
    logger.info("Request type: %s | intent: %s", req.object_type, getattr(req, "intent", None))
    response_envelope = skill.invoke(request_envelope=request_envelope, context=None)
    return JSONResponse(content=serializer.serialize(response_envelope))


if __name__ == "__main__":
    # Bind to localhost only: the Cloudflare tunnel connects from this machine, nothing else needs to reach the port.
    uvicorn.run(app, host="127.0.0.1", port=PORT)
