# 为什么「24 个月」结构性不可达

> 测试对象：某商业脚本 `automation_engine.py`（下文引用行号均指该文件）
> 测试账号：自有两个 Google 账号，均已先拿到首层 12 个月
> 时间：2026-11-06

## 结论

首层 12 个月是**真实**的。第二层、第三层在「AI Pro + YouTube 附加包」这个 bundle 结构下**永远过不去**，
四个变体全部失败，且**没有产生任何订单**。脚本日志里的「✅ 叠加完成」是假阳性（见 `false-positive.md`）。

## 一、四个变体与结果

升级请求的 `full_items` 必须携带当前订阅的**全部条目**。围绕这一点做了四组对照：

| # | payload | 结账弹窗表现 | 是否产生订单 |
|---|---|---|---|
| A | `AI Pro 6M_SS` + `YouTube 1M`（脚本原版） | 正常渲染，含「通过 Play 订阅 您不符合条件，无法免费试用 YouTube Premium Individual Add On」；点订阅后「目前无法完成结账。请尝试刷新页面。」 | ❌ |
| B | 只带 `AI Pro 6M_SS`（剔除 YouTube） | 弹窗直接「错误 我们这边出了点问题，请重试。」 | ❌ |
| C | 带 YouTube 条目但试用 token 为 `[]` | 「错误 我们这边出了点问题，请重试。」 | ❌ |
| D | 带 YouTube 条目但试用 token 为 `None` | `Error 500 (服务器错误)` | ❌ |

补充 E：保持订阅活跃（不取消、不重新订阅）后再跑一次原版，日志报「✅ 检测到订阅成功确认提示」，
核对后状态**毫无变化**。

## 二、决定性证据：订单记录只有一笔

```
Google AI Pro (5 TB) + YouTube Premium Individual Add On | 2026年11月6日 | US$0.00
```

A/B/C/D/E 全部**没有新增订单**。真叠成功的话，Play 必然多一条 US$0.00 订单。
「没有订单」比任何日志都硬。

## 三、结构性原因

升级（`ear8` 里带现有 `sub_id`）时，服务端要求 `full_items` 覆盖订阅的全部条目：

```
full_items = [
  [AI Pro 条目,  ..., [6M 试用 token]],
  [YouTube 条目, ..., [试用 token]],
]
```

- **少带 YouTube 条目** → 服务端当成不完整请求，500 / 通用错误
- **带上 YouTube 条目** → 必须给它一个试用 token，而该账号的 YouTube 1 个月试用
  已经被第一层消耗（当前正处于试用期内）→ `您不符合条件，无法免费试用` → 整单无法结账

即：只要基础套餐是「AI Pro + YouTube 附加包」这个 bundle，第 2、3 层就永远卡在 YouTube 条目上。
**这不是时序问题、不是风控问题，是产品结构问题。换新号也一样 —— 第一层同样会把 YouTube 试用吃掉。**

## 四、第一层真实到账的证据

```
play.google.com/store/account/subscriptions
活跃 | Google AI Pro (5 TB) + YouTube Premium Individual Add On
已取消 | 您的订阅期将于 2027年11月6日结束 | 重新订阅

one.google.com/settings
当前方案 Google AI Pro (5 TB) | US$19.99/月 | 结束时间：2027年11月6日

play.google.com/store/account/orderhistory
十一月的总支出：US$0
Google AI Pro (5 TB) + YouTube Premium Individual Add On | 2026年11月6日 | US$0.00
```

起始日 2026-11-06，结束日 2027-11-06，正好 12 个月，支出 US$0.00。

## 五、顺带发现：账单是两份试用期不同的条目

```
Google AI Pro (5 TB) - 免费试用 12 个月          US$0.00   开始日期 2027年11月6日
YouTube Premium Individual Add On - 免费试用 1 个月  US$0.00   开始日期 2026年12月6日  US$11.99/month
```

Play 页面上的「下次付款 US$11.99 / 2026年12月6日」说的是**附加包**，不是 AI Pro。
不关续费，30 天后就会拿卡去扣这笔钱；0 额度卡扣失败会把整个订阅拖停。
→ 每层成功后第一件事必须是关续费。
