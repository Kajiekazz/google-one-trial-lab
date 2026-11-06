# 假成功：为什么日志一路绿灯，实际什么都没发生

## 现象

Step 3 / Step 4 打印：

```
✅ [step3_layer2_6mss] 检测到订阅成功确认提示！
✅ Step 3 (二层 6个月免费包 US$0.00 -> 18个月) 叠加完成！
```

但 Play 订阅页的到期日没变，订单记录也没多一笔。

## 根因（代码级）

`automation_engine.py:1349-1368`，点击「订阅」之后用关键字判断是否成功：

```python
if any(ok_kw in clean_after for ok_kw in (
        "已订阅", "Subscribed", "感谢您订阅",
        "通过此类购买活动获取", "Google Play 积分", "Play Points",
        "Earn Google Play Points", "开启备用付款方式", "添加备用付款方式",
        "备用付款方式", "Backup payment", "以后再说", "知道了", "Got it",
)):
    self.log(f"✅ [{step_tag}] 检测到订阅成功确认提示！")
```

而失败时的弹窗本身就是：

```
错误 我们这边出了点问题，请重试。  [知道了]
```

`知道了` 在成功关键字里 → 关闭错误弹窗的动作被判定为「订阅成功」。

同理，`以后再说` / `Not now` 这类**关闭弹窗**的按钮文本也被算作成功信号，
所以脚本在「弹窗被关掉」这件事上永远不会报错。

## 影响

- B / C / D 三个变体全部报「成功」，实际零订单
- 脚本继续往下跑 Step 4、Step 5，截出来的「验真截图」是一张什么都没变的订阅页
- 用户拿到的是「24 个月已完成」的假结论

## 怎么改

成功判定不能只看文案关键字，要看**状态**：

1. 订单记录新增一条（`play.google.com/store/account/orderhistory`）
2. 订阅页到期日后移（`play.google.com/store/account/subscriptions`）
3. `one.google.com/settings` 的「结束时间」变化

文案类信号只能当「弹窗已关闭」，不能当「交易已成功」。
