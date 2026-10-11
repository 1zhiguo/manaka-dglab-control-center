"""
pc_controller.py  –  console helper (robust against non-JSON frames)

Run:  python pc_controller.py ws://<ip>:9999/<browserId>
"""

import asyncio, json, re, sys, websockets

URI = sys.argv[1]

WAVES = {
    "1": '["0A0A0A0A00000000","0A0A0A0A0A0A0A0A","0A0A0A0A14141414","0A0A0A0A1E1E1E1E","0A0A0A0A28282828","0A0A0A0A32323232","0A0A0A0A3C3C3C3C","0A0A0A0A46464646","0A0A0A0A50505050","0A0A0A0A5A5A5A5A","0A0A0A0A64646464"]',
    "2": '["0A0A0A0A00000000","0D0D0D0D0F0F0F0F","101010101E1E1E1E","1313131332323232","1616161641414141","1A1A1A1A50505050","1D1D1D1D64646464","202020205A5A5A5A","2323232350505050","262626264B4B4B4B","2A2A2A2A41414141"]',
    "3": '["4A4A4A4A64646464","4545454564646464","4040404064646464","3B3B3B3B64646464","3636363664646464","3232323264646464","2D2D2D2D64646464","2828282864646464","2323232364646464","1E1E1E1E64646464","1A1A1A1A64646464"]'
}

def str_msg(ch, mode, val): return f"strength-{ch}+{mode}+{val}"
def wrap(cid, tid, msg):   return json.dumps({"type":"msg","clientId":cid,"targetId":tid,"message":msg})
def wrap_clear(cid, tid, ch): return json.dumps({"type":"msg","clientId":cid,"targetId":tid,"message":"clear-"+("1" if ch=="A" else "2")})
def wrap_pulse(cid, tid, ch, preset, secs):
    return json.dumps({"type":"clientMsg","clientId":cid,"targetId":tid,
                       "channel":ch,"time":secs,"message":f"{ch}:{WAVES[preset]}"})

HELP = """\
incA/decA/setA N   | A-channel ± or =
incB/decB/setB N   | B-channel
clearA / clearB    | flush queue
pulseA P S         | preset 1-3 for S sec
pulseB P S
:json {...}        | raw packet
:q                 | quit
"""

async def main():
    async with websockets.connect(URI) as ws:
        hello = json.loads(await ws.recv())
        my_id, phone_id = hello["clientId"], None
        print("✅  PC clientId:", my_id)
        print(HELP)

        async def listener():
            nonlocal phone_id
            async for raw in ws:
                try:
                    pkt = json.loads(raw)
                    print("📨", pkt)
                    if isinstance(pkt, dict) and pkt.get("type")=="bind" \
                       and pkt.get("message")=="200" and pkt["clientId"]==my_id:
                        phone_id = pkt["targetId"]
                        print("🤝  Bound to phoneId:", phone_id)
                except json.JSONDecodeError:
                    # plain text frame (e.g., "发送完毕")
                    print("📨", raw)
        asyncio.create_task(listener())

        while True:
            cmd = await asyncio.to_thread(lambda: input("> ").strip())
            if cmd in (":q","quit","exit"): break
            if cmd.startswith(":json"): await ws.send(cmd[5:].strip()); continue
            if not phone_id:
                print("⏳  not bound yet"); continue

            m = re.fullmatch(r"(inc|dec|set)(A|B)\s+(\d{1,3})", cmd)
            if m:
                op,ch,val=m.group(1),m.group(2),int(m.group(3))
                if not 0<=val<=200: print("0-200 only"); continue
                chan = 1 if ch=="A" else 2
                mode = {"inc":1,"dec":0,"set":2}[op]
                await ws.send(wrap(my_id, phone_id, str_msg(chan,mode,val))); continue

            if cmd in ("clearA","clearB"):
                await ws.send(wrap_clear(my_id, phone_id, "A" if cmd=="clearA" else "B")); continue

            m = re.fullmatch(r"pulse([AB])\s+([123])\s+(\d+)", cmd)
            if m:
                ch,preset,secs=m.group(1),m.group(2),int(m.group(3))
                await ws.send(wrap_pulse(my_id, phone_id, ch, preset, secs)); continue

            print("❓  unknown command")

asyncio.run(main())
