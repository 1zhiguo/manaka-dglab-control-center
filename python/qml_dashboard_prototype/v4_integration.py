"""Qt adapter for Manaka's independent V4 Coyote and Opossum routes.

No automatic authorization, no physical test pulses, no persisted selection.
The existing V3 implementation remains the default electrical transport.
"""
from __future__ import annotations

import queue
import time
from copy import deepcopy

from PySide6.QtCore import QObject, Property, Signal, Slot

from manaka_dglab_bridge import DEFAULT_PORT, DGLabBridge
from manaka_devices.dglab_v4_hub import DGLabV4Hub
from manaka_devices.ovc import OvcPlanner, sanitize_profile, waveform_catalog, clean_points, step_strength
from manaka_waveforms import action_label, action_style
from manaka_devices.hud_settings import sanitize_settings
from manaka_devices import audit


REASONS = {
    "not-authorized": ("等待手动启用", "Enable output explicitly"),
    "waiting-for-game": ("已启用 · 等待游戏数据 · 输出为 0", "Enabled · waiting for game data · zero output"),
    "v4-required": ("当前使用 V3，负鼠不可用；请在「设备与游戏」切换为 V4", "Opossum is unavailable in V3; select V4 in Setup"),
    "telemetry-stale": ("等待新鲜游戏数据", "Waiting for fresh game data"),
    "producer-stale": ("输出刷新中断，已停止", "Output updates stalled; stopped"),
    "response-timeout": ("手机 App 输出确认超时，已停止", "App output confirmation timed out; stopped"),
    "game-safety-idle": ("游戏暂停或场景不可操作", "Game paused or not playable"),
    "invalid-telemetry": ("游戏数据无效", "Invalid game data"),
    "vibrator-off": ("游戏振动器关闭", "In-game vibrator is off"),
    "unknown-vibrator-mode": ("未知游戏振动器档位，不输出", "Unknown vibrator mode; output blocked"),
    "bluetooth-not-connected": ("设备蓝牙未连接", "Device Bluetooth disconnected"),
    "accessory-not-inserted": ("未插入负鼠配件", "Opossum accessory not inserted"),
    "channel-muted": ("通道已静音", "Channel muted"),
    "channel-fault-or-blocked": ("通道故障或被阻止", "Channel fault or blocked"),
    "unsupported-device": ("暂不支持此设备", "Unsupported device"),
    "unsupported-waveformat": ("此型号的 V4 波形尚未验证", "V4 waveform not verified for this model"),
    "missing-device-state": ("等待设备状态", "Waiting for device state"),
    "selected-device-disconnected": ("所选设备已断开", "Selected device disconnected"),
    "all-channels-blocked": ("全部通道不可用，请检查配件与静音", "All channels blocked; check accessories and mute"),
    "no-channel-output": ("当前配置没有非零输出", "No nonzero output in this configuration"),
    "vibrator-random-wait": ("等待游戏实际档位；请安装新版遥测插件并重启游戏", "Waiting for the game's effective mode; update telemetry and restart the game"),
}


