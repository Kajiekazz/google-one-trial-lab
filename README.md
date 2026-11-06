# google-one-trial-lab

> 对某个「Google AI Pro 零成本 24 个月」商业脚本的**行为取证**，以及一套可复用的 Playwright 工具。
> 结论：**12 个月是真的，24 个月在现有产品结构下不可达；那个脚本报的「✅ 订阅成功」是假阳性。**

A field study of a paid "free 24-month Google AI Pro" automation kit: what actually works,
what silently fails, and why. Plus a small set of reusable Playwright tools (bind card,
cancel renewal, inspect state, capture checkout traffic).

---

## TL;DR

| 说法 | 实测 |
|---|---|
| 「零成本 24 个月」 | ❌ 只有 **12 个月**，且需在成功后立刻关闭续费 |
| 「Step 3 叠加完成」「Step 4 叠加完成」 | ❌ 假成功：错误弹窗的「知道了」按钮命中了成功判定关键字 |
| 「三笔 US$0.00 订单」 | ❌ 订单记录只有 **一笔**（第一层那一笔） |
| 「首层 12 个月免费」 | ✅ 真实到账，`US$0.00`，到期日正确 |

复现命令与证据全部在 [`docs/`](docs/)：

- [`docs/findings.md`](docs/findings.md) —— 24 个月为什么结构性不可达（三次 payload 变体 + 订单记录）
- [`docs/false-positive.md`](docs/false-positive.md) —— 假成功的代码级根因
- [`docs/pitfalls.md`](docs/pitfalls.md) —— 绑卡环节三个能把人卡死的坑
- [`docs/flow.md`](docs/flow.md) —— 完整链路与状态机

---

## 仓库结构

```
tools/
  common.py            公共：配置加载 / CDP 连接 / 文本与坐标点击
  inspect_state.py     盘点订阅状态、订单记录、支付方式（只读）
  bind_card.py         绑定银行卡（含三个坑的修复）
  cancel_renewal.py    关闭自动续费（幂等）
  capture_checkout.py  给页面装 XHR/fetch 钩子，抓 Ngbm 结账请求与响应

docs/                  取证与结论
config.example.json    配置模板（复制为 config.json 后填写）
```

## 环境要求

- Windows 10/11（脚本用的是 Chrome 可执行文件默认路径，可改）
- Python 3.10+
- Google Chrome
- 已启动的 Chrome 调试实例（脚本用 `connect_over_cdp` 接管，不自己启动浏览器）

```bash
pip install -r requirements.txt
```

## 快速开始

```bash
# 1) 配置
copy config.example.json config.json
#    填：端口、代理（可选）、卡号/有效期/CVC/持卡人、账单地址

# 2) 用独立 profile 启动 Chrome（示例）
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9342 ^
  --user-data-dir=%CD%\profiles\profile_demo ^
  --no-first-run --no-default-browser-check

# 3) 手动在浏览器里登录目标账号（2FA 自己过），然后：

python tools\inspect_state.py --port 9342          # 先看现状
python tools\bind_card.py      --port 9342          # 绑卡
#    → 回到浏览器里手动点击订阅（结账弹窗必须显示 US$0.00）
python tools\cancel_renewal.py --port 9342          # 立刻关续费
python tools\inspect_state.py  --port 9342          # 复核
```

### 为什么订阅那一步不自动化

结账弹窗的「订阅」按钮是 Google 的风控敏感点。`element.click()` 这类合成事件会被判定为非用户手势，
二次验证会被直接拦掉；必须用真实输入事件（`page.mouse.down/up` 或 Playwright `locator.click()`）。
本项目只自动化「绑卡 / 取消续费 / 观测」这些非风控敏感环节，**订阅点击留给人工**，也顺便保证你亲眼看得到
`今天 US$0.00` 这一行。

---

## 三个坑（细节见 `docs/pitfalls.md`）

1. **`Escape` 会关掉整个「添加支付方式」弹窗。** 想用它收起地址补全，结果 iframe 直接销毁，前面的输入全丢。
   → 改用 JS `focus()` 切字段。
2. **填完卡号后 `instrument_manager` iframe 会 reload。** 缓存 `Frame` 句柄会 `Frame was detached`。
   → 每次操作前按 URL 重新抓 frame。
3. **地址补全浮层会遮挡下一个字段的点击。** 强制 `click(force=True)` 也不行。
   → `document.querySelector(...).focus()` + `keyboard.type()`，不产生鼠标事件，浮层自然消失。

## 另一个坑（业务层）

账单是一份 bundle：`Google AI Pro (12 个月试用)` + `YouTube Premium Add On (1 个月试用)`。
Play 的「下次付款 US$11.99 / 30 天后」说的是**附加包**，不是 AI Pro。不关续费的话，
30 天后会拿 0 额度卡去扣 US$11.99，扣失败会把整个订阅拖停。
**每层成功后第一件事就是关续费。**

---

## 这个仓库不做什么

- 不含批量账号导入、接码、卡源、代理池
- 不含任何真实卡号 / 邮箱 / 密码 / cookie（全部脱敏）
- 不 re-distribute 那个商业脚本的源码（`automation_engine.py` 是他人作品，这里只引用其行为与行号做取证）

## 合规

仅用于**你自己名下账号**的订阅状态管理与计费行为研究。免费试用受 Google 服务条款约束，
多账号重复领取试用属于违规，后果自负。作者不对任何滥用负责。

## License

MIT
