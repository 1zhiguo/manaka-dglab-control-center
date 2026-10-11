import json, asyncio, threading, PySimpleGUI as sg, websockets

# ── copy the 3 presets from your JS exactly ─────────────────────────────
WAVES = {
    "1": '["0A0A0A0A00000000","0A0A0A0A0A0A0A0A","0A0A0A0A14141414",'
         '"0A0A0A0A1E1E1E1E","0A0A0A0A28282828","0A0A0A0A32323232",'
         '"0A0A0A0A3C3C3C3C","0A0A0A0A46464646","0A0A0A0A50505050",'
         '"0A0A0A0A5A5A5A5A","0A0A0A0A64646464"]',
    "2": '["0A0A0A0A00000000","0D0D0D0D0F0F0F0F","101010101E1E1E1E",'
         '"1313131332323232","1616161641414141","1A1A1A1A50505050",'
         '"1D1D1D1D64646464","202020205A5A5A5A","2323232350505050",'
         '"262626264B4B4B4B","2A2A2A2A41414141"]',
    "3": '["4A4A4A4A64646464","4545454564646464","4040404064646464",'
         '"3B3B3B3B64646464","3636363664646464","3232323264646464",'
         '"2D2D2D2D64646464","2828282864646464","2323232364646464",'
         '"1E1E1E1E64646464","1A1A1A1A64646464"]'
}
# ───────────────────────────────────────────────────────────────────────

print("Enter WebSocket URL (e.g. ws://127.0.0.1:9999/<browserId>)")
URI = input("WS URL: ").strip()

layout = [
    [sg.Text("DG-LAB Controller", justification="center", expand_x=True)],
    [sg.Multiline(size=(60,10), key="-LOG-", disabled=True)],
    [sg.Frame("A channel", [
        [sg.Button("▲", key="incA"), sg.Button("▼", key="decA"),
         sg.Button("=", key="setA"), sg.Slider((0,200), orientation="h",
         key="sliderA", expand_x=True)] ]),
     sg.Frame("B channel", [
        [sg.Button("▲", key="incB"), sg.Button("▼", key="decB"),
         sg.Button("=", key="setB"), sg.Slider((0,200), orientation="h",
         key="sliderB", expand_x=True)] ])],
    [sg.Text("Pulse  "), sg.Combo(["A","B"], key="pChan", size=(2,1)),
     sg.Combo(["1","2","3"], key="pWave", size=(3,1)),
     sg.Input("5", size=(3,1), key="pSec"), sg.Button("Send pulse")],
    [sg.Button("Exit")]
]
win = sg.Window("DG-LAB", layout, finalize=True)

def log(*a): win["-LOG-"].print(*a)

async def ws_worker():
    ws = await websockets.connect(URI)
    hello = json.loads(await ws.recv())
    me, phone = hello["clientId"], None
    log("me =", me)

    async def recv():
        nonlocal phone
        async for raw in ws:
            try:
                pkt = json.loads(raw); log(pkt)
                if pkt.get("type")=="bind" and pkt.get("message")=="200" and pkt["clientId"]==me:
                    phone = pkt["targetId"]; log("phone =", phone)
            except json.JSONDecodeError: log(raw)
    asyncio.create_task(recv())

    def wrap(m): return json.dumps({"type":"msg","clientId":me,"targetId":phone,"message":m})

    while True:
        ev, val = await asyncio.to_thread(win.read, timeout=100)
        if ev in (None,"Exit"): break
        if not phone:
            sg.popup("Waiting for phone bind (message 200)…"); continue

        if ev=="incA": await ws.send(wrap(f"strength-1+1+{val['sliderA']}"))
        if ev=="decA": await ws.send(wrap(f"strength-1+0+{val['sliderA']}"))
        if ev=="setA": await ws.send(wrap(f"strength-1+2+{val['sliderA']}"))
        if ev=="incB": await ws.send(wrap(f"strength-2+1+{val['sliderB']}"))
        if ev=="decB": await ws.send(wrap(f"strength-2+0+{val['sliderB']}"))
        if ev=="setB": await ws.send(wrap(f"strength-2+2+{val['sliderB']}"))
        if ev=="Send pulse":
            ch = val["pChan"]; body = {"type":"clientMsg","clientId":me,"targetId":phone,
                                       "channel":ch,"time":int(val["pSec"]),
                                       "message":f"{ch}:{WAVES[val['pWave']]}"}
            await ws.send(json.dumps(body))
    await ws.close()
    win.close()

threading.Thread(target=lambda: asyncio.run(ws_worker()), daemon=True).start()
win.read_close()
