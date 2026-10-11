#!/usr/bin/env python3
# =============================================================================
#  aichat/aichat.py — AI chat window (GTK 4 + libadwaita)
# =============================================================================
#  A real application window (class dev.inkpaw.AIChat), tall and narrow,
#  docked on one side of the screen (AI_SIDE, AI_WIDTH) like in the mockup
#  Mew-AIChat: while it is open, the current workspace gets a wider outer gap
#  on that side (workspace rule sent with hyprctl eval), so the tiled windows
#  (your terminal…) shrink and move aside instead of being covered; the chat
#  window floats in that strip with exactly the height of the tiled windows
#  (geometry from the monitor's reserved area + GAPS_OUT, window rule
#  "aichat"). Only WINDOWS move: the bar, the notifications (swaync, always at
#  the screen edge, over the chat) and the tooltips keep the whole screen.
#  Closing the chat gives the workspace its normal gaps back.
#  Opened by the 󰚩 bar button or SUPER+I. Run it again to close it.
#
#  Providers (AI_PROVIDER in settings, page "AI assistant"):
#    claude      Anthropic API through the official `anthropic` Python SDK
#                (package python-anthropic). Streams, adaptive thinking with
#                AI_EFFORT, and server-side refusal fallback ("default").
#    openai | ollama | openrouter | custom
#                any OpenAI-compatible /chat/completions endpoint (AI_BASE_URL)
#
#  API keys never live in settings.conf: they are stored by the settings
#  window in ~/.local/state/inkpaw/secrets.conf (mode 600). For Claude,
#  without a stored key the SDK's own credentials are used (ANTHROPIC_API_KEY
#  or an `ant auth login` profile).
#
#  Conversations: several chats are kept in ~/.local/state/inkpaw/
#  aichat-chats.json (the old single aichat.json is imported once). The list
#  button of the header (or Ctrl+O) shows them, newest first, with a search
#  field: click one to continue it, ✎ renames it, the bin deletes it. A new
#  chat (＋ or Ctrl+N) is titled after its first question. The last open chat
#  comes back when the window opens again.
#  Answers are rendered as full Markdown (markdown-it-py, CommonMark + tables +
#  strikethrough): headings, paragraphs, bold / italic / strikethrough, inline
#  code, links (clickable), bullet / numbered / nested / task lists, quotes,
#  fenced code blocks (language label + Copy button, scroll sideways), tables,
#  rules. Re-rendered while the answer streams. Without markdown-it-py the old
#  light renderer (one Pango label) is used.
#  Keys: Enter = send · Shift+Enter = new line · Ctrl+N = new chat ·
#        Ctrl+O = conversations · Esc = back to the chat / close
#
#  Skins: with UI_SKIN set (e.g. "encre", hyprtheme/skin.sh), the generated
#  aichat/skins/<skin>.css (template hyprtheme/templates/aichat-<skin>.css) is
#  loaded after the built-in CSS, and the "encre" skin adds its cat mascot to
#  the header and a paw on the send button. UI_SKIN="default" = built-in look.
# =============================================================================
import os
import sys

import json
import re
import subprocess
import threading
import urllib.error
import urllib.request

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

HOME = os.path.expanduser("~")
CFG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
HISTORY = os.path.join(STATE, "aichat.json")          # old single conversation (imported once)
CHATS = os.path.join(STATE, "aichat-chats.json")
MAX_CHATS = 100           # oldest conversations beyond this are dropped
MAX_MESSAGES = 200        # per conversation

