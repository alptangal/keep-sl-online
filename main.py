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
intents = discord.Intents.all()
client = discord.Client(intents=intents)
RESULT = None
URL_STREAM='https://keep-sl-online-d7bnwfpjbw9cw23yreygwk.streamlit.app/'
RESTART_LOOP=random.randrange(24,72,1)#12,18,1)
NEXT_TIME=False
authorizations=json.loads(os.getenv('authorizations').replace("'",'"'))


@client.event
async def on_ready():
    global RESULT,GUILD_ID
    try:
        req=requests.get('http://localhost:8888')
        if int(str(datetime.datetime.now().timestamp()).split('.')[0])-int(req.text.split('.')[0])>=10:
            raise Exception("Server not response")
        sys.exit("Exited")
    except Exception as error:
        print(error)
        server.b()  
        guild = client.get_guild(GUILD_ID)
        RESULT=await getBasic(guild)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        if 'streamlitCate' not in RESULT:
            RESULT['streamlitCate']=await guild.create_category(name='streamlit',overwrites=overwrites)
            RESULT['urlsCh']=await RESULT['streamlitCate'].create_forum(name='urls',overwrites=overwrites)
            RESULT['rawCh']=await RESULT['streamlitCate'].create_text_channel(name='raw',overwrites=overwrites)
        if not keepLive.is_running():
            keepLive.start(guild)
        if not restartVM.is_running():
            restartVM.start()
            
