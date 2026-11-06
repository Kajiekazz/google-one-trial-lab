# 绑卡环节的坑（Playwright / Google Payments）

全都在真实跑的时候才炸，静态看 DOM 完全看不出来。

## 坑 1：`Escape` 会关掉整个「添加支付方式」对话框

**现象**：填完「地址第 1 行」后想按 `Escape` 收起地址补全浮层，结果整个弹窗消失，
已经填好的卡号/有效期/CVC/地址全部丢失，`instrument_manager` iframe 直接销毁。

**原因**：`Escape` 是对话框级的关闭快捷键，被最外层接走了，不是输入框在消费。

**修法**：全程不按 `Escape`。收起补全浮层用「把焦点移到下一个字段」代替 ——
补全列表在输入框失焦时自然收起。

```python
await frame.evaluate("s => { const e = document.querySelector(s); if (e) e.focus(); }", sel)
await page.keyboard.press("Control+A")
await page.keyboard.press("Delete")
await page.keyboard.type(value, delay=80)
```

## 坑 2：填完卡号后 iframe 会 reload

**现象**：`Frame.evaluate: Frame was detached`。接下来所有基于旧 `Frame` 对象的操作全部失败。

**原因**：卡号/BIN 校验通过后，Google Payments 会重新加载 `instrument_manager`
（去拉地址区配置、国家规则、持卡人预填）。旧的 `Frame` 句柄失效。

**修法**：不要缓存 `Frame`。每次交互前按 URL 重新抓一次：

```python
def find_frame(ctx, key):
    for p in ctx.pages:
        for f in p.frames:
            if key in (f.url or ""):
                return p, f
    return None, None
```

## 坑 3：地址补全浮层遮挡下一个字段的点击

**现象**：`locator.click()` 超时；加 `force=True` 仍然超时。

**原因**：`ADDRESS_LINE_1` 输入后弹出的 `pac-item` / `goog-menuitem` 浮层盖住了
`LOCALITY`（市/区）输入框，Playwright 的可点击性检查过不去。`force=True` 只跳过
`receives events` 检查，但元素仍在浮层下方，命中测试落到浮层上。

**修法**：不点，用 `focus()` + `keyboard.type()`（见坑 1 的代码）。

## 坑 4：州是 combobox，不是 `<select>`

**现象**：直接 `fill("MI")` 之后 `input.value` 是 `MI`，但保存时报「州无效」。

**原因**：州字段是 `goog.ui.ComboBox`，`address-level1` 真正提交的是**选项的值**（`Michigan`），
不是输入文本。必须从补全列表里点一条。

**修法**：

```python
await kb_type(page, fr, 'input[autocomplete="address-level1"]', "Michigan")
await asyncio.sleep(2)
item = fr.locator(".goog-menuitem", has_text="Michigan").first
if await item.count():
    await item.click()      # locator.click 是真实事件，坐标由 Playwright 换算
```

**验证**：保存前读 `input[autocomplete="address-level1"].value`，应该是 `Michigan`。

## 坑 5：`element.click()` 会触发 Google 二次验证

**现象**：用 `page.evaluate("el.click()")` 点「订阅」「保存」这类敏感按钮，
要么没反应，要么直接跳二次验证。

**原因**：合成事件没有 `isTrusted`，Google 的风控会把它当成脚本行为。

**修法**：一律用真实输入事件：

```python
# 方式一：坐标点击
await page.mouse.move(x, y)
await page.mouse.down()
await page.mouse.up()

# 方式二：locator.click()（内部走 CDP Input.dispatchMouseEvent，也是可信事件）
await locator.click()
```

## 坑 6（业务层）：账单是两份试用期不同的条目

结账弹窗里：

```
Google AI Pro (5 TB) - 免费试用 12 个月          → 开始日期 2027-11-06
YouTube Premium Individual Add On - 免费试用 1 个月 → 开始日期 2026-12-06  US$11.99/month
```

Play 订阅页只显示**最近的那个**：「下次付款 US$11.99，下次付款日期 2026年12月6日」。
这不是 AI Pro 的到期日，是附加包的。**必须关续费**，否则 30 天后扣款失败会拖停整个订阅。
