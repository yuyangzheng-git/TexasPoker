"""Verify the deployed HTTP API and an authenticated WebSocket hand end to end."""
import argparse
import asyncio
import json
from urllib.parse import urlsplit, urlunsplit

import httpx
from websockets.asyncio.client import connect


async def check(base_url):
    base_url = base_url.rstrip("/")
    async with httpx.AsyncClient(base_url=base_url, timeout=15) as client:
        response = await client.get("/api/health")
        response.raise_for_status()
        assert response.json()["status"] == "ok"
        response = await client.post("/api/games", json={
            "player_name": "Deployment check", "table_size": 2,
            "agent_ids": ["jiaoshou"],
        })
        response.raise_for_status()
        game = response.json()
    origin = urlsplit(base_url)
    # Use the public origin so this checks the actual reverse proxy and TLS.
    ws_url = urlunsplit(("wss" if origin.scheme == "https" else "ws", origin.netloc,
                        "/ws/" + game["gameId"], "", ""))
    actions = 0
    human_commands = 0
    hands = 0
    async with asyncio.timeout(120):
        async with connect(ws_url, open_timeout=15) as ws:
            await ws.send(json.dumps({"type": "AUTH", "sessionToken": game["sessionToken"]}))
            async for raw in ws:
                event = json.loads(raw)
                data = event.get("data", {})
                if event["type"] == "PLAYER_ACTION_REQUEST":
                    human_commands += 1
                    kind = "check" if "check" in data["validActions"] else "call"
                    await ws.send(json.dumps({"type": "ACTION", "requestId": data["requestId"],
                                              "action": kind}))
                elif event["type"] == "PLAYER_ACTION":
                    actions += 1
                elif event["type"] in {"SHOWDOWN", "GAME_ENDED"}:
                    assert actions > 0, "No player action received"
                    assert data["allocations"], "Hand settlement missing"
                    hands += 1
                    if not human_commands and hands < 20 and data.get("requestId"):
                        await ws.send(json.dumps({"type": "READY_FOR_NEXT_HAND", "requestId": data["requestId"]}))
                        continue
                    assert human_commands > 0, "No human turn tested"
                    print(f"PASS: API, WebSocket authentication, {actions} actions, human input and hand settlement.")
                    return
                elif event["type"] == "ERROR":
                    raise RuntimeError(data.get("message", "Unknown game error"))
    raise RuntimeError("WebSocket closed before hand settlement")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Public URL, e.g. https://poker.example.com")
    args = parser.parse_args()
    asyncio.run(check(args.url))
