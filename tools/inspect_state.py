"""只读盘点：订阅状态、订单记录、支付方式、Google One 会员页。

用来在动手前后各跑一次做对比，输出可以直接贴进 issue / 报告。

用法:
    python tools/inspect_state.py --port 9342
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common  # noqa: E402

TARGETS = [
    ("play_subscriptions", "https://play.google.com/store/account/subscriptions?hl=zh-CN", 6),
    ("play_orders", "https://play.google.com/store/account/orderhistory?hl=zh-CN", 7),
    ("play_paymentmethods", "https://play.google.com/store/paymentmethods?hl=zh-CN", 5),
    ("one_settings", "https://one.google.com/settings?hl=zh-CN", 7),
]


async def main():
    port = common.arg_port()
    pw, ctx, page = await common.connect(port)
    shots = os.path.join(common.ROOT, "shots")
    os.makedirs(shots, exist_ok=True)
    try:
        for tag, url, wait in TARGETS:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(wait)
            txt = await common.body_text(page, limit=900)
            print(f"\n### {tag}")
            print(txt)
            # 关键信号
            flags = {
                "已取消": "已取消" in txt,
                "下次付款": "下次付款" in txt,
                "US$0": "US$0" in txt,
            }
            print("[flags]", flags)
            await page.screenshot(path=os.path.join(shots, f"state_{tag}.png"))
    finally:
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
