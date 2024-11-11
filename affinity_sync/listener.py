import asyncio
import json
import logging
import threading
import time

from aiohttp import web

from .module_types import affinity_v1_api as affinity_types


class WebhookListener:
    __logger = logging.getLogger('WebhookListener')

    def __init__(self, port: int):
        self.__port = port
        self.__queue: list[affinity_types.WebhookEvent] = []
        self.__server_thread: threading.Thread | None = None
        self.__runner: web.AppRunner | None = None
        self.__loop: asyncio.AbstractEventLoop | None = None

    async def __handle_event(self, request) -> web.Response:
        self.__logger.info('Received webhook event - adding to queue')
        res = json.loads(await request.text())
        self.__queue.append(res)
        return web.Response(text="Nice Webhook")

    @property
    def __endpoints(self) -> list[web.RouteDef]:
        return [
            web.post('/', self.__handle_event)
        ]

    def start(self):
        self.__logger.info(f'Starting webhook listener on port {self.__port}')

        def run():
            app = web.Application()
            app.add_routes(self.__endpoints)
            self.__runner = web.AppRunner(app, access_log=self.__logger)
            self.__loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.__loop)
            self.__loop.run_until_complete(self.__runner.setup())
            site = web.TCPSite(self.__runner, '0.0.0.0', self.__port)
            self.__loop.run_until_complete(site.start())
            self.__loop.run_forever()

        self.__server_thread = threading.Thread(target=run, daemon=True)
        self.__server_thread.start()
        self.__logger.info('Webhook listener started')

    def stop(self):
        self.__logger.info('Stopping webhook listener')
        if self.__runner and self.__loop:
            async def shutdown():
                await self.__runner.cleanup()

            self.__loop.call_soon_threadsafe(self.__loop.create_task, shutdown())
            self.__loop.call_soon_threadsafe(self.__loop.stop)
            self.__server_thread.join()
            self.__server_thread = None
            self.__runner = None
            self.__loop = None
        self.__logger.info('Webhook listener stopped')

    def __next__(self) -> affinity_types.WebhookEvent:
        time_since_last_event = 0

        while not self.__queue:
            time_since_last_event += 0.2
            time.sleep(0.2)

            if round(time_since_last_event) % 20 == 0 and round(time_since_last_event) != 0:
                self.__logger.info('No events received in the last 20s')
                time_since_last_event = 0

        payload = self.__queue.pop(0)

        try:
            return affinity_types.WebhookEvent.model_validate(payload)

        except Exception as e:
            self.__logger.error(f'Invalid payload - {payload}')
            self.__logger.error(e)

            return self.__next__()

    def __iter__(self) -> 'WebhookListener':
        return self
