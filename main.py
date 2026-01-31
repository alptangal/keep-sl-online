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
