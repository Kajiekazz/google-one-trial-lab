# 完整链路（12 个月那一层）

```
[0] 准备
    独立 Chrome profile + 独立代理会话 + 独立端口
    └─ 一个账号一个出口 IP，别让两个号共用

[1] 登录（人工）
    accounts.google.com → 邮箱 → 密码 → 手机 Prompt 二次验证
    └─ 勾「在此设备上不再询问」，之后同一 profile 不再弹

[2] 盘点（tools/inspect_state.py）
    ├─ play.google.com/store/account/subscriptions   有没有订阅
    ├─ play.google.com/store/account/paymentmethods  有没有卡
    ├─ one.google.com/plans                          看得到美区价格吗
    └─ wallet → 添加支付方式 → 看 COUNTRY 字段的默认值

    判断：
    ├─ COUNTRY = US 且 disabled  → 全新号，直接绑卡（不用改区）
    └─ COUNTRY = 其他国家         → 需要先处理旧付款资料，否则绑卡必失败

[3] 绑卡（tools/bind_card.py）
    wallet.google.com/wallet/paymentmethods → 添加支付方式
    └─ instrument_manager iframe 内：卡号 / 月 / 年 / CVC / 持卡人 / 地址

    成功判据（两个页面都要对）：
    ├─ wallet.google.com/wallet/paymentmethods → Visa •••• 1234 11/27
    └─ play.google.com/store/paymentmethods    → Visa-1234

[4] 订阅（人工点）
    one.google.com/plans → 目标方案 → 开始使用 / 升级 → Play 结账弹窗
    └─ 必须亲眼确认弹窗写的是「今天 US$0.00」，再点「订阅」

[5] 立刻关续费（tools/cancel_renewal.py）
    play.google.com/store/account/subscriptions → 管理 → 取消订阅 → 取消订阅
    └─ 幂等，重复跑会直接跳过

[6] 复核（tools/inspect_state.py）
    ├─ play 订阅页：已取消 | 您的订阅期将于 YYYY年MM月DD日结束 | 重新订阅
    ├─ one settings：结束时间：YYYY年MM月DD日
    └─ 订单记录：只有一笔 US$0.00，且「下次付款」字样消失
```

## 状态机

```
无付款资料 ──绑卡──> 有卡 ──订阅(US$0.00)──> 试用中(自动续费开)
                                              │
                                    关续费     │
                                              ▼
                                    试用中(自动续费关) ──到期──> 结束，不扣款
```

## 判据汇总（只看这三样，别信日志）

| 判据 | 合格 |
|---|---|
| 订单记录 | 新增一条 `US$0.00` |
| 订阅页到期日 | 后移到预期月份 |
| `下次付款` 字样 | 关续费后**消失** |

## 不支持的操作

- 批量导入账号 / 自动过 2FA / 接码
- 卡源、代理池
- 任何「US$0.00 以外」的自动点击
