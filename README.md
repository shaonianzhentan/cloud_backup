# cloud_backup
在HA里使用的七牛云备份

[![hacs_badge](https://img.shields.io/badge/Home-Assistant-%23049cdb)](https://www.home-assistant.io/)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![visit](https://visitor-badge.laobi.icu/badge?page_id=shaonianzhentan.cloud_backup&left_text=visit)

## 安装

安装完成重启HA，刷新一下页面，在集成里搜索`cloud_backup`即可

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=cloud_backup)

## 使用

> 要求 Home Assistant 2025.1 及以上（本插件使用官方 Backup Agent 接口）。

新建一个自动化，在 YAML 模式中贴入以下内容
```yaml
alias: 自动备份
description: '每天晚上3点，自动备份文件到本地，同时上传到云端'
mode: single
trigger:
  - platform: time
    at: '03:00:00'
condition: []
action:
  - service: cloud_backup.create
    data:
      delete: true   # 可选：上传完成后删除本地备份文件（覆盖集成配置中的选项）
```

`cloud_backup.create` 的执行流程：

1. 先执行 Home Assistant 系统备份，生成本地 `.tar` 备份文件；
2. 系统备份完成后，将备份文件上传到七牛云（对象 key 形如 `HomeAssistant/<实例UUID>/<HA版本>/<日期>_<文件名>`）；
3. 根据配置项（或本次调用的 `delete` 参数）决定是否删除本地备份文件，云端副本始终保留。

### 配置项：上传后删除本地备份

在集成配置页面点击「配置」→「上传后删除本地备份」即可开启。开启后，每次通过本插件上传完成都会自动清理本地备份，仅保留云端副本（适合磁盘空间紧张的設備）。

> 另外，在 Home Assistant 自带的「备份」页面创建备份并选择「七牛云备份」作为上传目标时，也会走同一套上传逻辑；若开启了上面的选项，上传完成后同样会自动删除本地副本。

## 如果这个项目对你有帮助，请我喝杯<del style="font-size: 14px;">咖啡</del>奶茶吧😘
|  |支付宝|微信|
|---|---|---|
奶茶= | <img src="https://ha.jiluxinqing.com/img/alipay.png" align="left" height="160" width="160" alt="支付宝" title="支付宝">  |  <img src="https://ha.jiluxinqing.com/img/wechat.png" height="160" width="160" alt="微信支付" title="微信">

## 关注我的微信订阅号，了解更多HomeAssistant相关知识
<img src="https://ha.jiluxinqing.com/img/wechat-channel.png" height="160" alt="HomeAssistant家庭助理" title="HomeAssistant家庭助理">

---
**在使用的过程之中，如果遇到无法解决的问题，付费咨询请加Q`635147515`**