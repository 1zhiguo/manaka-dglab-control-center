"""Read-only Windows IPv4 adapter inventory and listening-port ownership."""
import ctypes
from ctypes import wintypes
import ipaddress
import os
from pathlib import Path
import socket
import sys


def ipv4_interfaces() -> list[dict]:
    if sys.platform != "win32":
        return []

    class SocketAddress(ctypes.Structure):
        _fields_ = [("address", ctypes.c_void_p), ("length", ctypes.c_int)]

    class Unicast(ctypes.Structure):
        pass
    Unicast._fields_ = [("header", ctypes.c_ulonglong), ("next", ctypes.POINTER(Unicast)),
                        ("socket", SocketAddress)]

    class Adapter(ctypes.Structure):
        pass
    Adapter._fields_ = [
        ("header", ctypes.c_ulonglong), ("next", ctypes.POINTER(Adapter)),
        ("name", ctypes.c_char_p), ("unicast", ctypes.POINTER(Unicast)),
        ("anycast", ctypes.c_void_p), ("multicast", ctypes.c_void_p), ("dns", ctypes.c_void_p),
        ("suffix", wintypes.LPWSTR), ("description", wintypes.LPWSTR), ("friendly", wintypes.LPWSTR),
        ("physical", ctypes.c_ubyte * 8), ("physical_length", wintypes.ULONG),
        ("flags", wintypes.ULONG), ("mtu", wintypes.ULONG), ("type", wintypes.ULONG),
        ("status", wintypes.ULONG),
    ]
    api = ctypes.WinDLL("iphlpapi", use_last_error=True)
    api.GetAdaptersAddresses.argtypes = [wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p,
                                        ctypes.c_void_p, ctypes.POINTER(wintypes.ULONG)]
    api.GetAdaptersAddresses.restype = wintypes.ULONG
    size = wintypes.ULONG(16384)
    for _ in range(3):
        buffer = ctypes.create_string_buffer(size.value)
        result = api.GetAdaptersAddresses(2, 0, None, buffer, ctypes.byref(size))
        if result == 111:
            continue
        if result != 0:
            return []
        break
    else:
        return []
    rows = []
    seen = set()
    adapter = ctypes.cast(buffer, ctypes.POINTER(Adapter))
    while adapter:
        value = adapter.contents
        name = value.friendly or value.description or "网络适配器"
        virtual = any(token in name.casefold() for token in (
            "vpn", "tun", "tap", "wireguard", "tailscale", "zerotier", "virtual", "vmware", "vethernet"))
        address = value.unicast if value.status == 1 else None
        while address:
            item = address.contents
            if item.socket.address and item.socket.length >= 8:
                raw = ctypes.string_at(item.socket.address, 8)
                if int.from_bytes(raw[:2], "little") == 2:
                    ip = str(ipaddress.IPv4Address(raw[4:8]))
                    parsed = ipaddress.IPv4Address(ip)
                    if ip not in seen and not (parsed.is_loopback or parsed.is_link_local or parsed.is_unspecified):
                        seen.add(ip)
                        rows.append({"address": ip, "name": name, "virtual": virtual,
                                     "label": f"{name} · {ip}" + ("（虚拟/VPN）" if virtual else "")})
            address = item.next
        adapter = value.next
    return sorted(rows, key=lambda item: (item["virtual"], item["name"], item["address"]))


def port_listeners(port: int) -> list[dict]:
    if sys.platform != "win32":
        return []
    api = ctypes.WinDLL("iphlpapi", use_last_error=True)
    api.GetExtendedTcpTable.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.ULONG),
                                       wintypes.BOOL, wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
    api.GetExtendedTcpTable.restype = wintypes.ULONG
    size = wintypes.ULONG()
    result = api.GetExtendedTcpTable(None, ctypes.byref(size), False, 2, 3, 0)
    if result not in {0, 122}:
        raise OSError(result, "读取 TCP 端口表失败")
    buffer = ctypes.create_string_buffer(size.value)
    result = api.GetExtendedTcpTable(buffer, ctypes.byref(size), False, 2, 3, 0)
    if result:
        raise OSError(result, "读取 TCP 端口表失败")

    class Row(ctypes.Structure):
        _fields_ = [(key, wintypes.DWORD) for key in
                    ("state", "local_address", "local_port", "remote_address", "remote_port", "pid")]

    count = wintypes.DWORD.from_buffer(buffer).value
    rows = []
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    for index in range(count):
        row = Row.from_buffer(buffer, 4 + index * ctypes.sizeof(Row))
        if socket.ntohs(row.local_port & 0xffff) != port:
            continue
        name = "未知进程"
        handle = kernel.OpenProcess(0x1000, False, row.pid)
        if handle:
            try:
                text = ctypes.create_unicode_buffer(32768)
                length = wintypes.DWORD(len(text))
                if kernel.QueryFullProcessImageNameW(handle, 0, text, ctypes.byref(length)):
                    name = Path(text.value).name
            finally:
                kernel.CloseHandle(handle)
        rows.append({"pid": row.pid, "name": name, "ours": row.pid == os.getpid()})
    return rows
