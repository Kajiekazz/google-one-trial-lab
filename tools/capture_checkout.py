"""给页面装 XHR / fetch 钩子，抓 Google Play 结账链路（Ngbm / eacquire）的请求与响应。

用于研究结账弹窗到底发了什么、服务端回了什么错误码。**不点「订阅」。**

用法:
    python tools/capture_checkout.py --port 9342
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common  # noqa: E402

CAPTURE_JS = r"""
(() => {
  if (window.__CAP_INSTALLED) return;
  window.__CAP_INSTALLED = true;
  window.__CAP = [];
  const push = (o) => { try { window.__CAP.push(o); if (window.__CAP.length > 40) window.__CAP.shift(); } catch (e) {} };

  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__u = String(u); this.__m = m; return origOpen.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (body) {
    const self = this;
    push({ t: 'xhr-req', m: self.__m, u: String(self.__u || '').slice(0, 300),
           body: (typeof body === 'string' ? body.slice(0, 2000) : null) });
    self.addEventListener('load', function () {
      let txt = '';
      try { txt = String(self.responseText || '').slice(0, 8000); } catch (e) {}
      push({ t: 'xhr-res', u: String(self.__u || '').slice(0, 300), status: self.status, body: txt });
    });
    return origSend.apply(this, arguments);
  };

  const of = window.fetch;
  if (of) {
    window.fetch = function () {
      const args = arguments;
      const u = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
      return of.apply(this, args).then((res) => {
        try {
          res.clone().text().then((t) => push({ t: 'fetch-res', u: String(u).slice(0, 300),
                                                status: res.status, body: String(t || '').slice(0, 8000) }))
                        .catch(() => {});
        } catch (e) {}
        return res;
      });
    };
  }
})();
"""

KEYS = ("Ngbm", "eacquire", "payment", "buyflow", "instrument")


async def main():
    port = common.arg_port()
    pw, ctx, page = await common.connect(port)
    try:
        await ctx.add_init_script(CAPTURE_JS)
        await page.goto("https://one.google.com/plans?hl=zh-CN", wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # 只点方案区按钮（升级 / 获取优惠），不点结账弹窗里的「订阅」
        clicked = await page.evaluate(
            """() => {
              const els = Array.from(document.querySelectorAll('button, a, [role="button"]'));
              const btns = els.filter(e => {
                const t = (e.innerText || '').trim();
                const r = e.getBoundingClientRect();
                return r.width > 15 && r.height > 15 && (
                  t.includes('开始使用') || t.includes('获取优惠') || t.includes('换用此方案') ||
                  t === '升级' || t === 'Upgrade' || t.includes('Get started'));
              });
              if (!btns.length) return null;
              const b = btns[btns.length - 1];
              b.scrollIntoView({block: 'center'});
              b.click();
              return (b.innerText || '').trim();
            }"""
        )
        print("[clicked]", clicked)
        await asyncio.sleep(12)

        for p in ctx.pages:
            for f in p.frames:
                try:
                    caps = await f.evaluate("() => window.__CAP || []")
                except Exception:
                    continue
                hits = [c for c in caps if any(k in c.get("u", "") for k in KEYS)]
                if not hits:
                    continue
                print(f"\n===== frame: {(f.url or '')[:100]}  ({len(hits)} captured) =====")
                for c in hits:
                    print(f"[{c.get('t')}] {c.get('status', '')} {c.get('u', '')}")
                    if c.get("body"):
                        print("   ", c["body"][:1500].replace("\n", " "))
    finally:
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
