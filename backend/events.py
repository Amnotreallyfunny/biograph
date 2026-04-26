import asyncio
import json
from typing import Dict, List

class EventBus:
    def __init__(self):
        # run_id -> list of subscriber queues
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        if run_id not in self._subscribers:
            self._subscribers[run_id] = []
        queue = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        return queue

    async def publish(self, run_id: str, event_type: str, data: dict):
        if run_id in self._subscribers:
            message = {
                "event": event_type,
                "data": data
            }
            # Remove inactive/full queues if necessary, or just broadcast
            for queue in self._subscribers[run_id]:
                await queue.put(message)

    def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        if run_id in self._subscribers:
            try:
                self._subscribers[run_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]

event_bus = EventBus()
