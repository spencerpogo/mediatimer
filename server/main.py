from aiohttp import web, WSMsgType
import asyncio
import timer

app = web.Application()
routes = web.RouteTableDef()
routes.static("/static", "./static")

app.timer = None
app.ws_clients = set()


@routes.get("/")
async def index(request):
    return web.FileResponse('./static/index.html')


async def get_status():
    if app.timer:
        return {
            'running': app.timer.running,
            'duration': app.timer.duration,
            'remaining': app.timer.remaining
        }
    else:
        return {
            'running': False,
            'duration': 0,
            'remaining': 0
        }


@routes.get("/api/status")
async def status(req):
    return web.json_response({
        **(await get_status()),
        "clients": list(app.ws_clients)
    })


async def get_data(req):
    try:
        return await req.json()
    except:
        return await req.post()


@routes.post("/api/set")
async def set_route(req):
    if app.timer and app.timer.running:
        return web.json_response({
            'error': 'Please stop timer first'
        })
    data = await get_data(req)
    try:
        sec = int(data.get('sec'))
    except:
        return web.json_response({
            'error': "Invalid time amount"
        })
    app.timer = timer.Timer(sec)
    return web.json_response({'success': True})


@routes.post("/api/start")
async def start(req):
    if not app.timer:
        return web.json_response({
            'error': "Set timer first"
        })
    if not app.timer.running:
        app.timer.start()
    return web.json_response({
        'success': True
    })


@routes.post("/api/stop")
async def stop(req):
    if not app.timer:
        return web.json_response({
            'error': "Set timer first"
        })
    if app.timer.running:
        app.timer.stop()
    return web.json_response({
        'success': True
    })


@routes.get("/api/status/ws")
async def status_ws(request):
    WS_TIMEOUT = 3

    async def cleanup_checker(ws):
        """Cancels the connection after WS_TIMEOUT seconds (unless cancelled)"""
        try:
            await asyncio.sleep(WS_TIMEOUT)
            print("websocket timed out")
            ws_main_task.cancel()
        except asyncio.CancelledError:
            pass
    
    async def ws_main():
        print("new ws")
        try:
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            name = None
            cleanup_task = None

            async def reset_cleanup():
                """Resets the cleanup checker function by cancelling it if started and starting it"""
                nonlocal cleanup_task
                if cleanup_task:
                    cleanup_task.cancel()
                cleanup_task = asyncio.create_task(cleanup_checker(ws))
            
            await reset_cleanup()
            #print("prepared")
            
            async for msg in ws:
                if msg.type is WSMsgType.CLOSE or msg.type is WSMsgType.CLOSED:
                    return
                elif msg.type is WSMsgType.TEXT:
                    #print("Text frame:", msg.data)
                    if msg.data.startswith("id "):
                        newname = msg.data[3:].strip()
                        if newname:
                            # If already identified
                            if name is not None:
                                try:
                                    # no longer store this client name
                                    app.ws_clients.remove(name)
                                except KeyError:
                                    pass
                            name = newname
                            # store new client name
                            app.ws_clients.add(name)
                            await reset_cleanup()
                elif msg.type is WSMsgType.BINARY:
                    # b"c" stands for check
                    # its 1 byte so as to not waste bandwidth
                    if msg.data == b"c":
                        if name is not None:
                            await reset_cleanup()
                            await ws.send_json(await get_status())
        except asyncio.CancelledError:
            pass
        finally:
            try:
                app.ws_clients.remove(name)
            except KeyError:
                pass
            await ws.close()
            print("Websocket cleaned up")
    
    ws_main_task = asyncio.create_task(ws_main())
    await ws_main_task


app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)