DEFAULT_URLS = {
    "openai": "https://api.openai.com/v1",
    "ollama": "http://localhost:11434/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}
KEY_NAMES = {"claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
             "openrouter": "OPENROUTER_API_KEY", "custom": "AI_CUSTOM_API_KEY", "ollama": ""}


def esc(text):
    return GLib.markup_escape_text(text or "")


# --- settings -------------------------------------------------------------------------
def read_conf(path, into=None):
    into = {} if into is None else into
    try:
        with open(path) as f:
            for line in f:
                m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
                if not m or line.lstrip().startswith("#"):
                    continue
                v = re.sub(r'\s+#.*$', "", m.group(2))
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                into[m.group(1)] = v
    except OSError:
        pass
    return into


def settings():
    s = read_conf(os.path.join(CFG, "hypr", "settings.conf"))
    read_conf(os.path.join(STATE, "toggles.conf"), s)
    return s


def skin_of(conf):
    """Active interface skin ("default" = built-in look)."""
    return conf.get("UI_SKIN") or "default"


def skin_css(skin):
    """Generated stylesheet of a skin, or None (default skin / not rendered yet)."""
    path = os.path.join(CFG, "aichat", "skins", f"{skin}.css")
    return path if skin != "default" and os.path.isfile(path) else None


def css_colors(path):
    """{name: "#hex"} of the "@define-color name #hex;" lines of a stylesheet."""
    colors = {}
    try:
        with open(path) as f:
            for m in re.finditer(r"@define-color\s+(\w+)\s+(#[0-9A-Fa-f]{3,8})\s*;", f.read()):
                colors[m.group(1)] = m.group(2)
    except OSError:
        pass
    return colors


def secret(name):
    if not name:
        return ""
    return read_conf(os.path.join(STATE, "secrets.conf")).get(name, "")


# --- light Markdown -> Pango (bold, italic, inline code, code blocks, headings) ----------
# Look of code spans; a skin replaces it (encre: ink background, paper text, Courier Prime).
CODE = {"font": "monospace", "bg": "#00000033", "fg": None}


def code_span(text):
    fg = f' foreground="{CODE["fg"]}"' if CODE["fg"] else ""
    return f'<span font_family="{CODE["font"]}" background="{CODE["bg"]}"{fg}>{text}</span>'


def to_markup(text):
    out, in_code = [], False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            out.append(code_span(f" {esc(line)} "))
            continue
        line = esc(line)
        line = re.sub(r"^#{1,6}\s+(.*)$", r"<b>\1</b>", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", line)
        line = re.sub(r"`([^`]+)`", lambda m: code_span(m.group(1)), line)
        line = re.sub(r"^\s*[-*]\s+", "  • ", line)
        out.append(line)
    return "\n".join(out)


# --- full Markdown (markdown-it-py) -----------------------------------------------------------
try:
    from markdown_it import MarkdownIt
    MD = MarkdownIt("commonmark", {"html": False, "breaks": True}).enable(["table", "strikethrough"])
except ImportError:                     # python-markdown-it-py missing: light renderer only
    MD = None


def inline_markup(tokens):
    """Pango markup of the children of an inline token."""
    out = []
    for t in tokens or []:
        k = t.type
        if k == "text":
            out.append(esc(t.content))
        elif k in ("softbreak", "hardbreak"):
            out.append("\n")
        elif k == "strong_open":
            out.append("<b>")
        elif k == "strong_close":
            out.append("</b>")
        elif k == "em_open":
            out.append("<i>")
        elif k == "em_close":
            out.append("</i>")
        elif k == "s_open":
            out.append("<s>")
        elif k == "s_close":
            out.append("</s>")
        elif k == "code_inline":
            out.append(code_span(esc(t.content)))
        elif k == "link_open":
            href = t.attrs.get("href", "")
            out.append(f'<a href="{GLib.markup_escape_text(href)}">' if re.match(r"^(https?|mailto|file):", href)
                       else "<u>")
        elif k == "link_close":
            out.append("</a>")                  # fix_links() turns it into the right closer
        elif k == "image":
            out.append(f"[{esc(t.content or t.attrs.get('alt', 'image'))}]")
        else:                                    # html_inline… shown as text
            out.append(esc(t.content))
    return fix_links("".join(out))


def fix_links(markup):
    """link_close does not know its opener: pair every <a …> / <u> with the right closer."""
    res, stack, i = [], [], 0
    for m in re.finditer(r"<a href=\"[^\"]*\">|<u>|</a>|</u>", markup):
        res.append(markup[i:m.start()])
        tag = m.group(0)
        if tag.startswith("<a") or tag == "<u>":
            stack.append("</a>" if tag.startswith("<a") else "</u>")
            res.append(tag)
        else:
            res.append(stack.pop() if stack else "")
        i = m.end()
    res.append(markup[i:])
    return "".join(res)


def md_label(markup, css=None):
    lbl = Gtk.Label(wrap=True, wrap_mode=2, xalign=0, selectable=True, use_markup=True)
    lbl.set_markup(markup)
    if css:
        lbl.add_css_class(css)
    return lbl


class Markdown:
    """Turns markdown-it block tokens into GTK widgets (one Gtk.Box per block level)."""

    def __init__(self, on_copy):
        self.on_copy = on_copy

    def render(self, text, box):
        tokens = MD.parse(text or "")
        self.blocks(tokens, 0, len(tokens), box)

    def blocks(self, tk, i, end, box, tight=False):
        while i < end:
            t = tk[i]
            k = t.type
            if k == "heading_open":
                lvl = min(int(t.tag[1]), 4)
                box.append(md_label(inline_markup(tk[i + 1].children), f"md-h{lvl}"))
                i += 3
            elif k == "paragraph_open":
                if not t.hidden or not tight:
                    box.append(md_label(inline_markup(tk[i + 1].children), "md-p"))
                else:
                    box.append(md_label(inline_markup(tk[i + 1].children), "md-li-text"))
                i += 3
            elif k in ("bullet_list_open", "ordered_list_open"):
                close = self.match(tk, i)
                box.append(self.list(tk, i, close))
                i = close + 1
            elif k == "blockquote_open":
                close = self.match(tk, i)
                q = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, css_classes=["md-quote"])
                self.blocks(tk, i + 1, close, q)
                box.append(q)
                i = close + 1
            elif k in ("fence", "code_block"):
                box.append(self.code(t.content.rstrip("\n"), (t.info or "").split(" ")[0]))
                i += 1
            elif k == "table_open":
                close = self.match(tk, i)
                box.append(self.table(tk, i, close))
                i = close + 1
            elif k == "hr":
                box.append(Gtk.Separator(css_classes=["md-hr"]))
                i += 1
            elif k == "html_block":
                box.append(md_label(esc(t.content.strip()), "md-p"))
                i += 1
            else:
                i += 1

    @staticmethod
    def match(tk, i):
        """Index of the closing token of tk[i] (same nesting level)."""
        depth, close = 0, tk[i].type.replace("_open", "_close")
        for j in range(i, len(tk)):
            if tk[j].type == tk[i].type:
                depth += 1
            elif tk[j].type == close:
                depth -= 1
                if depth == 0:
                    return j
        return len(tk) - 1

    def list(self, tk, i, close):
        ordered = tk[i].type == "ordered_list_open"
        n = int(tk[i].attrs.get("start", 1) or 1) if ordered else 0
        lst = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, css_classes=["md-list"])
        j = i + 1
        while j < close:
            if tk[j].type == "list_item_open":
                end = self.match(tk, j)
                item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True)
                self.blocks(tk, j + 1, end, item, tight=True)
                mark = f"{n}." if ordered else "•"
                first = item.get_first_child()
                # task lists: "[ ] x" / "[x] x"
                if isinstance(first, Gtk.Label):
                    m = re.match(r"^\[( |x|X)\]\s+", first.get_text())
                    if m:
                        mark = "☑" if m.group(1) in "xX" else "☐"
                        first.set_markup(re.sub(r"^\[( |x|X)\]\s+", "", first.get_label(), count=1))
                row = Gtk.Box(spacing=6)
                row.append(Gtk.Label(label=mark, valign=Gtk.Align.START, css_classes=["md-bullet"]))
                row.append(item)
                lst.append(row)
                n += 1
                j = end + 1
            else:
                j += 1
        return lst

    def code(self, text, lang):
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=["md-code"])
        head = Gtk.Box(spacing=4, css_classes=["md-code-head"])
        head.append(Gtk.Label(label=lang or "code", xalign=0, hexpand=True, css_classes=["md-code-lang"]))
        copy = Gtk.Button(label="Copy", css_classes=["flat", "md-code-copy"])
        copy.connect("clicked", lambda *_: self.on_copy(text))
        head.append(copy)
        frame.append(head)
        body = Gtk.Label(label=text, xalign=0, selectable=True, css_classes=["md-code-body"])
        frame.append(Gtk.ScrolledWindow(child=body, vscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=False,
                                        hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                                        propagate_natural_height=True))
        return frame

    def table(self, tk, i, close):
        grid = Gtk.Grid(css_classes=["md-table"], column_homogeneous=False)
        r = c = 0
        for j in range(i, close):
            t = tk[j]
            if t.type == "tr_open":
                c = 0
            elif t.type == "tr_close":
                r += 1
            elif t.type in ("th_open", "td_open"):
                style = t.attrs.get("style", "") or ""
                lbl = md_label(inline_markup(tk[j + 1].children), "md-th" if t.type == "th_open" else "md-td")
                lbl.set_xalign(1 if "right" in style else 0.5 if "center" in style else 0)
                # one line per cell: a wrapping label in a sideways scroller would be
                # measured at its narrowest (very tall); wide tables scroll instead
                lbl.set_wrap(False)
                grid.attach(lbl, c, r, 1, 1)
                c += 1
        return Gtk.ScrolledWindow(child=grid, vscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=False,
                                  hscrollbar_policy=Gtk.PolicyType.AUTOMATIC, propagate_natural_height=True)


