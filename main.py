import logging
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from ask_sdk_model import RequestEnvelope
from ask_sdk_core.serialize import DefaultSerializer

from config import PORT
from skill import skill

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
serializer = DefaultSerializer()

@app.post("/alexa")
async def alexa_endpoint(request: Request) -> JSONResponse:
    body = await request.body()
    request_envelope = serializer.deserialize(body.decode("utf-8"), RequestEnvelope)
    req = request_envelope.request
    logger.info("Request type: %s | intent: %s", req.object_type, getattr(req, "intent", None))
    response_envelope = skill.invoke(request_envelope=request_envelope, context=None)
    return JSONResponse(content=serializer.serialize(response_envelope))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)