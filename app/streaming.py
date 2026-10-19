"""Keep a recovery attached to an HTTP request on managed container hosts."""
from __future__ import annotations

import asyncio
import json

import anyio
from fastapi.responses import StreamingResponse


class RunStreamResponse(StreamingResponse):
    def __init__(self, record, work, release):
        self.record, self.work, self.release = record, work, release
        self.task = None
        super().__init__(self.frames(), media_type="text/event-stream",
                         headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    async def frames(self):
        previous = None
        while not self.task.done():
            current = json.dumps(self.record, ensure_ascii=False)
            yield f"data: {current}\n\n" if current != previous else ": waiting\n\n"
            previous = current
            await asyncio.wait({self.task}, timeout=0.4)
        await self.task
        yield f"data: {json.dumps(self.record, ensure_ascii=False)}\n\n"

    async def __call__(self, scope, receive, send):
        self.task = asyncio.create_task(self.work())
        try:
            await super().__call__(scope, receive, send)
        finally:
            interrupted = not self.task.done()
            if interrupted:
                self.task.cancel()
            try:
                with anyio.CancelScope(shield=True):
                    await asyncio.gather(self.task, return_exceptions=True)
                if interrupted:
                    self.record.update(status="error", phase="Interrupted", error={
                        "code": "RUN_INTERRUPTED",
                        "message": "The connection closed before recovery finished. Review the recorded actions before starting again.",
                    })
            finally:
                self.release()
