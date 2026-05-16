import asyncio
import hashlib
import hmac
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from trading_bot.core.application.trading.dto.event import EventDTO
from trading_bot.core.domain.value_objects.event import EventType
from trading_bot.infrastructure.exceptions import ExchangeAPIException
from trading_bot.infrastructure.exchanges.bybit.mapper import BybitOrderMapper

logger = logging.getLogger(__name__)


class BaseBybitAdapter:
    BASE_URL_MAINNET: str = "https://api.bybit.com"
    WS_URL_MAINNET: str = "wss://stream.bybit.com/v5/private"
    BASE_URL_DEMO: str = "https://api-demo.bybit.com"
    WS_URL_DEMO: str = "wss://stream-demo.bybit.com/v5/private"

    account_name: str
    ws_url: str
    base_url: str
    api_key: str
    api_secret: str
    recv_window: str
    timeout: ClientTimeout
    _lock: asyncio.Lock

    def __init__(self, account_name: str, api_key: str, api_secret: str, demo: bool = True, timeout: int = 30):
        self.account_name = account_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = ClientTimeout(total=timeout)
        self.recv_window = "5000"

        self.base_url = self.BASE_URL_DEMO if demo else self.BASE_URL_MAINNET
        self.ws_url = self.WS_URL_DEMO if demo else self.WS_URL_MAINNET
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    self._session = ClientSession(timeout=self.timeout, headers={"Content-Type": "application/json"})
        return self._session

    def _generate_signature(self, timestamp: str, payload: str) -> str:
        sign_str = f"{timestamp}{self.api_key}{self.recv_window}{payload}"
        signature = hmac.new(self.api_secret.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature

    async def _request(self, method: Literal["GET", "POST", "PUT", "DELETE"], endpoint: str, params: dict[str, Any] | None = None, signed: bool = False) -> dict[str, Any]:
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        headers = {"Content-Type": "application/json"}

        json_payload = json.dumps(params, separators=(",", ":"), sort_keys=True) if params else ""

        if signed:
            timestamp = str(int(time.time() * 1000))

            payload = urlencode(sorted(params.items())) if method == "GET" else json_payload

            signature = self._generate_signature(timestamp, payload)

            headers.update(
                {
                    "X-BAPI-API-KEY": self.api_key,
                    "X-BAPI-TIMESTAMP": timestamp,
                    "X-BAPI-SIGN": signature,
                    "X-BAPI-RECV-WINDOW": self.recv_window,
                }
            )

        if method == "GET":
            req = session.get(url, headers=headers, params=params)
        elif method == "POST":
            req = session.post(url, headers=headers, data=json_payload)
        elif method == "PUT":
            req = session.put(url, headers=headers, data=json_payload)
        else:  # DELETE
            req = session.delete(url, headers=headers, data=json_payload)

        async with req as response:
            if response.status != 200:
                raise ExchangeAPIException(f"HTTP {response.status}: {await response.text()}")
            data = await response.json(content_type=None)
            if data.get("retCode") != 0:
                raise ExchangeAPIException(message=data.get("retMsg", "Unknown Bybit Error"), code=data.get("retCode"), response=data)
            return data

    async def _process_ws_message(self, msg: aiohttp.WSMessage, on_update_callback: Callable[[EventDTO], Awaitable[None]]) -> None:
        if msg.type == aiohttp.WSMsgType.TEXT:
            data = msg.json()

            # Ignore pings and empty topics
            if data.get("op") == "ping" or data.get("ret_msg") == "pong" or "topic" not in data or not data.get("data"):
                return

            payload = data["data"][0]
            event_type = EventType.ORDER if data["topic"] == "order" else EventType.POSITION
            # if event_type == EventType.ORDER:
            clean_order_dto = BybitOrderMapper.from_bybit_response(payload)
            event = EventDTO(
                event_type=event_type,
                symbol=payload["symbol"],
                account_name=self.account_name,
                order=clean_order_dto,
            )
            await on_update_callback(event)

        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            logger.warning("⚠️ [Websocket] Connection closed by server. Reconnecting...")
            # Raise exception to break async for and trigger reconnect in main loop
            raise ConnectionError("Websocket closed by server")

    async def _ws_authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        expires = int((time.time() + 30) * 1000)
        signature = hmac.new(self.api_secret.encode("utf-8"), f"GET/realtime{expires}".encode(), hashlib.sha256).hexdigest()
        await ws.send_json({"op": "auth", "args": [self.api_key, expires, signature]})

        auth_resp = await ws.receive_json()
        if not auth_resp.get("success"):
            raise Exception(f"Auth failed: {auth_resp}")

    async def _ws_subscribe(self, ws: aiohttp.ClientWebSocketResponse, args: list[str]) -> None:
        await ws.send_json({"op": "subscribe", "args": args})
        sub_resp = await ws.receive_json()
        if not sub_resp.get("success"):
            raise Exception(f"[Websocket] Subscribe failed: {sub_resp}")
        logger.info(f"📡 [Websocket] subscribed on: {args}")

    async def _ws_keepalive(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        while not ws.closed:
            try:
                await ws.send_json({"op": "ping"})
                await asyncio.sleep(20)
            except Exception:
                break

    async def listen_user_stream(self, on_update_callback: Callable[[EventDTO], Awaitable[None]]):
        while True:
            ping_task = None
            try:
                session = await self._get_session()
                async with session.ws_connect(self.ws_url, heartbeat=20) as ws:
                    # 1. Authorization and Subscription
                    await self._ws_authenticate(ws)
                    await self._ws_subscribe(ws, ["order", "position"])

                    # 2. Start background ping
                    ping_task = asyncio.create_task(self._ws_keepalive(ws))

                    # 3. Stream reading
                    async for msg in ws:
                        await self._process_ws_message(msg, on_update_callback)

            except Exception as e:
                logger.info(f"⚠️ [Websocket] reconnecting: {e}")
                await asyncio.sleep(3)
            finally:
                if ping_task and not ping_task.done():
                    ping_task.cancel()
