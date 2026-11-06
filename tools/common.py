"""公共工具：配置加载、CDP 连接、页面文本、可信点击、frame 定位。"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- config

def load_config(path=None):
    path = path or os.path.join(ROOT, "config.json")
    if not os.path.exists(path):
        raise SystemExit(f"缺少配置文件: {path}\n请复制 config.example.json 为 config.json 后填写。")
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def arg_port(default=9342):
    """从命令行取 --port，缺省用配置里的 port。"""
    argv = sys.argv[1:]
    if "--port" in argv:
        return int(argv[argv.index("--port") + 1])
    try:
        return int(load_config().get("port") or default)
    except SystemExit:
        return default


# ---------------------------------------------------------------- browser

async def connect(port):
    """接管一个已经用 --remote-debugging-port 启动的 Chrome。

    注意：这里不自己启动浏览器，profile / 代理 / 登录态都由调用方掌控。
    """
    pw = await async_playwright().start()
    br = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    ctx = br.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await page.set_viewport_size({"width": 1400, "height": 950})
    await page.bring_to_front()
    return pw, ctx, page


async def body_text(page, sep=" | ", limit=None):
    txt = await page.evaluate(
        "(sep) => (document.body.innerText || '').replace(/\\s+/g, sep)", sep
    )
    return txt[:limit] if limit else txt


# ---------------------------------------------------------------- click

async def click_text(page, text, exact=True, wait=3.0, pick="last"):
    """用真实鼠标事件点一个文本节点，返回是否点到了。

    element.click() 之类的合成事件会被 Google 的敏感操作风控拦掉，
    所以这里统一走 mouse.down / mouse.up。
    """
    box = await page.evaluate(
        """([txt, exact, pick]) => {
          const els = Array.from(document.querySelectorAll('button,[role=button],a,span,div'));
          const hits = els.filter(e => {
            const t = (e.innerText || '').trim();
            const ok = exact ? (t === txt) : t.includes(txt);
            const r = e.getBoundingClientRect();
            return ok && r.width > 0 && r.height > 0;
          });
          if (!hits.length) return null;
          const e = pick === 'first' ? hits[0] : hits[hits.length - 1];
          e.scrollIntoView({block: 'center'});
          const r = e.getBoundingClientRect();
          return {x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2)};
        }""",
        [text, exact, pick],
    )
    if not box:
        return False
    await page.mouse.move(box["x"], box["y"])
    await asyncio.sleep(0.25)
    await page.mouse.down()
    await asyncio.sleep(0.1)
    await page.mouse.up()
    await asyncio.sleep(wait)
    return True


# ---------------------------------------------------------------- frames

def find_frame(ctx, key):
    """按 URL 关键字找 frame（如 instrument_manager）。"""
    for p in ctx.pages:
        for f in p.frames:
            if key in (f.url or ""):
                return p, f
    return None, None


async def wait_frame(ctx, key, timeout=25.0):
    """等 frame 出现。iframe 会 reload，所以每次操作前都要重新拿。"""
    for _ in range(int(timeout * 2)):
        p, f = find_frame(ctx, key)
        if f:
            return p, f
        await asyncio.sleep(0.5)
    return None, None