@tasks.loop(hours=RESTART_LOOP)
async def restartVM():
    global URL_STREAM,NEXT_TIME
    print(f'restart vm after {RESTART_LOOP} hours')
    if NEXT_TIME:
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
            async with session.get(URL_STREAM,headers=headers,allow_redirects=False) as res:
                if res.status<400:
                    headers['cookie']=''
                    if not location:
                        location=res.headers['location']
                        async with session.get(location,headers=headers,allow_redirects=False) as res:
                            if res.status<400:
                                location=res.headers['location']
                                async with session.get(location,headers=headers,allow_redirects=False) as res:
                                    if res.status<400:
                                        location=res.headers['location']
                                        async with session.get(location,headers=headers,allow_redirects=False) as res:
                                            if res.status<400:
                                                async with session.get(location+'api/v2/app/context',headers=headers,allow_redirects=False) as res:
                                                    if res.status<400:
                                                        cookies = session.cookie_jar.filter_cookies(location)
                                                        for key, cookie in cookies.items():
                                                            headers['cookie'] += cookie.key +'='+cookie.value+';'
                                                        async with session.get(URL_STREAM+'api/v2/app/disambiguate',headers=headers) as res:
                                                            if res.status<400:
                                                                headers['x-csrf-token']=res.headers['x-csrf-token']
                                                                url=URL_STREAM+'api/v2/app/status'
                                                                async with session.get(url,headers=headers) as res:
                                                                    js=await res.json()
                                                                    if js['status']!=5:
                                                                        print(URL_STREAM,'Resuming...')
                                                                        url=URL_STREAM+'api/v2/app/resume'
                                                                        async with session.post(url,headers=headers) as res:
                                                                            if res.status<400:
                                                                                stop=False
                                                                                i=0
                                                                                while not stop:
                                                                                    async with session.get(URL_STREAM+'api/v2/app/status',headers=headers) as res:
                                                                                        if res.status<400:
                                                                                            js=await res.json()
                                                                                            if js['status']==5:
                                                                                                stop=True
                                                                                    if i==20:
                                                                                        stop=True
                                                                                    await asyncio.sleep(2)
                                                                                    i+=1
                                                                    else:
                                                                        url=URL_STREAM+'api/v2/app/restart'
                                                                        for author in authorizations:
                                                                            async with session.post(URL_STREAM,headers={
                                                                                'cookie':author['cookie'],
                                                                                'x-csrf-token':author['csrf_token']
                                                                            }) as res:
                                                                                print(url,res.status,2222222)
                                                                    async with session.get(URL_STREAM,headers=headers) as res:
                                                                        print(res.status)
                    else:
                        async with session.get(location+'api/v2/app/context',headers=headers,allow_redirects=False) as res:
                            if res.status<400:
                                cookies = session.cookie_jar.filter_cookies(location)
                                for key, cookie in cookies.items():
                                    headers['cookie'] += cookie.key +'='+cookie.value+';'
                                async with session.get(URL_STREAM+'api/v2/app/disambiguate',headers=headers) as res:
                                    if res.status<400:
                                        headers['x-csrf-token']=res.headers['x-csrf-token']
                                        url=URL_STREAM+'api/v2/app/status'
                                        async with session.get(url,headers=headers) as res:
                                            js=await res.json()
                                            if js['status']!=5:
                                                print(URL_STREAM,'Resuming...')
                                                url=URL_STREAM+'api/v2/app/resume'
                                                async with session.post(url,headers=headers) as res:
                                                    if res.status<400:
                                                        stop=False
                                                        i=0
                                                        while not stop:
                                                            async with session.get(URL_STREAM+'api/v2/app/status',headers=headers) as res:
                                                                if res.status<400:
                                                                    js=await res.json()
                                                                    if js['status']==5:
                                                                        stop=True
                                                            if i==20:
                                                                stop=True
                                                            await asyncio.sleep(2)
                                                            i+=1
                                            else:
                                                url=URL_STREAM+'api/v2/app/restart'
                                                headers['content-type']='application/json'
                                                headers['x-csrf-token']='NXlRV0lFQWRKY1NuZ0d5SmpidmloTWJIbmNZYTZEYkRlPBQ/KwsMAy4FNSUiESAPMjAYGR4bKSIeEC9WRjxWCQ=='
                                                headers['cookie']='streamlit_session=MTcyNzU4OTQ1MHwzc3ZnYmJ3Q1VjQVpObG53OU1ndkdJejFWSWZZU0tBRUctQjY5c3dfWjdVaEVrcXE2aFhmenZaam1JRy11VklhVzdXRExIZDdCTEc4ZlBPNmE1UUZPV0NpTFBnWjFWbEswSWN6N0EzcHBNRDh6VmVwMUZLRzYtaGdtOXRZcVZIdm5iZHBHVUFFMzBVbnRUVDhYMmE1dnF5N2sxUlpzM2dJYUVKV1pQY3U2Z1h3aTltUEI0TklNNUN2MWc9PXzRNXhbLSr7v2HEbKkW7dG7SYhIAG8syrA6cT6PcVoTUg==;_streamlit_csrf=MTcyNzU4OTQ2MHxJbFZGVmtaaFIwcFBWRmRrYTFwdFdreFNWbHBhVWxab1UySnVRakpXYTNSeFkwaE9NazR6UWpST1JUQTlJZz09fMCqnUsraPXID4OUqUlNQzBliXqyC6OBcvo4p_uRHB3R'
                                                headers={
                                                    'content-length':'0',
                                                    'x-csrf-token':'NXlRV0lFQWRKY1NuZ0d5SmpidmloTWJIbmNZYTZEYkRlPBQ/KwsMAy4FNSUiESAPMjAYGR4bKSIeEC9WRjxWCQ==',
                                                    'cookie':'streamlit_session=MTcyNzU4OTQ1MHwzc3ZnYmJ3Q1VjQVpObG53OU1ndkdJejFWSWZZU0tBRUctQjY5c3dfWjdVaEVrcXE2aFhmenZaam1JRy11VklhVzdXRExIZDdCTEc4ZlBPNmE1UUZPV0NpTFBnWjFWbEswSWN6N0EzcHBNRDh6VmVwMUZLRzYtaGdtOXRZcVZIdm5iZHBHVUFFMzBVbnRUVDhYMmE1dnF5N2sxUlpzM2dJYUVKV1pQY3U2Z1h3aTltUEI0TklNNUN2MWc9PXzRNXhbLSr7v2HEbKkW7dG7SYhIAG8syrA6cT6PcVoTUg==;_streamlit_csrf=MTcyNzU4OTQ2MHxJbFZGVmtaaFIwcFBWRmRrYTFwdFdreFNWbHBhVWxab1UySnVRakpXYTNSeFkwaE9NazR6UWpST1JUQTlJZz09fMCqnUsraPXID4OUqUlNQzBliXqyC6OBcvo4p_uRHB3R'
                                                }
                                                req=requests.post(url,headers=headers)
                                                print(req,url)
                                                stop=False
                                                i=0
                                                while not stop:
                                                    url=URL_STREAM+'api/v2/app/status'
                                                    req=requests.get(url,headers=headers)
                                                    if req.status_code<400:
                                                        js=req.json()
                                                        if js['status']!=5:
                                                            await asyncio.sleep(15)
                                                        else:
                                                            stop=True
                                                    if i==10:
                                                        stop=True
                                                    i+=1
                                            async with session.get(location+'api/v2/app/context',headers=headers,allow_redirects=False) as res:
                                                if res.status<400:
                                                    cookies = session.cookie_jar.filter_cookies(location)
                                                    for key, cookie in cookies.items():
                                                        headers['cookie'] += cookie.key +'='+cookie.value+';'
                                                    async with session.get(URL_STREAM+'api/v2/app/disambiguate',headers=headers) as res:
                                                        if res.status<400:
                                                            headers['x-csrf-token']=res.headers['x-csrf-token']
                                                            url=URL_STREAM+'api/v1/app/event/open'
                                                            async with session.post(url,headers=headers) as res:
                                                                url=URL_STREAM+'api/v2/app/status'
                                                                async with session.get(url,headers=headers) as res:
                                                                    print(res.status)
                                                                    await asyncio.sleep(60)
    else:
        NEXT_TIME=False
