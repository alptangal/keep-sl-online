import asyncio
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
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv
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


def myStyle(log_queue):
    intents = discord.Intents.all()
    client = discord.Client(intents=intents)
    authorizations = json.loads(str(os.getenv("authorizations")).replace("'", '"'))

    @client.event
    async def on_ready():
        global RESULT
        # try:
        #     req = requests.get("http://localhost:8888")
        #     if (
        #         int(str(datetime.datetime.now().timestamp()).split(".")[0])
        #         - int(req.text.split(".")[0])
        #         >= 10
        #     ):
        #         raise Exception("Server not response")
        #     sys.exit("Exited")
        # except Exception as error:
        #     print(error)
        #     server.b()
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
        global URL_STREAM, NEXT_TIME
        location = None
        print(f"restart vm after {RESTART_LOOP} hours")
        log_queue.put(("info", f"restart vm after {RESTART_LOOP} hours"))
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        if NEXT_TIME and RESULT:
            async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
                async with session.get(
                    URL_STREAM, headers=headers, allow_redirects=False
                ) as res:
                    if res.status < 400:
                        headers["cookie"] = ""
                        if not location:
                            location = res.headers["location"]
                            async with session.get(
                                location, headers=headers, allow_redirects=False
                            ) as res:
                                print(location)
                                if res.status < 400:
                                    location = res.headers["location"]
                                    async with session.get(
                                        location, headers=headers, allow_redirects=False
                                    ) as res:
                                        if res.status < 400:
                                            location = res.headers["location"]
                                            async with session.get(
                                                location,
                                                headers=headers,
                                                allow_redirects=False,
                                            ) as res:
                                                if res.status < 400:
                                                    async with session.get(
                                                        location + "api/v2/app/context",
                                                        headers=headers,
                                                        allow_redirects=False,
                                                    ) as res:
                                                        if res.status < 400:
                                                            cookies = session.cookie_jar.filter_cookies(
                                                                URL(location)
                                                            )
                                                            for (
                                                                key,
                                                                cookie,
                                                            ) in cookies.items():
                                                                headers["cookie"] += (
                                                                    cookie.key
                                                                    + "="
                                                                    + cookie.value
                                                                    + ";"
                                                                )
                                                            async with session.get(
                                                                URL_STREAM
                                                                + "api/v2/app/disambiguate",
                                                                headers=headers,
                                                            ) as res:
                                                                if res.status < 400:
                                                                    headers[
                                                                        "x-csrf-token"
                                                                    ] = res.headers[
                                                                        "x-csrf-token"
                                                                    ]
                                                                    url = (
                                                                        URL_STREAM
                                                                        + "api/v2/app/status"
                                                                    )
                                                                    async with (
                                                                        session.get(
                                                                            url,
                                                                            headers=headers,
                                                                        ) as res
                                                                    ):
                                                                        js = await res.json()
                                                                        if (
                                                                            js["status"]
                                                                            != 5
                                                                        ):
                                                                            print(
                                                                                URL_STREAM,
                                                                                "Resuming...",
                                                                            )
                                                                            url = (
                                                                                URL_STREAM
                                                                                + "api/v2/app/resume"
                                                                            )
                                                                            async with (
                                                                                session.post(
                                                                                    url,
                                                                                    headers=headers,
                                                                                ) as res
                                                                            ):
                                                                                if (
                                                                                    res.status
                                                                                    < 400
                                                                                ):
                                                                                    stop = False
                                                                                    i = 0
                                                                                    while not stop:
                                                                                        async with (
                                                                                            session.get(
                                                                                                URL_STREAM
                                                                                                + "api/v2/app/status",
                                                                                                headers=headers,
                                                                                            ) as res
                                                                                        ):
                                                                                            if (
                                                                                                res.status
                                                                                                < 400
                                                                                            ):
                                                                                                js = await res.json()
                                                                                                if (
                                                                                                    js[
                                                                                                        "status"
                                                                                                    ]
                                                                                                    == 5
                                                                                                ):
                                                                                                    stop = True
                                                                                        if (
                                                                                            i
                                                                                            == 20
                                                                                        ):
                                                                                            stop = True
                                                                                        await asyncio.sleep(
                                                                                            2
                                                                                        )
                                                                                        i += 1
                                                                        else:
                                                                            for author in authorizations:
                                                                                headers = {
                                                                                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
                                                                                    "cookie": author[
                                                                                        "cookie"
                                                                                    ],
                                                                                    "x-csrf-token": author[
                                                                                        "csrf_token"
                                                                                    ],
                                                                                    "Accept": "*/*",
                                                                                    "Accept-Encoding": "gzip, deflate, br, zstd",
                                                                                    "Connection": "keep-alive",
                                                                                }
                                                                                url = f"{URL_STREAM}api/v2/app/disambiguate"
                                                                                async with (
                                                                                    session.get(
                                                                                        url,
                                                                                        headers=headers,
                                                                                    ) as res
                                                                                ):
                                                                                    if (
                                                                                        res.status
                                                                                        < 400
                                                                                    ):
                                                                                        jsonData = await res.json()
                                                                                        appId = jsonData[
                                                                                            "appId"
                                                                                        ]
                                                                                        url = f"https://share.streamlit.io/api/v2/apps/{appId}/restart"
                                                                                        res = requests.post(
                                                                                            url,
                                                                                            headers=headers,
                                                                                        )
                                                                                        if (
                                                                                            res.status_code
                                                                                            == 204
                                                                                        ):
                                                                                            print(
                                                                                                f"{URL_STREAM} restarted"
                                                                                            )
                                                                                            stopped = False
                                                                                            while not stopped:
                                                                                                res = requests.get(
                                                                                                    url,
                                                                                                    headers=headers,
                                                                                                )
                                                                                                if (
                                                                                                    res.status_code
                                                                                                    < 400
                                                                                                ):
                                                                                                    jsonData = res.json()
                                                                                                    stopped = (
                                                                                                        jsonData[
                                                                                                            "status"
                                                                                                        ]
                                                                                                        == 5
                                                                                                    )
                                                                                                    print(
                                                                                                        f"{URL_STREAM} is running"
                                                                                                    )
                                                                                                else:
                                                                                                    print(
                                                                                                        f"Error: {res.status_code}"
                                                                                                    )
                                                                                                    stopped = True
                                                                                                await asyncio.sleep(
                                                                                                    1
                                                                                                )
                                                                                        else:
                                                                                            print(
                                                                                                f"{URL_STREAM} restart failed"
                                                                                            )
                                                                        async with (
                                                                            session.get(
                                                                                URL_STREAM,
                                                                                headers=headers,
                                                                            ) as res
                                                                        ):
                                                                            print(
                                                                                res.status
                                                                            )
                        else:
                            async with session.get(
                                location + "api/v2/app/context",
                                headers=headers,
                                allow_redirects=False,
                            ) as res:
                                if res.status < 400:
                                    cookies = session.cookie_jar.filter_cookies(
                                        URL(location)
                                    )
                                    for key, cookie in cookies.items():
                                        headers["cookie"] += (
                                            cookie.key + "=" + cookie.value + ";"
                                        )
                                    async with session.get(
                                        URL_STREAM + "api/v2/app/disambiguate",
                                        headers=headers,
                                    ) as res:
                                        if res.status < 400:
                                            headers["x-csrf-token"] = res.headers[
                                                "x-csrf-token"
                                            ]
                                            url = URL_STREAM + "api/v2/app/status"
                                            async with session.get(
                                                url, headers=headers
                                            ) as res:
                                                js = await res.json()
                                                if js["status"] != 5:
                                                    print(URL_STREAM, "Resuming...")
                                                    url = (
                                                        URL_STREAM + "api/v2/app/resume"
                                                    )
                                                    async with session.post(
                                                        url, headers=headers
                                                    ) as res:
                                                        if res.status < 400:
                                                            stop = False
                                                            i = 0
                                                            while not stop:
                                                                async with session.get(
                                                                    URL_STREAM
                                                                    + "api/v2/app/status",
                                                                    headers=headers,
                                                                ) as res:
                                                                    if res.status < 400:
                                                                        js = await res.json()
                                                                        if (
                                                                            js["status"]
                                                                            == 5
                                                                        ):
                                                                            stop = True
                                                                if i == 20:
                                                                    stop = True
                                                                await asyncio.sleep(2)
                                                                i += 1
                                                else:
                                                    for author in authorizations:
                                                        headers = {
                                                            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
                                                            "cookie": author["cookie"],
                                                            "x-csrf-token": author[
                                                                "csrf_token"
                                                            ],
                                                            "Accept": "*/*",
                                                            "Accept-Encoding": "gzip, deflate, br, zstd",
                                                            "Connection": "keep-alive",
                                                        }
                                                        url = f"{URL_STREAM}api/v2/app/disambiguate"
                                                        async with session.get(
                                                            url,
                                                            headers=headers,
                                                        ) as res:
                                                            if res.status < 400:
                                                                jsonData = (
                                                                    await res.json()
                                                                )
                                                                appId = jsonData[
                                                                    "appId"
                                                                ]
                                                                url = f"https://share.streamlit.io/api/v2/apps/{appId}/restart"
                                                                res = requests.post(
                                                                    url,
                                                                    headers=headers,
                                                                )
                                                                if (
                                                                    res.status_code
                                                                    == 204
                                                                ):
                                                                    print(
                                                                        f"{URL_STREAM} restarted"
                                                                    )
                                                                    stopped = False
                                                                    while not stopped:
                                                                        res = requests.get(
                                                                            url,
                                                                            headers=headers,
                                                                        )
                                                                        if (
                                                                            res.status_code
                                                                            < 400
                                                                        ):
                                                                            jsonData = res.json()
                                                                            stopped = (
                                                                                jsonData[
                                                                                    "status"
                                                                                ]
                                                                                == 5
                                                                            )
                                                                            print(
                                                                                f"{URL_STREAM} is running"
                                                                            )
                                                                        else:
                                                                            print(
                                                                                f"Error: {res.status_code}"
                                                                            )
                                                                            stopped = (
                                                                                True
                                                                            )
                                                                        await asyncio.sleep(
                                                                            1
                                                                        )
                                                                else:
                                                                    print(
                                                                        f"{URL_STREAM} restart failed"
                                                                    )
                                                    # req = requests.post(
                                                    #     url, headers=headers
                                                    # )
                                                    print(url, 4444555)
                                                for author in authorizations:
                                                    async with session.get(
                                                        location + "api/v2/app/context",
                                                        headers={
                                                            "cookie": author["cookie"],
                                                            "x-csrf-token": author[
                                                                "csrf_token"
                                                            ],
                                                        },
                                                        allow_redirects=False,
                                                    ) as res:
                                                        if res.status < 400:
                                                            cookies = session.cookie_jar.filter_cookies(
                                                                URL(location)
                                                            )
                                                            for (
                                                                key,
                                                                cookie,
                                                            ) in cookies.items():
                                                                headers["cookie"] += (
                                                                    cookie.key
                                                                    + "="
                                                                    + cookie.value
                                                                    + ";"
                                                                )
                                                            async with session.get(
                                                                URL_STREAM
                                                                + "api/v2/app/disambiguate",
                                                                headers=headers,
                                                            ) as res:
                                                                if res.status < 400:
                                                                    headers[
                                                                        "x-csrf-token"
                                                                    ] = res.headers[
                                                                        "x-csrf-token"
                                                                    ]
                                                                    url = (
                                                                        URL_STREAM
                                                                        + "api/v1/app/event/open"
                                                                    )
                                                                    async with (
                                                                        session.post(
                                                                            url,
                                                                            headers=headers,
                                                                        ) as res
                                                                    ):
                                                                        url = (
                                                                            URL_STREAM
                                                                            + "api/v2/app/status"
                                                                        )
                                                                        async with (
                                                                            session.get(
                                                                                url,
                                                                                headers=headers,
                                                                            ) as res
                                                                        ):
                                                                            print(
                                                                                res.status
                                                                            )
                                                                            await asyncio.sleep(
                                                                                60
                                                                            )
        else:
            NEXT_TIME = False

    @tasks.loop(seconds=15)
    async def updateUrl():
        global RESULT
        obj = {}
        try:
            async for msg in RESULT["rawCh"].history():
                if msg.content.strip() not in str(RESULT["urlsCh"].threads):
                    url = msg.content.strip().split(" || ")[0]
                    await RESULT["urlsCh"].create_thread(
                        name=msg.content.strip(), content=url
                    )
                    BASE_URL = msg.content.strip()
                    headers = {
                        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
                    }
                    async with aiohttp.ClientSession(
                        cookie_jar=aiohttp.CookieJar()
                    ) as session:
                        async with session.get(
                            BASE_URL, headers=headers, allow_redirects=False
                        ) as res:
                            if res.status < 400:
                                location = res.headers["location"]
                                headers["cookie"] = ""
                                async with session.get(
                                    location, headers=headers, allow_redirects=False
                                ) as res:
                                    cookies = session.cookie_jar.filter_cookies(
                                        location
                                    )
                                    for key, cookie in cookies.items():
                                        headers["cookie"] += (
                                            cookie.key + "=" + cookie.value + ";"
                                        )
                                    async with session.get(
                                        BASE_URL + "api/v2/app/disambiguate",
                                        headers=headers,
                                    ) as res:
                                        if res.status < 400:
                                            headers["x-csrf-token"] = res.headers[
                                                "x-csrf-token"
                                            ]
                                            url = BASE_URL + "api/v2/app/status"
                                            async with session.get(
                                                url, headers=headers
                                            ) as res:
                                                js = await res.json()
                                                if js["status"] != 5:
                                                    url = BASE_URL + "api/v2/app/resume"
                                                    req = requests.post(
                                                        url, headers=headers
                                                    )
                                                async with session.get(
                                                    BASE_URL, headers=headers
                                                ) as res:
                                                    print(BASE_URL, "Ping success!")
        except Exception as e:
            print(f"Error:{e}")
            pass

    @tasks.loop(seconds=30)
    async def keepLive(guild):
        global RESULT
        location = None
        try:
            async for msg in RESULT["rawCh"].history():
                BASE_URL = msg.content.strip().split(" || ")[0]
                print(BASE_URL + " processing")
                isPaused = False
                headers = {
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
                }
                async with aiohttp.ClientSession(
                    cookie_jar=aiohttp.CookieJar()
                ) as session:
                    async with session.get(
                        BASE_URL + "api/v2/app/status", headers=headers
                    ) as res:
                        if res.status < 400:
                            js = await res.json()
                            if js["status"] != 5:
                                isPaused = True
                    if not isPaused:
                        async with session.get(
                            BASE_URL, headers=headers, allow_redirects=False
                        ) as res:
                            if res.status < 400:
                                headers["cookie"] = ""
                                if not location:
                                    location = res.headers["location"]
                                    #
                                    async with session.get(
                                        location, headers=headers, allow_redirects=False
                                    ) as res:
                                        if res.status < 400:
                                            location = res.headers["location"]
                                            async with session.get(
                                                location,
                                                headers=headers,
                                                allow_redirects=False,
                                            ) as res:
                                                if res.status < 400:
                                                    location = res.headers["location"]
                                                    async with session.get(
                                                        location,
                                                        headers=headers,
                                                        allow_redirects=False,
                                                    ) as res:
                                                        if res.status < 400:
                                                            async with session.get(
                                                                location
                                                                + "api/v2/app/context",
                                                                headers=headers,
                                                                allow_redirects=False,
                                                            ) as res:
                                                                if res.status < 400:
                                                                    print(session)
                                                                    cookies = session.cookie_jar.filter_cookies(
                                                                        URL(location)
                                                                    )
                                                                    for (
                                                                        key,
                                                                        cookie,
                                                                    ) in (
                                                                        cookies.items()
                                                                    ):
                                                                        headers[
                                                                            "cookie"
                                                                        ] += (
                                                                            cookie.key
                                                                            + "="
                                                                            + cookie.value
                                                                            + ";"
                                                                        )
                                                                    async with (
                                                                        session.get(
                                                                            BASE_URL
                                                                            + "api/v2/app/disambiguate",
                                                                            headers=headers,
                                                                        ) as res
                                                                    ):
                                                                        print(
                                                                            BASE_URL,
                                                                            "Ping success!1111111",
                                                                        )
                                else:
                                    location = res.headers["location"]
                                    async with session.get(
                                        location, headers=headers, allow_redirects=False
                                    ) as res:
                                        if res.status < 400:
                                            cookies = session.cookie_jar.filter_cookies(
                                                URL(location)
                                            )
                                            for key, cookie in cookies.items():
                                                headers["cookie"] += (
                                                    cookie.key
                                                    + "="
                                                    + cookie.value
                                                    + ";"
                                                )
                                            async with session.get(
                                                BASE_URL + "api/v2/app/context",
                                                headers=headers,
                                                allow_redirects=False,
                                            ) as res:
                                                if res.status < 400:
                                                    cookies = session.cookie_jar.filter_cookies(
                                                        URL(location)
                                                    )
                                                    for key, cookie in cookies.items():
                                                        headers["cookie"] += (
                                                            cookie.key
                                                            + "="
                                                            + cookie.value
                                                            + ";"
                                                        )
                                                    async with session.get(
                                                        BASE_URL
                                                        + "api/v2/app/disambiguate",
                                                        headers=headers,
                                                    ) as res:
                                                        print(BASE_URL, "Ping success!")
                id = int(msg.content.strip().split(" || ")[1])

                for member in guild.members:
                    location = None
                    if id == member.id and str(member.status) == "offline" or isPaused:
                        headers = {
                            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
                        }
                        async with aiohttp.ClientSession(
                            cookie_jar=aiohttp.CookieJar()
                        ) as session:
                            async with session.get(
                                BASE_URL, headers=headers, allow_redirects=False
                            ) as res:
                                print(4445555)
                                if res.status < 400:
                                    print(res.headers["location"], 11111)
                                    headers["cookie"] = ""
                                    if not location:
                                        location = res.headers["location"]
                                        async with session.get(
                                            location,
                                            headers=headers,
                                            allow_redirects=False,
                                        ) as res:
                                            if res.status < 400:
                                                cookies = (
                                                    session.cookie_jar.filter_cookies(
                                                        URL(location)
                                                    )
                                                )
                                                for key, cookie in cookies.items():
                                                    headers["cookie"] += (
                                                        cookie.key
                                                        + "="
                                                        + cookie.value
                                                        + ";"
                                                    )
                                                location = res.headers["location"]
                                                async with session.get(
                                                    location,
                                                    headers=headers,
                                                    allow_redirects=False,
                                                ) as res:
                                                    if res.status < 400:
                                                        location = res.headers[
                                                            "location"
                                                        ]
                                                        async with session.get(
                                                            location,
                                                            headers=headers,
                                                            allow_redirects=False,
                                                        ) as res:
                                                            if res.status < 400:
                                                                async with session.get(
                                                                    location
                                                                    + "api/v2/app/context",
                                                                    headers=headers,
                                                                    allow_redirects=False,
                                                                ) as res:
                                                                    if res.status < 400:
                                                                        async with (
                                                                            session.get(
                                                                                BASE_URL
                                                                                + "api/v2/app/disambiguate",
                                                                                headers=headers,
                                                                            ) as res
                                                                        ):
                                                                            if (
                                                                                res.status
                                                                                < 400
                                                                            ):
                                                                                headers[
                                                                                    "x-csrf-token"
                                                                                ] = res.headers[
                                                                                    "x-csrf-token"
                                                                                ]
                                                                                url = (
                                                                                    BASE_URL
                                                                                    + "api/v2/app/status"
                                                                                )
                                                                                async with (
                                                                                    session.get(
                                                                                        url,
                                                                                        headers=headers,
                                                                                    ) as res
                                                                                ):
                                                                                    js = await res.json()
                                                                                    if (
                                                                                        js[
                                                                                            "status"
                                                                                        ]
                                                                                        != 5
                                                                                    ):
                                                                                        print(
                                                                                            BASE_URL,
                                                                                            "Resuming...",
                                                                                        )
                                                                                        url = (
                                                                                            BASE_URL
                                                                                            + "api/v2/app/resume"
                                                                                        )
                                                                                        async with (
                                                                                            session.post(
                                                                                                url,
                                                                                                headers=headers,
                                                                                            ) as res
                                                                                        ):
                                                                                            if (
                                                                                                res.status
                                                                                                < 400
                                                                                            ):
                                                                                                stop = False
                                                                                                i = 0
                                                                                                while not stop:
                                                                                                    async with (
                                                                                                        session.get(
                                                                                                            BASE_URL
                                                                                                            + "api/v2/app/status",
                                                                                                            headers=headers,
                                                                                                        ) as res
                                                                                                    ):
                                                                                                        if (
                                                                                                            res.status
                                                                                                            < 400
                                                                                                        ):
                                                                                                            js = await res.json()
                                                                                                            if (
                                                                                                                js[
                                                                                                                    "status"
                                                                                                                ]
                                                                                                                == 5
                                                                                                            ):
                                                                                                                stop = True
                                                                                                    if (
                                                                                                        i
                                                                                                        == 20
                                                                                                    ):
                                                                                                        stop = True
                                                                                                    await asyncio.sleep(
                                                                                                        2
                                                                                                    )
                                                                                                    i += 1
                                                                                    else:
                                                                                        for author in authorizations:
                                                                                            headers = {
                                                                                                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
                                                                                                "cookie": author[
                                                                                                    "cookie"
                                                                                                ],
                                                                                                "x-csrf-token": author[
                                                                                                    "csrf_token"
                                                                                                ],
                                                                                                "Accept": "*/*",
                                                                                                "Accept-Encoding": "gzip, deflate, br, zstd",
                                                                                                "Connection": "keep-alive",
                                                                                            }
                                                                                            url = f"{BASE_URL}api/v2/app/disambiguate"
                                                                                            async with (
                                                                                                session.get(
                                                                                                    url,
                                                                                                    headers=headers,
                                                                                                ) as res
                                                                                            ):
                                                                                                if (
                                                                                                    res.status
                                                                                                    < 400
                                                                                                ):
                                                                                                    jsonData = await res.json()
                                                                                                    appId = jsonData[
                                                                                                        "appId"
                                                                                                    ]
                                                                                                    url = f"https://share.streamlit.io/api/v2/apps/{appId}/restart"
                                                                                                    res = requests.post(
                                                                                                        url,
                                                                                                        headers=headers,
                                                                                                    )
                                                                                                    if (
                                                                                                        res.status_code
                                                                                                        == 204
                                                                                                    ):
                                                                                                        print(
                                                                                                            f"{BASE_URL} restarted"
                                                                                                        )
                                                                                                        url = f"{BASE_URL}api/v2/app/status"
                                                                                                        stopped = False
                                                                                                        while not stopped:
                                                                                                            res = requests.get(
                                                                                                                url,
                                                                                                                headers=headers,
                                                                                                            )
                                                                                                            if (
                                                                                                                res.status_code
                                                                                                                < 400
                                                                                                            ):
                                                                                                                jsonData = res.json()
                                                                                                                stopped = (
                                                                                                                    jsonData[
                                                                                                                        "status"
                                                                                                                    ]
                                                                                                                    == 5
                                                                                                                )
                                                                                                                print(
                                                                                                                    f"{BASE_URL} is running"
                                                                                                                )
                                                                                                            else:
                                                                                                                print(
                                                                                                                    f"Error: {res.status_code}"
                                                                                                                )
                                                                                                                stopped = True
                                                                                                            await asyncio.sleep(
                                                                                                                1
                                                                                                            )
                                                                                                    else:
                                                                                                        print(
                                                                                                            f"{BASE_URL} restart failed"
                                                                                                        )
                                                                            else:
                                                                                try:
                                                                                    await msg.delete()
                                                                                except Exception as error:
                                                                                    print(
                                                                                        error,
                                                                                        3333,
                                                                                    )
                                                                                    pass
                                    else:
                                        location = BASE_URL
                                        print(location, 33333, headers)
                                        async with session.get(
                                            location + "api/v2/app/context",
                                            headers=headers,
                                            allow_redirects=False,
                                        ) as res:
                                            if res.status < 400:
                                                """cookies = session.cookie_jar.filter_cookies(location)
                                                for key, cookie in cookies.items():
                                                    headers['cookie'] += cookie.key +'='+cookie.value+';'
                                                """
                                                async with session.get(
                                                    BASE_URL
                                                    + "api/v2/app/disambiguate",
                                                    headers=headers,
                                                ) as res:
                                                    if res.status < 400:
                                                        headers["x-csrf-token"] = (
                                                            res.headers["x-csrf-token"]
                                                        )
                                                        url = (
                                                            BASE_URL
                                                            + "api/v2/app/status"
                                                        )
                                                        async with session.get(
                                                            url, headers=headers
                                                        ) as res:
                                                            js = await res.json()
                                                            if js["status"] != 5:
                                                                print(
                                                                    BASE_URL,
                                                                    "Resuming...",
                                                                )
                                                                url = (
                                                                    BASE_URL
                                                                    + "api/v2/app/resume"
                                                                )
                                                                async with session.post(
                                                                    url, headers=headers
                                                                ) as res:
                                                                    if res.status < 400:
                                                                        stop = False
                                                                        i = 0
                                                                        while not stop:
                                                                            async with (
                                                                                session.get(
                                                                                    BASE_URL
                                                                                    + "api/v2/app/status",
                                                                                    headers=headers,
                                                                                ) as res
                                                                            ):
                                                                                if (
                                                                                    res.status
                                                                                    < 400
                                                                                ):
                                                                                    js = await res.json()
                                                                                    if (
                                                                                        js[
                                                                                            "status"
                                                                                        ]
                                                                                        == 5
                                                                                    ):
                                                                                        stop = True
                                                                            if i == 20:
                                                                                stop = (
                                                                                    True
                                                                                )
                                                                            await asyncio.sleep(
                                                                                2
                                                                            )
                                                                            i += 1
                                                            else:
                                                                for (
                                                                    author
                                                                ) in authorizations:
                                                                    headers = {
                                                                        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
                                                                        "cookie": author[
                                                                            "cookie"
                                                                        ],
                                                                        "x-csrf-token": author[
                                                                            "csrf_token"
                                                                        ],
                                                                        "Accept": "*/*",
                                                                        "Accept-Encoding": "gzip, deflate, br, zstd",
                                                                        "Connection": "keep-alive",
                                                                    }
                                                                    url = f"{BASE_URL}api/v2/app/disambiguate"
                                                                    async with (
                                                                        session.get(
                                                                            url,
                                                                            headers=headers,
                                                                        ) as res
                                                                    ):
                                                                        if (
                                                                            res.status
                                                                            < 400
                                                                        ):
                                                                            jsonData = await res.json()
                                                                            appId = jsonData[
                                                                                "appId"
                                                                            ]
                                                                            url = f"https://share.streamlit.io/api/v2/apps/{appId}/restart"
                                                                            res = requests.post(
                                                                                url,
                                                                                headers=headers,
                                                                            )
                                                                            if (
                                                                                res.status_code
                                                                                == 204
                                                                            ):
                                                                                print(
                                                                                    f"{BASE_URL} restarted"
                                                                                )
                                                                                stopped = False
                                                                                while not stopped:
                                                                                    res = requests.get(
                                                                                        url,
                                                                                        headers=headers,
                                                                                    )
                                                                                    if (
                                                                                        res.status_code
                                                                                        < 400
                                                                                    ):
                                                                                        jsonData = res.json()
                                                                                        stopped = (
                                                                                            jsonData[
                                                                                                "status"
                                                                                            ]
                                                                                            == 5
                                                                                        )
                                                                                        print(
                                                                                            f"{BASE_URL} is running"
                                                                                        )
                                                                                    else:
                                                                                        print(
                                                                                            f"Error: {res.status_code}"
                                                                                        )
                                                                                        stopped = True
                                                                                    await asyncio.sleep(
                                                                                        1
                                                                                    )
                                                                            else:
                                                                                print(
                                                                                    f"{BASE_URL} restart failed"
                                                                                )
                                                            async with session.get(
                                                                location
                                                                + "api/v2/app/context",
                                                                headers=headers,
                                                                allow_redirects=False,
                                                            ) as res:
                                                                if res.status < 400:
                                                                    cookies = session.cookie_jar.filter_cookies(
                                                                        location
                                                                    )
                                                                    for (
                                                                        key,
                                                                        cookie,
                                                                    ) in (
                                                                        cookies.items()
                                                                    ):
                                                                        headers[
                                                                            "cookie"
                                                                        ] += (
                                                                            cookie.key
                                                                            + "="
                                                                            + cookie.value
                                                                            + ";"
                                                                        )
                                                                    async with (
                                                                        session.get(
                                                                            BASE_URL
                                                                            + "api/v2/app/disambiguate",
                                                                            headers=headers,
                                                                        ) as res
                                                                    ):
                                                                        if (
                                                                            res.status
                                                                            < 400
                                                                        ):
                                                                            headers[
                                                                                "x-csrf-token"
                                                                            ] = res.headers[
                                                                                "x-csrf-token"
                                                                            ]
                                                                            url = (
                                                                                BASE_URL
                                                                                + "api/v1/app/event/open"
                                                                            )
                                                                            async with (
                                                                                session.post(
                                                                                    url,
                                                                                    headers=headers,
                                                                                ) as res
                                                                            ):
                                                                                url = (
                                                                                    BASE_URL
                                                                                    + "api/v2/app/status"
                                                                                )
                                                                                async with (
                                                                                    session.get(
                                                                                        url,
                                                                                        headers=headers,
                                                                                    ) as res
                                                                                ):
                                                                                    print(
                                                                                        res.status
                                                                                    )
                                                                                    await asyncio.sleep(
                                                                                        60
                                                                                    )
                                                    else:
                                                        try:
                                                            await msg.delete()
                                                        except Exception as error:
                                                            print(error, 3333)
                                                            pass
                        break

        except Exception as error:
            RESULT = await getBasic(guild)
            print(error, 112233)
            pass

    client.run(os.environ.get("botToken"))


