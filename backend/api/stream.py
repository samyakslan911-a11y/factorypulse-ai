"""
Server-Sent Events — el frontend escucha el progreso del agente en tiempo real.
"""
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["stream"])

_queues: dict[str, asyncio.Queue] = {}
_loop: asyncio.AbstractEventLoop | None = None


def ensure_queue(analysis_id: str) -> asyncio.Queue:
    """Crea la cola si no existe. Puede llamarse desde cualquier thread."""
    if analysis_id not in _queues:
        _queues[analysis_id] = asyncio.Queue()
    return _queues[analysis_id]


def emit(analysis_id: str, event: str, data: str) -> None:
    """Llamado desde el agente (thread) para emitir progreso al cliente SSE."""
    if analysis_id not in _queues:
        return
    loop = _loop
    if loop and loop.is_running():
        loop.call_soon_threadsafe(
            _queues[analysis_id].put_nowait,
            f"event: {event}\ndata: {data}\n\n"
        )


@router.get("/{analysis_id}")
async def stream_analysis(analysis_id: str):
    global _loop
    _loop = asyncio.get_event_loop()
    queue = ensure_queue(analysis_id)

    async def generator():
        yield f"event: connected\ndata: {analysis_id}\n\n"
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield msg
                if '"done"' in msg or '"failed"' in msg:
                    break
            except asyncio.TimeoutError:
                yield "event: ping\ndata: keep-alive\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
