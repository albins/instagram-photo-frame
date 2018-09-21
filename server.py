#!/usr/bin/env python3
# -*- coding: future_fstrings -*-
import mimetypes
import os.path

import aiofiles
import aiohttp
from aiohttp import web

from shared import dict_without, read_or_create_ringbuffer

FIELDS_TO_DROP = ['image url']

routes = web.RouteTableDef()


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
    ringbuffer = read_or_create_ringbuffer(25)
    app = web.Application()
    app['ringbuffer'] = ringbuffer
    routes.static('/', "static")
    app.add_routes(routes)
    return app


def main():
    web.run_app(init_webapp())


if __name__ == '__main__':
    main()
