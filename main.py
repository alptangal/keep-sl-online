import asyncio
import os,sys
import re,json
import discord
from discord.ext import commands, tasks
from discord.utils import get
import random
from guild import *
import server
import aiohttp
import requests
import datetime
from dotenv import load_dotenv
load_dotenv()


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
    global RESULT,GUILD_ID
    try:
        req=requests.get('http://localhost:8888')
        #server.b()
        if int(str(datetime.datetime.now().timestamp()).split('.')[0])-int(req.text.split('.')[0])>=10:
            raise Exception("Server not response")
        sys.exit("Exited")   
    except Exception as error:
        print(error)
        #if 'No connection could be made because the target machine actively refused it' in str(error) or "Server not response" in str(error):
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
            RESULT['rawCh']=await RESULT['streamlitCate'].create_text_channel(name='raw',overwrites=overwrites)
        if not keepLive.is_running():
            keepLive.start()
        if not updateUrl.is_running():
            updateUrl.start()
@tasks.loop(seconds=1)
async def updateUrl():
    global RESULT
    obj={}
    try:
        async for msg in RESULT['rawCh'].history():
            if msg.content.strip() not in obj:
                obj[msg.content.strip()]=''
            else:
                await msg.delete()
            if msg.content.strip() not in str(RESULT['urlsCh'].threads):
                await RESULT['urlsCh'].create_thread(name=msg.content.strip(),content=msg.content.strip())
                BASE_URL=msg.content.strip()
                headers={
                    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'
                }
                async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
                    async with session.get(BASE_URL,headers=headers,allow_redirects=False) as res:
                        if res.status<400:
                            location=res.headers['location']
                            headers['cookie']=''
                            async with session.get(location,headers=headers,allow_redirects=False) as res:
                                cookies = session.cookie_jar.filter_cookies(location)
                                for key, cookie in cookies.items():
                                    headers['cookie'] += cookie.key +'='+cookie.value+';'
                                async with session.get(BASE_URL+'api/v2/app/disambiguate',headers=headers) as res:
                                    if res.status<400:
                                        headers['x-csrf-token']=res.headers['x-csrf-token']
                                        url=BASE_URL+'api/v2/app/status'
                                        async with session.get(url,headers=headers) as res:
                                            js=await res.json()
                                            if js['status']!=5:
                                                url=BASE_URL+'api/v2/app/resume'
                                                req=requests.post(url,headers=headers)
                                            async with session.get(BASE_URL,headers=headers) as res:
                                                print(BASE_URL,'Ping success!')
    except:
        pass
@tasks.loop(minutes=5)
async def keepLive():
    global RESULT
    try:
        async for msg in RESULT['rawCh'].history():
            BASE_URL=msg.content.strip()
            print(BASE_URL+' processing')
            headers={
                'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'
            }
            async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
                async with session.get(BASE_URL,headers=headers,allow_redirects=False) as res:
                    if res.status<400:
                        location=res.headers['location']
                        headers['cookie']=''
                        async with session.get(location,headers=headers,allow_redirects=False) as res:
                            if res.status<400:
                                location=res.headers['location']
                                async with session.get(location,headers=headers,allow_redirects=False) as res:
                                    if res.status<400:
                                        location=res.headers['location']
                                        async with session.get(location,headers=headers,allow_redirects=False) as res:
                                            if res.status<400:
                                                async with session.get(location+'pi/v2/app/context',headers=headers,allow_redirects=False) as res:
                                                    if res.status<400:
                                                        cookies = session.cookie_jar.filter_cookies(location)
                                                        for key, cookie in cookies.items():
                                                            headers['cookie'] += cookie.key +'='+cookie.value+';'
                                                        async with session.get(BASE_URL+'api/v2/app/disambiguate',headers=headers) as res:
                                                            for thread in RESULT['urlsCh'].threads:
                                                                if BASE_URL in thread.name:
                                                                    try:
                                                                        await thread.delete()
                                                                    except Exception as error:
                                                                        print(error,2222)
                                                                        pass
                                                            if res.status<400:
                                                                headers['x-csrf-token']=res.headers['x-csrf-token']
                                                                url=BASE_URL+'api/v2/app/status'
                                                                async with session.get(url,headers=headers) as res:
                                                                    js=await res.json()
                                                                    if js['status']!=5:
                                                                        print(BASE_URL,'Resuming...')
                                                                        url=BASE_URL+'api/v2/app/resume'
                                                                        async with session.post(url,headers=headers) as res:
                                                                            if res.status<400:
                                                                                stop=False
                                                                                i=0
                                                                                while not stop:
                                                                                    async with session.get(BASE_URL+'api/v2/app/status',headers=headers) as res:
                                                                                        if res.status<400:
                                                                                            js=await res.json()
                                                                                            if js['status']==5:
                                                                                                stop=True
                                                                                    if i==20:
                                                                                        stop=True
                                                                                    asyncio.sleep(2)
                                                                                    i+=1
                                                                    now=datetime.datetime.now()
                                                                    if now.hour+7==0 and now.minute==0:
                                                                        url=BASE_URL+'api/v2/app/restart'
                                                                        async with session.post(BASE_URL,headers=headers) as res:
                                                                            print(res.status)
                                                                    async with session.get(BASE_URL,headers=headers) as res:
                                                                        print(res.status)
                                                                    
                                                                    await RESULT['urlsCh'].create_thread(name=BASE_URL,content=BASE_URL)
                                                                    print(BASE_URL,'Ping success!')
                                                            else:
                                                                try:
                                                                    await msg.delete()
                                                                except Exception as error:
                                                                    print(error,3333)
                                                                    pass
    except Exception as error:
        print(error,112233)
        pass
client.run(os.environ.get('botToken'))