class V4DeviceBackend(QObject):
    devicesChanged = Signal()
    ovcProfileChanged = Signal()
    ovcCatalogChanged = Signal()
    hudSettingsChanged = Signal()

    def _init_device_support(self, saved, persist):
        self._device_persist = persist
        self.socket_protocol = "v4" if saved.get("socket_protocol") == "v4" else "v3"
        self.v4_hub = None
        self.v4_messages = queue.Queue()
        self._v3_messages = queue.Queue()
        self._v4_seen_links = set()
        self._v4_seen_devices = set()
        self.ovc_profile = sanitize_profile(saved.get("ovc_profile"))
        self.ovc_planner = OvcPlanner()
        self.ovc_frame = {}
        self.ovc_enabled = False
        self.coyote_waiting_for_game = False
        self.ovc_waiting_for_game = False
        self.coyote_resume_after = 0.0
        self.ovc_resume_after = 0.0
        self.ovc_connected = False
        self.ovc_mode = "off"
        self.ovc_output = (0, 0)
        self.ovc_gate = "not-authorized"
        self._last_ovc_ui = 0.0
        self._last_ovc_sync = 0.0
        self.v4_error = ""
        self.v4_qr_source = ""
        self.hud_settings = sanitize_settings(saved.get("hud_settings"))

    @Property("QVariantMap", notify=hudSettingsChanged)
    def hudSettings(self):
        return dict(self.hud_settings)

    @Property(str, notify=hudSettingsChanged)
    def hudPluginHint(self):
        if self.demo_mode:
            return self._device_text("演示预览，不连接游戏", "Demo preview; no game connection")
        if not self.last_packet:
            return self._device_text("等待游戏 HUD 组件状态", "Waiting for game HUD component")
        if self.last_packet.get("hudProtocol") != 2:
            return self._device_text("游戏 HUD 组件需要更新：关闭游戏，安装 / 修复运行环境后重启游戏。", "HUD update needed: close the game, run Setup Runtime, then restart the game.")
        return self._device_text("游戏 HUD 组件已就绪 · V2", "Game HUD ready · V2")

    @Slot("QVariantMap", result=bool)
    def saveHudSettings(self, raw):
        if not isinstance(raw, dict) or not (raw.get("show_pulse") or raw.get("show_ovc")) or not (raw.get("show_a") or raw.get("show_b")):
            return False
        clean = sanitize_settings(raw)
        try:
            if not self.demo_mode:
                self._device_persist({"hud_settings": clean})
        except OSError as error:
            self._toast("保存失败", str(error))
            return False
        self.hud_settings = clean
        self.hudSettingsChanged.emit()
        return True

    def _device_text(self, zh, en):
        return en if self.language_name == "en" else zh

    def _reason_text(self, reason):
        return self._device_text(*REASONS.get(reason, (reason, reason)))

    @Property(str, notify=devicesChanged)
    def socketProtocol(self):
        return self.socket_protocol

    @Property(str, notify=devicesChanged)
    def v4QrSource(self):
        return self.v4_qr_source

    @Property(str, notify=devicesChanged)
    def v4Address(self):
        return f"{self.v4_hub.lan_ip}:{self.v4_hub.port}" if self.v4_hub else "—"

    @Property(str, notify=devicesChanged)
    def v4Status(self):
        if self.demo_mode:
            return self._device_text("演示模式 · 不启动连接", "Demo · no connection")
        if self.v4_error:
            return self.v4_error
        if not self.v4_hub:
            return self._device_text("V4 未启动", "V4 not started")
        if self.v4_hub.app_connected:
            return self._device_text("手机 App 已连接 · 自动选择已发现设备", "App connected · discovered devices auto-selected")
        return self._device_text("等待 DG-LAB 4 App 扫码", "Scan with DG-LAB 4 App")

    @Property(bool, notify=devicesChanged)
    def phoneConnected(self):
        if self.demo_mode:
            return False
        return bool(self.v4_hub and self.v4_hub.app_connected) if self.socket_protocol == "v4" else self.device_connected_value

    @Property(bool, notify=devicesChanged)
    def coyoteRunning(self):
        return bool(not self.demo_mode and self.device_connected_value and self.auto_output_enabled)

    @Property(bool, notify=devicesChanged)
    def ovcRunning(self):
        return bool(not self.demo_mode and self.ovc_connected and self.ovc_enabled)

    @staticmethod
    def _link_present(device):
        props, state = device.get("props", {}), device.get("slotState", {})
        if not isinstance(props, dict) or not isinstance(state, dict):
            return False
        return not (state.get("hasDevice") is False or props.get("connectState") == "disconnected") and (state.get("hasDevice") is True or props.get("connectState") == "connected")

    def _auto_select_new_v4_devices(self, devices):
        announced = {(d.get("clientId"), d.get("slotId"), d.get("type")) for d in devices if d.get("clientId") and d.get("slotId")}
        linked = {(d.get("clientId"), d.get("slotId"), d.get("type")) for d in devices if d.get("clientId") and d.get("slotId") and self._link_present(d)}
        candidates = (announced - self._v4_seen_devices) | (linked - self._v4_seen_links)
        self._v4_seen_devices = announced
        self._v4_seen_links = linked
        if not self.v4_hub:
            return
        for role, kind in (("coyote", "COYOTE_030"), ("ovc", "OVC_1")):
            if role == "coyote" and self.socket_protocol != "v4":
                continue
            route = self.v4_hub.channel(role)
            # Never replace an existing user selection/running route on a patch.
            if route.selected_slot_id:
                continue
            # Discovery/selection is separate from Bluetooth/output readiness.
            # APP can initially report hasDevice=false alongside connected.
            # Select the announced slot once; the transport still blocks all
            # output until the full readiness and zero barriers succeed.
            candidate = next((d for d in reversed(devices) if (d.get("clientId"), d.get("slotId"), d.get("type")) in candidates and d.get("type") == kind), None)
            if candidate and self.selectV4Device(role, candidate["clientId"], candidate["slotId"]):
                audit.record("socket.v4_auto_selection", role=role, app_client_id=candidate["clientId"], slot_id=candidate["slotId"], link_present=self._link_present(candidate), authorized=False)

    @staticmethod
    def _needs_phone_bluetooth_connection(device):
        props, state = device.get("props") or {}, device.get("slotState") or {}
        return isinstance(props, dict) and isinstance(state, dict) and state.get("hasDevice") is False and props.get("connectState") == "connected"

    @Slot(str, result=str)
    def deviceBlockReason(self, role):
        if role == "ovc" and self.socket_protocol != "v4":
            return self._reason_text("v4-required")
        if self.demo_mode:
            return self._device_text("演示模式不连接或启动真实设备", "Demo mode does not connect or start real devices")
        if role not in {"ovc", "coyote"}:
            return self._device_text("请选择设备", "Select a device")
        if role == "coyote" and self.socket_protocol == "v3":
            if not self.device_connected_value:
                return self._device_text("请先使用 DG-LAB 3 App 扫码连接设备", "Scan the QR code with DG-LAB 3 App first")
        else:
            if not self.v4_hub or not self.v4_hub.server_ready:
                return self.v4_error or self._device_text("V4 连接服务尚未就绪，请检查二维码和端口", "V4 server is not ready; check QR and port")
            if not self.v4_hub.app_connected:
                return self._device_text("请先使用 DG-LAB 4 App 扫码连接", "Scan the QR with DG-LAB 4 App first")
            route = self.v4_hub.channel(role)
            if not route.selected_slot_id:
                return self._device_text("请在 App 中连接设备，并在控制中心选择对应设备", "Connect hardware in the App and select the device in the control center")
            selected = next((d for d in route.devices_snapshot() if d.get("selected")), None)
            if not selected:
                return self._device_text("等待设备状态同步", "Waiting for device state")
            if self._needs_phone_bluetooth_connection(selected):
                return self._device_text("已发现设备，请先在手机 App 中连接设备蓝牙。", "Device discovered. Connect the hardware via Bluetooth in the phone App first.")
            channels = [ch for ch in ("A", "B") if role != "ovc" or self.ovc_profile["channels"][ch]["enabled"]]
            if not channels:
                return self._device_text("A/B 通道均未启用，请到工作台配置", "Both channels are disabled; configure a workbench channel")
            failures = []
            for ch in channels:
                reason = selected.get("channel" + ch + "Reason", "missing-device-state")
                state = selected.get("slotState") or {}
                channel_state = state.get("channel" + ch) if isinstance(state, dict) else None
                maximum = channel_state.get("intensityMax") if isinstance(channel_state, dict) else None
                if reason:
                    failures.append(ch + "：" + self._reason_text(reason))
                elif type(maximum) in (int, float) and maximum <= 0:
                    failures.append(ch + "：" + self._device_text("App 强度上限为 0", "App intensity limit is zero"))
                else:
                    failures = []
                    break
            if failures:
                return "\n".join(failures)
            if not route.connected:
                if getattr(route, "_readiness_failure_latched", False) is True:
                    return self._device_text("设备同步或归零确认失败，请重新选择设备并查看诊断日志", "Device synchronization or zero confirmation failed; reselect the device and check diagnostics")
                return self._device_text("设备正在安全归零，请稍候；未就绪时不会输出", "Device is confirming a safe zero; wait for readiness")
        cap = self.ovc_profile["hard_cap"] if role == "ovc" else getattr(self, "hard_cap_value", 0)
        if cap <= 0:
            return self._device_text("安全硬上限为 0，请先在工作台设置", "The safety cap is zero; configure it in the workbench")
        return ""

    @Slot(str)
    def explainDeviceBlock(self, role):
        self._toast(self._device_text("暂时无法启用", "Cannot Enable Yet"), self.deviceBlockReason(role) or self._device_text("等待设备确认，请稍后重试", "Waiting for device confirmation; try again"))

    def _device_choices(self, kind):
        selected = self.v4_hub.channel(kind) if self.v4_hub else None
        result = [{"label": self._device_text("不选择设备", "No device selected"), "clientId": "", "slotId": "", "selected": not selected or not selected.selected_slot_id}]
        if not self.v4_hub:
            return result
        for item in self.v4_hub.devices_snapshot():
            if item.get("type") not in ({"OVC_1"} if kind == "ovc" else {"COYOTE_030", "COYOTE_020"}):
                continue
            result.append({**item, "label": f"{item.get('name') or item['type']} · {item['slotId']}",
                           "selected": (item["clientId"], item["slotId"]) == (selected.selected_client_id, selected.selected_slot_id)})
        return result

    @Property("QVariantList", notify=devicesChanged)
    def coyoteDevices(self):
        return self._device_choices("coyote")

    @Property("QVariantList", notify=devicesChanged)
    def ovcDevices(self):
        return self._device_choices("ovc")

    @Property("QVariantMap", notify=ovcProfileChanged)
    def ovcProfile(self):
        return deepcopy(self.ovc_profile)

    @Property("QVariantList", notify=ovcCatalogChanged)
    def ovcWaveforms(self):
        items = waveform_catalog(self.ovc_profile, getattr(self, "custom_wave_library_value", []), self.language_name)
        for index, item in enumerate(items):
            item["color"] = ("#EE81C8", "#68D7E5", "#B9A0E8", "#80D5A0")[index % 4]
        return items

    @Property("QVariantList", notify=ovcCatalogChanged)
    def ovcActions(self):
        labels = {"rhythmic": ("规律动作", "Rhythmic"), "static": ("静态姿势", "Static"), "off": ("普通交互", "Interaction")}
        return [{"key": action, "name": action_label(action, self.language_name), "style": action_style(action),
                 "styleLabel": self._device_text(*labels[action_style(action)])}
                for action in getattr(self, "known_actions_value", [])]

    @Property(bool, notify=devicesChanged)
    def ovcEnabled(self):
        return self.ovc_enabled

    @Property(bool, notify=devicesChanged)
    def ovcConnected(self):
        return self.ovc_connected

    @Property(str, notify=devicesChanged)
    def ovcMode(self):
        labels = {"off": ("关闭", "Off"), "low": ("低", "Low"), "medium": ("中", "Medium"), "random": ("随机档", "Random"), "high": ("高", "High"), "unknown": ("未知", "Unknown")}
        return self._device_text(*labels[self.ovc_mode])

    @Property(int, notify=devicesChanged)
    def ovcOutputA(self):
        return self.ovc_output[0]

    @Property(int, notify=devicesChanged)
    def ovcOutputB(self):
        return self.ovc_output[1]

    def _selected_channel_status(self, role):
        if not self.v4_hub:
            return ""
        route = self.v4_hub.channel(role)
        selected = next((d for d in route.devices_snapshot() if d.get("selected")), None)
        if not selected:
            return self._device_text("请先选择设备", "Select a device first")
        parts = [self._device_text("已发现设备，请先在手机 App 中连接设备蓝牙", "Device discovered; connect its Bluetooth in the phone App")] if self._needs_phone_bluetooth_connection(selected) else []
        for ch in ("A", "B"):
            reason = selected.get("channel" + ch + "Reason", "")
            maximum = selected.get("slotState", {}).get("channel" + ch, {}).get("intensityMax", "—")
            reported = selected.get("props", {}).get("intensity" + ch, "—")
            parts.append(f"{ch}: {self._reason_text(reason) if reason else self._device_text('就绪', 'Ready')} · max {maximum} · App {reported}")
        return "\n".join(parts)

    @Property(str, notify=devicesChanged)
    def coyoteChannelStatus(self):
        waiting = self._reason_text("waiting-for-game") + "\n" if self.auto_output_enabled and self.coyote_waiting_for_game else ""
        return waiting + self._selected_channel_status("coyote")

    @Property(str, notify=devicesChanged)
    def ovcStatus(self):
        if self.ovc_enabled and self.ovc_waiting_for_game:
            gate = self._reason_text("waiting-for-game")
        elif self.ovc_gate:
            gate = self._reason_text(self.ovc_gate)
        elif self.ovc_profile["mode"] == "independent":
            gate = self._device_text("独立波形配置输出中", "Independent waveform output")
        else:
            gate = self._device_text("游戏振动器联动中", "Following in-game vibrator")
        return gate + "\n" + self._selected_channel_status("ovc")

    @Slot()
    def startV4(self):
        if self.demo_mode or not self.agreement_accepted_value:
            return
        if self.v4_hub is None:
            self.v4_hub = DGLabV4Hub(self.v4_messages, port=9998, lan_ip=str(self.saved.get("socket_lan_ip", "")))
            self.v4_hub.start()
            self.v4_error = ""
            self._log("V4 Hub 启动；不会自动启用任何设备输出")
            self.devicesChanged.emit()

    def _make_coyote_bridge(self):
        if self.socket_protocol == "v4":
            self.startV4()
            return self.v4_hub.channel("coyote")
        return DGLabBridge(self._v3_messages, port=int(self.saved.get("socket_port", DEFAULT_PORT)),
                           lan_ip=str(self.saved.get("socket_lan_ip", "")))

    @Slot(str)
    def selectSocketProtocol(self, protocol):
        if protocol not in {"v3", "v4"} or protocol == self.socket_protocol:
            return
        try:
            if not self.demo_mode:
                self._device_persist({"socket_protocol": protocol})
        except OSError as error:
            self._toast("保存失败", str(error))
            return
        old = self.bridge
        self.auto_output_enabled = False
        self.coyote_waiting_for_game = False
        self.device_connected_value = False
        self.server_ready_value = False
        self.qr_source_value = ""
        if old:
            old.stop()
        if protocol == "v3":
            self._stop_ovc("not-authorized")
        self._v3_messages = queue.Queue()  # Discard late events from the retired V3 bridge.
        self.socket_protocol = protocol
        self.device_status_value = "等待手动连接和启用"
        if self.runtime_started and not self.demo_mode:
            self.bridge = self._make_coyote_bridge()
            self.bridge.start()
            if protocol == "v4" and self.v4_hub.server_ready:
                self._use_coyote_qr()
                self._v4_seen_links = {identity for identity in self._v4_seen_links if identity[2] != "COYOTE_030"}
                self._v4_seen_devices = {identity for identity in self._v4_seen_devices if identity[2] != "COYOTE_030"}
                self._auto_select_new_v4_devices(self.v4_hub.devices_snapshot())
        self._show_frame(self.current_source_frame)
        self.devicesChanged.emit()
        self.connectionChanged.emit()
        self.statusChanged.emit()

    def _use_coyote_qr(self):
        if self.bridge:
            self.server_ready_value = self.bridge.server_ready
            self.lan_addresses_value = list(self.bridge.available_lan_ips)
            self.lan_address_value = f"{self.bridge.lan_ip}:{self.bridge.port}"
            self.qr_source_value = self._qr_data_url(self.bridge.qr_url)

    @Slot(str, str, str, result=bool)
    def selectV4Device(self, role, client_id, slot_id):
        if role not in {"ovc", "coyote"} or not self.v4_hub or self.demo_mode:
            return False
        if role == "coyote" and self.socket_protocol != "v4":
            return False
        if not self.v4_hub.select_device(role, client_id, slot_id):
            return False
        if role == "ovc":
            self.ovc_enabled = self.ovc_connected = False
            self.ovc_waiting_for_game = False
            self.ovc_output = (0, 0)
            self.ovc_gate = "not-authorized"
        else:
            self.auto_output_enabled = self.device_connected_value = False
            self.coyote_waiting_for_game = False
        self.devicesChanged.emit()
        self.statusChanged.emit()
        return True

    @Slot()
    def toggleOvcOutput(self):
        if self.ovc_enabled:
            self._stop_ovc("not-authorized")
        elif self.deviceBlockReason("ovc"):
            self.explainDeviceBlock("ovc")
        elif self.ovc_connected and self.v4_hub:
            route = self.v4_hub.channel("ovc")
            route.clear_global_emergency_stop()
            self.ovc_waiting_for_game = not bool(self.last_receive and time.monotonic() - self.last_receive < .5)
            self.ovc_resume_after = time.monotonic() if self.ovc_waiting_for_game else 0.0
            self.ovc_enabled = True
            if self.ovc_waiting_for_game:
                route.emergency_stop()  # Standby never arms the transport.
            self._sync_ovc(force=True)
        self.devicesChanged.emit()

    def _stop_ovc(self, reason):
        self.ovc_enabled = False
        self.ovc_waiting_for_game = False
        self.ovc_resume_after = 0.0
        self.ovc_output = (0, 0)
        self.ovc_gate = reason
        self.ovc_planner.reset()
        if self.v4_hub:
            self.v4_hub.channel("ovc").emergency_stop()

    def _enter_game_standby(self, role, reason, *, stopped_at=None, stop_transport=True):
        """Keep the user's enable intent; revoke transport output until NEW data."""
        now = time.monotonic()
        cutoff = stopped_at if type(stopped_at) in (int, float) and 0 < stopped_at <= now else now
        if role == "ovc":
            if not self.ovc_enabled or self.ovc_waiting_for_game:
                return
            self.ovc_waiting_for_game = True
            self.ovc_resume_after = max(self.ovc_resume_after, cutoff)
            self.ovc_output = (0, 0)
            self.ovc_gate = "waiting-for-game"
            self.ovc_planner.reset()
            route = self.v4_hub.channel("ovc") if self.v4_hub else None
        else:
            if not self.auto_output_enabled or self.coyote_waiting_for_game:
                return
            self.coyote_waiting_for_game = True
            self.coyote_resume_after = max(self.coyote_resume_after, cutoff)
            self.current_output_a = self.current_output_b = 0.0
            self.safety_wait_reason = "waiting-for-game"
            self.device_status_value = self._reason_text("waiting-for-game")
            route = self.bridge
        if stop_transport and route:
            route.emergency_stop()
        audit.record("control.game_standby", role=role, reason=reason, game_age_ms=round((now-self.last_receive)*1000) if self.last_receive else None)
        self._log(self._device_text("输出刷新中断，已归零待机；等待新的游戏数据", "Output updates paused; zero standby until new game data") + " · " + role)
        self.devicesChanged.emit()

    @Slot(int, int, int, int, bool, bool, result=bool)
    def saveOvcSettings(self, low, random, high, cap, channel_a, channel_b):
        raw = {"low": low, "random": random, "high": high, "hard_cap": cap,
               "channel_a": channel_a, "channel_b": channel_b}
        if any(v < 0 or v > 200 or v % 10 for v in (low, random, high, cap)) or max(low, random, high) > cap:
            return False
        clean = sanitize_profile({**self.ovc_profile, **raw})
        for channel in ("A", "B"):
            clean["channels"][channel]["enabled"] = clean["channel_" + channel.lower()]
        return self._save_ovc_profile(clean)

    def _save_ovc_profile(self, clean):
        if self.socket_protocol != "v4":
            self._toast(self._device_text("负鼠需要 V4", "Opossum Requires V4"), self._reason_text("v4-required"))
            return False
        try:
            if not self.demo_mode:
                self._device_persist({"ovc_profile": clean})
        except OSError as error:
            self._toast("保存失败", str(error))
            return False
        self._stop_ovc("not-authorized")  # Editing does not authorize an output jump.
        self.ovc_profile = clean
        self.ovcProfileChanged.emit()
        self.ovcCatalogChanged.emit()
        self.devicesChanged.emit()
        return True

    @Slot("QVariantMap", result=bool)
    def saveOvcProfile(self, raw):
        if not isinstance(raw, dict):
            return False
        clean = sanitize_profile(raw)
        for key in ("low", "medium", "high", "hard_cap"):
            value = raw.get(key)
            if type(value) not in (int, float) or value != step_strength(value) or value > clean["hard_cap"]:
                return False
        allowed = {wave["key"] for wave in waveform_catalog(clean, getattr(self, "custom_wave_library_value", []))}
        for policy in clean["channels"].values():
            if policy["strength"] > clean["hard_cap"] or policy["wave"] not in allowed:
                return False
            if any(rule["strength"] > clean["hard_cap"] or (rule["mode"] == "wave" and rule["wave"] not in allowed) for rule in policy["actions"].values()):
                return False
        saved = self._save_ovc_profile(clean)
        if saved:
            self._toast(self._device_text("负鼠配置已保存", "Opossum Settings Saved"),
                        time.strftime("%H:%M:%S") + " · " + self._device_text("负鼠已暂停，准备好后可重新启用。", "Opossum paused. Re-enable when ready."))
        return saved

    @Slot(str, "QVariantList", str, result=str)
    def saveOvcWaveform(self, name, points, key=""):
        points = clean_points(points)
        if points is None or len(points) != 16:
            return ""
        profile = deepcopy(self.ovc_profile)
        waves = profile["custom_waves"]
        existing = next((wave for wave in waves if wave["key"] == key), None)
        if existing is None:
            if len(waves) >= 64:
                return ""
            number = 1
            while any(wave["key"] == f"ovc_custom:{number}" for wave in waves):
                number += 1
            key = f"ovc_custom:{number}"
            name = str(name).strip() or self._device_text(f"自定义振动 {number}", f"Custom Vibration {number}")
            existing = {"key": key}
            waves.append(existing)
        existing.update(name=str(name).strip()[:64] or existing.get("name", key), points=points, group="custom")
        return key if self._save_ovc_profile(profile) else ""

    @Slot()
    def emergencyStopAll(self):
        self.auto_output_enabled = False
        self.coyote_waiting_for_game = False
        self._stop_ovc("not-authorized")
        if self.bridge:
            self.bridge.emergency_stop()
        if self.v4_hub:
            self.v4_hub.latch_global_emergency_stop()
        self.device_status_value = "输出已暂停 · A/B 已归零 · 设备保持连接"
        self.devicesChanged.emit()
        self.statusChanged.emit()
        self.outputChanged.emit()
        self._log("全局停止：郊狼及负鼠全部撤销授权并归零")

    def _poll_device_support(self):
        while not self._v3_messages.empty():
            event = self._v3_messages.get_nowait()
            if self.socket_protocol == "v3":
                self.messages.put(event)
        while not self.v4_messages.empty():
            _, payload = self.v4_messages.get_nowait()
            role, event = payload.get("role"), payload.get("event")
            if (self.v4_hub and role in {"ovc", "coyote"}
                    and "selection_epoch" in payload
                    and payload["selection_epoch"] != self.v4_hub.channel(role)._selection_epoch):
                continue
            if role == "hub":
                if event == "ready":
                    self.v4_error = ""
                    self.v4_qr_source = self._qr_data_url(payload.get("qr_url", ""))
                    if self.socket_protocol == "v4":
                        self._use_coyote_qr()
                elif event == "devices":
                    self._auto_select_new_v4_devices(payload.get("devices", []))
                elif event in {"error", "server_error"}:
                    self.v4_error = str(payload.get("detail", "V4 error"))
                    self._stop_ovc("not-authorized")
                    self.ovc_connected = False
                    if self.socket_protocol == "v4":
                        self.auto_output_enabled = self.device_connected_value = False
                    self._log(self.v4_error)
            elif role == "ovc":
                if event == "connected":
                    self.ovc_connected = bool(self.v4_hub and self.v4_hub.channel("ovc").connected)
                    self._stop_ovc("not-authorized")
                elif event == "output_timeout" and payload.get("reason") == "producer-stale":
                    self._enter_game_standby("ovc", "producer-stale", stopped_at=payload.get("producer_stalled_at"), stop_transport=False)
                elif event in {"disconnected", "waiting", "error", "output_timeout"}:
                    self.ovc_connected = False if event != "output_timeout" else self.ovc_connected
                    self._stop_ovc(payload.get("reason", "not-authorized"))
                if event not in {"devices", "feedback"}:
                    self._log(f"OVC · {event} · {payload.get('reason', payload.get('detail', ''))}")
            elif role == "coyote" and self.socket_protocol == "v4":
                if event == "connected" and not self.bridge.connected:
                    continue
                if event == "output_timeout" and payload.get("reason") == "producer-stale":
                    self._enter_game_standby("coyote", "producer-stale", stopped_at=payload.get("producer_stalled_at"), stop_transport=False)
                elif event in {"waiting", "error", "output_timeout"}:
                    self.auto_output_enabled = False
                    self.coyote_waiting_for_game = False
                    self.device_connected_value = bool(self.bridge and self.bridge.connected)
                    self.device_status_value = str(payload.get("detail") or self._reason_text(payload.get("reason", "not-authorized")))
                else:
                    self.messages.put(("dglab", payload))
            self.devicesChanged.emit()
            self.statusChanged.emit()
            self.connectionChanged.emit()
        self._sync_ovc()

    def _sync_ovc(self, force=False):
        now = time.monotonic()
        if not force and now - self._last_ovc_sync < .1:
            return
        self._last_ovc_sync = now
        fresh = bool(not self.demo_mode and self.last_receive and 0 <= now - self.last_receive < .5)
        if self.ovc_enabled and fresh and self.last_receive > self.ovc_resume_after:
            self.ovc_waiting_for_game = False
        if self.ovc_enabled and not fresh and not self.ovc_waiting_for_game:
            self._enter_game_standby("ovc", "telemetry-stale")
        self.ovc_frame = self.ovc_planner.evaluate(self.last_packet, self.ovc_profile, self.ovcWaveforms,
                            now=now, fresh=fresh and not self.ovc_waiting_for_game, authorized=self.ovc_enabled and self.ovc_connected)
        mode, a, b, gate = (self.ovc_frame["mode"], self.ovc_frame["A"]["strength"], self.ovc_frame["B"]["strength"], self.ovc_frame["gate"])
        if self.ovc_enabled and self.ovc_waiting_for_game:
            gate = "waiting-for-game"
        if not self.ovc_enabled and self.ovc_gate in {"telemetry-stale", "producer-stale", "response-timeout"}:
            gate = self.ovc_gate
        signature = (mode, (a, b), gate)
        changed = signature != (self.ovc_mode, self.ovc_output, self.ovc_gate)
        self.ovc_mode, self.ovc_output, self.ovc_gate = mode, (a, b), gate
        if self.v4_hub and self.ovc_enabled and not self.ovc_waiting_for_game:
            route = self.v4_hub.channel("ovc")
            route.update_auto_outputs(a, self.ovc_frame["A"]["frames"], wave_key_a=self.ovc_frame["A"]["token"],
                strength_b=b, frames_b=self.ovc_frame["B"]["frames"], wave_key_b=self.ovc_frame["B"]["token"], hard_cap=self.ovc_profile["hard_cap"])
            # A user's enable may arrive while the acknowledged zero barrier
            # is finishing. Retry only while that explicit authorization lives,
            # with a fresh desired frame first, never by bypassing the barrier.
            route.set_auto_enabled(True)
        if changed:
            self.devicesChanged.emit()

    def _shutdown_device_support(self):
        self._stop_ovc("not-authorized")
        if self.v4_hub:
            self.v4_hub.stop()
