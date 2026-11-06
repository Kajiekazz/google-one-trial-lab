"""关闭 Google Play 订阅的自动续费（幂等）。

为什么要立刻做：账单是 bundle（AI Pro 12 个月试用 + YouTube 附加包 1 个月试用），
不关续费的话 30 天后会拿卡去扣附加包月费，扣失败会把整个订阅拖停。

用法:
    python tools/cancel_renewal.py --port 9342
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common  # noqa: E402

URL = "https://play.google.com/store/account/subscriptions?hl=zh-CN"


async def main():
    port = common.arg_port()
    pw, ctx, page = await common.connect(port)
    try:
        await page.goto(URL, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        txt = await common.body_text(page, limit=600)
        print("[before]", txt)

        if "已取消" in txt:
            print("[skip] 已经是已取消状态")
            return

        for text, label in (("管理", "manage"), ("取消订阅", "open-dialog"), ("取消订阅", "confirm")):
            ok = await common.click_text(page, text)
            print(f"[click] {text} ({label}) -> {ok}")
            if not ok:
                break

        await page.goto(URL, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        print("[after]", await common.body_text(page, limit=600))
        shots = os.path.join(common.ROOT, "shots")
        os.makedirs(shots, exist_ok=True)
        await page.screenshot(path=os.path.join(shots, "after_cancel.png"))
    finally:
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