class MdBubble(Gtk.Box):
    """Assistant bubble: Markdown blocks, or one plain markup label (dots, errors)."""

    def __init__(self, on_copy):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True, vexpand=False)
        self.md = Markdown(on_copy)
        self.pending = None
        self.text = ""
        self.actions = None            # the "Copy" row under the bubble (set by add_bubble)

    def clear(self):
        while (c := self.get_first_child()) is not None:
            self.remove(c)

    def set_markup(self, markup):
        self.clear()
        self.append(md_label(markup))
        self.show_actions(False)            # dots / error: nothing to copy

    def show_actions(self, on):
        if self.actions is not None:
            self.actions.set_visible(on)

    def set_markdown(self, text):
        self.text = text or ""
        self.show_actions(bool(self.text.strip()) and self.pending is None and self.text != "…")
        self.clear()
        if MD is None:
            self.append(md_label(to_markup(text)))
        else:
            self.md.render(text, self)

    def stream(self, text):
        """Re-render at most every 120 ms while the answer streams in."""
        self.latest = text
        self.show_actions(False)
        if self.pending is None:
            self.pending = GLib.timeout_add(120, self.flush)

    def flush(self):
        self.pending = None
        self.set_markdown(self.latest)
        self.show_actions(False)            # still streaming: copy when it is finished
        return False

    def done(self, text):
        if self.pending is not None:
            GLib.source_remove(self.pending)
            self.pending = None
        self.set_markdown(text)
        self.show_actions(bool((text or "").strip()))


# --- providers ------------------------------------------------------------------------------
class ChatError(Exception):
    pass


