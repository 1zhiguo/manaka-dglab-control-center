"""FN010-RX Qt adapter. Device policy stays separate from transport and UI."""
from __future__ import annotations
import time
from copy import deepcopy
from PySide6.QtCore import Property, Signal, Slot
from manaka_devices.booboop import sanitize_profile, evaluate
from manaka_devices.booboop_ble import BooBoopBleBridge
from manaka_devices import audit
try:
    from .v4_integration import V4DeviceBackend
except ImportError:
    from v4_integration import V4DeviceBackend


class BooDeviceBackend(V4DeviceBackend):
    booProfileChanged=Signal()
    booStateChanged=Signal()

    def _init_device_support(self,saved,persist):
        super()._init_device_support(saved,persist)
        self.devicesChanged.connect(self.booStateChanged.emit)
        self.boo_ble=None
        self.boo_profile=sanitize_profile(saved.get("booboop_profile"))
        self.boo_enabled=False
        self.boo_connected=False
        self.boo_waiting=False
        self.boo_resume_after=0.
        self.boo_frame={"stretch":0,"vibration":0,"piston":None,"reason":"not-authorized"}
        self._last_boo_sync=0.

    def _ble_routes(self):
        return {**super()._ble_routes(),"booboop":self.boo_ble}

    def _ble_role_name(self,role):
        return "FN010-RX" if role=="booboop" else super()._ble_role_name(role)

    def _start_ble_companions(self):
        super()._start_ble_companions()
        self.boo_ble=BooBoopBleBridge(self._ble_messages)
        self.boo_ble.start()

    def _stop_ble_companions(self,timeout=4):
        self._stop_boo()
        if self.boo_ble:
            self.boo_ble.stop(timeout=timeout)
            self.boo_ble=None
        self.boo_connected=False
        super()._stop_ble_companions(timeout)

    def _prepare_extra_ble_selection(self,role):
        if role=="booboop":
            self._stop_boo()
            self.boo_connected=False

    def _handle_extra_ble_event(self,role,route,payload):
        if role!="booboop":return
        event=payload.get("event")
        if event=="connected":
            self.boo_connected=bool(route.connected)
            self._stop_boo()
        elif event=="output_timeout" and payload.get("reason")=="producer-stale":
            self.boo_waiting=True
            self.boo_resume_after=time.monotonic()
        elif event in {"error","disconnected"}:
            self.boo_connected=bool(route.connected)
            self._stop_boo()
        if event!="ble_status":
            self._log("FN010-RX · "+event+" · "+str(payload.get("detail","")))

    @Property("QVariantMap",notify=booProfileChanged)
    def booProfile(self):return deepcopy(self.boo_profile)

    @Property("QVariantList",notify=booStateChanged)
    def booDevices(self):return self._ble_choices(self.boo_ble)

    @Property(bool,notify=booStateChanged)
    def booConnected(self):return self.socket_protocol=="ble" and self.boo_connected

    @Property(bool,notify=booStateChanged)
    def booEnabled(self):return self.boo_enabled

    @Property(bool,notify=booStateChanged)
    def booConnecting(self):return self.socket_protocol=="ble" and self._ble_connecting(self.boo_ble)

    @Property(str,notify=booStateChanged)
    def booGamePiston(self):
        if not self.last_receive or not 0<=time.monotonic()-self.last_receive<.5:
            return self._device_text("等待游戏活塞数据","Waiting for game piston data")
        names={0:("关闭","Off"),1:("慢速","Slow"),2:("中速","Medium"),3:("快速","Fast")}
        mode=self.boo_frame.get("pistonEffective",self.boo_frame.get("piston"))
        label=self._device_text(*names.get(mode,("未知","Unknown")))
        prefix=self._device_text("游戏活塞：","Game piston: ")
        if self.boo_frame.get("pistonRandom"):
            return prefix+self._device_text("随机 → ","Random → ")+label
        return prefix+label

    @Property(str,notify=booStateChanged)
    def booStatus(self):
        if self.socket_protocol!="ble":
            return self._device_text("请在「设备与游戏」切换到蓝牙直连","Select direct Bluetooth in Setup")
        if self.demo_mode:
            return self._device_text("演示模式，不连接真实设备","Demo mode; no hardware connection")
        if not self.boo_ble:
            return self._device_text("等待蓝牙连接服务","Waiting for Bluetooth services")
        if not self.boo_connected:return self.boo_ble.detail
        if not self.boo_enabled:return self._device_text("握手就绪 · 停止指令已发送 · 等待手动启用","Handshake ready · stop commands sent · enable manually")
        if self.boo_waiting:return self._device_text("已启用 · 归零待机，等待新的游戏数据","Enabled · stopped standby; waiting for new game data")
        reasons={"piston-random-wait":("随机档实际速度未同步，请更新游戏遥测插件并重启游戏","Random speed unavailable; update telemetry and restart the game"),
                 "game-safety-idle":("游戏暂停或场景不可操作 · 停止","Game paused or not playable · stopped"),
                 "unknown-piston-mode":("活塞档位未知 · 停止","Unknown piston mode · stopped"),
                 "invalid-telemetry":("游戏数据无效 · 停止","Invalid telemetry · stopped"),
                 "action-off":("当前动作已配置关闭","Current action is configured off")}
        if self.boo_frame.get("reason") in reasons:
            return self._device_text(*reasons[self.boo_frame["reason"]])
        return self.booGamePiston

    @Property(int,notify=booStateChanged)
    def booStretch(self):return self.boo_frame["stretch"]

    @Property(int,notify=booStateChanged)
    def booVibration(self):return self.boo_frame["vibration"]

    @Property(str,notify=booStateChanged)
    def booSent(self):
        if not self.booConnected or not self.boo_ble:return "—"
        levels=self.boo_ble.sent_levels
        a,b=levels["A"],levels["B"]
        return self._device_text("最近写入的协议档位：","Last written protocol indices: ")+f"{a if a is not None else '—'} / {b if b is not None else '—'}"

    @Slot()
    def scanBooDevice(self):
        self._scan_ble_roles(("booboop",))

    @Slot()
    def toggleBooOutput(self):
        if self.boo_enabled:
            self._stop_boo()
        elif self.demo_mode:
            self._toast("FN010-RX",self._device_text("演示模式不发送输出","Demo mode does not send output"))
        elif self.socket_protocol!="ble" or not self.boo_connected or not self.boo_ble:
            self._toast("FN010-RX",self._device_text("请先切换蓝牙模式，并连接匹配的 FN010-RX","Select BLE mode and connect a matching FN010-RX first"))
        elif self.boo_profile["hard_cap"]==0:
            self._toast("FN010-RX",self._device_text("档位上限为 0，请先设置","The level cap is zero; configure it first"))
        else:
            self.boo_ble.clear_global_emergency_stop()
            self.boo_waiting=not bool(self.last_receive and 0<=time.monotonic()-self.last_receive<.5)
            self.boo_resume_after=time.monotonic() if self.boo_waiting else 0.
            self.boo_enabled=True
            if self.boo_waiting:self.boo_ble.emergency_stop()
            self._sync_extra_devices(force=True)
        self.devicesChanged.emit()

    def _stop_boo(self):
        self.boo_enabled=False
        self.boo_waiting=False
        self.boo_resume_after=0.
        self.boo_frame={**getattr(self,"boo_frame",{}),"stretch":0,"vibration":0,"reason":"not-authorized"}
        if self.boo_ble:self.boo_ble.emergency_stop()

    @Slot("QVariantMap",result=bool)
    def saveBooProfile(self,raw):
        if not isinstance(raw,dict):return False
        clean=sanitize_profile(raw)
        for key in ("hard_cap","slow","medium","fast","vibration_level"):
            value=raw.get(key)
            if type(value) is not int or value<0 or value>9 or (key!="hard_cap" and value>clean["hard_cap"]):
                self._toast("FN010-RX",self._device_text("请检查 0–9 档位及上限","Check indices 0–9 and the cap"))
                return False
        rules=raw.get("actions",{})
        if (type(raw.get("vibration_enabled")) is not bool or not isinstance(rules,dict) or len(rules)>1024
            or any(not isinstance(k,str) or not k or len(k)>128 or not isinstance(v,dict)
                   or v.get("mode") not in {"sync","level","off"} or type(v.get("level")) is not int
                   or not 0<=v["level"]<=clean["hard_cap"] for k,v in rules.items())):
            self._toast("FN010-RX",self._device_text("请检查动作规则与档位","Check action rules and levels"))
            return False
        try:
            if not self.demo_mode:self._device_persist({"booboop_profile":clean})
        except OSError as error:
            self._toast("FN010-RX",str(error))
            return False
        self._stop_boo()
        self.boo_profile=clean
        self.booProfileChanged.emit()
        self.devicesChanged.emit()
        self._toast("FN010-RX",self._device_text("设置已保存；重新启用后应用","Saved; re-enable output when ready"))
        return True

    @Slot()
    def emergencyStopAll(self):
        self._stop_boo()
        super().emergencyStopAll()

    def _sync_extra_devices(self,force=False):
        now=time.monotonic()
        if not force and now-self._last_boo_sync<.1:return
        self._last_boo_sync=now
        fresh=bool(not self.demo_mode and self.last_receive and 0<=now-self.last_receive<.5)
        if self.boo_enabled and not fresh and not self.boo_waiting:
            self.boo_waiting=True
            self.boo_resume_after=now
            if self.boo_ble:self.boo_ble.emergency_stop()
        if self.boo_waiting and fresh and self.last_receive>self.boo_resume_after:
            self.boo_waiting=False
        frame=evaluate(self.last_packet,self.boo_profile,fresh=fresh and not self.boo_waiting,
                       authorized=self.boo_enabled and self.boo_connected)
        changed=frame!=self.boo_frame
        self.boo_frame=frame
        if self.socket_protocol=="ble" and self.boo_ble and self.boo_enabled and not self.boo_waiting:
            self.boo_ble.update_levels(frame["stretch"],frame["vibration"],self.boo_profile["hard_cap"])
            self.boo_ble.set_auto_enabled(True)
        if changed:
            audit.record("booboop.plan",selected_mode=frame["piston"],effective_mode=frame["pistonEffective"],
                         random=frame["pistonRandom"],stretch=frame["stretch"],vibration=frame["vibration"],
                         enabled=self.boo_enabled,connected=self.boo_connected,reason=frame["reason"])
            self.devicesChanged.emit()
