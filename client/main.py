import websockets
import asyncio
from time import time
import datetime
import winsound
import traceback
import sys
import subprocess
import json


async def play_alert(data):
    fname = data["file"]
    winsound.PlaySound(fname,
                        winsound.SND_FILENAME | winsound.SND_ASYNC)


async def run_cmd(data):
    cmd = data["cmd"]
    subprocess.Popen(cmd.split(" "))


ALERT_FUNCS = {
    "play": (play_alert, (lambda d: "Must include file key in alert" if "file" not in d else None)),
    "run": (run_cmd, (lambda d: "Must include cmd key in alert" if "cmd" not in d else None))
}

def verify_alert(d):
    if type(d) != dict:
        raise TypeError("Alert should be dict")

    if "type" not in d:
        raise KeyError("Alert requires type key")
    alert_type = d["type"]

    if alert_type not in ALERT_FUNCS:
        raise KeyError(f"Invalid alert type {alert_type!r}")

    error = ALERT_FUNCS[alert_type][1](d)
    if error:
        raise ValueError(error)


def is_digit(n):
    try:
        int(n)
        return True
    except ValueError:
        return False


def get_config():
    conf_file = "config.json"
    if len(sys.argv) > 1:
        conf_file = sys.argv[1]

    with open(conf_file, "r") as f:
        data = f.read()

    config = json.loads(data)
    if type(config) != dict:
        raise ValueError("config should be a dict")

    if "ws_url" not in config:
        raise ValueError("No ws_url key in config")
    ws_url = str(config['ws_url'])

    if "alerts" not in config:
        raise ValueError("No alerts in config")
    alerts_data = config["alerts"]
    if type(alerts_data) != dict or not all([is_digit(k) for k in alerts_data.keys()]):
        raise ValueError("Alerts should be a dict like {\"60\": \"filename.mp3\"}")
    alerts = {}
    for k, v in alerts_data.items():
        alerts[int(k)] = v
    # Sort the alerts based on their time
    alerts = {k: v for k, v in sorted(alerts.items(), key=(lambda item: item[0]))}

    for v in alerts.values():
        verify_alert(v)

    if "name" not in config:
        raise ValueError("No name key in config")
    name = str(config['name'])

    return ws_url, alerts, name

last_alert = None


async def process_alerts(t, alerts):
    global last_alert
    #print("processing", t)
    # alerts are assumed to be in least to greatest order
    for atime, data in alerts.items():
        if t <= atime and (last_alert is None or last_alert > atime):
            last_alert = atime

            await ALERT_FUNCS[data["type"]][0](data)
            return


async def countdown(msg, sec):
    for s in reversed(range(1, sec + 1)):
        print("\r", msg, f" in {s}...", sep="")
        await asyncio.sleep(1)
    print(msg, "...", sep="")


def format_time(secs, hour=False):
    """Formats seconds into a string. If hour is False it will only contain the hour if it is not 0. """
    secs = round(secs)
    # timedelta handles negatives weirdly (e.g. -2 sec becomes -1 day, 23:59:58), so just treat it as
    #  positive and add negative sign if negative
    prefix = '-' if secs < 0 else ''
    ts = str(datetime.timedelta(seconds=abs(secs)))
    if not hour and ts[:2] == '0:':
        return prefix + ts[2:]
    else:
        return prefix + ts


async def get_ws_data(ws_url, name):
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                await ws.send("id " + name)
                while True:
                    await ws.send(b"c")
                    data = json.loads(await ws.recv())
                    t = data["remaining"]
                    running = data["running"]
                    yield t, running
        except websockets.ConnectionClosed:
            print("Lost connection to server")
        except json.JSONDecodeError as e:
            print(f"Got invalid data from server: {e}")
        except KeyError as e:
            print(f"Invalid data: missing key {e}")
        except (KeyboardInterrupt, GeneratorExit):
            raise
        except:
            traceback.print_exc()
        await countdown("Retrying", 3)


async def main():
    global last_alert
    ws_url, alerts, name = get_config()
    last_time = None
    CHECK_INTERVAL = 1
    while True:
        try:
            last_check = time()
            async for t, running in get_ws_data(ws_url, name):

                # When the time increases
                if last_time is not None and t > last_time:
                    # Reset the alerts
                    last_alert = None

                last_time = t

                status = "Running" if running else "Paused"
                print(
                    "\r", # go to beginning and clear line
                    status,
                    " ",
                    format_time(t), # print time
                    sep="", end="", flush=True)

                if running:
                    await process_alerts(t, alerts)

                since_last = (time() - last_check)
                to_wait = CHECK_INTERVAL - since_last
                if to_wait > 0:
                    await asyncio.sleep(to_wait)

                last_check = time()
        except:
            traceback.print_exc()
        await countdown("Retrying", 3)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
