import asyncio
import binascii
import json
import locale
import os
import queue
import random
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

import aiohttp
import discord
import requests
import streamlit as st
import websockets
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv
from google.protobuf.internal.encoder import _VarintBytes
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from yarl import URL

import server
from guild import *

load_dotenv()

if "log_queue" not in st.session_state:
    st.session_state["log_queue"] = queue.Queue()

if "logs" not in st.session_state:
    st.session_state["logs"] = []

if "task_running" not in st.session_state:
    st.session_state["task_running"] = False
GUILD_ID = 1122707918177960047
BOT_NAME = "shopee"
SESSION_ID = None
SESSION_ID_OLD = None
LAST_UPDATE = None
LAST_MSG = None
HEADERS = []

RESULT = None
URL_STREAM = "https://keep-sl-online-d7bnwfpjbw9cw23yreygwk.streamlit.app/"
RESTART_LOOP = random.randrange(12, 18, 1)
NEXT_TIME = False
timeout = 30

data = {
    "timezone": "Asia/Bangkok",
    "timezone_offset": -420,
    "locale": "en-US",
    "url": "https://bot-bm-ghfzbuypvbrku5jbtobuks.streamlit.app/",
    "is_embedded": False,
    "color_scheme": "dark",
}


def encode_varint(value):
    if value < 0:
        value += 1 << 64
    res = bytearray()
    while True:
        bits = value & 0x7F
        value >>= 7
        if value:
            res.append(0x80 | bits)
        else:
            res.append(bits)
            break
    return bytes(res)


def encode_tag(field_number, wire_type):
    return encode_varint((field_number << 3) | wire_type)


def encode_string(field_number, s=""):
    data = s.encode("utf-8")
    return encode_tag(field_number, 2) + encode_varint(len(data)) + data


def encode_int32(field_number, val):
    return encode_tag(field_number, 0) + encode_varint(
        val if val >= 0 else (val + (1 << 64))
    )


def encode_bool(field_number, val):
    return encode_tag(field_number, 0) + (b"\x01" if val else b"\x00")


def get_init_message(url: str):
    ctx_parts = [
        encode_string(1, "Asia/Bangkok"),
        encode_int32(2, -420),
        encode_string(3, "en-US"),
        encode_string(4, url),
        encode_bool(5, False),
        encode_string(6, "dark"),
    ]
    ctx_bin = b"".join(ctx_parts)

    forward_parts = [
        encode_string(1, ""),
        encode_tag(2, 2) + b"\x00",
        encode_string(3, ""),
        encode_string(4, ""),
        encode_tag(5, 2) + b"\x00",
        encode_tag(8, 2) + encode_varint(len(ctx_bin)) + ctx_bin,
    ]
    forward_bin = b"".join(forward_parts)

    final_msg = encode_tag(11, 2) + encode_varint(len(forward_bin)) + forward_bin
    return final_msg


async def connect(base_url):
    uri = f"wss://{base_url}/~/+/_stcore/stream"
    print(f"connecting to {uri}")
    async with websockets.connect(
        uri,
        ping_interval=25,
        ping_timeout=30,
        max_size=None,
        additional_headers={
            "Origin": f"https://{base_url}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
    ) as ws:
        print("WebSocket connected successfully")
        url = f"https://{base_url}/"
        init_msg = get_init_message(url)
        await ws.send(init_msg)
        try:
            for i in range(10):
                response = await asyncio.wait_for(ws.recv(), timeout=15)
                print(f"Message {i + 1} received | Length: {len(response)}")
                try:
                    import msgpack

                    print(msgpack.unpackb(response))
                except Exception:
                    pass
        except asyncio.TimeoutError:
            print("Timeout waiting for response")
        except Exception as e:
            print("Error receiving:", e)


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
)


def _emit(log_queue, level, message):
    """Push a log line to the Streamlit UI queue (safe no-op if queue is None)."""
    print(f"[{level}] {message}")
    if log_queue is not None:
        try:
            log_queue.put((level, message))
        except Exception:
            pass


