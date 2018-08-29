#!/usr/bin/env python3

import asyncio
import collections
import getpass
import json
import mimetypes
import os
import os.path
import threading
from contextlib import asynccontextmanager

import aiohttp
from aiohttp import web

import aiofiles

INSTAGRAM_HEADERS = {
    'user-agent':
    "Instagram 10.3.2 (iPhone7,2; iPhone OS 9_3_3; en_US; en-US; scale=2.00; 750x1334) AppleWebKit/420+",
}
TIMELINE_URL = "https://i.instagram.com/api/v1/feed/timeline/"
BUFFER_LENGTH = 25
SLEEP_SECONDS = 120
FIELDS_TO_DROP = ['image url']

routes = web.RouteTableDef()


def dict_without(d, *keys_to_drop):
    return {k: d[k] for k in d if k not in keys_to_drop}


@routes.get('/image/{image_id}')
async def get_image(request):
    image_id = request.match_info['image_id']
    file_name = f"{image_id}.jpeg"

    ringbuffer = request.app['ringbuffer']
    for post in ringbuffer:
        if post['id'] == image_id:
            break
    else:
        return web.Response(
            body=f'Image <{image_id}> does not exist', status=404)

    image_path = os.path.join("images", file_name)
    async with aiofiles.open(image_path, "rb") as f:
        return web.Response(
            body=await f.read(),
            headers={"Content-type": mimetypes.guess_type(image_path)[0]})


@routes.get('/feed')
async def get_feed(request):
    return web.json_response([
        dict_without(post, *FIELDS_TO_DROP)
        for post in request.app['ringbuffer']
    ])


@routes.get('/')
async def get_index(request):
    return aiohttp.web.HTTPFound('/index.html')


def init_webapp():
    credential = ask_for_credentials() if not get_credentials() \
        else get_credentials()

    ringbuffer = RingBuffer(maxlen=BUFFER_LENGTH)
    t = threading.Thread(
        target=worker, args=[ringbuffer, credential], daemon=True)
    t.start()

    print("Waiting for ringbuffer to be populated...")
    while not ringbuffer:
        pass

    app = web.Application()
    app['ringbuffer'] = ringbuffer
    routes.static('/', "static")
    app.add_routes(routes)
    return app


class RingBuffer(collections.deque):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def push(self, item):
        if len(self) == self.maxlen:
            expunged_value = self[0]
        else:
            expunged_value = None
        self.append(item)
        return expunged_value


def get_credentials():
    if not os.path.exists('credential.json'):
        return
    try:
        with open('credential.json') as json_data:
            credential = json.load(json_data)
            return credential
    except FileNotFoundError:
        print("credential.json file not found in current directory. Exiting.")
        exit()


def is_ad(item):
    return "ad_action" in item or "injected" in item


def decode_feed_item(item):
    if is_ad(item):
        return None
    try:
        return {
            'username': item['user']['username'],
            'full name': item['user']['full_name'],
            'id': item['id'],
            'caption': item['caption'].get('text', ''),
            'image url': item['image_versions2']['candidates'][0]['url'],
            'taken at': item['taken_at'],
        }
    except (KeyError, AttributeError) as e:
        return None


async def fetch_news_feed(session):
    res = await session.get(TIMELINE_URL, headers=INSTAGRAM_HEADERS)
    if res.status != 200:
        print(f"ERROR: got {res.status} when fetching!")
        raise Exception
    res = await res.json()
    return list(
        filter(lambda i: i is not None,
               [decode_feed_item(item) for item in res['items']]))


def post_filename(post):
    return f'images/{post["id"]}.jpeg'


async def save_image(post, session):
    if not os.path.exists('images'):
        os.makedirs('images')

    res = await session.get(post['image url'])
    async with aiofiles.open(post_filename(post), 'wb') as f:
        async for chunk in res.content.iter_chunked(1024):
            if chunk:
                await f.write(chunk)


def save_credentials(credential, permission):
    if not permission:
        return
    with open('credential.json', 'w') as _file:
        json.dump(credential, _file)


async def handle_2factor(session, login_response, username):
    identifier = login_response['two_factor_info']['two_factor_identifier']
    verification_code = input('2FA Verification Code: ')
    verification_data = {
        'username': username,
        'verificationCode': verification_code,
        'identifier': identifier
    }
    two_factor_response = await (await session.post(
        'https://www.instagram.com/accounts/login/ajax/two_factor/',
        data=verification_data,
        allow_redirects=True)).json()
    if not two_factor_response['authenticated']:
        raise Exception(two_factor_response)


@asynccontextmanager
async def login_session(credential):
    async with aiohttp.ClientSession(
            headers={'Referer': 'https://www.instagram.com/'}) as session:
        req = await session.get('https://www.instagram.com/')
        login_response = await (await session.post(
            'https://www.instagram.com/accounts/login/ajax/',
            data=credential,
            allow_redirects=True,
            headers={'X-CSRFToken': req.cookies['csrftoken'].value})).json()
        if login_response.get('two_factor_required', None):
            await handle_2factor(session, login_response,
                                 credential['username'])

        yield session


def ask_for_credentials():
    user, pwd = "", ""
    while True:
        user = input('Username: ')
        pwd = getpass.getpass(prompt='Password: ')
        session, res = get_login_session({"username": user, "password": pwd})
        if res['authenticated']:
            break
        if not res['authenticated']:
            print("Bad username or password")
        if res['status'] == 'fail':
            print(res['message'])
            exit()

    permission = input("save credentials(y/N)?: ")
    credential = {"username": user, "password": pwd}
    save_credentials(credential, permission == 'y')
    return credential


def delete_image(post):
    if not os.path.isdir("images"):
        return
    os.remove(post_filename(post))


async def handle_new_post(ringbuffer, post, session):
    if not post in ringbuffer:
        print(f"Found new image file {post_filename(post)}")
        await save_image(post=post, session=session)
        maybe_expunged = ringbuffer.push(post)
        if maybe_expunged:
            print(f"Expunged {post_filename(maybe_expunged)}")
            delete_image(maybe_expunged)


async def wait_for_new_posts(session, ringbuffer):
    while True:
        print("Fetching feed...")
        for post in await fetch_news_feed(session):
            await handle_new_post(ringbuffer, post, session)
        print(f"Done fetching feed. Sleeping for {SLEEP_SECONDS}s.")
        await asyncio.sleep(SLEEP_SECONDS)


async def do_work(ringbuffer, credentials):
    async with login_session(credentials) as session:
        await wait_for_new_posts(session, ringbuffer)


def worker(ringbuffer, credentials):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(do_work(ringbuffer, credentials))


def main():
    web.run_app(init_webapp())


if __name__ == '__main__':
    main()
