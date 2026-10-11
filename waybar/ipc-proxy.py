#!/usr/bin/env python3
# =============================================================================
#  waybar/ipc-proxy.py — lets Waybar's workspace buttons work with a Lua config
# =============================================================================
#  Waybar's hyprland/workspaces module switches workspace on click by sending
#  the legacy command "dispatch workspace N" to Hyprland's socket. With a Lua
#  config (Hyprland 0.56) a dispatch is evaluated as Lua, so that command fails
#  and clicking a number does nothing.
#
#  This tiny relay sits between Waybar and Hyprland:
#    * it serves a .socket.sock of its own in PROXY_DIR and forwards every
#      request to the real Hyprland socket, unchanged...
#    * ...except the three legacy dispatchers Waybar uses, rewritten in Lua:
#        workspace X                       → hl.dsp.focus({ workspace = "X" })
#        focusworkspaceoncurrentmonitor X  → hl.dsp.focus({ workspace = "X" })
#        togglespecialworkspace [name]     → hl.dsp.workspace.toggle_special("name")
#    * the event socket (.socket2.sock), hyprland.lock and hyprland.log are
#      symlinks to the real ones, so everything else behaves as usual.
#  hypr/scripts/waybar.sh starts it and points Waybar's
#  HYPRLAND_INSTANCE_SIGNATURE at PROXY_DIR (a path relative to
#  $XDG_RUNTIME_DIR/hypr, which is how Waybar and hyprctl build socket paths).
#
#  Usage: ipc-proxy.py PROXY_DIR
#    Prints the value to give HYPRLAND_INSTANCE_SIGNATURE, then goes to the
#    background once its socket is listening (a relay already running for
#    this Hyprland is reused). Exits by itself when Hyprland quits.
#    Keep PROXY_DIR short: a socket path is limited to 108 bytes.
#  Needs HYPRLAND_INSTANCE_SIGNATURE (the real one) and XDG_RUNTIME_DIR.
# =============================================================================
import asyncio
import os
import re
import socket
import sys

RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
HIS = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
REAL_DIR = os.path.join(RUNTIME, "hypr", HIS)
REAL_SOCK = os.path.join(REAL_DIR, ".socket.sock")
LINKED = (".socket2.sock", "hyprland.lock", "hyprland.log")   # served as symlinks
LOG = os.environ.get("INKPAW_IPC_LOG")       # debug: append "request -> sent" lines to this file

LEGACY = re.compile(r"^(?P<flags>\S*/)?dispatch\s+(?P<cmd>workspace|focusworkspaceoncurrentmonitor|togglespecialworkspace)"
                    r"(?:\s+(?P<arg>.*))?$")


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def translate_one(cmd):
    """One request (no [[BATCH]]): rewrite a legacy workspace dispatch, else unchanged."""
    m = LEGACY.match(cmd.strip())
    if not m:
        return cmd
    flags, name, arg = m.group("flags") or "", m.group("cmd"), (m.group("arg") or "").strip()
    if name == "togglespecialworkspace":
        call = f"hl.dsp.workspace.toggle_special({lua_str(arg)})" if arg else "hl.dsp.workspace.toggle_special()"
    else:
        call = f"hl.dsp.focus({{ workspace = {lua_str(arg)} }})"
    return f"{flags}dispatch {call}"


def translate(req):
    if req.startswith("[[BATCH]]"):
        return "[[BATCH]]" + ";".join(translate_one(c) for c in req[len("[[BATCH]]"):].split(";"))
    return translate_one(req)


async def handle(reader, writer):
    try:
        data = await asyncio.wait_for(reader.read(65536), timeout=5)
        req = data.decode("utf-8", "replace")
        out = translate(req).encode()
        if LOG:
            with open(LOG, "a") as f:
                f.write(f"{req!r} -> {out.decode()!r}\n")
        r_reader, r_writer = await asyncio.open_unix_connection(REAL_SOCK)
        r_writer.write(out)
        await r_writer.drain()
        while chunk := await r_reader.read(65536):
            writer.write(chunk)
        await writer.drain()
        r_writer.close()
    except (OSError, asyncio.TimeoutError):
        pass
    finally:
        writer.close()


def already_running(path):
    s = socket.socket(socket.AF_UNIX)
    try:
        s.connect(path)
        return True
    except OSError:
        return False
    finally:
        s.close()


async def watch_hyprland(server):
    """Stop when the real Hyprland socket disappears (session ended)."""
    while os.path.exists(REAL_SOCK):
        await asyncio.sleep(5)
    server.close()


async def serve(listener):
    server = await asyncio.start_unix_server(handle, sock=listener)
    asyncio.create_task(watch_hyprland(server))
    async with server:
        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            pass


def main(proxy_dir):
    fake = os.path.relpath(proxy_dir, os.path.join(RUNTIME, "hypr"))
    sock = os.path.join(proxy_dir, ".socket.sock")
    current = os.path.realpath(os.path.join(proxy_dir, LINKED[0])) == os.path.realpath(os.path.join(REAL_DIR, LINKED[0]))
    if current and already_running(sock):          # a relay for this Hyprland is up
        print(fake)
        return
    os.makedirs(proxy_dir, exist_ok=True)
    for name in LINKED:
        link = os.path.join(proxy_dir, name)
        if os.path.lexists(link):
            os.unlink(link)
        os.symlink(os.path.join(REAL_DIR, name), link)
    if os.path.lexists(sock):
        os.unlink(sock)
    listener = socket.socket(socket.AF_UNIX)
    listener.bind(sock)
    listener.listen(64)
    sys.stdout.flush()
    if os.fork():                                   # parent: ready, hand the path to the caller
        print(fake)
        return
    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    asyncio.run(serve(listener))


if __name__ == "__main__":
    if len(sys.argv) != 2 or not HIS:
        sys.exit("usage: ipc-proxy.py PROXY_DIR  (inside a Hyprland session)")
    main(os.path.abspath(sys.argv[1]))