async def wake_streamlit_app(
    session, base_url, headers, authorizations=None, log_queue=None
):
    """
    Ensures the Streamlit Cloud app at `base_url` is awake.
    Fully async (aiohttp) - never blocks the event loop.
    Returns True if the app ends up running (or was already running), False on hard failure.
    """
    if not base_url.endswith("/"):
        base_url += "/"

    # Follow the normal browser flow once so cookies land in the session's cookie jar.
    try:
        async with session.get(base_url, headers=headers, allow_redirects=True) as res:
            if res.status >= 400:
                _emit(
                    log_queue, "error", f"{base_url} initial GET failed: {res.status}"
                )
                return False
    except Exception as e:
        _emit(log_queue, "error", f"{base_url} initial GET error: {e}")
        return False

    try:
        session.cookie_jar.clear()
        async with session.get(
            base_url + "api/v2/app/context", headers=headers, allow_redirects=False
        ) as res:
            if res.status >= 400:
                body = await res.text()
                jar_cookies = {c.key: c.value for c in session.cookie_jar}
                print(f"[debug] cookie jar: {jar_cookies}")
                print(f"[debug] {base_url} context {res.status} body: {body[:500]}")
                _emit(log_queue, "error", f"{base_url} context failed: {res.status}")
                return False
    except Exception as e:
        _emit(log_queue, "error", f"{base_url} context error: {e}")
        return False

    try:
        async with session.get(
            base_url + "api/v2/app/disambiguate", headers=headers
        ) as res:
            if res.status >= 400:
                _emit(
                    log_queue, "error", f"{base_url} disambiguate failed: {res.status}"
                )
                return False
            headers["x-csrf-token"] = res.headers.get("x-csrf-token", "")
    except Exception as e:
        _emit(log_queue, "error", f"{base_url} disambiguate error: {e}")
        return False

    try:
        async with session.get(base_url + "api/v2/app/status", headers=headers) as res:
            if res.status >= 400:
                _emit(log_queue, "error", f"{base_url} status failed: {res.status}")
                return False
            js = await res.json()
    except Exception as e:
        _emit(log_queue, "error", f"{base_url} status error: {e}")
        return False

    if js.get("status") == 5:
        # Already running -> restart it via one of the authorized accounts, if configured.
        _emit(log_queue, "info", f"{base_url} already running, restarting...")
        if not authorizations:
            return True

        for author in authorizations:
            auth_headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
                "cookie": author["cookie"],
                "x-csrf-token": author["csrf_token"],
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
            }
            try:
                async with session.get(
                    base_url + "api/v2/app/disambiguate", headers=auth_headers
                ) as res:
                    if res.status >= 400:
                        continue
                    js = await res.json()
                    app_id = js.get("appId")
                if not app_id:
                    continue

                restart_url = f"https://share.streamlit.io/api/v2/apps/{app_id}/restart"
                async with session.post(restart_url, headers=auth_headers) as res:
                    if res.status != 204:
                        _emit(
                            log_queue,
                            "error",
                            f"{base_url} restart failed: {res.status}",
                        )
                        continue

                _emit(log_queue, "info", f"{base_url} restart triggered")
                for _ in range(30):
                    await asyncio.sleep(1)
                    async with session.get(restart_url, headers=auth_headers) as res:
                        if res.status >= 400:
                            break
                        js = await res.json()
                        if js.get("status") == 5:
                            _emit(log_queue, "success", f"{base_url} is running again")
                            return True
                break
            except Exception as e:
                _emit(log_queue, "error", f"{base_url} restart error: {e}")
                continue
        return True

    # Not running -> resume it.
    _emit(log_queue, "info", f"{base_url} resuming...")
    try:
        async with session.post(base_url + "api/v2/app/resume", headers=headers) as res:
            if res.status >= 400:
                _emit(log_queue, "error", f"{base_url} resume failed: {res.status}")
                return False
    except Exception as e:
        _emit(log_queue, "error", f"{base_url} resume error: {e}")
        return False

    for _ in range(20):
        await asyncio.sleep(2)
        try:
            async with session.get(
                base_url + "api/v2/app/status", headers=headers
            ) as res:
                if res.status >= 400:
                    continue
                js = await res.json()
                if js.get("status") == 5:
                    _emit(log_queue, "success", f"{base_url} resumed")
                    return True
        except Exception as e:
            _emit(log_queue, "error", f"{base_url} poll error: {e}")

    _emit(log_queue, "error", f"{base_url} resume timed out")
    return False


async def wake_and_connect(base_url, authorizations=None, log_queue=None):
    """Wake the app (if needed) then open the websocket stream, all on aiohttp - non-blocking."""
    headers = {"user-agent": DEFAULT_UA}
    timeout_cfg = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar(), timeout=timeout_cfg
    ) as session:
        ok = await wake_streamlit_app(
            session, base_url, headers, authorizations, log_queue
        )
        if ok:
            try:
                await connect(base_url[8:].rstrip("/"))
            except Exception as e:
                _emit(log_queue, "error", f"{base_url} connect() failed: {e}")
        return ok