@tasks.loop(seconds=15)
async def updateUrl():
    global RESULT
    obj={}
    try:
        async for msg in RESULT['rawCh'].history():
            if msg.content.strip() not in str(RESULT['urlsCh'].threads):
                url=msg.content.strip().split(' || ')[0]
                await RESULT['urlsCh'].create_thread(name=msg.content.strip(),content=url)
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
@tasks.loop(seconds=30)
async def keepLive(guild):
    global RESULT
    location=None
    
    try:
        async for msg in RESULT['rawCh'].history():
            BASE_URL=msg.content.strip().split(' || ')[0]
            print(BASE_URL+' processing')
            isPaused=False
            headers={
                'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'
            }
            async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
                async with session.get(BASE_URL+'api/v2/app/status',headers=headers) as res:
                    if res.status<400:
                        js=await res.json()
                        if js['status']!=5:
                            isPaused=True
                if not isPaused:
                    async with session.get(BASE_URL,headers=headers,allow_redirects=False) as res:
                        if res.status<400:
                            
                            headers['cookie']=''
                            if not location:
                                location=res.headers['location']
                                #
                                async with session.get(location,headers=headers,allow_redirects=False) as res:
                                    if res.status<400:
                                        location=res.headers['location']
                                        async with session.get(location,headers=headers,allow_redirects=False) as res:
                                            if res.status<400:
                                                location=res.headers['location']
                                                async with session.get(location,headers=headers,allow_redirects=False) as res:
                                                    if res.status<400:
                                                        async with session.get(location+'api/v2/app/context',headers=headers,allow_redirects=False) as res:
                                                            if res.status<400:
                                                                cookies = session.cookie_jar.filter_cookies(location)
                                                                for key, cookie in cookies.items():
                                                                    headers['cookie'] += cookie.key +'='+cookie.value+';'
                                                                async with session.get(BASE_URL+'api/v2/app/disambiguate',headers=headers) as res:
                                                                    print(BASE_URL,'Ping success!1111111')
                            else:
                                #location=res.headers['location']
                                print(location,22222)
                                async with session.get(location,headers=headers,allow_redirects=False) as res:
                                    if res.status<400:
                                        cookies = session.cookie_jar.filter_cookies(location)
                                        for key, cookie in cookies.items():
                                            headers['cookie'] += cookie.key +'='+cookie.value+';'
                                        async with session.get(BASE_URL+'api/v2/app/context',headers=headers,allow_redirects=False) as res:
                                            if res.status<400:
                                                cookies = session.cookie_jar.filter_cookies(location)
                                                for key, cookie in cookies.items():
                                                    headers['cookie'] += cookie.key +'='+cookie.value+';'
                                                async with session.get(BASE_URL+'api/v2/app/disambiguate',headers=headers) as res:
                                                    print(BASE_URL,'Ping success!')
            id=int(msg.content.strip().split(' || ')[1])
            
            for member in guild.members:
                location=None
                if id==member.id and str(member.status)=='offline' or isPaused:
                    headers={
                        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'
                    }
                    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
                        async with session.get(BASE_URL,headers=headers,allow_redirects=False) as res:
                            if res.status<400:
                                print(res.headers['location'],11111)
                                headers['cookie']=''
                                if not location:
                                    location=res.headers['location']
                                    async with session.get(location,headers=headers,allow_redirects=False) as res:
                                        if res.status<400:
                                            cookies = session.cookie_jar.filter_cookies(location)
                                            for key, cookie in cookies.items():
                                                headers['cookie'] += cookie.key +'='+cookie.value+';'
                                            location=res.headers['location']
                                            async with session.get(location,headers=headers,allow_redirects=False) as res:
                                                if res.status<400:
                                                    location=res.headers['location']
                                                    async with session.get(location,headers=headers,allow_redirects=False) as res:
                                                        if res.status<400:
                                                            async with session.get(location+'api/v2/app/context',headers=headers,allow_redirects=False) as res:
                                                                if res.status<400:
                                                                    
                                                                    async with session.get(BASE_URL+'api/v2/app/disambiguate',headers=headers) as res:
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
                                                                                                await asyncio.sleep(2)
                                                                                                i+=1
                                                                                else:
                                                                                    url=BASE_URL+'api/v2/app/restart'
                                                                                    async with session.post(BASE_URL,headers=headers) as res:
                                                                                        print(res.status,2222222)
                                                                                async with session.get(BASE_URL,headers=headers) as res:
                                                                                    print(res.status)
                                                                        else:
                                                                            try:
                                                                                await msg.delete()
                                                                            except Exception as error:
                                                                                print(error,3333)
                                                                                pass
                                else:
                                    location=BASE_URL
                                    print(location,33333,headers)
                                    async with session.get(location+'api/v2/app/context',headers=headers,allow_redirects=False) as res:
                                        if res.status<400:
                                            
                                            '''cookies = session.cookie_jar.filter_cookies(location)
                                            for key, cookie in cookies.items():
                                                headers['cookie'] += cookie.key +'='+cookie.value+';'
                                            '''
                                            async with session.get(BASE_URL+'api/v2/app/disambiguate',headers=headers) as res:
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
                                                                        await asyncio.sleep(2)
                                                                        i+=1
                                                        else:
                                                            url=BASE_URL+'api/v2/app/restart'
                                                            headers['content-type']='application/json'
                                                            print(headers)
                                                            #headers['x-csrf-token']='NXlRV0lFQWRKY1NuZ0d5SmpidmloTWJIbmNZYTZEYkRlPBQ/KwsMAy4FNSUiESAPMjAYGR4bKSIeEC9WRjxWCQ=='
                                                            #headers['cookie']='streamlit_session=MTcyNzU4OTQ1MHwzc3ZnYmJ3Q1VjQVpObG53OU1ndkdJejFWSWZZU0tBRUctQjY5c3dfWjdVaEVrcXE2aFhmenZaam1JRy11VklhVzdXRExIZDdCTEc4ZlBPNmE1UUZPV0NpTFBnWjFWbEswSWN6N0EzcHBNRDh6VmVwMUZLRzYtaGdtOXRZcVZIdm5iZHBHVUFFMzBVbnRUVDhYMmE1dnF5N2sxUlpzM2dJYUVKV1pQY3U2Z1h3aTltUEI0TklNNUN2MWc9PXzRNXhbLSr7v2HEbKkW7dG7SYhIAG8syrA6cT6PcVoTUg==;_streamlit_csrf=MTcyNzU4OTQ2MHxJbFZGVmtaaFIwcFBWRmRrYTFwdFdreFNWbHBhVWxab1UySnVRakpXYTNSeFkwaE9NazR6UWpST1JUQTlJZz09fMCqnUsraPXID4OUqUlNQzBliXqyC6OBcvo4p_uRHB3R'
                                                            req=requests.post(url,headers=headers)
                                                            print(req,url)
                                                            stop=False
                                                            i=0
                                                            while not stop:
                                                                url=BASE_URL+'api/v2/app/status'
                                                                req=requests.get(url,headers=headers)
                                                                if req.status_code<400:
                                                                    js=req.json()
                                                                    if js['status']!=5:
                                                                        await asyncio.sleep(15)
                                                                    else:
                                                                        stop=True
                                                                if i==10:
                                                                    stop=True
                                                                i+=1
                                                        async with session.get(location+'api/v2/app/context',headers=headers,allow_redirects=False) as res:
                                                            if res.status<400:
                                                                cookies = session.cookie_jar.filter_cookies(location)
                                                                for key, cookie in cookies.items():
                                                                    headers['cookie'] += cookie.key +'='+cookie.value+';'
                                                                async with session.get(BASE_URL+'api/v2/app/disambiguate',headers=headers) as res:
                                                                    if res.status<400:
                                                                        headers['x-csrf-token']=res.headers['x-csrf-token']
                                                                        url=BASE_URL+'api/v1/app/event/open'
                                                                        async with session.post(url,headers=headers) as res:
                                                                            url=BASE_URL+'api/v2/app/status'
                                                                            async with session.get(url,headers=headers) as res:
                                                                                print(res.status)
                                                                                await asyncio.sleep(60)
                                                else:
                                                    try:
                                                        await msg.delete()
                                                    except Exception as error:
                                                        print(error,3333)
                                                        pass
                    break
                        
    except Exception as error:
        RESULT=await getBasic(guild)
        print(error,112233)
        pass
    #11111

client.run(os.environ.get('botToken'))
