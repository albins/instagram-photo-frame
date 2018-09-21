#!/usr/bin/env python3
# -*- coding: future_fstrings -*-
import asyncio
import getpass
import json
import os
import os.path
import pickle

import aiofiles
import aiohttp
from async_generator import async_generator, asynccontextmanager, yield_

from shared import read_or_create_ringbuffer

INSTAGRAM_HEADERS = {
    'user-agent':
    "Instagram 10.3.2 (iPhone7,2; iPhone OS 9_3_3; en_US; en-US; scale=2.00; 750x1334) AppleWebKit/420+",
}
TIMELINE_URL = "https://i.instagram.com/api/v1/feed/timeline/"
BUFFER_LENGTH = 25


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
@async_generator
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

        await yield_(session)


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


async def main():
    credentials = ask_for_credentials() if not get_credentials() \
        else get_credentials()

    ringbuffer = read_or_create_ringbuffer(buffer_length=BUFFER_LENGTH)

    async with login_session(credentials) as session:
        print("Fetching feed...")
        for post in await fetch_news_feed(session):
            await handle_new_post(ringbuffer, post, session)

    with open("ringbuffer.pickle", "wb") as fp:
        fp.write(pickle.dumps(ringbuffer))
    print("Dumped {} lines of ringbuffer".format(len(ringbuffer)))


if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