def myStyle(log_queue):
    intents = discord.Intents.all()
    client = discord.Client(intents=intents)
    authorizations = json.loads(str(os.getenv("authorizations")).replace("'", '"'))

    @client.event
    async def on_ready():
        global RESULT
        guild = None
        for g in client.guilds:
            if g.name == "llyllr's server":
                guild = g
        if guild:
            RESULT = await getBasic(guild)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
            }
            if "streamlit" not in str(RESULT):
                RESULT["streamlitCate"] = await guild.create_category(
                    name="streamlit", overwrites=overwrites
                )
                RESULT["urlsCh"] = await RESULT["streamlitCate"].create_forum(
                    name="urls", overwrites=overwrites
                )
                RESULT["rawCh"] = await RESULT["streamlitCate"].create_text_channel(
                    name="raw", overwrites=overwrites
                )
            if not keepLive.is_running():
                keepLive.start(guild)
            if not restartVM.is_running():
                restartVM.start()

    @tasks.loop(hours=RESTART_LOOP)
    async def restartVM():
        global NEXT_TIME
        if NEXT_TIME and RESULT:
            _emit(log_queue, "info", f"restart vm after {RESTART_LOOP} hours")
            await wake_and_connect(URL_STREAM, authorizations, log_queue)
        else:
            NEXT_TIME = False

    @tasks.loop(seconds=15)
    async def updateUrl():
        global RESULT
        if not RESULT:
            return
        try:
            async for msg in RESULT["rawCh"].history():
                content = msg.content.strip()
                if content not in str(RESULT["urlsCh"].threads):
                    base_url = content.split(" || ")[0]
                    await RESULT["urlsCh"].create_thread(name=content, content=base_url)
                    # New URL just registered - just a quick "wake if asleep" ping, no restart-of-running-app.
                    await wake_and_connect(
                        base_url, authorizations=None, log_queue=log_queue
                    )
        except Exception as e:
            _emit(log_queue, "error", f"updateUrl error: {e}")

    @tasks.loop(seconds=30)
    async def keepLive(guild):
        global RESULT
        if not RESULT:
            return
        headers = {"user-agent": DEFAULT_UA}
        timeout_cfg = aiohttp.ClientTimeout(total=timeout)
        try:
            async with aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar(), timeout=timeout_cfg
            ) as session:
                async for msg in RESULT["rawCh"].history():
                    parts = msg.content.strip().split(" || ")
                    base_url = parts[0]
                    member_id = (
                        int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                    )

                    is_paused = False
                    try:
                        async with session.get(
                            base_url + "api/v2/app/status", headers=headers
                        ) as res:
                            if res.status < 400:
                                js = await res.json()
                                is_paused = js.get("status") != 5

                    except Exception as e:
                        _emit(log_queue, "error", f"{base_url} status check error: {e}")

                    member_offline = False
                    if member_id:
                        member = guild.get_member(member_id)
                        member_offline = (
                            member is not None and str(member.status) == "offline"
                        )
                    if is_paused or member_offline:
                        ok = await wake_streamlit_app(
                            session, base_url, dict(headers), authorizations, log_queue
                        )
                        if ok:
                            try:
                                await connect(base_url[8:].rstrip("/"))
                            except Exception as e:
                                _emit(
                                    log_queue,
                                    "error",
                                    f"{base_url} connect() failed: {e}",
                                )
                    else:
                        # App already awake and member online - lightweight keep-alive ping only.
                        try:
                            async with session.get(
                                base_url + "api/v2/app/disambiguate", headers=headers
                            ) as res:
                                _emit(
                                    log_queue,
                                    "info",
                                    f"{base_url} ping -> {res.status}",
                                )
                                await connect(base_url[8:].rstrip("/"))
                        except Exception as e:
                            _emit(log_queue, "error", f"{base_url} ping error: {e}")
        except Exception as e:
            RESULT = await getBasic(guild)
            _emit(log_queue, "error", f"keepLive error: {e}")

    client.run(os.environ.get("botToken"))


@st.cache_resource
def initialize_heavy_stuff():
    """
    Runs exactly once per server process (cache_resource). The thread object
    itself is returned as part of the cached result - that's the only way to
    keep a reference to it across Streamlit reruns, since every top-level
    variable in this script gets re-executed (and reset) on every rerun.
    """
    with st.spinner("running your scripts..."):
        t = threading.Thread(
            target=myStyle, args=(st.session_state.log_queue,), daemon=True
        )
        t.start()
        print("Heavy initialization running...")
        return {
            "thread": t,
            "model": "loaded_successfully",
            "timestamp": time.time(),
            "db_status": "connected",
        }


st.title("my style")

result = initialize_heavy_stuff()
thread = result["thread"]

st.success("The system is ready!")
st.write("Result:")
st.json({k: v for k, v in result.items() if k != "thread"})

with st.status("Processing...", expanded=True) as status:
    placeholder = st.empty()
    logs = []
    while thread.is_alive() or not st.session_state.log_queue.empty():
        try:
            level, message = st.session_state.log_queue.get_nowait()
            logs.append((level, message))
            with placeholder.container():
                for lvl, msg in logs[-200:]:
                    if lvl == "info":
                        st.write(msg)
                    elif lvl == "success":
                        st.success(msg)
                    elif lvl == "error":
                        st.error(msg)
        except queue.Empty:
            time.sleep(0.3)

    status.update(label="Bot is running", state="complete", expanded=False)