thread = None


@st.cache_resource
def initialize_heavy_stuff():
    global thread
    # Đây là phần chỉ chạy ĐÚNG 1 LẦN khi server khởi động (hoặc khi cache miss)
    with st.spinner("running your scripts..."):
        thread = threading.Thread(target=myStyle, args=(st.session_state.log_queue,))
        thread.start()
        print(
            "Heavy initialization running..."
        )  # bạn sẽ thấy log này chỉ 1 lần trong console/cloud log
        with st.status("Processing...", expanded=True) as status:
            placeholder = st.empty()
            logs = []
            while thread.is_alive() or not st.session_state.log_queue.empty():
                try:
                    level, message = st.session_state.log_queue.get_nowait()
                    logs.append((level, message))

                    with placeholder.container():
                        for lvl, msg in logs:
                            if lvl == "info":
                                st.write(msg)
                            elif lvl == "success":
                                st.success(msg)
                            elif lvl == "error":
                                st.error(msg)

                    time.sleep(0.2)
                except queue.Empty:
                    time.sleep(0.3)

            status.update(label="Hoàn thành!", state="complete", expanded=False)
        return {
            "model": "loaded_successfully",
            "timestamp": time.time(),
            "db_status": "connected",
        }


# Trong phần chính của app
st.title("my style")

# Dòng này đảm bảo: chạy 1 lần duy nhất, mọi user đều dùng chung kết quả
result = initialize_heavy_stuff()

st.success("The system is ready!")
st.write("Result:")
st.json(result)
