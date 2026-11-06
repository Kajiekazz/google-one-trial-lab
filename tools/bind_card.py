"""绑定银行卡到 Google 账号（wallet.google.com → 添加支付方式）。

为什么这样写（三个坑，见 docs/pitfalls.md）：
  1. 全程不按 Escape —— Escape 会关掉整个「添加支付方式」对话框
  2. 每次操作前重新抓 instrument_manager frame —— 填卡后该 iframe 会 reload
  3. 地址栏用 JS focus() + keyboard.type() —— 补全浮层会遮挡 force click

用法:
    python tools/bind_card.py --port 9342
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common  # noqa: E402

CARD_SELECTORS = [
    ("input[name=cardnumber]", "number"),
    ("input[name=ccmonth]", "exp_month"),
    ("input[name=ccyear]", "exp_year"),
    ("input[name=cvc]", "cvc"),
]


async def open_form(ctx, page):
    await page.bring_to_front()
    await page.goto("https://wallet.google.com/wallet/paymentmethods", wait_until="domcontentloaded")
    await asyncio.sleep(5)
    btn = page.locator("button:has-text('添加支付方式'), [role=button]:has-text('添加支付方式')").first
    await btn.click(timeout=15000)
    _, fr = await common.wait_frame(ctx, "instrument_manager", 25)
    return fr


async def js_focus(fr, sel):
    return await fr.evaluate(
        "s => { const e = document.querySelector(s); if (!e) return false; e.focus(); return true; }", sel
    )


async def kb_type(page, fr, sel, val):
    if not await js_focus(fr, sel):
        print(f"  [skip] 找不到字段 {sel}")
        return False
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Delete")
    await page.keyboard.type(str(val), delay=80)
    await asyncio.sleep(0.6)
    return True


async def snapshot(fr):
    return await fr.evaluate(
        """() => {
             const g = n => { const e = document.querySelector(`input[name="${n}"]`); return e ? e.value : null; };
             return {number: g('cardnumber'), exp_month: g('ccmonth'), exp_year: g('ccyear'),
                     cvc: g('cvc'), holder: g('ccname'),
                     addr1: g('ADDRESS_LINE_1'), addr2: g('ADDRESS_LINE_2'), city: g('LOCALITY'),
                     state: (document.querySelector('input[autocomplete="address-level1"]') || {}).value,
                     zip: g('POSTAL_CODE'), country: g('COUNTRY')}; }"""
    )


async def fill(ctx, page, card, addr):
    # ---- 卡信息：locator 点击 + 输入（这一段的 frame 是稳定的）
    for sel, key in CARD_SELECTORS:
        for _ in range(3):
            _, fr = await common.wait_frame(ctx, "instrument_manager", 20)
            if not fr:
                return None
            try:
                loc = fr.locator(sel).first
                await loc.click(timeout=8000)
                await loc.fill("", force=True)
                await loc.type(str(card[key]), delay=70)
                break
            except Exception as e:  # iframe 正在 reload
                print(f"  [retry] {sel}: {str(e)[:50]}")
                await asyncio.sleep(1.5)
        await asyncio.sleep(0.4)
    await asyncio.sleep(2.2)

    _, fr = await common.wait_frame(ctx, "instrument_manager", 20)
    print("[after-card]", json.dumps(await snapshot(fr), ensure_ascii=False))

    # ---- 地址：JS focus + 键盘输入，不产生鼠标事件，避免被补全浮层吃掉
    await kb_type(page, fr, "input[name=ADDRESS_LINE_1]", addr["address_line1"])
    await asyncio.sleep(0.8)
    await kb_type(page, fr, "input[name=LOCALITY]", addr["locality"])
    await asyncio.sleep(0.8)

    # ---- 州：combobox，输入州名后从补全列表里选
    st = addr.get("state_name") or addr.get("province") or ""
    await kb_type(page, fr, 'input[autocomplete="address-level1"]', st)
    await asyncio.sleep(2.0)
    try:
        item = fr.locator(".goog-menuitem", has_text=addr.get("state_name", "")).first
        if await item.count():
            await item.click(timeout=6000)
            print(f"[pick] {addr.get('state_name')}")
    except Exception as e:
        print("[pick-err]", str(e)[:70])

    await asyncio.sleep(1.5)
    await kb_type(page, fr, "input[name=POSTAL_CODE]", addr["postal_code"])
    await asyncio.sleep(1.5)
    return fr


async def main():
    cfg = common.load_config()
    port = common.arg_port(cfg.get("port", 9342))
    card = cfg["card"]
    addr = cfg["billing_address"]

    pw, ctx, page = await common.connect(port)
    try:
        for round_no in range(2):
            fr = await open_form(ctx, page)
            if not fr:
                print(f"[round {round_no}] 弹窗没打开")
                continue
            fr = await fill(ctx, page, card, addr)
            if not fr:
                continue

            snap = await snapshot(fr)
            print("[before-save]", json.dumps(snap, ensure_ascii=False))
            if not all(snap.get(k) for k in ("number", "addr1", "city", "zip")):
                print(f"[round {round_no}] 字段不全，重来")
                continue

            save = fr.locator('div[role=button]:has-text("保存"), button:has-text("保存")').first
            await save.click(timeout=15000)   # locator.click 是真实事件
            print("[clicked] 保存")
            await asyncio.sleep(14)
            print("[result]", "弹窗已关闭 → 绑卡成功" if not common.find_frame(ctx, "instrument_manager")[1]
                  else "弹窗仍开 → 看截图确认错误提示")
            break
    finally:
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
