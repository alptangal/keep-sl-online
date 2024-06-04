import asyncio
import os
import re,json
import discord
from discord.ext import commands, tasks
from discord.utils import get
import random
from guild import *
import server
import aiohttp
import requests


GUILD_ID=1122707918177960047
BOT_NAME='shopee'
SESSION_ID=None
SESSION_ID_OLD=None
LAST_UPDATE=None
LAST_MSG=None
HEADERS=[]
intents = discord.Intents.default()
client = discord.Client(intents=intents)
RESULT = None
URL_STREAM='https://shoebee-fswaboivdxpaan5ewbppbf.streamlit.app/'

@client.event
async def on_ready():
    global RESULT
    try:
        req=requests.get('http://localhost:8888')
        print(req.status_code)
        await client.close() 
        print('Client closed')
        exit()
    except:
        server.b()  
        guild = client.get_guild(GUILD_ID)
        RESULT=await getBasic(guild)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        if not RESULT['streamlitCate']:
            RESULT['streamlitCate']=await guild.create_category(name='streamlit',overwrites=overwrites)
            RESULT['urlsCh']=await RESULT['streamlitCate'].create_forum(name='urls',overwrites=overwrites)
        if not keepLive.is_running():
            keepLive.start()
    
@tasks.loop(minutes=15)
async def keepLive():
    global RESULT
    for thread in RESULT['urlsCh'].threads:
        BASE_URL=thread.name
        headers={
            'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'
        }
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
            async with session.get(BASE_URL,headers=headers,allow_redirects=False) as res:
                if res.status<400:
                    location=res.headers['location']
                    headers['cookie']=''
                    async with session.get(location,headers=headers,allow_redirects=False) as res:
                        cookies = session.cookie_jar.filter_cookies('streamlit.app')
                        for key, cookie in cookies.items():
                            headers['cookie'] += cookie.key +'='+cookie.value+';'
                        async with session.get(BASE_URL+'api/v2/app/disambiguate',headers=headers) as res:
                            if res.status<400:
                                headers['x-csrf-token']=res.headers['x-csrf-token']
                                url=BASE_URL+'api/v2/app/status'
                                req=requests.get(url,headers=headers)
                                js=req.json()
                                if js['status']!=5:
                                    url=BASE_URL+'api/v2/app/resume'
                                    req=requests.post(url,headers=headers)
                                requests.get(BASE_URL,headers=headers)
                                print(BASE_URL,'Ping success!')
client.run(os.environ.get('botToken'))