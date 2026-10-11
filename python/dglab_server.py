"""
dglab_server_bind.py  –  DG-LAB back-end with strength + pulse support
requires:  websockets==12.*   qrcode[pil]
run:       python dglab_server_bind.py
"""

import asyncio, json, socket, uuid, qrcode, websockets
from websockets.server import WebSocketServerProtocol

# ───────── configuration ─────────
PORT              = 9999
HEARTBEAT_SECONDS = 60
PUNISH_LEN        = 5          # default pulse seconds
PUNISH_RATE       = 1          # msgs per second

# runtime maps
clients:   dict[str, WebSocketServerProtocol] = {}
relations: dict[str, str] = {}
pending:    dict[tuple, WebSocketServerProtocol] = {}
timers:     dict[str, asyncio.Task] = {}          # "<client>-<ch>" → task


# ───────── helpers ─────────
def lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        sock.close()

def show_qr(ip, browser_id):
    url = ("https://www.dungeon-lab.com/app-download.php"
           f"#DGLAB-SOCKET#ws://{ip}:{PORT}/{browser_id}")
    qrcode.make(url).save("dglab_socket_qr.png")
    print("\n📱  Scan dglab_socket_qr.png")
    print("🔗 ", url, "\n")

async def jsend(ws, obj):
    await ws.send(json.dumps(obj, ensure_ascii=False))

async def heartbeats():
    while True:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        for cid, ws in list(clients.items()):
            await jsend(ws, {"type":"heartbeat",
                             "clientId":cid,
                             "targetId":relations.get(cid,""),
                             "message":"200"})


# ───────── pulse spammer ─────────
async def spam_pulse(src_ws, tgt_ws, send_obj, total, interval, key):
    try:
        await jsend(tgt_ws, send_obj)
        total -= 1
        while total > 0:
            await asyncio.sleep(interval)
            await jsend(tgt_ws, send_obj)
            total -= 1
        await jsend(src_ws, "发送完毕")
    finally:
        timers.pop(key, None)


# ───────── connection handler ─────────
async def handler(ws: WebSocketServerProtocol):
    cid = str(uuid.uuid4())
    clients[cid] = ws
    print("🌐  NEW:", cid)

    await jsend(ws, {"type":"bind","clientId":cid,
                     "targetId":"","message":"targetId"})

    if len(clients) == 1:
        show_qr(lan_ip(), cid)

    if not hasattr(handler, "hb_task"):
        handler.hb_task = asyncio.create_task(heartbeats())

    try:
        async for raw in ws:
            pkt = json.loads(raw)
            t, me, peer, msg = pkt.get("type"), pkt.get("clientId"), pkt.get("targetId"), pkt.get("message")
            print("📨 RAW:", pkt)

            # ---------- full-field validation ----------
            if not all([t, me, peer, msg]):
                await jsend(ws, {"type":"error","clientId":me,"targetId":peer,"message":"405-empty"})
                continue

            # ---------- phone → bind request ----------
            if t == "bind" and msg == "DGLAB":
                if me not in clients or peer not in clients:
                    pending[(me, peer)] = ws
                    await jsend(ws, {"type":"bind","clientId":me,"targetId":peer,"message":"202-pending"})
                    continue
                if any(x in relations or x in relations.values() for x in (me, peer)):
                    await jsend(ws, {"type":"bind","clientId":me,"targetId":peer,"message":"400"})
                    continue
                relations[me] = peer
                relations[peer] = me
                ok = {"type":"bind","clientId":me,"targetId":peer,"message":"200"}
                await jsend(clients[me], ok); await jsend(clients[peer], ok)
                continue

            # ---------- strength / other msg ----------
            if t == "msg":
                if relations.get(me) != peer or peer not in clients:
                    await jsend(ws, {"type":"bind","clientId":me,"targetId":peer,"message":"402"})
                    continue
                await jsend(clients[peer], pkt)
                continue

            # ---------- pulse queue ("clientMsg") ----------
            if t == "clientMsg":
                chan = pkt.get("channel")
                if relations.get(me) != peer or peer not in clients:
                    await jsend(ws, {"type":"bind","clientId":me,"targetId":peer,"message":"402"}); continue
                if not chan:
                    await jsend(ws, {"type":"error","clientId":me,"targetId":peer,"message":"406-channel is empty"}); continue
                runtime  = pkt.get("time", PUNISH_LEN)
                total    = runtime * PUNISH_RATE
                interval = 1 / PUNISH_RATE
                tgt_ws   = clients[peer]
                send_obj = {"type":"msg","clientId":me,"targetId":peer,"message":"pulse-" + msg}
                key      = f"{me}-{chan}"

                # cancel existing spammer + clear queue
                if key in timers:
                    timers[key].cancel()
                    reset = "1" if chan == "A" else "2"
                    await jsend(tgt_ws, {"type":"msg","clientId":me,"targetId":peer,"message":"clear-" + reset})
                    await asyncio.sleep(0.15)

                timers[key] = asyncio.create_task(spam_pulse(ws, tgt_ws, send_obj, total, interval, key))
                continue

            # ---------- late browser arrives ----------
            if (peer, me) in pending and t == "bind" and msg == "DGLAB":
                pending.pop((peer, me), None)
                relations[me] = peer; relations[peer] = me
                ok = {"type":"bind","clientId":peer,"targetId":me,"message":"200"}
                await jsend(clients[peer], ok); await jsend(ws, ok)

    finally:
        print("❌ CLOSE:", cid)
        for k, task in list(timers.items()):
            if k.startswith(f"{cid}-"):
                task.cancel(); timers.pop(k, None)
        partner = relations.pop(cid, None)
        if partner and partner in clients:
            await jsend(clients[partner], {"type":"break","clientId":partner,"targetId":cid,"message":"209"})
            await clients[partner].close(); relations.pop(partner, None)
        clients.pop(cid, None)


# ───────── server runner ─────────
async def main():
    async with websockets.serve(handler, "", PORT):
        ip = lan_ip()
        print(f"🚀  WS listening on port {PORT}")
        print(f"复制以下地址：")
        print(f"ws://{ip}:{PORT}/\n")
        print("这边这个Terminal不要关闭，否则服务器会关闭")
        print("新打开一个Terminal，按以下顺序执行：")
        print("> cd scripts")
        print("> python .\heart_hud.py <刚刚复制的服务器地址>")
        print("然后看那边的提示")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
