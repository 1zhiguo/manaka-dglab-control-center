"""Pure Manaka piston/action -> FN010-RX protocol-index policy."""
from __future__ import annotations
import math

DEFAULT={"hard_cap":4,"slow":1,"medium":2,"fast":3,"vibration_enabled":False,"vibration_level":1,"actions":{}}


def index(value,cap=9):
    if type(value) not in (int,float) or not math.isfinite(value):return 0
    return int(max(0,min(9,cap,value)))


def sanitize_profile(raw):
    raw=raw if isinstance(raw,dict) else {}
    result={**DEFAULT,"actions":{}}
    result["hard_cap"]=index(raw.get("hard_cap",4))
    for key in ("slow","medium","fast","vibration_level"):
        result[key]=index(raw.get(key,DEFAULT[key]),result["hard_cap"])
    result["vibration_enabled"]=raw.get("vibration_enabled") is True
    rules=raw.get("actions",{})
    if isinstance(rules,dict):
        for action,rule in list(rules.items())[:1024]:
            if not isinstance(action,str) or not action or len(action)>128 or not isinstance(rule,dict):continue
            if rule.get("mode") not in {"sync","level","off"}:continue
            result["actions"][action]={"mode":rule["mode"],"level":index(rule.get("level",1),result["hard_cap"])}
    return result


def evaluate(packet,profile,*,fresh,authorized):
    selected=packet.get("piston")
    random=selected==4 or packet.get("pistonRandom") is True
    effective=packet.get("pistonEffective") if random else selected
    result={"stretch":0,"vibration":0,"piston":selected,"pistonEffective":effective,
            "pistonRandom":random,"reason":""}
    def blocked(reason):
        return {**result,"reason":reason}
    if not authorized:return blocked("not-authorized")
    if not fresh:return blocked("telemetry-stale")
    if packet.get("paused") or packet.get("systemMenuOpen") or packet.get("gameOver") or str(packet.get("stage","None")) in {"","None"}:
        return blocked("game-safety-idle")
    try:
        scales=[float(packet.get(k,1)) for k in ("timeScale","managedTimeScale")]
        if any(not math.isfinite(v) or v<=.001 for v in scales):return blocked("game-safety-idle")
    except (ValueError,TypeError):return blocked("invalid-telemetry")
    if type(selected) is not int or selected not in (0,1,2,3,4):return blocked("unknown-piston-mode")
    if selected==0:return blocked("piston-off")
    mode=effective
    if type(mode) is not int or mode not in (0,1,2,3):
        return blocked("piston-random-wait" if random else "unknown-piston-mode")
    if mode==0:return blocked("piston-off")
    level=profile[{1:"slow",2:"medium",3:"fast"}[mode]]
    rule=profile["actions"].get(str(packet.get("action","")),{"mode":"sync"})
    if rule["mode"]=="off":return blocked("action-off")
    if rule["mode"]=="level":level=rule["level"]
    result["stretch"]=index(level,profile["hard_cap"])
    if profile["vibration_enabled"]:
        result["vibration"]=index(profile["vibration_level"],profile["hard_cap"])
    return result