def ask_claude(conf, history, on_text):
    """Stream one answer from Claude. Returns the assistant content blocks (dicts)."""
    try:
        import anthropic
    except ImportError:
        raise ChatError("The Claude provider needs the Anthropic Python SDK:\n"
                        "    yay -S python-anthropic\n"
                        "or pick another provider in Settings → AI assistant.")
    key = secret("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
    messages = []
    for m in history:
        if m["role"] == "assistant" and m.get("blocks"):
            messages.append({"role": "assistant", "content": m["blocks"]})   # keep thinking blocks as-is
        else:
            messages.append({"role": m["role"], "content": m["text"]})
    try:
        with client.beta.messages.stream(
            model=conf.get("AI_MODEL") or "claude-opus-5-5",
            max_tokens=64000,
            system=conf.get("AI_SYSTEM_PROMPT") or DEFAULT_SYSTEM,
            messages=messages,
            output_config={"effort": conf.get("AI_EFFORT") or "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            for text in stream.text_stream:
                on_text(text)
            final = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise ChatError("Claude rejected the API key. Add or fix it in Settings → AI assistant.")
    except anthropic.PermissionDeniedError as e:
        raise ChatError(f"Not allowed: {e.message}")
    except anthropic.NotFoundError:
        raise ChatError(f"Unknown model “{conf.get('AI_MODEL')}”. Check Settings → AI assistant.")
    except anthropic.RateLimitError:
        raise ChatError("Rate limited by the Claude API, try again in a moment.")
    except anthropic.APIConnectionError:
        raise ChatError("Cannot reach the Claude API (network?).")
    except anthropic.APIStatusError as e:
        raise ChatError(f"Claude API error {e.status_code}: {e.message}")
    if final.stop_reason == "refusal":
        on_text("\n\n_(The model declined to answer this request.)_")
    elif final.stop_reason == "max_tokens":
        on_text("\n\n_(Answer cut: maximum length reached.)_")
    return [b.model_dump(mode="json", exclude_none=True) for b in final.content]


def ask_openai_compatible(conf, history, on_text):
    provider = conf.get("AI_PROVIDER", "openai")
    base = (conf.get("AI_BASE_URL") or DEFAULT_URLS.get(provider, "")).rstrip("/")
    if not base:
        raise ChatError("Set the endpoint URL in Settings → AI assistant.")
    key = secret(KEY_NAMES.get(provider, ""))
    model = conf.get("AI_MODEL") or ""
    if not model or model.startswith("claude-"):
        raise ChatError(f"Choose a model for {provider} in Settings → AI assistant.")
    body = {"model": model, "stream": True,
            "messages": [{"role": "system", "content": conf.get("AI_SYSTEM_PROMPT") or DEFAULT_SYSTEM}]
            + [{"role": m["role"], "content": m["text"]} for m in history]}
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {key}"} if key else {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0].get("delta", {}).get("content")
                except (ValueError, KeyError, IndexError):
                    continue
                if delta:
                    on_text(delta)
    except urllib.error.HTTPError as e:
        raise ChatError(f"{provider} error {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    except urllib.error.URLError as e:
        raise ChatError(f"Cannot reach {base} ({e.reason}).")
    return None


DEFAULT_SYSTEM = ("You are a helpful assistant in a small side panel of a Linux desktop (Hyprland). "
                  "Answer concisely and use short paragraphs; Markdown is rendered lightly.")


# --- UI ---------------------------------------------------------------------------------------
CSS = """
window.aichat-backdrop { background: transparent; }
/* As a window, Hyprland draws the border, the corners and the shadow: the
   panel fills the window flat (rules repeated by WINDOW_CSS over the skin). */
.aichat {
    background-color: @window_bg_color;
    border: 1px solid alpha(@accent_bg_color, 0.55);
    border-radius: 16px;
    box-shadow: 0 14px 40px alpha(black, 0.40);
}
.aichat-head { padding: 10px 10px 6px 14px; }
.aichat-title { font-weight: 800; font-size: 15px; }
.aichat-model { font-size: 11px; opacity: 0.6; }
.bubble { padding: 9px 12px; border-radius: 14px; }
.bubble.user { background: alpha(@accent_bg_color, 0.85); color: @accent_fg_color; }
.bubble.assistant { background: alpha(currentColor, 0.06); }
.bubble.error { background: alpha(@error_color, 0.18); }
.aichat-input { padding: 8px 10px; border-radius: 12px; background: alpha(currentColor, 0.06); }
.aichat-input text { background: transparent; }
.aichat-empty { opacity: 0.5; font-size: 12px; }
/* Markdown of the answers */
.md-h1 { font-size: 19px; font-weight: 800; }
.md-h2 { font-size: 17px; font-weight: 800; }
.md-h3 { font-size: 15px; font-weight: 700; }
.md-h4 { font-size: 13px; font-weight: 700; }
.md-bullet { font-weight: 700; min-width: 16px; }
.md-quote { border-left: 3px solid alpha(@accent_bg_color, 0.8); padding-left: 10px; opacity: 0.9; }
.md-code { background: alpha(black, 0.28); border-radius: 10px; }
.md-code-head { padding: 2px 4px 0 10px; }
.md-code-lang { font-size: 10px; opacity: 0.65; }
.md-code-copy { font-size: 11px; min-height: 22px; padding: 0 8px; }
.md-code-body { font-family: monospace; padding: 4px 10px 9px 10px; }
.md-table { border: 1px solid alpha(currentColor, 0.2); border-radius: 8px; }
.md-th, .md-td { padding: 4px 9px; border-bottom: 1px solid alpha(currentColor, 0.12); }
.md-th { font-weight: 800; background: alpha(currentColor, 0.06); }
.md-hr { margin: 4px 0; opacity: 0.4; }
.bubble-copy { font-size: 11px; min-height: 24px; padding: 0 8px; opacity: 0.7; }
.bubble-copy:hover { opacity: 1; }
/* conversations list */
.chats-title { font-weight: 800; font-size: 15px; }
.chat-row { padding: 8px 10px; border-radius: 12px; }
.chat-row:hover { background: alpha(currentColor, 0.06); }
.chat-row.current { background: alpha(@accent_bg_color, 0.22); }
.chat-row-title { font-weight: 700; }
.chat-row-meta { font-size: 11px; opacity: 0.6; }
"""

# Loaded last (over a skin): the panel is the whole window, so no own frame
WINDOW_CSS = """
window.aichat-backdrop { background: transparent; }
window.aichat-backdrop .aichat { border: none; border-radius: 0; box-shadow: none; margin: 0; }
window.aichat-backdrop .aichat-head { border-radius: 0; }
"""

# Send-button paw of the "encre" skin (same pad shape as the mockup), {ink} = color
PAW_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="{ink}">'
           '<ellipse cx="12" cy="16" rx="5" ry="4"/><circle cx="5.5" cy="10" r="2.2"/>'
           '<circle cx="9.5" cy="6" r="2.2"/><circle cx="14.5" cy="6" r="2.2"/>'
           '<circle cx="18.5" cy="10" r="2.2"/></svg>')


class ChatApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.inkpaw.AIChat", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.win = None
        self.history = []
        self.chats, self.current = [], None
        self.busy = False
        self.skin = "default"
        self.skin_colors = {}

    def do_startup(self):
        Adw.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_activate(self):
        if self.win:                     # second launch = close (toggle)
            self.quit()
            return
        self.conf = settings()
        self.load_skin()
        frame = Gtk.CssProvider()
        frame.load_from_string(WINDOW_CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), frame,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2)
        self.load_history()
        self.build()

    def load_skin(self):
        """UI_SKIN != default: load aichat/skins/<skin>.css over the built-in CSS."""
        path = skin_css(skin_of(self.conf))
        if not path:
            return
        self.skin = skin_of(self.conf)
        css = Gtk.CssProvider()
        css.load_from_path(path)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
        self.skin_colors = css_colors(path)
        if self.skin == "encre" and "ink" in self.skin_colors:      # code blocks: ink plate, paper text
            CODE.update(font=self.conf.get("MONO_FONT") or "monospace",
                        bg=self.skin_colors["ink"], fg=self.skin_colors.get("paper"))

    def skin_picture(self, name, size):
        """Picture of a skin file (hyprtheme/skins/<skin>/cats/<name>.svg|png), or None."""
        base = os.path.join(CFG, "hyprtheme", "skins", self.skin, "cats", name)
        for path in (base + ".svg", base + ".png"):
            if os.path.isfile(path):
                pic = Gtk.Picture.new_for_filename(path)
                pic.set_content_fit(Gtk.ContentFit.CONTAIN)
                pic.set_can_shrink(True)
                pic.set_size_request(size, size)
                return pic
        return None

    # --- persistence: several conversations ---
    def load_history(self):
        """Read every conversation; self.history = the messages of the current one."""
        try:
            with open(CHATS) as f:
                data = json.load(f)
            self.chats = [c for c in data.get("chats", []) if isinstance(c, dict) and "id" in c]
            self.current = data.get("current")
        except (OSError, ValueError, AttributeError):
            self.chats, self.current = [], None
            try:                                         # first run: import the old single chat
                with open(HISTORY) as f:
                    old = json.load(f)
                if isinstance(old, list) and old:
                    self.chats = [self.make_chat(old)]
            except (OSError, ValueError):
                pass
        if not any(c["id"] == self.current for c in self.chats):
            self.current = self.chats[0]["id"] if self.chats else None
        self.history = self.chat()["messages"] if self.current else []

    @staticmethod
    def make_chat(messages=None):
        now = GLib.DateTime.new_now_local().to_unix()
        msgs = messages or []
        first = next((m["text"] for m in msgs if m.get("role") == "user"), "")
        return {"id": f"{now}-{os.getpid()}-{GLib.random_int()}", "title": ChatApp.title_of(first),
                "created": now, "updated": now, "messages": msgs}

    @staticmethod
    def title_of(text):
        line = " ".join((text or "").split())
        return (line[:42] + "…") if len(line) > 42 else (line or "New chat")

    def chat(self):
        return next((c for c in self.chats if c["id"] == self.current), None)

    def save_history(self, touch=True):
        """Write every conversation (the current one first gets self.history).
        touch=False: opening / renaming a chat does not move it to the top."""
        cur = self.chat()
        if cur is None and self.history:                 # first message of a brand new chat
            cur = self.make_chat()
            self.chats.insert(0, cur)
            self.current = cur["id"]
        if cur is not None:
            cur["messages"] = self.history[-MAX_MESSAGES:]
            self.history = cur["messages"]
            if cur.get("title") in (None, "", "New chat"):
                cur["title"] = self.title_of(next((m["text"] for m in self.history if m["role"] == "user"), ""))
            if touch:
                cur["updated"] = GLib.DateTime.new_now_local().to_unix()
        self.chats = [c for c in self.chats if c.get("messages")]       # drop empty chats
        self.chats.sort(key=lambda c: c.get("updated", 0), reverse=True)
        self.chats = self.chats[:MAX_CHATS]
        os.makedirs(STATE, exist_ok=True)
        tmp = CHATS + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"current": self.current, "chats": self.chats}, f)
        os.replace(tmp, CHATS)

    # --- docking: reserve a strip of the screen, place the window in it ---
    def dock_geometry(self, width):
        """(x, y, w, h) of the chat in the focused monitor, same height as the tiled windows."""
        gap = self.gap()
        try:
            mons = json.loads(subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True,
                                             text=True, timeout=2).stdout)
            m = next((m for m in mons if m.get("focused")), mons[0])
            scale = m.get("scale") or 1
            mw, mh = round(m["width"] / scale), round(m["height"] / scale)
            res = m.get("reserved") or [0, 0, 0, 0]          # left, top, right, bottom
            self.workspace = str((m.get("activeWorkspace") or {}).get("name") or "")
        except (OSError, ValueError, KeyError, IndexError, StopIteration, subprocess.SubprocessError):
            mw, mh, res = 1920, 1080, [0, 60, 0, 0]
        top, bottom = res[1] + gap, res[3] + gap
        side = self.conf.get("AI_SIDE", "right")
        x = gap + res[0] if side == "left" else mw - res[2] - gap - width
        # the rule places the window INSIDE its border, like the tiled windows
        b = 1 if self.conf.get("GAMEMODE") == "true" else int(float(self.conf.get("BORDER_SIZE") or 2))
        return x + b, top + b, width - 2 * b, mh - top - bottom - 2 * b

    def gap(self):
        return 0 if self.conf.get("GAMEMODE") == "true" else int(float(self.conf.get("GAPS_OUT") or 12))

    def dock(self, width):
        """Window rule with the exact geometry + wider outer gaps on this workspace.

        The tiled windows of the current workspace stop one gap before the chat
        (a workspace rule: it only moves WINDOWS — no exclusive zone, so the bar,
        the notifications and the tooltips of this window keep the whole screen)."""
        gap = self.gap()
        x, y, w, h = self.dock_geometry(width)
        rule = ('hl.window_rule({ name = "aichat", match = { class = "^(dev.inkpaw.AIChat)$" }, '
                f'float = true, size = "{w} {h}", move = "{x} {y}", opacity = "1.0 override 1.0 override" }})')
        side = "left" if self.conf.get("AI_SIDE", "right") == "left" else "right"
        gaps = {"top": gap, "right": gap, "bottom": gap, "left": gap}
        gaps[side] = gap + width + gap
        self.hypr_eval(rule)
        if getattr(self, "workspace", ""):
            self.hypr_eval(self.ws_rule(", ".join(f"{k} = {v}" for k, v in gaps.items())))
            self.docked = True

    def undock(self):
        """Give the workspace its normal gaps back (window closed)."""
        if getattr(self, "docked", False):
            self.hypr_eval(self.ws_rule(str(self.gap())), wait=True)
            self.docked = False

    def ws_rule(self, gaps):
        name = self.workspace.replace("\\", "").replace('"', "")
        return f'hl.workspace_rule({{ workspace = "{name}", gaps_out = {{ {gaps} }} }})' if "=" in gaps \
            else f'hl.workspace_rule({{ workspace = "{name}", gaps_out = {gaps} }})'

    @staticmethod
    def hypr_eval(code, wait=True):
        try:
            subprocess.run(["hyprctl", "eval", code], capture_output=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            pass

    def do_shutdown(self):
        self.undock()
        Adw.Application.do_shutdown(self)

    # --- window ---
    def build(self):
        c = self.conf
        width = int(c.get("AI_WIDTH") or 420)

        # A normal window: size / position / float come from the Hyprland rule
        # "aichat" (hypr/conf/windowrules.lua), the size here is the fallback
        self.dock(width)
        win = self.win = Adw.ApplicationWindow(application=self, title="Assistant")
        win.add_css_class("aichat-backdrop")
        win.set_default_size(width, 900)
        # closed by Hyprland (SUPER+Q…): quit, which also restores the gaps
        win.connect("close-request", lambda *_: (self.quit(), False)[1])

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.add_css_class("aichat")
        encre = self.skin == "encre"
        if encre:
            panel.set_overflow(Gtk.Overflow.HIDDEN)            # the ochre header follows the corners

        head = Gtk.Box(spacing=4)
        head.add_css_class("aichat-head")
        mascot = self.skin_picture("head-gribouille", 52) if encre else None
        if mascot is not None:                                 # encre: the 3-eyed grey cat
            mascot.set_valign(Gtk.Align.CENTER)
            mascot.add_css_class("aichat-mascot")
            head.append(mascot)
        # [mascot] | "Assistant" ........ [buttons]   ← title on the buttons' line
        #          | provider · model                ← model underneath
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        top = Gtk.Box(spacing=4)
        t = self.title_lbl = Gtk.Label(label="Assistant", xalign=0, hexpand=True, valign=Gtk.Align.CENTER)
        t.add_css_class("aichat-title")
        top.append(t)
        provider = c.get("AI_PROVIDER", "claude")
        self.model_text = f"{provider} · {c.get('AI_MODEL') or ('claude-opus-5-5' if provider == 'claude' else '?')}"
        m = self.subtitle = Gtk.Label(label=self.model_text, xalign=0, ellipsize=3)
        m.add_css_class("aichat-model")
        for icon, tip, cb in (("view-list-symbolic", "Conversations (Ctrl+O)", self.toggle_chats),
                              ("list-add-symbolic", "New chat (Ctrl+N)", self.new_chat),
                              ("emblem-system-symbolic", "AI settings", self.open_settings),
                              ("window-close-symbolic", "Close (Esc)", self.quit)):
            b = Gtk.Button(icon_name=icon, tooltip_text=tip, valign=Gtk.Align.CENTER)
            b.add_css_class("flat")
            b.add_css_class("circular")
            b.connect("clicked", lambda *_, cb=cb: cb())
            top.append(b)
        col.append(top)
        col.append(m)
        head.append(col)
        panel.append(head)

        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_start=12, margin_end=12,
                            margin_top=4, margin_bottom=8)
        self.scroll = Gtk.ScrolledWindow(child=self.list, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        chat_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        chat_page.append(self.scroll)
        self.stack = Gtk.Stack(vexpand=True, transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.add_named(chat_page, "chat")
        self.stack.add_named(self.build_chats_page(), "chats")
        panel.append(self.stack)
        self.toasts = Adw.ToastOverlay(child=panel)

        # input: multi-line, Enter sends, Shift+Enter new line
        bottom = Gtk.Box(spacing=6, margin_start=10, margin_end=10, margin_bottom=10)
        bottom.add_css_class("aichat-bottom")
        if encre:                       # the skin draws a full-width rule: spacing moves to its CSS padding
            bottom.set_margin_start(0)
            bottom.set_margin_end(0)
            bottom.set_margin_bottom(0)
            bottom.set_spacing(10)
        self.input = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, hexpand=True, accepts_tab=False)
        self.input.add_css_class("aichat-input")
        self.input.set_size_request(-1, 40)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_input_key)
        self.input.add_controller(keys)
        in_scroll = Gtk.ScrolledWindow(child=self.input, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                       propagate_natural_height=True, max_content_height=160)
        in_scroll.set_hexpand(True)
        self.send_btn = Gtk.Button(icon_name="mail-send-symbolic", valign=Gtk.Align.END, tooltip_text="Send (Enter)")
        self.send_btn.add_css_class("suggested-action")
        self.send_btn.add_css_class("circular")
        self.send_btn.add_css_class("aichat-send")
        if encre:                       # a paw instead of the paper plane
            try:
                svg = PAW_SVG.format(ink=self.skin_colors.get("ochre_fg", "#2a2420"))
                paw = Gdk.Texture.new_from_bytes(GLib.Bytes.new(svg.encode()))
                self.send_btn.set_child(Gtk.Image(paintable=paw, pixel_size=20))
            except GLib.Error:
                pass
            self.send_btn.set_valign(Gtk.Align.CENTER)
        self.send_btn.connect("clicked", lambda *_: self.send())
        bottom.append(in_scroll)
        bottom.append(self.send_btn)
        chat_page.append(bottom)

        win_keys = Gtk.EventControllerKey()
        win_keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        win_keys.connect("key-pressed", self.on_win_key)
        win.add_controller(win_keys)
        win.set_content(self.toasts)

        self.show_chat()
        win.present()
        self.input.grab_focus()

    def show_empty(self):
        self.empty = Gtk.Label(label="Ask anything…\nEnter to send · Shift+Enter for a new line",
                               justify=Gtk.Justification.CENTER, vexpand=True)
        self.empty.add_css_class("aichat-empty")
        self.list.append(self.empty)

    def add_bubble(self, role, text, css=None):
        if getattr(self, "empty", None) is not None:
            self.list.remove(self.empty)
            self.empty = None
        if role == "assistant":
            lbl = MdBubble(self.copy_text)
            lbl.set_markdown(text)
        else:
            lbl = Gtk.Label(wrap=True, wrap_mode=2, xalign=0, selectable=True, max_width_chars=48)
            lbl.set_markup(esc(text))
        lbl.add_css_class("bubble")
        lbl.add_css_class(css or role)
        lbl.set_halign(Gtk.Align.END if role == "user" else Gtk.Align.FILL)
        if role == "assistant":
            # answer + a "Copy" button under it (raw Markdown to the clipboard)
            wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            wrap.append(lbl)
            row = Gtk.Box(halign=Gtk.Align.START, css_classes=["bubble-actions"])
            copy = Gtk.Button(tooltip_text="Copy the answer", css_classes=["flat", "bubble-copy"])
            inner = Gtk.Box(spacing=5)
            inner.append(Gtk.Image(icon_name="edit-copy-symbolic"))
            inner.append(Gtk.Label(label="Copy"))
            copy.set_child(inner)
            copy.connect("clicked", lambda *_b, b=lbl: self.copy_text(b.text, "Answer copied"))
            row.append(copy)
            wrap.append(row)
            lbl.actions = row
            lbl.show_actions(bool(lbl.text.strip()) and lbl.text != "…")
            self.list.append(wrap)
        else:
            self.list.append(lbl)
        GLib.idle_add(self.scroll_bottom)
        return lbl

    def scroll_bottom(self):
        adj = self.scroll.get_vadjustment()
        adj.set_value(adj.get_upper())
        return False

    def on_input_key(self, _ctl, keyval, _code, state):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not (state & Gdk.ModifierType.SHIFT_MASK):
            self.send()
            return True
        return False

    # --- conversation ---
    def send(self):
        buf = self.input.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        if not text or self.busy:
            return
        buf.set_text("")
        self.history.append({"role": "user", "text": text})
        self.add_bubble("user", text)
        self.busy = True
        self.send_btn.set_sensitive(False)
        bubble = self.add_bubble("assistant", "…")
        if self.skin == "encre":        # "thinking" dots fading out, like the mockup
            bubble.set_markup('<span size="large">●</span> <span size="large" alpha="60%">●</span> '
                              '<span size="large" alpha="30%">●</span>   <b>the cat is thinking…</b>')
        parts = []

        def on_text(chunk):
            parts.append(chunk)
            GLib.idle_add(lambda: (bubble.stream("".join(parts)), self.scroll_bottom(), False)[2])

        def work():
            conf = settings()
            try:
                if conf.get("AI_PROVIDER", "claude") == "claude":
                    blocks = ask_claude(conf, self.history, on_text)
                else:
                    blocks = ask_openai_compatible(conf, self.history, on_text)
                GLib.idle_add(self.finished, "".join(parts), blocks, None, bubble)
            except ChatError as e:
                GLib.idle_add(self.finished, "".join(parts), None, str(e), bubble)
            except Exception as e:  # noqa: BLE001 - show anything unexpected in the panel
                GLib.idle_add(self.finished, "".join(parts), None, f"Unexpected error: {e}", bubble)
        threading.Thread(target=work, daemon=True).start()

    def finished(self, text, blocks, error, bubble):
        self.busy = False
        self.send_btn.set_sensitive(True)
        if error:
            bubble.set_markup(esc(error))
            bubble.remove_css_class("assistant")
            bubble.add_css_class("error")
            self.history.pop()                    # the question was not answered: forget it
        else:
            bubble.done(text)                     # final render (the stream is throttled)
            self.history.append({"role": "assistant", "text": text, **({"blocks": blocks} if blocks else {})})
            self.save_history()
            GLib.idle_add(self.scroll_bottom)
        self.input.grab_focus()
        return False

    def copy_text(self, text, what="Copied"):
        Gdk.Display.get_default().get_clipboard().set(text)
        self.toast(what)

    # --- conversations ---
    def show_chat(self):
        """Rebuild the bubbles of the current conversation."""
        while (c := self.list.get_first_child()) is not None:
            self.list.remove(c)
        self.empty = None
        for msg in self.history:
            self.add_bubble(msg["role"], msg["text"])
        if not self.history:
            self.show_empty()
        cur = self.chat()
        # the conversation's title: window title + tooltip of "Assistant"
        self.title_lbl.set_tooltip_text(cur["title"] if cur else "New chat")
        self.win.set_title(f"Assistant — {cur['title']}" if cur else "Assistant")

    def new_chat(self):
        if self.busy:
            return self.toast("Wait for the answer to finish")
        self.current, self.history = None, []
        self.show_chat()
        self.stack.set_visible_child_name("chat")
        self.input.grab_focus()

    def open_chat(self, cid):
        if self.busy:
            return self.toast("Wait for the answer to finish")
        self.current = cid
        self.history = self.chat()["messages"]
        self.save_history(touch=False)            # remember it as the last open chat
        self.show_chat()
        self.stack.set_visible_child_name("chat")
        self.input.grab_focus()

    def toggle_chats(self):
        if self.stack.get_visible_child_name() == "chats":
            self.stack.set_visible_child_name("chat")
            self.input.grab_focus()
        else:
            self.search.set_text("")
            self.fill_chats()
            self.stack.set_visible_child_name("chats")
            self.search.grab_focus()

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=2))

    def on_win_key(self, _ctl, keyval, _code, state):
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        if keyval == Gdk.KEY_Escape:
            if self.stack.get_visible_child_name() == "chats":
                self.toggle_chats()
            else:
                self.quit()
            return True
        if ctrl and keyval in (Gdk.KEY_n, Gdk.KEY_N):
            self.new_chat()
            return True
        if ctrl and keyval in (Gdk.KEY_o, Gdk.KEY_O):
            self.toggle_chats()
            return True
        return False

    def build_chats_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_start=12, margin_end=12,
                       margin_top=10, margin_bottom=12)
        page.add_css_class("aichat-chats")
        top = Gtk.Box(spacing=6)
        title = Gtk.Label(label="Conversations", xalign=0, hexpand=True)
        title.add_css_class("chats-title")
        top.append(title)
        new = Gtk.Button(label="＋ New chat", tooltip_text="Ctrl+N")
        new.add_css_class("chats-new")
        new.connect("clicked", lambda *_: self.new_chat())
        top.append(new)
        page.append(top)
        self.search = Gtk.SearchEntry(placeholder_text="Search the conversations…")
        self.search.add_css_class("chats-search")
        self.search.connect("search-changed", lambda *_: self.fill_chats())
        self.search.connect("activate", lambda *_: self.open_first_match())
        page.append(self.search)
        self.chat_rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.append(Gtk.ScrolledWindow(child=self.chat_rows, vexpand=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER))
        return page

    def matching_chats(self):
        q = self.search.get_text().strip().lower()
        if not q:
            return self.chats
        return [c for c in self.chats
                if q in c.get("title", "").lower() or any(q in m["text"].lower() for m in c["messages"])]

    def open_first_match(self):
        found = self.matching_chats()
        if found:
            self.open_chat(found[0]["id"])

    def fill_chats(self):
        while (c := self.chat_rows.get_first_child()) is not None:
            self.chat_rows.remove(c)
        found = self.matching_chats()
        if not found:
            empty = Gtk.Label(label="No conversation yet" if not self.chats else "Nothing found",
                              vexpand=True)
            empty.add_css_class("aichat-empty")
            self.chat_rows.append(empty)
        for c in found:
            self.chat_rows.append(self.chat_row(c))

    def chat_row(self, c):
        row = Gtk.Box(spacing=6)
        row.add_css_class("chat-row")
        if c["id"] == self.current:
            row.add_css_class("current")
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        name = Gtk.Label(label=c.get("title") or "New chat", xalign=0, ellipsize=3)
        name.add_css_class("chat-row-title")
        when = GLib.DateTime.new_from_unix_local(c.get("updated", 0)).format("%d %b · %H:%M")
        n = len(c["messages"])
        meta = Gtk.Label(label=f"{when} · {n} message{'s' if n != 1 else ''}", xalign=0)
        meta.add_css_class("chat-row-meta")
        texts.append(name)
        texts.append(meta)
        row.append(texts)
        click = Gtk.GestureClick()
        click.connect("released", lambda *_a, cid=c["id"]: self.open_chat(cid))
        texts.add_controller(click)
        texts.set_cursor_from_name("pointer")
        for icon, tip, cb in (("document-edit-symbolic", "Rename", lambda b, cid=c["id"], r=row, t=texts: self.rename(cid, r, t)),
                              ("user-trash-symbolic", "Delete", lambda b, cid=c["id"]: self.delete_chat(cid))):
            b = Gtk.Button(icon_name=icon, tooltip_text=tip, valign=Gtk.Align.CENTER)
            b.add_css_class("flat")
            b.add_css_class("circular")
            b.add_css_class("chat-row-btn")
            b.connect("clicked", cb)
            row.append(b)
        return row

    def rename(self, cid, row, texts):
        c = next(x for x in self.chats if x["id"] == cid)
        entry = Gtk.Entry(text=c.get("title", ""), hexpand=True)
        entry.add_css_class("chat-rename")

        def done(*_):
            c["title"] = self.title_of(entry.get_text()) if entry.get_text().strip() else c["title"]
            self.save_history(touch=False)
            self.fill_chats()
            if cid == self.current:
                self.show_chat()
        entry.connect("activate", done)
        row.insert_child_after(entry, texts)
        row.remove(texts)
        entry.grab_focus()

    def delete_chat(self, cid):
        if self.busy and cid == self.current:
            return self.toast("Wait for the answer to finish")
        self.chats = [c for c in self.chats if c["id"] != cid]
        if cid == self.current:
            self.current, self.history = None, []
            self.show_chat()
        self.save_history(touch=False)
        self.fill_chats()
        self.toast("Conversation deleted")

    def open_settings(self):
        subprocess.Popen([os.path.join(CFG, "hypr", "scripts", "settings-ui.sh"), "AI assistant"],
                         start_new_session=True)
        self.quit()


if __name__ == "__main__":
    sys.exit(ChatApp().run([]))
