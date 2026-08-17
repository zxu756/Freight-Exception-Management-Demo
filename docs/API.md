# 新西兰物流数字孪生 · API 接入文档

> 版本 v1.0 · 基于当前运行中的后端实测生成 · 供组员直接对接：前端展示 / 短信邮件外发 / 数据处理 / 报表。

## 目录

1. [概览](#1-概览)  
2. [必读约定（重要坑）](#2-必读约定)  
3. [端点总览](#3-端点总览)  
4. [世界内核（God）端点](#4-世界内核端点)  
5. [海运 sea](#5-海运-sea)  
6. [空运 air](#6-空运-air)  
7. [陆运 road](#7-陆运-road)  
8. [AI 问答 ask](#8-ai-问答)  
9. [字段字典（枚举）](#9-字段字典)  
10. [组员接入场景 Recipes](#10-组员接入场景)  
11. [注意事项与 FAQ](#11-注意事项与-faq)

---

## 1. 概览

| 项目 | 值 |
| --- | --- |
| 系统 | Freight Exception Management Demo（新西兰海/空/陆货运异常管理数字孪生） |
| Base URL | `http://<host>:8000/api`（本地演示 `http://localhost:8000/api`） |
| 认证 | 无（内网/演示环境）。直接请求即可 |
| 数据格式 | 请求/响应均为 JSON；时间戳为 ISO8601 **模拟世界时间**（无时区） |
| 错误格式 | FastAPI 标准：HTTP 4xx/5xx + `{"detail": "..."}` |
| 健康检查 | `GET /health` 与 `GET /`（这两个不带 `/api` 前缀） |

快速冒烟测试：

    curl http://localhost:8000/health
    curl http://localhost:8000/api/world/clock
    curl "http://localhost:8000/api/sea/exceptions?risk_level=high"

---

## 2. 必读约定

### 2.1 所有时间戳是「模拟世界时间」

系统里有一个统一世界时钟（默认 60x 速度，1 真实秒 ≈ 1 模拟分钟）。所有时间字段（`detected_at`、`sent_at`、`scheduled_delivery`、`sla_deadline` 等）都是**模拟时间**，不是真实时间。

**做增量拉取时，不要拿服务器真实时间做比较，要用数据自带的时间戳。** 当前世界时间取：`GET /api/world/clock` → `now`。

### 2.2 ⚠️ exception_id 在三种方式间会重复（最大的坑）

`EXC-SIM-000123` 这种 ID 在 sea / air / road 是**各自独立计数**的：三个模式可能各有一个 `EXC-SIM-000123`，它们是三条不同的异常。

因此：

- 用 exception_id 查详情必须带 mode：`GET /api/{mode}/exceptions/{exception_id}`；
- 通知（notification）与异常的关联键是 **(mode, exception_id)**，不是 exception_id 单独一个字段；
- 你们自己的系统里保存异常时，请同时保存 `mode` + `exception_id` 两个字段。

同理 `notification_id`（NTF-SEA-xxx / NTF-AIR-xxx / NTF-ROAD-xxx）自带模式前缀，全局唯一。

### 2.3 票级数据（一个装载单元里有多票货）

| 方式 | 装载单元 | 票级表 | 票号字段 |
| --- | --- | --- | --- |
| 海运 | container（集装箱，LCL 时多票） | cargo_lines | `line_number` |
| 空运 | waybill（MAWB 主单，拼单时多票） | house_waybills | `hawb_number` |
| 陆运 | consignment（LTL 拼车时多票） | consignment_lines | `line_number` |

异常可能是**票级**的：异常详情 `cargo` 块里的 `line_number` / `hawb_number` 不为空即表示这条异常只属于该装载单元里的那一票；通知也只发给那一票的货主。

### 2.4 recovery_options 是「JSON 字符串」，且有两种历史格式

异常里的 `recovery_options` 字段是 **JSON 字符串**（需要先 `JSON.parse`）。历史数据是字符串数组：

    ["submit_documents", "duty_payment", "coordinate_inspection", "broker_escalation"]

新数据是**按「最推荐 → 最不推荐」排序的对象数组**，每项带细节：

    [
      {
        "action": "submit_documents",   // 行动代码
        "label": "补充单证",             // 中文名
        "description": "补齐商业发票/申报单等所需单证",
        "impact_hours": 2,                // 预计挽回延误小时
        "cost": 100,                      // 成本 NZD
        "score": 65.2,                    // 综合得分 0-100
        "why": "综合得分 65.2 排名第一：...",  // 排位理由
        "recommended": true               // 是否 AI 推荐（第一名）
      },
      ...
    ]

注意：**列表端点** `/api/{mode}/exceptions` 里的 recovery_options 仍是字符串（老/新格式混存）；**详情端点** `/api/{mode}/exceptions/{id}` 里后端已统一升级为新格式对象数组的字符串。前端建议只依赖详情端点。

### 2.5 客户与联系方式

统一客户目录（34 家）：`GET /api/world/customers`。每家有 `contact_name` / `email` / `phone` / `mobile` / `preferred_channel`（email|sms）。
异常详情的 `cargo.customer_email` / `cargo.customer_phone` / `cargo.customer_contact` 是该票货主联系方式；通知里带 `recipient_email` / `recipient_phone` / `channel`。

### 2.6 列表无分页

除 `notifications` 有 `limit`（默认 20）外，其余列表端点**全量返回**，请尽量带过滤参数。数据量级参考：containers ~1800、waybills ~8400、road consignments ~16000、各模式 exceptions 几百到几千。

---

## 3. 端点总览

| 分类 | 方法 & 路径 | 说明 |
| --- | --- | --- |
| 世界 | GET `/world/clock` | 当前世界时间/速度/暂停 |
| 世界 | POST `/world/clock/control` | 上帝模式：暂停/变速/改时间 |
| 世界 | GET `/world/weather` | 区域 + 地点天气 |
| 世界 | POST `/world/weather/override` | 强制指定区域/地点天气 |
| 世界 | POST `/world/weather/clear` | 清除天气覆盖 |
| 世界 | GET `/world/weather/overrides` | 当前天气覆盖列表 |
| 世界 | GET `/world/weather/{code}` | 单区域/地点天气 |
| 世界 | GET `/world/state` | 世界总状态（时钟+天气+活跃事件） |
| 世界 | GET `/world/shipments` | 跨模式联运货物链 |
| 世界 | GET `/world/predictions` | 天气缓冲期预测影响 |
| 世界 | GET `/world/customers` | 客户目录（含联系方式） |
| 海运 | GET `/sea/ports` | 港口 |
| 海运 | GET `/sea/vessels` | 船期（PortConnect 真实数据） |
| 海运 | GET `/sea/containers` | 集装箱列表 |
| 海运 | GET `/sea/containers/{cn}` | 集装箱详情（含事件/异常/票） |
| 海运 | GET `/sea/containers/{cn}/lines` | 箱内全部票（CargoLine） |
| 海运 | GET `/sea/exceptions` | 异常列表 |
| 海运 | GET `/sea/exceptions/{id}` | 异常详情（AI 流水线四步数据） |
| 海运 | GET `/sea/dashboard` | 看板汇总 |
| 海运 | GET `/sea/kpi` | KPI 比率 |
| 海运 | GET `/sea/notifications` | 客户通知（含联系方式） |
| 海运 | GET `/sea/live` | 实时状态+近期动态 |
| 海运 | POST `/sea/sim/control` | 控制海运模拟器 |
| 海运 | POST `/sea/env/event` | 手动注入环境事件 |
| 海运 | GET `/sea/env/events` | 活跃环境事件 |
| 空运 | GET `/air/airports` | 机场 |
| 空运 | GET `/air/flights` | 航班 |
| 空运 | GET `/air/waybills` | 运单列表 |
| 空运 | GET `/air/waybills/{awb}` | 运单详情（含分单） |
| 空运 | GET `/air/waybills/{awb}/house-bills` | 主单下全部分单（HouseWaybill） |
| 空运 | GET `/air/exceptions` | 异常列表 |
| 空运 | GET `/air/exceptions/{id}` | 异常详情 |
| 空运 | GET `/air/dashboard` / `/air/kpi` | 看板 / KPI |
| 空运 | GET `/air/notifications` / `/air/live` | 通知 / 实时 |
| 空运 | POST `/air/sim/control` · `/air/env/event` | 控制 / 注入事件 |
| 空运 | GET `/air/env/events` | 活跃环境事件 |
| 陆运 | GET `/road/depots` | 站点 |
| 陆运 | GET `/road/segments` | 实时路况 |
| 陆运 | GET `/road/trips` | 车次 |
| 陆运 | GET `/road/consignments` | 托运单列表 |
| 陆运 | GET `/road/consignments/{cn}` | 托运单详情（含票） |
| 陆运 | GET `/road/consignments/{cn}/lines` | 全部票（ConsignmentLine） |
| 陆运 | GET `/road/exceptions` | 异常列表 |
| 陆运 | GET `/road/exceptions/{id}` | 异常详情 |
| 陆运 | GET `/road/dashboard` / `/road/kpi` | 看板 / KPI |
| 陆运 | GET `/road/notifications` / `/road/live` | 通知 / 实时 |
| 陆运 | POST `/road/sim/control` · `/road/env/event` | 控制 / 注入事件 |
| 陆运 | GET `/road/env/events` | 活跃环境事件 |
| AI | POST `/ask` | 用 LLM 问答某个异常或一般货运问题 |
---

## 4. 世界内核端点

### 4.1 GET /world/clock — 世界时钟

三个模拟器共用的单一时钟。

    {
      "now": "2026-09-04T02:32:52.495127",  // 模拟世界当前时间
      "speed": 60.0,                          // 倍速（x）
      "paused": false
    }

### 4.2 POST /world/clock/control — 上帝模式控制时钟

请求体：

    // 暂停 / 恢复
    { "action": "pause" }        |  { "action": "resume" }
    // 变速
    { "action": "set_speed", "speed": 60 }   // 常用 1 / 60 / 600 / 3600
    // 跳到指定世界时间
    { "action": "set_time", "time": "2026-09-04T12:00:00" }

响应：`{"success": true, "message": "...", "now": ..., "speed": ..., "paused": ...}`

### 4.3 GET /world/weather — 全部区域+地点天气

响应包含 `regions`（15 个区域）与 `locations`（港口/机场/站点码）两段，每项字段相同：

    {
      "code": "auckland", "region": "auckland", "region_name": "Auckland",
      "condition": "rain", "condition_label": "雨",
      "intensity": 0.86, "temperature_c": 12.5, "wind_knots": 16.9,
      "visibility_km": 8.0, "precip_mm_per_h": 1.72, "overridden": false
    }

`condition` 枚举：clear / cloudy / showers / rain / heavy_rain / storm / fog / snow / windy。

### 4.4 POST /world/weather/override — 强制天气（演示/压测用）

    { "target": "ZQN" | "central_otago",   // 地点码或区域码
      "condition": "snow",                   // 必须在上面的枚举里
      "intensity": 1.0,                        // 可选，默认 1.0
      "hours": 12 }                            // 可选，持续小时，默认 12

响应：`{"success": true, "override": {target, target_type, condition, condition_label, intensity, ends_at}}`

天气覆盖会通过因果引擎传导为海/空/陆的延误（带缓冲期，缓冲期内可在 `/world/predictions` 看到预测影响）。

### 4.5 POST /world/weather/clear — 清除覆盖

    {}                        // 清除全部
    { "target": "ZQN" }       // 只清一个目标

### 4.6 GET /world/weather/overrides — 当前覆盖列表

    { "overrides": [ { "target": "ZQN", "condition": "fog", "ends_at": ... }, ... ] }

### 4.7 GET /world/weather/{code} — 单区域/地点天气

### 4.8 GET /world/state — 世界总状态（前端世界控制台一次拉全）

    {
      "clock": { "now": ..., "speed": 60.0, "paused": false },
      "regions": [ { "region": "auckland", "name": "Auckland", "condition": "rain",
                       "condition_label": "雨", "temperature_c": 12.5, "wind_knots": 16.9,
                       "visibility_km": 8.0 }, ... ],
      "active_events": [ { "mode": "road", "location": "HLZ", "event_type": "weather",
                             "severity": "severe", "description": "...", "ends_at": ... }, ... ]
    }

### 4.9 GET /world/shipments — 跨模式联运货物链

    {
      "count": 50,
      "shipments": [ {
        "shipment_id": "SHIP-SEA-TLLU0001731",
        "legs": [
          { "leg_index": 1, "mode": "sea",  "reference": "TLLU0001731",      "origin": "origin", "destination": "TRG" },
          { "leg_index": 2, "mode": "road", "reference": "DC-170fc1e51baa", "origin": "TRG",    "destination": "ROT" }
        ] } ]
    }

### 4.10 GET /world/predictions — 天气缓冲期预测影响

    { "count": 100, "predictions": [ {
        "mode": "road", "reference": "DR-dab986ec3258", "location": "HLZ",
        "predicted_delay_minutes": 150,
        "impact_at": "2026-09-04T01:16:53.299257",
        "status": "materialized",      // predicted(待应验) / materialized(已应验)
        "description": "HLZ 大雨，道路通行受阻；预计 DR-dab986ec3258 在 09-04 01:16 后延误约 150 分钟" } ] }

### 4.11 GET /world/customers?q= — 客户目录（通知去向）

`q` 可选，按名称模糊过滤（ilike）。

    { "count": 34, "customers": [ {
        "customer_code": "CUS-002", "name": "Briscoe Group", "tier": "medium",
        "contact_name": "Sophie Lee", "contact_title": "Freight & Logistics Lead",
        "email": "sophie.lee@briscoegroup.co.nz", "phone": "+64 9 3599092",
        "mobile": "+64 21 39533030", "address_line": "94 Customs Street East",
        "city": "Auckland", "region": "Auckland", "preferred_channel": "email" } ] }

---

## 5. 海运 sea

### 5.1 GET /sea/ports

    { "count": 5, "ports": [ { "port_code": "NZAKL", "name": "Port of Auckland",
      "city": "Auckland", "country": "New Zealand", "is_nz_port": true,
      "congestion_level": 4 }, ... ] }

港口码：NZAKL（奥克兰）/ NZTRG（陶朗加）/ NZWLG（惠灵顿）/ NZLYT（利特尔顿）/ NZTIU（蒂马鲁）。

### 5.2 GET /sea/vessels?port=&status=&vessel_type=

PortConnect 真实船期快照 + 模拟演化。字段：`vessel_visit_id`、`vessel_name`、`imo_number`、`inbound_voyage`、`outbound_voyage`、`vessel_status`（EXPECTED/INPORT/DEPARTED）、`vessel_type`（CONTAINER/CRUISE/...）、`port_code`、`wharf_name`、`berth`、`previous_port`、`next_port`、`arrival_datetime`、`departure_datetime`、`delay_minutes`、`delay_reason_code`。

### 5.3 GET /sea/containers?direction=&status=&customer_tier=&has_exception=

`direction`：import / export（当前系统只生成进口 import）。`has_exception`：true/false。

    { "count": 1759, "containers": [ {
      "container_number": "TCNU0000001", "direction": "import", "size": "40HC",
      "container_type": "RF", "commodity_desc": "Pharmaceuticals (cold chain)",
      "commodity_code": "300241", "gross_weight_kg": 15592.0,
      "declared_value_nzd": 193891.0, "customer_name": "Pacific Fresh Foods",
      "customer_tier": "medium", "current_status": "delivered",
      "customs_cleared": false, "biosecurity_cleared": false, "is_dg": false,
      "scheduled_delivery": "...", "sla_deadline": "..." } ] }

### 5.4 GET /sea/containers/{container_number} — 集装箱详情

响应分组：`vessel`（船名/航次/港口）、`commodity`（品名/HS/重量/危品/冷链温度）、`parties`（customer/customer_tier/shipper/consignee）、`commercial`（declared_value_nzd）、`status`（current_status/清关状态/时间节点/ETA/SLA deadline）、`events`（追踪事件数组）、`exceptions`（本箱异常数组）、`cargo_lines`（箱内全部票）。

    "events": [ { "event_code": "DCH", "event_desc": "Discharged",
                   "location": "NZAKL", "timestamp": ..., "reason_code": null } ]

事件码（海运）：GAT 门进 / LOAD 装船 / DEP 离港 / ARR 到港 / DCH 卸船 / AVC 可提箱 / DLV 交付 等，以 `event_desc` 描述为准。

### 5.5 GET /sea/containers/{cn}/lines — 箱内全部票（票级）

    { "container_number": "CMAU0001759", "count": 1, "lines": [ {
      "line_number": 1, "commodity_desc": "Consumer electronics", "commodity_code": "854231",
      "customer_name": "Silver Fern Farms", "customer_tier": "high",
      "declared_value_nzd": 88148.0, "gross_weight_kg": 8212.0,
      "service_level": "priority", "sla_tier": "priority",
      "temp_min_c": null, "temp_max_c": null,
      "scheduled_delivery": "...", "sla_deadline": "...",
      "is_sla_breached": false, "breach_type": null, "sla_penalty_nzd": null } ] }

### 5.6 GET /sea/exceptions?exception_type=&risk_level=&status=

按 `risk_score` 降序返回。字段：`exception_id`、`container_number`、`exception_type`、`severity`（low/medium/high/critical）、`risk_level`、`risk_score`（0-100）、`status`、`requires_human_approval`、`root_cause`、`ai_diagnosis`、`ai_confidence`、`recovery_options`（JSON 字符串，见 2.4）、`delay_hours`、`business_section`、`classification_confidence`、`classification_decision`（automatic/human_review/ood）、`ood_score`、`is_ood`、`anomaly_score`、`anomaly_reason`、`exception_category`、`root_cause_category`、`predicted_downstream_impact`、`recovery_cost`、`recommended_action`、`recommendation_reason`、`detected_at`。

海运常见 `exception_type`：vessel_delay / customs_hold / biosecurity_hold / temp_excursion / damage / lost / failed_delivery / tracking_gap / port_congestion / predicted_anomaly。

### 5.7 GET /sea/exceptions/{exception_id} — 异常详情（AI 流水线四步 + 通知）

在 5.6 字段基础上增加 `cargo` 块与 `notifications` 数组：

    "cargo": {
      "container_number": "CMAU0000376", "cargo_line_id": null, "line_number": null,
      "commodity_desc": "E-commerce parcels (LCL)", "declared_value_nzd": 53617.0,
      "customer_name": "Manuka Health", "customer_tier": "VIP",
      "customer_contact": "Noah Lee", "customer_email": "noah.lee@manukahealth.co.nz",
      "customer_phone": "+64 9 7719905", "customer_channel": "email",
      "service_level": "priority", "sla_tier": "priority",
      "is_sla_breached": false, "breach_type": null, "sla_penalty_nzd": null,
      "size": "20FT", "direction": "import" },
    "notifications": [ {
      "notification_id": "NTF-SEA-000067", "recipient": "Manuka Health",
      "channel": "email", "recipient_email": null, "recipient_phone": null,
      "message": "Hi Manuka Health, your freight ...",
      "revised_eta": null, "confidence": 0.2986, "sent_at": "..." } ]

票级异常时 `cargo.line_number` 非空、`cargo_*` 为该票货主信息。`recipient_email` 为 null 的是历史通知（客户主数据上线前的旧数据）。

### 5.8 GET /sea/dashboard — 看板汇总

    { "containers": { "total": 1759, "imports": 1759, "exports": 0, "dg": 86 },
      "vessels": { "expected": 241, "in_port": 9 },
      "exceptions": { "open": 618, "high_risk": 136, "pending_approval": 524,
        "by_type": { "vessel_delay": 348, ... }, "by_risk_level": { "low": 70, ... } },
      "cold_chain": { "temp_excursion_alerts": 2 } }

### 5.9 GET /sea/kpi — KPI 比率

    { "total": 618, "automation_rate": 0.104, "pending_approval_rate": 0.848,
      "escalation_rate": 0.0, "high_risk_rate": 0.22, "ood_rate": 0.0,
      "sla_breach_rate": 0.005, "excused_rate": 0.0, "otd_rate": 0.995,
      "by_category": { "Delay": 447, ... }, "by_root_cause": { ... } }

### 5.10 GET /sea/notifications?limit=20 — 客户通知（外发数据源）

    { "count": 3, "notifications": [ {
      "notification_id": "NTF-SEA-003206", "exception_id": "EXC-SIM-003205",
      "reference": "CSLU0001515", "recipient": "Comvita", "channel": "email",
      "recipient_email": "jack.carter@comvita.co.nz", "recipient_phone": "+64 9 7778649",
      "message": "Hi Comvita, your freight ...", "revised_eta": "...",
      "confidence": 0.5855, "sent_at": "..." } ] }

`channel=sms` 时 message 已是短文案。**注意 `sent_at` 是模拟时间**，按它排序取最新 N 条。

### 5.11 GET /sea/live — 实时状态

    { "simulator": { "running": true, "paused": false, "speed": 60.0,
        "sim_now": "...", "vessels_loaded": 4, "containers_generated": 248,
        "exceptions_generated": 289, "events_generated": 673 },
      "vessels": { "total_in_db": 1361, "by_status": {...} },
      "open_exceptions": [ 精简字段，含 cargo_line_id / line_number ] ,
      "recent_events": [ { "event_code": "AVC", "event_desc": "...",
        "container_number": "...", "location": "NZAKL", "timestamp": ..., "reason_code": null } ] }

### 5.12 POST /sea/sim/control

    { "action": "pause" | "resume" | "set_speed", "speed": 60 }

响应：`{success, message, running, paused, speed, sim_now}`。**一般建议用世界时钟 `/world/clock/control` 统一控制**，本端点只影响海运模拟器。

### 5.13 POST /sea/env/event — 手动注入环境事件

    { "location": "NZAKL",            // 必须：NZAKL/NZTRG/NZWLG/NZLYT/NZTIU
      "event_type": "port_congestion", // port_congestion / weather / ferry_cancelled
      "severity": "severe",           // minor/moderate/severe
      "duration_hours": 12,
      "description": "可选，不填用默认模板" }

### 5.14 GET /sea/env/events — 活跃环境事件

    { "count": 3, "events": [ { "event_type": "port_congestion", "location": "NZAKL",
      "severity": "minor", "description": "...", "ends_at": ... } ] }
---

## 6. 空运 air

空运与海运结构对称，差异点如下（未列出的行为与 5.x 同名端点一致）。

### 6.1 GET /air/airports?region=

    { "count": 30, "airports": [ { "iata_code": "AKL",
      "name": "Auckland International Airport", "city": "Auckland",
      "country": "New Zealand", "region": "nz_domestic",
      "is_nz_gateway": true, "curfew_hours": null, "congestion_level": 3,
      "weather": "Gusty northerlies, 11C" } ] }

`region` 可选（nz_domestic / international 等）。

### 6.2 GET /air/flights?status=&origin=&destination=&is_freighter=

    { "count": 2579, "flights": [ { "flight_number": "NZ9837",
      "airline": "Air New Zealand Cargo", "aircraft_type": "A320neo",
      "is_freighter": false, "origin": "AKL", "destination": "CHC",
      "scheduled_departure": ..., "scheduled_arrival": ...,
      "actual_departure": null, "actual_arrival": ..., "status": "landed",
      "delay_minutes": 0, "delay_reason_code": null,
      "loaded_pct": 93.1, "capacity_kg": 4500 } ] }

航班 `status`：scheduled / delayed / departed / landed / cancelled。

### 6.3 GET /air/waybills?route_type=&status=&customer_tier=&has_exception=

    { "count": 8380, "waybills": [ { "awb_number": "086-81000001",
      "hawb_number": null, "route_type": "domestic", "origin": "AKL",
      "destination": "CHC", "flight_number": "NZ9837",
      "commodity_desc": "General freight (mixed pallets)", "commodity_code": "990000",
      "pieces": 3, "chargeable_weight_kg": 185.4, "declared_value_nzd": 17846.0,
      "customer_name": "Kmart NZ", "customer_tier": "low",
      "service_level": "priority", "priority": "normal",
      "special_handling_codes": null, "current_status": "DLV",
      "current_location": "CHC", "scheduled_delivery": ...,
      "estimated_delivery": ..., "sla_deadline": ... } ] }

`route_type`：domestic / international / transshipment。拼单主单 `hawb_number` 非空（老格式），新格式看 `is_consolidated`。

### 6.4 GET /air/waybills/{awb_number} — 运单详情

    { "awb_number": "086-81008784", "hawb_number": null, "is_consolidated": false,
      "route_type": "domestic", "origin": "AKL", "destination": "GIS",
      "transit_points": "[]", "flight_number": "NZ6823",
      "commodity": { "desc": "Medical supplies and equipment", "hs_code": "901831",
        "pieces": 8, "gross_weight_kg": 342.8, "volume_cbm": 2.14,
        "chargeable_weight_kg": 357.4, "special_handling_codes": "VAL",
        "dg_class": null, "un_number": null, "temp_min_c": null, "temp_max_c": null,
        "temp_excursion_alert": false, "expiry_date": null },
      "parties": { "shipper": "...", "consignee": "...", "customer": "...",
        "customer_tier": "medium" },
      "commercial": { "declared_value_nzd": 46416.0, "service_level": "economy",
        "priority": "normal", "sla_tier": "economy" },
      "status": { "current_status": "booked", "current_location": "AKL",
        "scheduled_delivery": ..., "estimated_delivery": ...,
        "sla_deadline": ..., "delivered_at": null },
      "events": [...], "inspections": [...], "exceptions": [...],
      "house_waybills": [ 分单数组，字段见 6.5 ] }

`status.current_status`（空运）：booked / RCS 已收运 / DEP 已离港 / ARR 已到港 / CUS 清关 / AVD 可交付 / DLV 已交付 等。

### 6.5 GET /air/waybills/{awb}/house-bills — 主单下全部分单（票级）

    { "awb_number": "086-81008784", "count": 1, "house_waybills": [ {
      "hawb_number": "086-81008784-01", "commodity_desc": "...",
      "commodity_code": "901831", "customer_name": "...", "customer_tier": "medium",
      "declared_value_nzd": 46416.0, "pieces": 8, "gross_weight_kg": 342.8,
      "service_level": "economy", "sla_tier": "economy",
      "temp_min_c": null, "temp_max_c": null, "sla_deadline": ...,
      "is_sla_breached": false, "breach_type": null, "sla_penalty_nzd": null } ] }

### 6.6 GET /air/exceptions?exception_type=&risk_level=&status=

同 5.6 结构，主键字段为 `awb_number`（票级时另有 `hawb_number`/`hawb_id`）。空运常见 `exception_type`：delay / customs_hold / misroute / temp_excursion / failed_delivery / lost / tracking_gap / predicted_anomaly。

### 6.7 GET /air/exceptions/{exception_id} — 异常详情

同 5.7 结构。`cargo` 块：`awb_number`、`hawb_id`、`hawb_number`、`commodity_desc`、`declared_value_nzd`、`customer_*`（含 customer_contact/email/phone/channel）、`service_level`、`sla_tier`、`is_sla_breached`、`breach_type`、`sla_penalty_nzd`、`route_type`。`notifications` 同 5.7（含 channel/recipient_email/recipient_phone）。

### 6.8 GET /air/dashboard · /air/kpi

    // dashboard
    { "waybills": { "total": 8380, "domestic": 7301, "international": 1079,
        "transshipment": 0 },
      "flights": { "active": 30, "delayed": 1 },
      "exceptions": { "open": 799, "high_risk": 2, "pending_approval": 237,
        "by_type": {...}, "by_risk_level": {...} },
      "cold_chain": { "temp_excursion_alerts": 3 },
      "customs": { "open_inspections": 4 } }

    // kpi 同 5.9 结构

### 6.9 GET /air/notifications?limit= · /air/live

同 5.10 / 5.11 结构。live 的 `simulator` 字段为 flights_generated / waybills_generated 等；另有 `upcoming_departures`、`delayed_flights`。

### 6.10 POST /air/sim/control · /air/env/event · GET /air/env/events

sim/control 同 5.12。env/event 差异：

    { "location": "WLG",        // 机场 IATA：AKL/CHC/WLG/ZQN/DUD/NSN/NPE/HLZ/TRG/IVC
      "event_type": "fog",      // weather / fog / snow
      "severity": "moderate", "duration_hours": 6 }

---

## 7. 陆运 road

### 7.1 GET /road/depots?island=

    { "count": 21, "depots": [ { "depot_code": "AKL", "name": "Auckland Metro Depot",
      "city": "Auckland", "region": "Auckland", "island": "north",
      "is_hub": true, "congestion_level": 5, "weather": "Fine, 15C, light breeze" } ] }

`island`：north / south。常用站点码：AKL/HLZ/TRG/WLG/CHC/DUD/ZQN/NPE/NPL/NSN/TIM/OAM/PIC/ROT/GIS/PMR/GBM/IVC。

### 7.2 GET /road/segments — 实时路况

    { "count": 74, "segments": [ { "origin": "AKL", "destination": "HLZ",
      "condition": "slow", "speed_factor": 0.7, "description": "天气影响，通行缓慢",
      "updated_at": ... } ] }

`condition`：clear / slow / congested / closed；`speed_factor` 通行速度系数（1.0=正常）。

### 7.3 GET /road/trips?status=&origin=&destination=&is_inter_island=

    { "count": 11512, "trips": [ { "trip_number": "MF63665", "carrier": "Mainfreight",
      "vehicle_type": "semi_trailer", "origin": "AKL", "destination": "HLZ",
      "is_inter_island": false, "scheduled_departure": ..., "scheduled_arrival": ...,
      "actual_departure": null, "actual_arrival": ..., "status": "arrived",
      "delay_minutes": 0, "delay_reason_code": null, "distance_km": 125.0,
      "loaded_pct": 87.1, "capacity_kg": 22000, "driver_name": "Driver 175",
      "driver_hours_remaining": 5.1 } ] }

车次 `status`：scheduled / loading / in_transit / delayed / arrived / cancelled。

### 7.4 GET /road/consignments?route_type=&status=&customer_tier=&has_exception=

    { "count": 16354, "consignments": [ { "consignment_number": "RD-50000001",
      "trip_number": "MF63665", "route_type": "regional", "origin": "AKL",
      "destination": "HLZ", "commodity_desc": "...", "commodity_code": "990000",
      "pieces": 29, "gross_weight_kg": 6554.1, "declared_value_nzd": 7114.0,
      "customer_name": "Mainfreight", "customer_tier": "medium",
      "service_level": "economy", "priority": "normal", "current_status": "POD",
      "current_location": "HLZ", "scheduled_delivery": ...,
      "estimated_delivery": ..., "sla_deadline": ... } ] }

`route_type`：line_haul / regional / inter_island。`current_status`（陆运）：booked / PUP 已提货 / LOAD / DEP / CKP / ARR / FERRY / UNLD / POD 已交付。

### 7.5 GET /road/consignments/{cn} — 托运单详情

    { "consignment_number": "RD-50014569", "trip_number": "DY55381",
      "route_type": "regional", "is_ltl": false, "origin": "PIC", "destination": "NSN",
      "commodity": { "desc": "Fresh salmon fillets", "hs_code": "030213",
        "pieces": 13, "gross_weight_kg": 5130.8, "volume_cbm": 32.07,
        "dg_class": null, "un_number": null, "temp_min_c": 0.0, "temp_max_c": 2.0,
        "temp_excursion_alert": false },
      "parties": { "shipper": "...", "consignee": "...", "customer": "...",
        "customer_tier": "high" },
      "commercial": { "declared_value_nzd": 18975.0, "service_level": "standard",
        "priority": "normal", "sla_tier": "standard" },
      "status": { "current_status": "booked", "current_location": "PIC",
        "scheduled_delivery": ..., "estimated_delivery": ...,
        "sla_deadline": ..., "delivered_at": null },
      "events": [...], "exceptions": [...], "cargo_lines": [ 见 7.6 ] }

### 7.6 GET /road/consignments/{cn}/lines — 全部票（票级）

    { "consignment_number": "RD-50014569", "count": 1, "lines": [ {
      "line_number": 1, "commodity_desc": "Fresh salmon fillets", "commodity_code": "030213",
      "customer_name": "Manuka Health", "customer_tier": "high",
      "declared_value_nzd": 18975.0, "pieces": 13, "gross_weight_kg": 5130.8,
      "service_level": "standard", "sla_tier": "standard",
      "temp_min_c": 0.0, "temp_max_c": 2.0, "sla_deadline": ...,
      "is_sla_breached": false, "breach_type": null, "sla_penalty_nzd": null } ] }

### 7.7 GET /road/exceptions?exception_type=&risk_level=&status= · /road/exceptions/{id}

同 5.6 / 5.7 结构，主键字段 `consignment_number`（票级时另有 `consignment_line_id`/`line_number`）。
陆运常见 `exception_type`：delay / road_closure / breakdown / accident / driver_hours / temp_excursion / ferry_delay / overweight / service_cancelled / predicted_anomaly。

### 7.8 GET /road/dashboard · /road/kpi

    // dashboard
    { "consignments": { "total": 16354, "line_haul": 4322, "regional": 9650,
        "inter_island": 2382 },
      "trips": { "active": 157, "delayed": 11 },
      "exceptions": { "open": 3181, "high_risk": 81, "pending_approval": 1747,
        "by_type": { "breakdown": 338, ... }, "by_risk_level": {...} },
      "cold_chain": { "temp_excursion_alerts": 195 } }

    // kpi 同 5.9 结构

### 7.9 GET /road/notifications?limit= · /road/live

同 5.10 / 5.11 结构。live 另有 `upcoming_departures`、`delayed_trips`；`simulator` 字段为 trips_generated / consignments_generated 等。

### 7.10 POST /road/sim/control · /road/env/event · GET /road/env/events

sim/control 同 5.12。env/event 差异：

    { "location": "HLZ",         // 站点码：AKL/HLZ/TRG/WLG/CHC/GBM/DUD/ZQN/NPE/NPL
      "event_type": "road_closure", // weather / road_closure / accident
      "severity": "severe", "duration_hours": 12 }
---

## 8. AI 问答

### POST /ask

请求体：

    // 针对某条异常提问（推荐，带上下文）
    { "question": "这个异常应该怎么处理？",
      "mode": "sea", "exception_id": "EXC-SIM-000066" }

    // 一般货运问题
    { "question": "新西兰海关查验一般多久放行？" }

响应：

    { "answer": "...", "mode": "sea", "exception_id": "EXC-SIM-000066" }

注意：需要后端配置 LLM（DEEPSEEK_API_KEY + llm_enabled=true），否则返回 503。

---

## 9. 字段字典

### 异常状态 `status`（exceptions）

| 值 | 含义 |
| --- | --- |
| detected | 已检测，尚未诊断 |
| diagnosed | 已自动诊断（低风险+高置信） |
| pending_approval | 待人工审批（AI 已给出推荐行动） |
| escalated | 已升级人工（OOD 陌生模式等） |
| resolved | 已解决 |

### 风险/严重度

- `risk_level`：low / medium / high
- `severity`：low / medium / high / critical
- `risk_score`：0-100 整数

### 客户等级 `customer_tier`

VIP / high / medium / low

### 异常权威分类 `exception_category`（8 类）

Delay（延误）/ Damage（货损）/ Mis-routing（错运）/ Customs Hold（海关扣留）/ Lost/Missing（丢失）/ Failed Delivery（派送失败）/ Tracking/Data（跟踪数据）/ Capacity/Transport（运力）。

### 根因类别 `root_cause_category`（10 类）

weather-natural（天气）/ traffic-infrastructure（交通设施）/ equipment-failure（设备）/ capacity-scheduling（运力排班）/ documentation-compliance（单证合规）/ human-error（人为）/ security-theft（安全盗窃）/ packaging-loading（包装装卸）/ receiving-site（收货端）/ technology-connectivity（技术联通）。

### 分类决策 `classification_decision`

automatic（自动）/ human_review（人工复核）/ ood（分布外陌生模式）。`is_ood=true` 表示升级人工。

### 通知渠道 `channel`

email（邮件，完整文案）/ sms（短信，短文案）。

### SLA 相关

- `is_sla_breached`：是否违约；`breach_type`：excused（豁免，天气/海关等排除项）/ 其他或 null；
- `sla_penalty_nzd`：违约金（NZD）；`sla_deadline`：票级截止时间。

### 天气 `condition`

clear / cloudy / showers / rain / heavy_rain / storm / fog / snow / windy。

---

## 10. 组员接入场景

### 10.1 前端展示一条异常详情（推荐数据链）

1. `GET /api/{mode}/exceptions?status=pending_approval` 拿列表（记下 mode + exception_id）；
2. `GET /api/{mode}/exceptions/{id}` 拿详情：AI 诊断、风险、恢复行动排序（parse recovery_options）、票级 cargo、客户联系方式、通知；
3. 票级对比：详情 cargo 里的 container_number / awb_number / consignment_number 传给 `/lines` 或 `/house-bills` 端点拿同一装载单元的全部票；
4. 客户信息：详情 cargo 里的 customer_email/phone/contact，或 `GET /api/world/customers` 目录。

### 10.2 邮件 / 短信外发 worker（通知处理流水线）

数据源：`GET /api/{mode}/notifications?limit=100`（带 recipient_email / recipient_phone / channel / message）。三个模式分别拉，或按 notification_id 前缀归并。

    while true:
      对每个 mode in [sea, air, road]:
        通知 = GET /api/{mode}/notifications?limit=100
        对每条通知:
          if notification_id 已处理过: 跳过        # 用 notification_id 去重
          if channel == "sms" and recipient_phone:
             发送短信(recipient_phone, message)     # message 已是短文案
          elif recipient_email:
             发送邮件(recipient_email, message)
          记录(notification_id, 发送状态, 发送时间)
        睡 10-30 秒再轮询

要点：

- 系统**只生成通知、不真实外发**；外发后请回写 POST /api/notifications/{notification_id}/delivery（status + external_message_id），系统的指标快照会统计外发积压（notifications_pending_send）；
- `notification_id` 全局唯一（NTF-SEA/AIR/ROAD-xxx），天然适合做幂等去重；
- `sent_at` 是模拟时间；按返回顺序（sent_at 降序）处理即可；
- 世界时钟 60x 时数据增长快，建议把 limit 调大或缩短轮询间隔；处理慢时优先处理最新（列表已按 sent_at 降序）。

### 10.3 实时监控 / 告警

- 高风险新异常：`GET /api/{mode}/exceptions?risk_level=high&status=pending_approval`；
- 总览一次拉全：`GET /api/world/state`（时钟+天气+活跃环境事件）；
- 单模式实时：`GET /api/{mode}/live`（open_exceptions + recent_events + 延误航班/车次）；
- 天气缓冲期预测：`GET /api/world/predictions`（status=predicted 是还没发生的）；
- 增量去重：用 (mode, exception_id) 组合键。

### 10.4 报表 / 数据仓库 ETL

- 汇总：`/api/{mode}/dashboard`（计数）+ `/api/{mode}/kpi`（比率：automation_rate / sla_breach_rate / otd_rate 等）；
- 明细：`/api/{mode}/exceptions`、`/notifications`、票级端点；
- 建议主键：mode + exception_id（异常）、notification_id（通知）、各单据号；
- 时间维度用数据自带的模拟时间戳，与 `/api/world/clock` 对齐版本。

### 10.5 演示操控（上帝模式）

- 制造一场暴雪看缓冲期预测：POST `/world/weather/override` {target: "central_otago", condition: "snow", hours: 24} → 看 `/world/predictions` → 快进 `/world/clock/control` {action: "set_speed", speed: 3600}；
- 制造港口拥堵：POST `/sea/env/event` {location: "NZAKL", event_type: "port_congestion", severity: "severe", duration_hours: 24}；
- 制造大雾：POST `/air/env/event` {location: "ZQN", event_type: "fog"}；
- 制造封路：POST `/road/env/event` {location: "CHC", event_type: "road_closure"}。

### 10.6 把 AI 问答包成聊天机器人

前端先拿到异常列表/详情，用户点某条异常问问题 → POST `/ask` {question, mode, exception_id} → 显示 answer。

---

## 11. 注意事项与 FAQ

**Q：多久轮询一次合适？**  
A：世界时钟默认 60x（1 真实秒 = 1 模拟分钟）。做展示 4-10 秒一次即可；做通知外发 10-30 秒；避免对无过滤的大列表高频全量拉取。

**Q：数据会重置吗？**  
A：数据持久化在 SQLite（backend/freight_demo.db），重启后端不丢数据；世界时钟会对齐到数据库最新时间继续演化。

**Q：为什么 detail 里有些通知 recipient_email 是 null？**  
A：客户主数据是后加的，历史通知没有联系方式；新生成的通知都有。前端应兼容 null（降级显示 recipient 名称）。

**Q：exception 列表里的 recovery_options 和详情里不一样？**  
A：列表返回原始存储值（历史字符串数组），详情端点会统一升级为「排序对象数组」的 JSON 字符串。要做 AI 行动展示请用详情端点。

**Q：能分页吗？**  
A：目前只有 notifications 有 limit；其余全量。需要分页请先用过滤参数，或告诉我们加。

**Q：CORS？**  
A：后端已配 CORS，浏览器前端可直接跨域调用。

**Q：我想直接读数据库。**  
A：可以（SQLite 单文件，WAL 模式），但不保证表结构稳定；对接请优先走 REST API。

---

*文档与代码同仓库维护（docs/API.md）。后端有字段新增时请同步更新本文档。*
---

## 12. Scenario 4 数据闭环（P0/P1/P2 新增）

### 12.1 协调员决策（审批 + 学习）

**POST /api/{mode}/exceptions/{exception_id}/decision** — 记录协调员对 AI 建议的审批/驳回/修改，异常随即标记为 resolved 并写入实际执行结果。

请求体：

    {
      "decided_by": "Coordinator Alice",   // 决策人，默认 Coordinator
      "decision": "approve",               // approve / modify / reject
      "chosen_action": "submit_documents", // modify 时必填；approve 缺省用 recommended_action；reject 忽略
      "note": "现场确认可行",               // 可选
      "actual_cost": 120,                    // 可选，缺省按行动标准成本
      "actual_recovery_hours": 2.5           // 可选，缺省按行动预计挽回小时
    }

响应：

    {
      "success": true,
      "decision": { "decision_id": "DEC-2c58d8db2e", "decided_by": "...",
        "decision": "approve", "chosen_action": "...",
        "decision_latency_minutes": 18057.8, "decided_at": "..." },
      "exception": { "exception_id": "...", "status": "resolved",
        "actual_action": "...", "actual_cost": 100.0,
        "actual_recovery_hours": 2.0, "resolved_at": "..." }
    }

**学习机制**：每次决策更新 decision_stats（分类 × 行动的采纳/驳回计数）；后续同一分类的新异常，被协调员多次采纳的行动会在 AI 排序里获得最多 +1.5 的偏好加分（recovery_options 的 why 里会注明），推荐逐渐向协调员实际偏好收敛。

异常详情端点新增字段：trigger_event_id（触发该异常的那条追踪事件）、detection_latency_minutes（事件→检测的分钟数，仅当触发事件在 24h 内才记录）、actual_action / actual_cost / actual_recovery_hours / resolved_at、decisions（决策历史数组）。

### 12.2 通知外发回写

**POST /api/notifications/{notification_id}/delivery** — 外发 worker 回写真实送达状态。

    { "status": "sent", "external_message_id": "mail-abc-123" }
    // status: sent / delivered / failed

通知对象新增字段：sent_status（pending/sent/delivered/failed，初始 pending）、external_message_id、sent_real_at（真实世界时间）。列表与详情端点都返回。

### 12.3 客户来电记录

**POST /api/world/customer-contacts** — 记录一次客户来电/投诉，后端自动判定 proactive（联系前系统是否已通知过该客户）。

    { "customer_name": "Fonterra", "contact_type": "inbound_call",
      "channel": "phone", "note": "询问延误情况",
      "exception_id": "EXC-SIM-000066", "mode": "sea" }   // 后两个可选

**GET /api/world/customer-contacts?limit=50** — 联系记录列表。
### 12.4 承运人历史绩效（预测特征，P1）

**GET /api/world/carrier-performance?mode=&risky_only=&limit=** — 每 12 模拟小时由世界维护任务自动刷新（保留每模式样本量前 200）：

    { "count": 4, "carriers": [ {
      "mode": "road", "carrier_key": "Mainfreight|CHC|HLZ",
      "origin": "CHC", "destination": "HLZ",
      "total_runs": 4, "delayed_runs": 2, "cancelled_runs": 0,
      "avg_delay_minutes": 135.0, "on_time_rate": 0.5,
      "top_reason": "breakdown", "refreshed_at": "..." } ] }

risky_only=true 只返回准点率 ≤70% 且样本 ≥3 的高风险承运人。同时系统会给高风险承运人生成 historical_risk 状态的预测行（出现在 /world/predictions）。

### 12.5 时序指标快照（P2）

**GET /api/world/metrics?hours=72&mode=&name=** — 每 12 模拟小时一帧的 KPI 时序（保留 60 模拟天）：

    { "count": 26, "from": "...", "metrics": [
      { "ts": "2026-09-05T10:55:03", "mode": "sea", "name": "open_exceptions", "value": 1072.0 }, ... ] }

指标名：open_exceptions / pending_approval / high_risk / resolved / automation_rate / escalation_rate / avg_detection_latency_min / notifications_pending_send / notifications_sent / decisions_total / proactive_notification_rate / sla_penalty_month_nzd。

### 12.6 统一票视图（P2，ETL 用）

**GET /api/world/tickets?limit=500** — 把三种方式的票级数据合并成统一结构：mode、parent_reference、ticket_number、commodity、customer、declared_value、service_level、sla_deadline、is_sla_breached、sla_penalty、parent_status、customer_email。按 sla_deadline 降序。

---

*本文档与代码同仓库维护（docs/API.md）。后端有字段新增时请同步更新。*
---

## 13. 铁路 rail（第 4 种运输方式）+ 校准与回写（新增）

### 13.1 铁路端点（与其它三种方式对称）

| 方法 & 路径 | 说明 |
| --- | --- |
| GET /rail/stations?island= | 10 个铁路车站（AKL/HLZ/TRG/MTM/NPL/PNM/WGN/CHC/DUD/IVC） |
| GET /rail/segments | 线路区间实时状态（clear/slow/restricted/closed） |
| GET /rail/services?status=&origin=&destination= | 班列（KR-xxxxx，含延误原因/分钟） |
| GET /rail/consignments?route_type=&status=&customer_tier=&has_exception= | 托运单列表 |
| GET /rail/consignments/{cn} | 托运单详情（车次/货物/事件/异常/票） |
| GET /rail/consignments/{cn}/lines | 全部票（RailConsignmentLine） |
| GET /rail/exceptions | 异常列表（rail_delay/track_closure/mechanical_failure/weather_delay/signal_failure） |
| GET /rail/exceptions/{id} | 异常详情（含票级 cargo、联系人、决策、通知） |
| POST /rail/exceptions/{id}/decision | 协调员审批（同 12.1） |
| GET /rail/dashboard · /rail/kpi | 看板 / KPI |
| GET /rail/notifications?limit= · /rail/live | 通知 / 实时（upcoming_departures/delayed_services） |
| POST /rail/sim/control · /rail/env/event | 控制 / 注入事件（track_closure/signal/mechanical/weather） |
| GET /rail/env/events | 线路异常事件 |

铁路已接入世界内核：天气因果（暴雨/雪 → 线路封闭，含缓冲期预测，/world/predictions 会预报受影响班列）、承运人绩效（carrier_performance 含 rail）、指标快照（metric_snapshots 含 rail）、统一票视图（/world/tickets 含 rail）、客户目录与通知外发、决策学习（decision_stats）。

### 13.2 TMS / 客户门户回写（Scenario 4: update the TMS automatically）

**GET /api/world/tms-updates?limit=50** — 回写审计列表。

**POST /api/world/tms-updates** — 手动登记一次回写：

    { "mode": "sea", "exception_id": "EXC-SIM-...", "field": "eta",
      "new_value": "2026-09-20 10:00", "reference": "CMAU...",
      "target": "tms" }   // target: tms / portal / both；status 可选 applied/recorded/failed

协调员每次决策（12.1）会自动登记一条 status→resolved 的 tms_updates 记录。

### 13.3 订单量校准旋钮（config）

- order_scale（全局 0.094）× road_scale 0.15 / air_scale 0.3 / sea_scale 0.6 / rail_scale 1.0 → 目标 ~15-18k 票/月（陆 ~7k / 空 ~5k / 海 ~2.5k / 铁 ~2.5k）；
- 异常率 8-12% 目标：海运 vessel_delay 已按箱概率化（30%），避免一条船延误给全船开异常；
- 重启幂等：海运按船期已生成箱则跳过、铁路班列 2 小时窗口去重，避免重复堆积；
- 检测延迟 detection_latency_minutes 仅在触发事件 24h 内记录（>24h 视为无法判定，置空），指标快照只统计 0-1440 分钟区间。

*本文档与代码同仓库维护（docs/API.md）。*
---

## 14. 人工处置 / 通知审核 / 承运商报价（EVT-006 · COM-003 · QTE-001 · MON-005）

### 14.1 异常处置（误报/重复/数据问题/结案/重开）

| 方法 & 路径 | 说明 |
| --- | --- |
| POST /api/{mode}/exceptions/{id}/disposition | body={disposition: confirmed\|false_positive\|duplicate\|data_issue, note, by}；案件置为 closed 并记录处置人/备注 |
| POST /api/{mode}/exceptions/{id}/close | 人工结案，body={evidence}（POD/交付/海关放行等客观证据） |
| POST /api/{mode}/exceptions/{id}/reopen | 重新打开（二次异常），reopen_count+1，原时间线保留 |
| POST /api/{mode}/exceptions | 人工创建异常，body={reference, exception_type, root_cause, diagnosis}；绑定现有装载单元，走完整风险/分类/方案/通知流程 |

异常详情新增字段：disposition / disposition_note / disposition_by / disposition_at / closed_at / close_evidence / reopen_count。
开放异常统计（dashboard/live）已把 closed 排除；kpi 不受影响。

### 14.2 通知人工审核（COM-003）

高风险异常（risk_level=high）生成的通知 review_status=pending_review，必须人工确认后才能外发。

| 方法 & 路径 | 说明 |
| --- | --- |
| GET /api/world/notifications?review_status=pending_review | 跨模式待审通知队列 |
| POST /api/notifications/{id}/review | body={action: approve\|edit\|reject, message?, reviewed_by}；edit 会把新文案写入 edited_message 并置为 approved，reject 置为 rejected |

### 14.3 承运商报价（QTE-001/002）

| 方法 & 路径 | 说明 |
| --- | --- |
| GET /api/world/quotes?exception_id= | 某异常的全部报价（含版本/状态） |
| POST /api/world/quotes | 人工录入：body={mode, exception_id, carrier, price_nzd, service, new_eta, surcharges_nzd, capacity_note, note}；同一异常重复录入版本自动 +1 |
| POST /api/world/quotes/{quote_id}/select | 选择报价（其余同异常报价自动置为 rejected） |

*本文档与代码同仓库维护（docs/API.md）。*
---

## 15. RBAC / 审批升级 / 二次偏差重开 / 网络事件编组（ADM-001 · APR-005 · MON-002 · EVT-008）

### 15.1 简化 RBAC（ADM-001）

- 预置用户：U-ALICE 协调员(planner) / U-BOB 经理(manager) / U-CAROL 客服(cs) / U-DAVE 管理员(admin) / U-EVE 分析师(analyst)；
- 敏感操作按角色矩阵校验：decision/disposition/close/reopen/create_exception → planner+manager；review → cs+manager；quotes → planner+manager；
- 审批矩阵（APR-001/002）：risk_level=high 或 recovery_cost>=2000 的动作必须 manager/admin，否则 403；
- 操作人从 body 的 user/user_id/decided_by/by/reviewed_by 任一字段解析（找不到用户时宽松放行，兼容旧调用）；
- GET /api/world/users 列出用户与角色；权限不足统一返回 403 {"detail": "..."}。

### 15.2 审批超时升级（APR-005）

世界维护任务每 12 模拟小时检查：pending_approval 超过 24 模拟小时未处理 → 自动升级为 escalated，并在 escalation_reason 记录原因。异常详情端点返回 escalation_reason。

### 15.3 二次偏差自动重开（MON-002）

任一方式生成新异常时，若该装载单元已有 closed 案件 → 自动重新打开（status=reopened、reopen_count+1、escalation_reason 追加时间戳），保留原时间线。

### 15.4 网络事件编组（EVT-008）

| 方法 & 路径 | 说明 |
| --- | --- |
| GET /api/world/network-events | 活跃天气/港口/线路事件 → 受影响班次数（来自预测行）+ 受影响客户清单 |
| POST /api/world/network-events/{event_id}/notify | 批量处置：把一个网络事件影响的全部待审通知一次性批准外发（body={by}），返回批准数 |

### 15.5 性能修复

- 所有端点由 async def 改为同步 def（无 await），FastAPI 在线程池执行，事件循环不再被同步 SQL 阻塞——重负载下时钟/健康接口仍即时响应；
- 事件积压每 tick 最多处理 1000 条；重启重建 pending 堆只取 48 小时窗口；海运回填幂等改为批量集合查询——启动/时钟大跳后不再长时间卡死。

*本文档与代码同仓库维护（docs/API.md）。*
---

## 16. 第三批：审计日志 / 承运商指令 / 责任分配 / 费用收口（ADM-006 · EXE-002/003 · EXC-004 · MON-006）

- GET /api/world/audit?mode=&exception_id=&limit= — 审计日志（决策/处置/关闭/重开/审核/报价/指令/TMS 回写全留痕，含修改前后值与操作人）
- POST /api/{mode}/exceptions/{id}/assign（body={assignee, by}）— 责任分配，详情返回 assignee
- 审批通过/修改时自动生成承运商指令（drafted）；
  GET /api/world/instructions?exception_id= ；POST /api/world/instructions/{id}/send|confirm|fail
  confirm 记录订舱号(external_ref)/最终费用(final_cost_nzd)/新 ETA
- GET /api/world/cost-closure?exception_id= — 费用收口：估算恢复成本 vs 批准实际成本 vs 选中报价 vs 承运商确认费用 vs SLA 违约金，含偏差值

## 17. 稳定性修复（世界冻结根因）

- 移除 API 写操作的 WRITE_LOCK 装饰器（线程锁 + 长 tick 组合曾导致全系统冻结）；依赖 SQLite busy_timeout 自愈；
- 每 tick 事件处理加 20 秒时间盒 + 每 200 事件提交一次，事务窗口有界；
- 海运启动跳过非全新库的船舶窗口回填（分块提交），缩短启动写锁占用；
- 协调器启动时初始化维护时间戳（首个 tick 不立即跑维护）；main.py 注册 faulthandler（kill -USR1 打印线程栈诊断）。

*本文档与代码同仓库维护（docs/API.md）。*
