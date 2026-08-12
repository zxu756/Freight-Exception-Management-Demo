# PortConnect API 中文参考文档

> 数据快照：2026-08-13（Pacific/Auckland）  
> API Revision：19 — Added berth to vessel schedule API  
> 范围：30 个接口、7 个分组、108 个公开接口可达 Schema

本文件根据 PortConnect 公共开发者门户的操作和 Schema 定义整理。门户未提供接口 description，因此本文中的中文“用途”是依据操作 ID、HTTP 方法和路径补充的便捷说明，并非官方业务承诺。字段名、类型、必填约束、枚举、示例与成功状态码来自门户快照。

## 1. 快速接入

- Base URL：`https://api.portconnect.io`
- 协议：HTTPS
- 鉴权：订阅密钥必需。推荐 Header：`Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY`
- 备选鉴权：Query 参数 `subscription-key=YOUR_SUBSCRIPTION_KEY`
- JSON 请求：发送 `Content-Type: application/json`
- 门户仅逐接口列出成功状态码，未给出统一 4xx/5xx 错误结构。

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/about' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

## 2. API 总览

| 分组 | 方法 | 路径 | 用途 | 成功状态 |
| --- | --- | --- | --- | --- |
| 服务信息 | GET | `/v1/about` | 获取 API 服务的构建信息。 | 200 |
| 集装箱访问记录 | GET | `/v1/container-visits/{containerVisitId}` | 按 containerVisitId 获取单条集装箱访问记录。 | 200 |
| 集装箱访问记录 | GET | `/v1/container-visits` | 按箱号、港口、类别或运输方向筛选集装箱访问记录。 | 200 |
| 出口预报 | DELETE | `/v1/export-preadvices` | 取消已提交的出口预报。 | 204 |
| 出口预报 | GET | `/v1/export-preadvices/{partnerPortCode}/{userReference}` | 按合作港口代码和用户引用查询出口预报。 | 200 |
| 出口预报 | GET | `/v1/export-preadvices/{partnerPortCode}/{userReference}/{containerNumber}` | 按合作港口代码、用户引用和箱号查询出口预报。 | 200 |
| 出口预报 | POST | `/v1/export-preadvices` | 提交出口预报。 | 201 |
| 计划船舶 | GET | `/v1/scheduled-vessels` | 按港口、船型、状态、到港时间或船名查询计划船舶。 | 200 |
| 订阅 V1 | POST | `/v1/subscriptions` | 创建 V1 集装箱/订舱事件订阅。 | 201 |
| 订阅 V1 | DELETE | `/v1/subscriptions/{subscriptionId}` | 删除指定 V1 订阅。 | 204 |
| 订阅 V1 | DELETE | `/v1/subscriptions/{subscriptionId}/bookings/{bookingNumber}` | 从指定 V1 订阅中删除一个订舱号。 | 200 |
| 订阅 V1 | DELETE | `/v1/subscriptions/{subscriptionId}/containers/{containerNumber}` | 从指定 V1 订阅中删除一个箱号。 | 200 |
| 订阅 V1 | GET | `/v1/subscriptions/{subscriptionId}` | 获取指定 V1 订阅。 | 200 |
| 订阅 V1 | GET | `/v1/subscriptions` | 获取全部 V1 订阅。 | 200 |
| 订阅 V1 | GET | `/v1/subscriptions/{subscriptionId}/bookings` | 获取指定 V1 订阅下的订舱信息。 | 200 |
| 订阅 V1 | GET | `/v1/subscriptions/{subscriptionId}/bookings/{bookingNumber}` | 按订舱号获取指定 V1 订阅下的订舱信息。 | 200 |
| 订阅 V2 | POST | `/v2/subscriptions` | 创建 V2 集装箱/订舱事件订阅。 | 201 |
| 订阅 V2 | DELETE | `/v2/subscriptions/{subscriptionId}` | 删除指定 V2 订阅。 | 204 |
| 订阅 V2 | DELETE | `/v2/subscriptions/{subscriptionId}/bookings/{bookingNumber}` | 从指定 V2 订阅中删除一个订舱号。 | 200 |
| 订阅 V2 | DELETE | `/v2/subscriptions/{subscriptionId}/containers/{containerNumber}` | 从指定 V2 订阅中删除一个箱号。 | 200 |
| 订阅 V2 | GET | `/v2/subscriptions/{subscriptionId}` | 获取指定 V2 订阅。 | 200 |
| 订阅 V2 | GET | `/v2/subscriptions` | 获取全部 V2 订阅。 | 200 |
| 订阅 V2 | GET | `/v2/subscriptions/{subscriptionId}/bookings` | 获取指定 V2 订阅下的订舱信息。 | 200 |
| 订阅 V2 | GET | `/v2/subscriptions/{subscriptionId}/bookings/{bookingNumber}` | 按订舱号获取指定 V2 订阅下的订舱信息。 | 200 |
| 船期订阅 | POST | `/v1/subscriptions-vessel-schedule` | 创建船期事件订阅。 | 201 |
| 船期订阅 | DELETE | `/v1/subscriptions-vessel-schedule/{subscriptionId}` | 删除指定船期订阅。 | 204 |
| 船期订阅 | DELETE | `/v1/subscriptions-vessel-schedule/{subscriptionId}/lloydnumber/{lloydNumber}` | 从船期订阅中删除指定 Lloyd 编号。 | 204 |
| 船期订阅 | DELETE | `/v1/subscriptions-vessel-schedule/{subscriptionId}/vesselRef/{vesselRef}` | 从船期订阅中删除指定 vesselRef。 | 204 |
| 船期订阅 | GET | `/v1/subscriptions-vessel-schedule/{subscriptionId}` | 获取指定船期订阅。 | 200 |
| 船期订阅 | GET | `/v1/subscriptions-vessel-schedule` | 查询全部船期订阅。 | 200 |

## 3. API 详细说明

### 3.1 服务信息（About）

#### 3.1.1 `GET /v1/about`

**操作 ID：** `About_About`  
**用途：** 获取 API 服务的构建信息。  
**完整 URL：** `https://api.portconnect.io/v1/about`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/about' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `AboutResponse` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "build": "string"
}
```

---

### 3.2 集装箱访问记录（ContainerVisits）

#### 3.2.1 `GET /v1/container-visits/{containerVisitId}`

**操作 ID：** `ContainerVisits_ContainerVisit`  
**用途：** 按 containerVisitId 获取单条集装箱访问记录。  
**完整 URL：** `https://api.portconnect.io/v1/container-visits/{containerVisitId}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `containerVisitId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/container-visits/12345' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `ContainerVisit` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "containerVisitId": 0,
  "portCode": "string",
  "category": "string",
  "containerNumber": "string",
  "shipmentDirection": "string",
  "inboundVesselRef": "string",
  "inboundVesselName": "string",
  "inboundVesselIMONumber": 0,
  "inboundVesselPublishedArrivalDatetime": "string",
  "inboundVesselActualArrivalDatetime": "string",
  "inboundVesselPublishedDepartureDatetime": "string",
  "inboundVesselActualDepartureDatetime": "string",
  "outboundVesselRef": "string",
  "outboundVesselName": "string",
  "outboundVesselIMONumber": 0,
  "outboundVesselPublishedArrivalDatetime": "string",
  "outboundVesselActualArrivalDatetime": "string",
  "outboundVesselPublishedDepartureDatetime": "string",
  "outboundVesselActualDepartureDatetime": "string",
  "containerIsoTypeCode": "string",
  "containerIsoTypeDescription": "string",
  "declaredWeight": 0,
  "declaredWeightVgm": true,
  "commodityCode": "string",
  "containerStatus": "string",
  "requiredTemperature": 0,
  "ventSetting": "string",
  "o2Percent": 0,
  "cO2Percent": 0,
  "humidityPercent": 0,
  "packedOffPowerDatetime": "string",
  "packedOffPowerTemp": 0,
  "maxHoursAllowedOffPower": 0,
  "containerOperatorCode": "string",
  "containerOperatorName": "string",
  "containerOperatorVoyageId": "string",
  "loadPortCode": "string",
  "loadPortName": "string",
  "dischargePortCode": "string",
  "dischargePortName": "string",
  "destinationPortCode": "string",
  "destinationPortName": "string",
  "inlandPortArrivalDatetime": "string",
  "inlandPortCarrier": "string",
  "seaPortCarrier": "string",
  "seaportTransportMode": "string",
  "loadDatetime": "string",
  "receivedDatetime": "string",
  "inlandPortInboundCarrier": "string",
  "seaPortArrivalDatetime": "string",
  "seaPortInboundCarrier": "string",
  "bookingReference": "string",
  "cedoNumberCode": "string",
  "dischargedDatetime": "string",
  "deliveredDatetime": "string",
  "securityCheck": "string",
  "lastFreeDatetime": "string",
  "lineReleaseDatetime": "string",
  "customsReleaseDatetime": "string",
  "mpiReleaseDatetime": "string",
  "containerLocation": "string",
  "emptyReturnDepotCode": "string",
  "emptyReturnDepotName": "string",
  "sealCount": 0,
  "hazardCount": 0,
  "stopCount": 0,
  "oversizeCount": 0,
  "seals": [
    {
      "containerSealTypeCode": "string",
      "containerSealValue": "string"
    }
  ],
  "hazards": [
    {
      "unHazardousCode": "string",
      "unHazardousDescription": "string",
      "unHazardousClassCode": "string"
    }
  ],
  "stops": [
    {
      "stopTypeCode": "string"
    }
  ],
  "oversizes": [
    {
      "dimensionCode": "string",
      "oversizeValueCm": 0
    }
  ],
  "seaPortGateOutDateTime": "string",
  "inlandPortGateOutDateTime": "string",
  "cedoReleaseDateTime": "string",
  "attachedEquipment": "string",
  "vbsSlotDatetime": "string",
  "lastUpdated": "string",
  "activatedDate": "string",
  "previousContainerVisitId": 0,
  "expressPin": 0,
  "expressPinStatus": "string",
  "powerLastFreeDatetime": "string",
  "shuttleConnectPriorityStatus": "string"
}
```

---

#### 3.2.2 `GET /v1/container-visits`

**操作 ID：** `ContainerVisits_ContainerVisits`  
**用途：** 按箱号、港口、类别或运输方向筛选集装箱访问记录。  
**完整 URL：** `https://api.portconnect.io/v1/container-visits`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| query | `containerNumber` | 否 | `array<string>` | — |
| query | `portCode` | 否 | `string` | — |
| query | `category` | 否 | `ContainerVisitCategory` | 枚举：Domestic, Export, Import, Restow, Storage, Through, Transhipment |
| query | `shippingDirection` | 否 | `string` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/container-visits?containerNumber=MSCU1234567&portCode=NZAKL' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `V1Container-visitsGet200ApplicationJsonResponse` | 成功 |

响应示例（`200 application/json`）：

```json
[
  {
    "containerVisitId": 0,
    "portCode": "string",
    "category": "string",
    "containerNumber": "string",
    "shipmentDirection": "string",
    "inboundVesselRef": "string",
    "inboundVesselName": "string",
    "inboundVesselIMONumber": 0,
    "inboundVesselPublishedArrivalDatetime": "string",
    "inboundVesselActualArrivalDatetime": "string",
    "inboundVesselPublishedDepartureDatetime": "string",
    "inboundVesselActualDepartureDatetime": "string",
    "outboundVesselRef": "string",
    "outboundVesselName": "string",
    "outboundVesselIMONumber": 0,
    "outboundVesselPublishedArrivalDatetime": "string",
    "outboundVesselActualArrivalDatetime": "string",
    "outboundVesselPublishedDepartureDatetime": "string",
    "outboundVesselActualDepartureDatetime": "string",
    "containerIsoTypeCode": "string",
    "containerIsoTypeDescription": "string",
    "declaredWeight": 0,
    "declaredWeightVgm": true,
    "commodityCode": "string",
    "containerStatus": "string",
    "requiredTemperature": 0,
    "ventSetting": "string",
    "o2Percent": 0,
    "cO2Percent": 0,
    "humidityPercent": 0,
    "packedOffPowerDatetime": "string",
    "packedOffPowerTemp": 0,
    "maxHoursAllowedOffPower": 0,
    "containerOperatorCode": "string",
    "containerOperatorName": "string",
    "containerOperatorVoyageId": "string",
    "loadPortCode": "string",
    "loadPortName": "string",
    "dischargePortCode": "string",
    "dischargePortName": "string",
    "destinationPortCode": "string",
    "destinationPortName": "string",
    "inlandPortArrivalDatetime": "string",
    "inlandPortCarrier": "string",
    "seaPortCarrier": "string",
    "seaportTransportMode": "string",
    "loadDatetime": "string",
    "receivedDatetime": "string",
    "inlandPortInboundCarrier": "string",
    "seaPortArrivalDatetime": "string",
    "seaPortInboundCarrier": "string",
    "bookingReference": "string",
    "cedoNumberCode": "string",
    "dischargedDatetime": "string",
    "deliveredDatetime": "string",
    "securityCheck": "string",
    "lastFreeDatetime": "string",
    "lineReleaseDatetime": "string",
    "customsReleaseDatetime": "string",
    "mpiReleaseDatetime": "string",
    "containerLocation": "string",
    "emptyReturnDepotCode": "string",
    "emptyReturnDepotName": "string",
    "sealCount": 0,
    "hazardCount": 0,
    "stopCount": 0,
    "oversizeCount": 0,
    "seals": [
      {
        "containerSealTypeCode": "string",
        "containerSealValue": "string"
      }
    ],
    "hazards": [
      {
        "unHazardousCode": "string",
        "unHazardousDescription": "string",
        "unHazardousClassCode": "string"
      }
    ],
    "stops": [
      {
        "stopTypeCode": "string"
      }
    ],
    "oversizes": [
      {
        "dimensionCode": "string",
        "oversizeValueCm": 0
      }
    ],
    "seaPortGateOutDateTime": "string",
    "inlandPortGateOutDateTime": "string",
    "cedoReleaseDateTime": "string",
    "attachedEquipment": "string",
    "vbsSlotDatetime": "string",
    "lastUpdated": "string",
    "activatedDate": "string",
    "previousContainerVisitId": 0,
    "expressPin": 0,
    "expressPinStatus": "string",
    "powerLastFreeDatetime": "string",
    "shuttleConnectPriorityStatus": "string"
  }
]
```

---

### 3.3 出口预报（ExportPreadvice）

#### 3.3.1 `DELETE /v1/export-preadvices`

**操作 ID：** `ExportPreadvice_CancelViaApim`  
**用途：** 取消已提交的出口预报。  
**完整 URL：** `https://api.portconnect.io/v1/export-preadvices`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v1/export-preadvices' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY' \
  --header 'Content-Type: application/json' \
  --data @request.json
```

**请求体**

| Content-Type | Schema |
| --- | --- |
| application/json | `GenericPreadviceRequest_Cancel` |

请求示例（`application/json`）：

```json
{
  "header": {
    "messageAction": {},
    "messageType": {},
    "tradingPartnerCode": "string",
    "notificationEmails": [
      "string"
    ],
    "userReference": "string",
    "partnerPortCode": "string",
    "loadPortCode": "string"
  },
  "containers": [
    {
      "containerNumber": "string"
    }
  ]
}
```

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 204 | — | 无响应体 | 成功 |

---

#### 3.3.2 `GET /v1/export-preadvices/{partnerPortCode}/{userReference}`

**操作 ID：** `ExportPreadvice_GetViaApim1`  
**用途：** 按合作港口代码和用户引用查询出口预报。  
**完整 URL：** `https://api.portconnect.io/v1/export-preadvices/{partnerPortCode}/{userReference}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `partnerPortCode` | 是 | `string` | — |
| path | `userReference` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/export-preadvices/NZAKL/REF-001' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `GenericPreadviceRequest` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "header": {
    "messageAction": {},
    "messageType": {},
    "tradingPartnerCode": "string",
    "notificationEmails": [
      "string"
    ],
    "shipperName": "string",
    "consigneeName": "string",
    "loadPortCode": "string",
    "bookingReference": "string",
    "pointOfOriginCode": "string",
    "vessel": {
      "shipName": "string",
      "voyageNumber": "string",
      "partnerPortShippingReference": "string"
    },
    "loadPortFacility": "string",
    "userName": "string",
    "lineOperatorCode": "string",
    "portOfDischarge": "string",
    "foreignPortOfDischarge": "string",
    "overseasDestinationFinal": "string",
    "userReference": "string"
  },
  "containers": [
    {
      "containerNumber": "string",
      "hazardousCertificate": {
        "hazardousCertificateUri": "string",
        "hazardousCertificateBase64": "string"
      },
      "latestSubmissionStatus": {
        "action": "string",
        "success": true
      },
      "currentStatus": "string",
      "attachedContainerNumbers": [
        "string"
      ],
      "isoTypeCode": "string",
      "flexiTank": true,
      "isFull": true,
      "commodityCode": "string",
      "isNonOperatingReefer": true,
      "refrigeration": {
        "isFantainer": true,
        "co2Percent": 0,
        "o2Percent": 0,
        "maximumOffPowerHours": 0,
        "offPowerTemperature": 0,
        "timeAllowedOffPowerHours": 0,
        "timeAllowedOffPowerMinutes": 0,
        "activeRefrigerationRequired": true,
        "offPowerTimestamp": "string",
        "onPowerTargetTime": "string",
        "requiredTemperature": 0,
        "humidityPercent": 0,
        "refrigerationType": {}
      },
      "vent": {
        "ventSettingType": "PercentageOpen",
        "ventSetting": 0
      },
      "imex": {
        "cutOffTimestamp": "string",
        "customsClearanceNumber": "string",
        "exportEntryNumber": "string"
      },
      "cargoWeightKg": 0,
      "totalWeightKg": 0,
      "hazardous": [
        {
          "flashPoint": 0,
          "medicalFirstAidGuide": "string",
          "medicalFirstAidGuideSet": true,
          "flashPointSet": true,
          "hazardousClass": "string",
          "unNumber": "string",
          "packagingGroup": "string",
          "limitedQuantities": true,
          "marinePollutant": true,
          "hazardousWeight": 0,
          "quantity": "string",
          "emsCode": "string",
          "uniqueId": "string",
          "hazardContact": {
            "name": "string",
            "phone": "string",
            "email": "string"
          }
        }
      ],
      "overGauge": [
        {
          "area": "Back",
          "measureCm": 0
        }
      ],
      "containerSeals": [
        {
          "sealType": "NZFSA",
          "sealCode": "string"
        }
      ],
      "arrivalCarrierType": {},
      "carrier": "string"
    }
  ],
  "comments": "string"
}
```

---

#### 3.3.3 `GET /v1/export-preadvices/{partnerPortCode}/{userReference}/{containerNumber}`

**操作 ID：** `ExportPreadvice_GetViaApim2`  
**用途：** 按合作港口代码、用户引用和箱号查询出口预报。  
**完整 URL：** `https://api.portconnect.io/v1/export-preadvices/{partnerPortCode}/{userReference}/{containerNumber}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `partnerPortCode` | 是 | `string` | — |
| path | `userReference` | 是 | `string` | — |
| path | `containerNumber` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/export-preadvices/NZAKL/REF-001/MSCU1234567' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `GenericPreadviceRequest` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "header": {
    "messageAction": {},
    "messageType": {},
    "tradingPartnerCode": "string",
    "notificationEmails": [
      "string"
    ],
    "shipperName": "string",
    "consigneeName": "string",
    "loadPortCode": "string",
    "bookingReference": "string",
    "pointOfOriginCode": "string",
    "vessel": {
      "shipName": "string",
      "voyageNumber": "string",
      "partnerPortShippingReference": "string"
    },
    "loadPortFacility": "string",
    "userName": "string",
    "lineOperatorCode": "string",
    "portOfDischarge": "string",
    "foreignPortOfDischarge": "string",
    "overseasDestinationFinal": "string",
    "userReference": "string"
  },
  "containers": [
    {
      "containerNumber": "string",
      "hazardousCertificate": {
        "hazardousCertificateUri": "string",
        "hazardousCertificateBase64": "string"
      },
      "latestSubmissionStatus": {
        "action": "string",
        "success": true
      },
      "currentStatus": "string",
      "attachedContainerNumbers": [
        "string"
      ],
      "isoTypeCode": "string",
      "flexiTank": true,
      "isFull": true,
      "commodityCode": "string",
      "isNonOperatingReefer": true,
      "refrigeration": {
        "isFantainer": true,
        "co2Percent": 0,
        "o2Percent": 0,
        "maximumOffPowerHours": 0,
        "offPowerTemperature": 0,
        "timeAllowedOffPowerHours": 0,
        "timeAllowedOffPowerMinutes": 0,
        "activeRefrigerationRequired": true,
        "offPowerTimestamp": "string",
        "onPowerTargetTime": "string",
        "requiredTemperature": 0,
        "humidityPercent": 0,
        "refrigerationType": {}
      },
      "vent": {
        "ventSettingType": "PercentageOpen",
        "ventSetting": 0
      },
      "imex": {
        "cutOffTimestamp": "string",
        "customsClearanceNumber": "string",
        "exportEntryNumber": "string"
      },
      "cargoWeightKg": 0,
      "totalWeightKg": 0,
      "hazardous": [
        {
          "flashPoint": 0,
          "medicalFirstAidGuide": "string",
          "medicalFirstAidGuideSet": true,
          "flashPointSet": true,
          "hazardousClass": "string",
          "unNumber": "string",
          "packagingGroup": "string",
          "limitedQuantities": true,
          "marinePollutant": true,
          "hazardousWeight": 0,
          "quantity": "string",
          "emsCode": "string",
          "uniqueId": "string",
          "hazardContact": {
            "name": "string",
            "phone": "string",
            "email": "string"
          }
        }
      ],
      "overGauge": [
        {
          "area": "Back",
          "measureCm": 0
        }
      ],
      "containerSeals": [
        {
          "sealType": "NZFSA",
          "sealCode": "string"
        }
      ],
      "arrivalCarrierType": {},
      "carrier": "string"
    }
  ],
  "comments": "string"
}
```

---

#### 3.3.4 `POST /v1/export-preadvices`

**操作 ID：** `ExportPreadvice_SubmitViaApim`  
**用途：** 提交出口预报。  
**完整 URL：** `https://api.portconnect.io/v1/export-preadvices`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request POST \
  --url 'https://api.portconnect.io/v1/export-preadvices' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY' \
  --header 'Content-Type: application/json' \
  --data @request.json
```

**请求体**

| Content-Type | Schema |
| --- | --- |
| application/json | `GenericPreadviceRequest` |

请求示例（`application/json`）：

```json
{
  "header": {
    "messageAction": {},
    "messageType": {},
    "tradingPartnerCode": "string",
    "notificationEmails": [
      "string"
    ],
    "shipperName": "string",
    "consigneeName": "string",
    "loadPortCode": "string",
    "bookingReference": "string",
    "pointOfOriginCode": "string",
    "vessel": {
      "shipName": "string",
      "voyageNumber": "string",
      "partnerPortShippingReference": "string"
    },
    "loadPortFacility": "string",
    "userName": "string",
    "lineOperatorCode": "string",
    "portOfDischarge": "string",
    "foreignPortOfDischarge": "string",
    "overseasDestinationFinal": "string",
    "userReference": "string"
  },
  "containers": [
    {
      "containerNumber": "string",
      "hazardousCertificate": {
        "hazardousCertificateUri": "string",
        "hazardousCertificateBase64": "string"
      },
      "latestSubmissionStatus": {
        "action": "string",
        "success": true
      },
      "currentStatus": "string",
      "attachedContainerNumbers": [
        "string"
      ],
      "isoTypeCode": "string",
      "flexiTank": true,
      "isFull": true,
      "commodityCode": "string",
      "isNonOperatingReefer": true,
      "refrigeration": {
        "isFantainer": true,
        "co2Percent": 0,
        "o2Percent": 0,
        "maximumOffPowerHours": 0,
        "offPowerTemperature": 0,
        "timeAllowedOffPowerHours": 0,
        "timeAllowedOffPowerMinutes": 0,
        "activeRefrigerationRequired": true,
        "offPowerTimestamp": "string",
        "onPowerTargetTime": "string",
        "requiredTemperature": 0,
        "humidityPercent": 0,
        "refrigerationType": {}
      },
      "vent": {
        "ventSettingType": "PercentageOpen",
        "ventSetting": 0
      },
      "imex": {
        "cutOffTimestamp": "string",
        "customsClearanceNumber": "string",
        "exportEntryNumber": "string"
      },
      "cargoWeightKg": 0,
      "totalWeightKg": 0,
      "hazardous": [
        {
          "flashPoint": 0,
          "medicalFirstAidGuide": "string",
          "medicalFirstAidGuideSet": true,
          "flashPointSet": true,
          "hazardousClass": "string",
          "unNumber": "string",
          "packagingGroup": "string",
          "limitedQuantities": true,
          "marinePollutant": true,
          "hazardousWeight": 0,
          "quantity": "string",
          "emsCode": "string",
          "uniqueId": "string",
          "hazardContact": {
            "name": "string",
            "phone": "string",
            "email": "string"
          }
        }
      ],
      "overGauge": [
        {
          "area": "Back",
          "measureCm": 0
        }
      ],
      "containerSeals": [
        {
          "sealType": "NZFSA",
          "sealCode": "string"
        }
      ],
      "arrivalCarrierType": {},
      "carrier": "string"
    }
  ],
  "comments": "string"
}
```

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 201 | application/json | `ApiPreadviceResponseModel` | 成功 |

响应示例（`201 application/json`）：

```json
{
  "success": true,
  "errors": [
    "string"
  ],
  "containers": [
    {
      "containerNumber": "string",
      "errors": [
        "string"
      ],
      "success": true
    }
  ],
  "preadviceSubmissionAuditHeaderId": 0
}
```

---

### 3.4 计划船舶（ScheduledVessels）

#### 3.4.1 `GET /v1/scheduled-vessels`

**操作 ID：** `ScheduledVessels_ScheduledVessels`  
**用途：** 按港口、船型、状态、到港时间或船名查询计划船舶。  
**完整 URL：** `https://api.portconnect.io/v1/scheduled-vessels`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| query | `portCode` | 否 | `string` | — |
| query | `vesselType` | 否 | `VesselTypes` | 枚举：None, Cruise, Commercial |
| query | `vesselStatus` | 否 | `VesselStatuses` | 枚举：None, Expected, Inport, Departed |
| query | `arrivalDateFrom` | 否 | `string<date-time>` | 可为 null |
| query | `arrivalDateTo` | 否 | `string<date-time>` | 可为 null |
| query | `vesselName` | 否 | `string` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/scheduled-vessels?portCode=NZAKL&vesselType=Commercial' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `V1Scheduled-vesselsGet200ApplicationJsonResponse` | 成功 |

响应示例（`200 application/json`）：

```json
[
  {
    "vesselVisitReference": "string",
    "vesselName": "string",
    "imoNumber": 0,
    "inboundVoyage": "string",
    "alternativeInboundVoyage": "string",
    "outboundVoyage": "string",
    "alternativeOutboundVoyage": "string",
    "vesselStatus": "string",
    "vesselType": "string",
    "portCode": "string",
    "wharfName": "string",
    "previousPortName": "string",
    "nextPortName": "string",
    "vesselOperator": "string",
    "serviceCode": "string",
    "arrivalDatetime": "string",
    "departureDatetime": "string",
    "receivalCommenceInland": "string",
    "receivalCommenceSeaport": "string",
    "receivalCutoffInland": "string",
    "rcvCommReeferinland": "string",
    "rcvCommHazinland": "string",
    "rcvCutoffHazinland": "string",
    "rcvCommReeferSeaport": "string",
    "rcvCommHazSeaport": "string",
    "rcvCutoffHazSeaport": "string",
    "receivalCutoffSeaport": "string",
    "lastUpdatedDateTime": "string",
    "visitPhase": "string",
    "agent": "string",
    "berth": "string"
  }
]
```

---

### 3.5 订阅 V1（Subscription）

#### 3.5.1 `POST /v1/subscriptions`

**操作 ID：** `Subscription_Create`  
**用途：** 创建 V1 集装箱/订舱事件订阅。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request POST \
  --url 'https://api.portconnect.io/v1/subscriptions' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY' \
  --header 'Content-Type: application/json' \
  --data @request.json
```

**请求体**

| Content-Type | Schema |
| --- | --- |
| application/json | `SubscriptionNewV1` |

请求示例（`application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "category": "string",
  "facilityCode": "string",
  "eventTypeCode": "string",
  "wharfType": "string",
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "bookings": [
    {
      "bookingNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ]
}
```

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 201 | application/json | `SubscriptionContainerV1Response` | 成功 |

响应示例（`201 application/json`）：

```json
{
  "subscriptionId": 0,
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ]
}
```

---

#### 3.5.2 `DELETE /v1/subscriptions/{subscriptionId}`

**操作 ID：** `Subscription_Delete`  
**用途：** 删除指定 V1 订阅。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions/{subscriptionId}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v1/subscriptions/12345' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 204 | — | 无响应体 | 成功 |

---

#### 3.5.3 `DELETE /v1/subscriptions/{subscriptionId}/bookings/{bookingNumber}`

**操作 ID：** `Subscription_DeleteBooking`  
**用途：** 从指定 V1 订阅中删除一个订舱号。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions/{subscriptionId}/bookings/{bookingNumber}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |
| path | `bookingNumber` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v1/subscriptions/12345/bookings/BOOKING-001' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/octet-stream | `V1Subscriptions-subscriptionId-Bookings-bookingNumber-Delete200ApplicationOctet-streamResponse` | 成功 |

---

#### 3.5.4 `DELETE /v1/subscriptions/{subscriptionId}/containers/{containerNumber}`

**操作 ID：** `Subscription_DeleteContainer`  
**用途：** 从指定 V1 订阅中删除一个箱号。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions/{subscriptionId}/containers/{containerNumber}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |
| path | `containerNumber` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v1/subscriptions/12345/containers/MSCU1234567' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/octet-stream | `V1Subscriptions-subscriptionId-Containers-containerNumber-Delete200ApplicationOctet-streamResponse` | 成功 |

---

#### 3.5.5 `GET /v1/subscriptions/{subscriptionId}`

**操作 ID：** `Subscription_Get`  
**用途：** 获取指定 V1 订阅。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions/{subscriptionId}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/subscriptions/12345' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `SubscriptionV1` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "category": "string",
  "facilityCode": "string",
  "eventTypeCode": "string",
  "wharfType": "string",
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "bookings": [
    {
      "bookingNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "subscriptionId": 0,
  "bookingsCount": 0
}
```

---

#### 3.5.6 `GET /v1/subscriptions`

**操作 ID：** `Subscription_GetAll`  
**用途：** 获取全部 V1 订阅。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/subscriptions' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `V1SubscriptionsGet200ApplicationJsonResponse` | 成功 |

响应示例（`200 application/json`）：

```json
[
  {
    "webhookURI": "string",
    "webhookToken": "string",
    "emailAddressList": [
      "string"
    ],
    "portCode": "string",
    "category": "string",
    "facilityCode": "string",
    "eventTypeCode": "string",
    "wharfType": "string",
    "containers": [
      {
        "containerNumber": "string",
        "userDefinedReference": "string",
        "expirationDatetime": "string"
      }
    ],
    "bookings": [
      {
        "bookingNumber": "string",
        "userDefinedReference": "string",
        "expirationDatetime": "string"
      }
    ],
    "subscriptionId": 0,
    "bookingsCount": 0
  }
]
```

---

#### 3.5.7 `GET /v1/subscriptions/{subscriptionId}/bookings`

**操作 ID：** `Subscription_GetBooking`  
**用途：** 获取指定 V1 订阅下的订舱信息。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions/{subscriptionId}/bookings`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/subscriptions/12345/bookings' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `SubscriptionV1` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "category": "string",
  "facilityCode": "string",
  "eventTypeCode": "string",
  "wharfType": "string",
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "bookings": [
    {
      "bookingNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "subscriptionId": 0,
  "bookingsCount": 0
}
```

---

#### 3.5.8 `GET /v1/subscriptions/{subscriptionId}/bookings/{bookingNumber}`

**操作 ID：** `Subscription_GetBooking2`  
**用途：** 按订舱号获取指定 V1 订阅下的订舱信息。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions/{subscriptionId}/bookings/{bookingNumber}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |
| path | `bookingNumber` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/subscriptions/12345/bookings/BOOKING-001' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `SubscriptionV1` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "category": "string",
  "facilityCode": "string",
  "eventTypeCode": "string",
  "wharfType": "string",
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "bookings": [
    {
      "bookingNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "subscriptionId": 0,
  "bookingsCount": 0
}
```

---

### 3.6 订阅 V2（Subscription2）

#### 3.6.1 `POST /v2/subscriptions`

**操作 ID：** `Subscription2_Create`  
**用途：** 创建 V2 集装箱/订舱事件订阅。  
**完整 URL：** `https://api.portconnect.io/v2/subscriptions`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request POST \
  --url 'https://api.portconnect.io/v2/subscriptions' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY' \
  --header 'Content-Type: application/json' \
  --data @request.json
```

**请求体**

| Content-Type | Schema |
| --- | --- |
| application/json | `SubscriptionNewV2` |

请求示例（`application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "category": "string",
  "facilityCode": "string",
  "eventTypeCodes": [
    "string"
  ],
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string",
      "subscriptionContainerId": 0
    }
  ],
  "bookings": [
    {
      "bookingNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ]
}
```

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 201 | application/json | `SubscriptionContainerV2Response` | 成功 |

响应示例（`201 application/json`）：

```json
{
  "subscriptionId": 0,
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string",
      "subscriptionContainerId": 0
    }
  ]
}
```

---

#### 3.6.2 `DELETE /v2/subscriptions/{subscriptionId}`

**操作 ID：** `Subscription2_Delete`  
**用途：** 删除指定 V2 订阅。  
**完整 URL：** `https://api.portconnect.io/v2/subscriptions/{subscriptionId}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v2/subscriptions/12345' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 204 | — | 无响应体 | 成功 |

---

#### 3.6.3 `DELETE /v2/subscriptions/{subscriptionId}/bookings/{bookingNumber}`

**操作 ID：** `Subscription2_DeleteBooking`  
**用途：** 从指定 V2 订阅中删除一个订舱号。  
**完整 URL：** `https://api.portconnect.io/v2/subscriptions/{subscriptionId}/bookings/{bookingNumber}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |
| path | `bookingNumber` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v2/subscriptions/12345/bookings/BOOKING-001' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/octet-stream | `V2Subscriptions-subscriptionId-Bookings-bookingNumber-Delete200ApplicationOctet-streamResponse` | 成功 |

---

#### 3.6.4 `DELETE /v2/subscriptions/{subscriptionId}/containers/{containerNumber}`

**操作 ID：** `Subscription2_DeleteContainer`  
**用途：** 从指定 V2 订阅中删除一个箱号。  
**完整 URL：** `https://api.portconnect.io/v2/subscriptions/{subscriptionId}/containers/{containerNumber}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |
| path | `containerNumber` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v2/subscriptions/12345/containers/MSCU1234567' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/octet-stream | `V2Subscriptions-subscriptionId-Containers-containerNumber-Delete200ApplicationOctet-streamResponse` | 成功 |

---

#### 3.6.5 `GET /v2/subscriptions/{subscriptionId}`

**操作 ID：** `Subscription2_Get`  
**用途：** 获取指定 V2 订阅。  
**完整 URL：** `https://api.portconnect.io/v2/subscriptions/{subscriptionId}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v2/subscriptions/12345' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `SubscriptionV2` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "category": "string",
  "facilityCode": "string",
  "eventTypeCodes": [
    "string"
  ],
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string",
      "subscriptionContainerId": 0
    }
  ],
  "bookings": [
    {
      "bookingNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "subscriptionId": 0,
  "bookingsCount": 0
}
```

---

#### 3.6.6 `GET /v2/subscriptions`

**操作 ID：** `Subscription2_GetAll`  
**用途：** 获取全部 V2 订阅。  
**完整 URL：** `https://api.portconnect.io/v2/subscriptions`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v2/subscriptions' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `V2SubscriptionsGet200ApplicationJsonResponse` | 成功 |

响应示例（`200 application/json`）：

```json
[
  {
    "webhookURI": "string",
    "webhookToken": "string",
    "emailAddressList": [
      "string"
    ],
    "portCode": "string",
    "category": "string",
    "facilityCode": "string",
    "eventTypeCodes": [
      "string"
    ],
    "containers": [
      {
        "containerNumber": "string",
        "userDefinedReference": "string",
        "expirationDatetime": "string",
        "subscriptionContainerId": 0
      }
    ],
    "bookings": [
      {
        "bookingNumber": "string",
        "userDefinedReference": "string",
        "expirationDatetime": "string"
      }
    ],
    "subscriptionId": 0,
    "bookingsCount": 0
  }
]
```

---

#### 3.6.7 `GET /v2/subscriptions/{subscriptionId}/bookings`

**操作 ID：** `Subscription2_GetBooking`  
**用途：** 获取指定 V2 订阅下的订舱信息。  
**完整 URL：** `https://api.portconnect.io/v2/subscriptions/{subscriptionId}/bookings`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v2/subscriptions/12345/bookings' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `SubscriptionV2` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "category": "string",
  "facilityCode": "string",
  "eventTypeCodes": [
    "string"
  ],
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string",
      "subscriptionContainerId": 0
    }
  ],
  "bookings": [
    {
      "bookingNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "subscriptionId": 0,
  "bookingsCount": 0
}
```

---

#### 3.6.8 `GET /v2/subscriptions/{subscriptionId}/bookings/{bookingNumber}`

**操作 ID：** `Subscription2_GetBooking2`  
**用途：** 按订舱号获取指定 V2 订阅下的订舱信息。  
**完整 URL：** `https://api.portconnect.io/v2/subscriptions/{subscriptionId}/bookings/{bookingNumber}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |
| path | `bookingNumber` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v2/subscriptions/12345/bookings/BOOKING-001' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `SubscriptionV2` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "category": "string",
  "facilityCode": "string",
  "eventTypeCodes": [
    "string"
  ],
  "containers": [
    {
      "containerNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string",
      "subscriptionContainerId": 0
    }
  ],
  "bookings": [
    {
      "bookingNumber": "string",
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ],
  "subscriptionId": 0,
  "bookingsCount": 0
}
```

---

### 3.7 船期订阅（SubscriptionVesselSchedule）

#### 3.7.1 `POST /v1/subscriptions-vessel-schedule`

**操作 ID：** `SubscriptionVesselSchedule_CreateSubscription`  
**用途：** 创建船期事件订阅。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions-vessel-schedule`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request POST \
  --url 'https://api.portconnect.io/v1/subscriptions-vessel-schedule' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY' \
  --header 'Content-Type: application/json' \
  --data @request.json
```

**请求体**

| Content-Type | Schema |
| --- | --- |
| application/json | `SubscriptionVesselScheduleNewV1` |

请求示例（`application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "subscriptionId": 0,
  "wharfType": "string",
  "eventTypeCodes": [
    "string"
  ],
  "vessels": [
    {
      "vesselRef": "string",
      "lloydNumber": 0,
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ]
}
```

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 201 | application/json | `SubscriptionVesselScheduleV1` | 成功 |

响应示例（`201 application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "subscriptionId": 0,
  "wharfType": "string",
  "eventTypeCodes": [
    "string"
  ],
  "vessels": [
    {
      "vesselRef": "string",
      "lloydNumber": 0,
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ]
}
```

---

#### 3.7.2 `DELETE /v1/subscriptions-vessel-schedule/{subscriptionId}`

**操作 ID：** `SubscriptionVesselSchedule_DeleteSubscription`  
**用途：** 删除指定船期订阅。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions-vessel-schedule/{subscriptionId}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v1/subscriptions-vessel-schedule/12345' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 204 | — | 无响应体 | 成功 |

---

#### 3.7.3 `DELETE /v1/subscriptions-vessel-schedule/{subscriptionId}/lloydnumber/{lloydNumber}`

**操作 ID：** `SubscriptionVesselSchedule_DeleteSubscriptionByLloydNumber`  
**用途：** 从船期订阅中删除指定 Lloyd 编号。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions-vessel-schedule/{subscriptionId}/lloydnumber/{lloydNumber}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |
| path | `lloydNumber` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v1/subscriptions-vessel-schedule/12345/lloydnumber/1234567' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 204 | — | 无响应体 | 成功 |

---

#### 3.7.4 `DELETE /v1/subscriptions-vessel-schedule/{subscriptionId}/vesselRef/{vesselRef}`

**操作 ID：** `SubscriptionVesselSchedule_DeleteSubscriptionByVesselRef`  
**用途：** 从船期订阅中删除指定 vesselRef。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions-vessel-schedule/{subscriptionId}/vesselRef/{vesselRef}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |
| path | `vesselRef` | 是 | `string` | — |

**cURL 示例**

```bash
curl --request DELETE \
  --url 'https://api.portconnect.io/v1/subscriptions-vessel-schedule/12345/vesselRef/VESSEL-REF-001' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 204 | — | 无响应体 | 成功 |

---

#### 3.7.5 `GET /v1/subscriptions-vessel-schedule/{subscriptionId}`

**操作 ID：** `SubscriptionVesselSchedule_GetSubscription`  
**用途：** 获取指定船期订阅。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions-vessel-schedule/{subscriptionId}`

**参数**

| 位置 | 名称 | 必填 | 类型 | 约束/枚举 |
| --- | --- | --- | --- | --- |
| path | `subscriptionId` | 是 | `integer<int32>` | — |

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/subscriptions-vessel-schedule/12345' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `SubscriptionVesselScheduleV1` | 成功 |

响应示例（`200 application/json`）：

```json
{
  "webhookURI": "string",
  "webhookToken": "string",
  "emailAddressList": [
    "string"
  ],
  "portCode": "string",
  "subscriptionId": 0,
  "wharfType": "string",
  "eventTypeCodes": [
    "string"
  ],
  "vessels": [
    {
      "vesselRef": "string",
      "lloydNumber": 0,
      "userDefinedReference": "string",
      "expirationDatetime": "string"
    }
  ]
}
```

---

#### 3.7.6 `GET /v1/subscriptions-vessel-schedule`

**操作 ID：** `SubscriptionVesselSchedule_SearchSubscriptions`  
**用途：** 查询全部船期订阅。  
**完整 URL：** `https://api.portconnect.io/v1/subscriptions-vessel-schedule`

**参数**

无路径、查询或操作级 Header 参数。

**cURL 示例**

```bash
curl --request GET \
  --url 'https://api.portconnect.io/v1/subscriptions-vessel-schedule' \
  --header 'Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY'
```

**请求体**

无请求体。

**响应**

| 状态码 | Content-Type | Schema | 说明 |
| --- | --- | --- | --- |
| 200 | application/json | `V1Subscriptions-vessel-scheduleGet200ApplicationJsonResponse` | 成功 |

响应示例（`200 application/json`）：

```json
[
  {
    "webhookURI": "string",
    "webhookToken": "string",
    "emailAddressList": [
      "string"
    ],
    "portCode": "string",
    "subscriptionId": 0,
    "wharfType": "string",
    "eventTypeCodes": [
      "string"
    ],
    "vessels": [
      {
        "vesselRef": "string",
        "lloydNumber": 0,
        "userDefinedReference": "string",
        "expirationDatetime": "string"
      }
    ]
  }
]
```

---

## 附录 A：数据模型

以下展开 108 个被公开接口直接或间接引用的 Schema。门户快照中的其他未引用 Schema 仍完整保留在随附 OpenAPI JSON 中。

### `AboutResponse`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `build` | 否 | `string` | 可为 null |

### `ApiPreadviceResponseContainerModel`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerNumber` | 否 | `string` | 可为 null |
| `errors` | 否 | `array<string>` | 可为 null |
| `success` | 否 | `boolean` | — |

### `ApiPreadviceResponseModel`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `success` | 否 | `boolean` | — |
| `errors` | 否 | `array<string>` | 可为 null |
| `containers` | 否 | `array<ApiPreadviceResponseContainerModel>` | 可为 null |
| `preadviceSubmissionAuditHeaderId` | 否 | `integer<int32>` | — |

### `ContainerOversize`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `dimensionCode` | 否 | `string` | 可为 null |
| `oversizeValueCm` | 否 | `number<float>` | — |

### `ContainerStop`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `stopTypeCode` | 否 | `string` | 可为 null |

### `ContainerVisit`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerVisitId` | 否 | `integer<int32>` | — |
| `portCode` | 否 | `string` | 可为 null |
| `category` | 否 | `string` | 可为 null |
| `containerNumber` | 否 | `string` | 可为 null |
| `shipmentDirection` | 否 | `string` | 可为 null |
| `inboundVesselRef` | 否 | `string` | 可为 null |
| `inboundVesselName` | 否 | `string` | 可为 null |
| `inboundVesselIMONumber` | 否 | `integer<int32>` | 可为 null |
| `inboundVesselPublishedArrivalDatetime` | 否 | `string<date-time>` | 可为 null |
| `inboundVesselActualArrivalDatetime` | 否 | `string<date-time>` | 可为 null |
| `inboundVesselPublishedDepartureDatetime` | 否 | `string<date-time>` | 可为 null |
| `inboundVesselActualDepartureDatetime` | 否 | `string<date-time>` | 可为 null |
| `outboundVesselRef` | 否 | `string` | 可为 null |
| `outboundVesselName` | 否 | `string` | 可为 null |
| `outboundVesselIMONumber` | 否 | `integer<int32>` | 可为 null |
| `outboundVesselPublishedArrivalDatetime` | 否 | `string<date-time>` | 可为 null |
| `outboundVesselActualArrivalDatetime` | 否 | `string<date-time>` | 可为 null |
| `outboundVesselPublishedDepartureDatetime` | 否 | `string<date-time>` | 可为 null |
| `outboundVesselActualDepartureDatetime` | 否 | `string<date-time>` | 可为 null |
| `containerIsoTypeCode` | 否 | `string` | 可为 null |
| `containerIsoTypeDescription` | 否 | `string` | 可为 null |
| `declaredWeight` | 否 | `number<float>` | — |
| `declaredWeightVgm` | 否 | `boolean` | — |
| `commodityCode` | 否 | `string` | 可为 null |
| `containerStatus` | 否 | `string` | 可为 null |
| `requiredTemperature` | 否 | `number<float>` | — |
| `ventSetting` | 否 | `string` | 可为 null |
| `o2Percent` | 否 | `number<float>` | 可为 null |
| `cO2Percent` | 否 | `number<float>` | 可为 null |
| `humidityPercent` | 否 | `number<float>` | 可为 null |
| `packedOffPowerDatetime` | 否 | `string<date-time>` | 可为 null |
| `packedOffPowerTemp` | 否 | `number<float>` | 可为 null |
| `maxHoursAllowedOffPower` | 否 | `number<float>` | 可为 null |
| `containerOperatorCode` | 否 | `string` | 可为 null |
| `containerOperatorName` | 否 | `string` | 可为 null |
| `containerOperatorVoyageId` | 否 | `string` | 可为 null |
| `loadPortCode` | 否 | `string` | 可为 null |
| `loadPortName` | 否 | `string` | 可为 null |
| `dischargePortCode` | 否 | `string` | 可为 null |
| `dischargePortName` | 否 | `string` | 可为 null |
| `destinationPortCode` | 否 | `string` | 可为 null |
| `destinationPortName` | 否 | `string` | 可为 null |
| `inlandPortArrivalDatetime` | 否 | `string<date-time>` | 可为 null |
| `inlandPortCarrier` | 否 | `string` | 可为 null |
| `seaPortCarrier` | 否 | `string` | 可为 null |
| `seaportTransportMode` | 否 | `string` | 可为 null |
| `loadDatetime` | 否 | `string<date-time>` | 可为 null |
| `receivedDatetime` | 否 | `string<date-time>` | 可为 null |
| `inlandPortInboundCarrier` | 否 | `string` | 可为 null |
| `seaPortArrivalDatetime` | 否 | `string<date-time>` | 可为 null |
| `seaPortInboundCarrier` | 否 | `string` | 可为 null |
| `bookingReference` | 否 | `string` | 可为 null |
| `cedoNumberCode` | 否 | `string` | 可为 null |
| `dischargedDatetime` | 否 | `string<date-time>` | 可为 null |
| `deliveredDatetime` | 否 | `string<date-time>` | 可为 null |
| `securityCheck` | 否 | `string` | 可为 null |
| `lastFreeDatetime` | 否 | `string<date-time>` | 可为 null |
| `lineReleaseDatetime` | 否 | `string<date-time>` | 可为 null |
| `customsReleaseDatetime` | 否 | `string<date-time>` | 可为 null |
| `mpiReleaseDatetime` | 否 | `string<date-time>` | 可为 null |
| `containerLocation` | 否 | `string` | 可为 null |
| `emptyReturnDepotCode` | 否 | `string` | 可为 null |
| `emptyReturnDepotName` | 否 | `string` | 可为 null |
| `sealCount` | 否 | `integer<int32>` | — |
| `hazardCount` | 否 | `integer<int32>` | — |
| `stopCount` | 否 | `integer<int32>` | — |
| `oversizeCount` | 否 | `integer<int32>` | — |
| `seals` | 否 | `array<ContainerVisitSeal>` | 可为 null |
| `hazards` | 否 | `array<HazardousCargo>` | 可为 null |
| `stops` | 否 | `array<ContainerStop>` | 可为 null |
| `oversizes` | 否 | `array<ContainerOversize>` | 可为 null |
| `seaPortGateOutDateTime` | 否 | `string<date-time>` | 可为 null |
| `inlandPortGateOutDateTime` | 否 | `string<date-time>` | 可为 null |
| `cedoReleaseDateTime` | 否 | `string<date-time>` | 可为 null |
| `attachedEquipment` | 否 | `string` | 可为 null |
| `vbsSlotDatetime` | 否 | `string<date-time>` | 可为 null |
| `lastUpdated` | 否 | `string<date-time>` | 可为 null |
| `activatedDate` | 否 | `string<date-time>` | 可为 null |
| `previousContainerVisitId` | 否 | `integer<int32>` | 可为 null |
| `expressPin` | 否 | `integer<int32>` | 可为 null |
| `expressPinStatus` | 否 | `string` | 可为 null |
| `powerLastFreeDatetime` | 否 | `string<date-time>` | 可为 null |
| `shuttleConnectPriorityStatus` | 否 | `string` | 可为 null |

### `ContainerVisitCategory`

**类型：** `string`  
**枚举值：** `Domestic`, `Export`, `Import`, `Restow`, `Storage`, `Through`, `Transhipment`


### `ContainerVisitSeal`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerSealTypeCode` | 否 | `string` | 可为 null |
| `containerSealValue` | 否 | `string` | 可为 null |

### `GenericPreadviceArrivalCarrierTypes`

**类型：** `string`  
**枚举值：** `Truck`, `Rail`


### `GenericPreadviceContainer`

**类型：** `GenericPreadviceContainerBase`  
**继承/组合：** `GenericPreadviceContainerBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerNumber` | 是 | `string` | 最短长度：1 |
| `hazardousCertificate` | 否 | `GenericPreadviceHazardousCertificate` | 可为 null |
| `latestSubmissionStatus` | 否 | `GenericPreadviceContainerSubmission` | 可为 null |
| `currentStatus` | 否 | `string` | 可为 null |
| `attachedContainerNumbers` | 否 | `array<string>` | 可为 null |
| `isoTypeCode` | 是 | `string` | 最短长度：1 |
| `flexiTank` | 否 | `boolean` | 可为 null |
| `isFull` | 否 | `boolean` | 可为 null |
| `commodityCode` | 是 | `string` | 最短长度：1 |
| `isNonOperatingReefer` | 否 | `boolean` | 可为 null |
| `refrigeration` | 否 | `GenericPreadviceRefrigeration` | 可为 null |
| `vent` | 否 | `GenericPreadviceVent` | 可为 null |
| `imex` | 否 | `GenericPreadviceIMEX` | 可为 null |
| `cargoWeightKg` | 否 | `number<float>` | — |
| `totalWeightKg` | 否 | `number<float>` | — |
| `hazardous` | 否 | `array<GenericPreadviceHazardous>` | 可为 null |
| `overGauge` | 否 | `array<GenericPreadviceOverDimension>` | 可为 null |
| `containerSeals` | 否 | `array<GenericPreadviceContainerSeal>` | 可为 null |
| `arrivalCarrierType` | 否 | `GenericPreadviceArrivalCarrierTypes` | 可为 null；枚举：Truck, Rail |
| `carrier` | 否 | `string` | 可为 null |

### `GenericPreadviceContainer_Cancel`

**类型：** `GenericPreadviceContainerBase`  
**继承/组合：** `GenericPreadviceContainerBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerNumber` | 是 | `string` | 最短长度：1 |

### `GenericPreadviceContainerBase`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerNumber` | 是 | `string` | 最短长度：1 |

### `GenericPreadviceContainerSeal`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `sealType` | 是 | `GenericPreadviceSealTypes` | 枚举：NZFSA, LineOperator, Shipper, Other |
| `sealCode` | 否 | `string` | 可为 null |

### `GenericPreadviceContainerSubmission`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `action` | 否 | `string` | 可为 null |
| `success` | 否 | `boolean` | — |

### `GenericPreadviceHazardContact`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `name` | 否 | `string` | 可为 null |
| `phone` | 否 | `string` | 可为 null |
| `email` | 否 | `string` | 可为 null |

### `GenericPreadviceHazardous`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `flashPoint` | 否 | `number<decimal>` | 可为 null |
| `medicalFirstAidGuide` | 否 | `string` | 可为 null |
| `medicalFirstAidGuideSet` | 否 | `boolean` | — |
| `flashPointSet` | 否 | `boolean` | — |
| `hazardousClass` | 否 | `string` | 可为 null |
| `unNumber` | 否 | `string` | 可为 null |
| `packagingGroup` | 否 | `string` | 可为 null |
| `limitedQuantities` | 否 | `boolean` | 可为 null |
| `marinePollutant` | 否 | `boolean` | 可为 null |
| `hazardousWeight` | 否 | `number<decimal>` | 可为 null |
| `quantity` | 否 | `string` | 可为 null |
| `emsCode` | 否 | `string` | 可为 null |
| `uniqueId` | 否 | `string<guid>` | 可为 null |
| `hazardContact` | 否 | `GenericPreadviceHazardContact` | 可为 null |

### `GenericPreadviceHazardousCertificate`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `hazardousCertificateUri` | 否 | `string` | 可为 null |
| `hazardousCertificateBase64` | 否 | `string` | 可为 null |

### `GenericPreadviceHeader`

**类型：** `GenericPreadviceHeaderBase`  
**继承/组合：** `GenericPreadviceHeaderBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `messageAction` | 否 | `MessageActions` | 可为 null；枚举：Create, Cancel, Get |
| `messageType` | 否 | `PreadviceMessageTypes` | 可为 null；枚举：PreAdvice, ExportPreAdvice, RailOrderPreAdvice |
| `tradingPartnerCode` | 否 | `string` | 可为 null |
| `notificationEmails` | 否 | `array<string>` | 可为 null |
| `shipperName` | 否 | `string` | 可为 null |
| `consigneeName` | 否 | `string` | 可为 null |
| `loadPortCode` | 是 | `string` | 最短长度：1 |
| `bookingReference` | 是 | `string` | 最短长度：1 |
| `pointOfOriginCode` | 否 | `string` | 可为 null |
| `vessel` | 否 | `GenericPreadviceVessel` | 可为 null |
| `loadPortFacility` | 是 | `string` | 最短长度：1 |
| `userName` | 否 | `string` | 可为 null |
| `lineOperatorCode` | 否 | `string` | 可为 null |
| `portOfDischarge` | 否 | `string` | 可为 null |
| `foreignPortOfDischarge` | 否 | `string` | 可为 null |
| `overseasDestinationFinal` | 否 | `string` | 可为 null |
| `userReference` | 否 | `string` | 可为 null |

### `GenericPreadviceHeader_Cancel`

**类型：** `GenericPreadviceHeaderBase`  
**继承/组合：** `GenericPreadviceHeaderBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `messageAction` | 否 | `MessageActions` | 可为 null；枚举：Create, Cancel, Get |
| `messageType` | 否 | `PreadviceMessageTypes` | 可为 null；枚举：PreAdvice, ExportPreAdvice, RailOrderPreAdvice |
| `tradingPartnerCode` | 否 | `string` | 可为 null |
| `notificationEmails` | 否 | `array<string>` | 可为 null |
| `userReference` | 是 | `string` | 最短长度：1 |
| `partnerPortCode` | 否 | `string` | 可为 null |
| `loadPortCode` | 否 | `string` | 可为 null |

### `GenericPreadviceHeaderBase`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `messageAction` | 否 | `MessageActions` | 可为 null；枚举：Create, Cancel, Get |
| `messageType` | 否 | `PreadviceMessageTypes` | 可为 null；枚举：PreAdvice, ExportPreAdvice, RailOrderPreAdvice |
| `tradingPartnerCode` | 否 | `string` | 可为 null |
| `notificationEmails` | 否 | `array<string>` | 可为 null |

### `GenericPreadviceIMEX`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `cutOffTimestamp` | 否 | `string<date-time>` | 可为 null |
| `customsClearanceNumber` | 否 | `string` | 可为 null |
| `exportEntryNumber` | 否 | `string` | 可为 null |

### `GenericPreadviceOverDimension`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `area` | 是 | `GenericPreadviceOverDimensionAreas` | 枚举：Back, Front, Top, Bottom, Left, Right |
| `measureCm` | 否 | `number<double>` | — |

### `GenericPreadviceOverDimensionAreas`

**类型：** `string`  
**枚举值：** `Back`, `Front`, `Top`, `Bottom`, `Left`, `Right`


### `GenericPreadviceRefrigeration`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `isFantainer` | 否 | `boolean` | — |
| `co2Percent` | 否 | `number<float>` | 可为 null |
| `o2Percent` | 否 | `number<float>` | 可为 null |
| `maximumOffPowerHours` | 否 | `number<float>` | 可为 null |
| `offPowerTemperature` | 否 | `number<float>` | 可为 null |
| `timeAllowedOffPowerHours` | 否 | `integer<int32>` | 可为 null |
| `timeAllowedOffPowerMinutes` | 否 | `integer<int32>` | 可为 null |
| `activeRefrigerationRequired` | 否 | `boolean` | 可为 null |
| `offPowerTimestamp` | 否 | `string<date-time>` | 可为 null |
| `onPowerTargetTime` | 否 | `string<date-time>` | 可为 null |
| `requiredTemperature` | 否 | `number<float>` | 可为 null |
| `humidityPercent` | 否 | `number<float>` | 可为 null |
| `refrigerationType` | 否 | `GenericPreadviceRefrigerationTypes` | 可为 null；枚举：Frozen, Chilled, Insulated, Hot |

### `GenericPreadviceRefrigerationTypes`

**类型：** `string`  
**枚举值：** `Frozen`, `Chilled`, `Insulated`, `Hot`


### `GenericPreadviceRequest`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `header` | 否 | `GenericPreadviceHeader` | 可为 null |
| `containers` | 否 | `array<GenericPreadviceContainer>` | 可为 null |
| `comments` | 否 | `string` | 可为 null |

### `GenericPreadviceRequest_Cancel`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `header` | 否 | `GenericPreadviceHeader_Cancel` | 可为 null |
| `containers` | 否 | `array<GenericPreadviceContainer_Cancel>` | 可为 null |

### `GenericPreadviceSealTypes`

**类型：** `string`  
**枚举值：** `NZFSA`, `LineOperator`, `Shipper`, `Other`


### `GenericPreadviceVent`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `ventSettingType` | 是 | `GenericPreadviceVentSettingTypes` | 枚举：PercentageOpen, FlowM3PerHour |
| `ventSetting` | 否 | `number<float>` | — |

### `GenericPreadviceVentSettingTypes`

**类型：** `string`  
**枚举值：** `PercentageOpen`, `FlowM3PerHour`


### `GenericPreadviceVessel`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `shipName` | 否 | `string` | 可为 null |
| `voyageNumber` | 否 | `string` | 可为 null |
| `partnerPortShippingReference` | 否 | `string` | 可为 null |

### `HazardousCargo`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `unHazardousCode` | 否 | `string` | 可为 null |
| `unHazardousDescription` | 否 | `string` | 可为 null |
| `unHazardousClassCode` | 否 | `string` | 可为 null |

### `MessageActions`

**类型：** `string`  
**枚举值：** `Create`, `Cancel`, `Get`


### `PreadviceMessageTypes`

**类型：** `string`  
**枚举值：** `PreAdvice`, `ExportPreAdvice`, `RailOrderPreAdvice`


### `ScheduledVessel`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `vesselVisitReference` | 否 | `string` | 可为 null |
| `vesselName` | 否 | `string` | 可为 null |
| `imoNumber` | 否 | `integer<int32>` | 可为 null |
| `inboundVoyage` | 否 | `string` | 可为 null |
| `alternativeInboundVoyage` | 否 | `string` | 可为 null |
| `outboundVoyage` | 否 | `string` | 可为 null |
| `alternativeOutboundVoyage` | 否 | `string` | 可为 null |
| `vesselStatus` | 否 | `string` | 可为 null |
| `vesselType` | 是 | `string` | 最短长度：1 |
| `portCode` | 否 | `string` | 可为 null |
| `wharfName` | 否 | `string` | 可为 null |
| `previousPortName` | 否 | `string` | 可为 null |
| `nextPortName` | 否 | `string` | 可为 null |
| `vesselOperator` | 否 | `string` | 可为 null |
| `serviceCode` | 否 | `string` | 可为 null |
| `arrivalDatetime` | 否 | `string<date-time>` | 可为 null |
| `departureDatetime` | 否 | `string<date-time>` | 可为 null |
| `receivalCommenceInland` | 否 | `string<date-time>` | 可为 null |
| `receivalCommenceSeaport` | 否 | `string<date-time>` | 可为 null |
| `receivalCutoffInland` | 否 | `string<date-time>` | 可为 null |
| `rcvCommReeferinland` | 否 | `string<date-time>` | 可为 null |
| `rcvCommHazinland` | 否 | `string<date-time>` | 可为 null |
| `rcvCutoffHazinland` | 否 | `string<date-time>` | 可为 null |
| `rcvCommReeferSeaport` | 否 | `string<date-time>` | 可为 null |
| `rcvCommHazSeaport` | 否 | `string<date-time>` | 可为 null |
| `rcvCutoffHazSeaport` | 否 | `string<date-time>` | 可为 null |
| `receivalCutoffSeaport` | 否 | `string<date-time>` | 可为 null |
| `lastUpdatedDateTime` | 否 | `string<date-time>` | 可为 null |
| `visitPhase` | 否 | `string` | 可为 null |
| `agent` | 否 | `string` | 可为 null |
| `berth` | 否 | `string` | 可为 null |

### `SubscriptionBooking`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `bookingNumber` | 否 | `string` | 可为 null |
| `userDefinedReference` | 否 | `string` | 可为 null；最长长度：500 |
| `expirationDatetime` | 否 | `string<date-time>` | 可为 null |

### `SubscriptionContainerV1`

**类型：** `SubscriptionPatchContainerV1`  
**继承/组合：** `SubscriptionPatchContainerV1`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerNumber` | 否 | `string` | 可为 null |
| `userDefinedReference` | 否 | `string` | 可为 null；最长长度：500 |
| `expirationDatetime` | 否 | `string<date-time>` | 可为 null |

### `SubscriptionContainerV1Response`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `subscriptionId` | 否 | `integer<int32>` | — |
| `containers` | 否 | `array<SubscriptionContainerV1>` | 可为 null |

### `SubscriptionContainerV2`

**类型：** `SubscriptionPatchContainerV2`  
**继承/组合：** `SubscriptionPatchContainerV2`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerNumber` | 否 | `string` | 可为 null |
| `userDefinedReference` | 否 | `string` | 可为 null；最长长度：500 |
| `expirationDatetime` | 否 | `string<date-time>` | 可为 null |
| `subscriptionContainerId` | 否 | `integer<int32>` | — |

### `SubscriptionContainerV2Response`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `subscriptionId` | 否 | `integer<int32>` | — |
| `containers` | 否 | `array<SubscriptionContainerV2>` | 可为 null |

### `SubscriptionNewV1`

**类型：** `SubscriptionPatchV1`  
**继承/组合：** `SubscriptionPatchV1`, `SubscriptionPatchBaseV1`, `SubscriptionPatchContainerBase`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |
| `eventTypeCode` | 是 | `string` | 最短长度：1 |
| `wharfType` | 否 | `string` | 可为 null |
| `containers` | 否 | `array<SubscriptionContainerV1>` | 可为 null |
| `bookings` | 否 | `array<SubscriptionBooking>` | 可为 null |

### `SubscriptionNewV2`

**类型：** `SubscriptionPatchV2`  
**继承/组合：** `SubscriptionPatchV2`, `SubscriptionPatchBaseV2`, `SubscriptionPatchContainerBase`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |
| `eventTypeCodes` | 是 | `array<string>` | — |
| `containers` | 否 | `array<SubscriptionContainerV2>` | 可为 null |
| `bookings` | 否 | `array<SubscriptionBooking>` | 可为 null |

### `SubscriptionPatchBase`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |

### `SubscriptionPatchBaseV1`

**类型：** `SubscriptionPatchContainerBase`  
**继承/组合：** `SubscriptionPatchContainerBase`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |

### `SubscriptionPatchBaseV2`

**类型：** `SubscriptionPatchContainerBase`  
**继承/组合：** `SubscriptionPatchContainerBase`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |

### `SubscriptionPatchContainerBase`

**类型：** `SubscriptionPatchBase`  
**继承/组合：** `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |

### `SubscriptionPatchContainerV1`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerNumber` | 否 | `string` | 可为 null |
| `userDefinedReference` | 否 | `string` | 可为 null；最长长度：500 |

### `SubscriptionPatchContainerV2`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `containerNumber` | 否 | `string` | 可为 null |
| `userDefinedReference` | 否 | `string` | 可为 null；最长长度：500 |

### `SubscriptionPatchV1`

**类型：** `SubscriptionPatchBaseV1`  
**继承/组合：** `SubscriptionPatchBaseV1`, `SubscriptionPatchContainerBase`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |
| `eventTypeCode` | 是 | `string` | 最短长度：1 |
| `wharfType` | 否 | `string` | 可为 null |

### `SubscriptionPatchV2`

**类型：** `SubscriptionPatchBaseV2`  
**继承/组合：** `SubscriptionPatchBaseV2`, `SubscriptionPatchContainerBase`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |
| `eventTypeCodes` | 是 | `array<string>` | — |

### `SubscriptionPatchVesselV1`

**类型：** `object`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `vesselRef` | 否 | `string` | 可为 null |
| `lloydNumber` | 否 | `integer<int32>` | 可为 null |
| `userDefinedReference` | 否 | `string` | 可为 null；最长长度：500 |

### `SubscriptionV1`

**类型：** `SubscriptionNewV1`  
**继承/组合：** `SubscriptionNewV1`, `SubscriptionPatchV1`, `SubscriptionPatchBaseV1`, `SubscriptionPatchContainerBase`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |
| `eventTypeCode` | 是 | `string` | 最短长度：1 |
| `wharfType` | 否 | `string` | 可为 null |
| `containers` | 否 | `array<SubscriptionContainerV1>` | 可为 null |
| `bookings` | 否 | `array<SubscriptionBooking>` | 可为 null |
| `subscriptionId` | 否 | `integer<int32>` | — |
| `bookingsCount` | 否 | `integer<int32>` | — |

### `SubscriptionV2`

**类型：** `SubscriptionNewV2`  
**继承/组合：** `SubscriptionNewV2`, `SubscriptionPatchV2`, `SubscriptionPatchBaseV2`, `SubscriptionPatchContainerBase`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `category` | 是 | `string` | 最短长度：1 |
| `facilityCode` | 否 | `string` | 可为 null |
| `eventTypeCodes` | 是 | `array<string>` | — |
| `containers` | 否 | `array<SubscriptionContainerV2>` | 可为 null |
| `bookings` | 否 | `array<SubscriptionBooking>` | 可为 null |
| `subscriptionId` | 否 | `integer<int32>` | — |
| `bookingsCount` | 否 | `integer<int32>` | — |

### `SubscriptionVesselScheduleNewV1`

**类型：** `SubscriptionVesselSchedulePatchV1`  
**继承/组合：** `SubscriptionVesselSchedulePatchV1`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `subscriptionId` | 否 | `integer<int32>` | — |
| `wharfType` | 否 | `string` | 可为 null |
| `eventTypeCodes` | 是 | `array<string>` | — |
| `vessels` | 否 | `array<SubscriptionVesselV1>` | 可为 null |

### `SubscriptionVesselSchedulePatchV1`

**类型：** `SubscriptionPatchBase`  
**继承/组合：** `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `subscriptionId` | 否 | `integer<int32>` | — |
| `wharfType` | 否 | `string` | 可为 null |
| `eventTypeCodes` | 是 | `array<string>` | — |

### `SubscriptionVesselScheduleV1`

**类型：** `SubscriptionVesselScheduleNewV1`  
**继承/组合：** `SubscriptionVesselScheduleNewV1`, `SubscriptionVesselSchedulePatchV1`, `SubscriptionPatchBase`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `webhookURI` | 否 | `string` | 可为 null |
| `webhookToken` | 否 | `string` | 可为 null |
| `emailAddressList` | 是 | `array<string>` | — |
| `portCode` | 是 | `string` | 最短长度：1 |
| `subscriptionId` | 否 | `integer<int32>` | — |
| `wharfType` | 否 | `string` | 可为 null |
| `eventTypeCodes` | 是 | `array<string>` | — |
| `vessels` | 否 | `array<SubscriptionVesselV1>` | 可为 null |

### `SubscriptionVesselV1`

**类型：** `SubscriptionPatchVesselV1`  
**继承/组合：** `SubscriptionPatchVesselV1`  

| 字段 | 必填 | 类型 | 约束/说明 |
| --- | --- | --- | --- |
| `vesselRef` | 否 | `string` | 可为 null |
| `lloydNumber` | 否 | `integer<int32>` | 可为 null |
| `userDefinedReference` | 否 | `string` | 可为 null；最长长度：500 |
| `expirationDatetime` | 否 | `string<date-time>` | 可为 null |

### `V1Container-visits-containerVisitId-GetRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Container-visitsGet200ApplicationJsonResponse`

**类型：** `array<ContainerVisit>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Container-visitsGetRequest`

**类型：** `array<string>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Container-visitsGetRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Container-visitsGetRequest-2`

**类型：** `ContainerVisitCategory`  
**枚举值：** `Domestic`, `Export`, `Import`, `Restow`, `Storage`, `Through`, `Transhipment`


### `V1Container-visitsGetRequest-3`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Export-preadvices-partnerPortCode-userReference-containerNumber-GetRequest`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Export-preadvices-partnerPortCode-userReference-containerNumber-GetRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Export-preadvices-partnerPortCode-userReference-containerNumber-GetRequest-2`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Export-preadvices-partnerPortCode-userReference-GetRequest`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Export-preadvices-partnerPortCode-userReference-GetRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Scheduled-vesselsGet200ApplicationJsonResponse`

**类型：** `array<ScheduledVessel>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Scheduled-vesselsGetRequest`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Scheduled-vesselsGetRequest-1`

**类型：** `VesselTypes`  
**枚举值：** `None`, `Cruise`, `Commercial`


### `V1Scheduled-vesselsGetRequest-2`

**类型：** `VesselStatuses`  
**枚举值：** `None`, `Expected`, `Inport`, `Departed`


### `V1Scheduled-vesselsGetRequest-3`

**类型：** `string<date-time>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Scheduled-vesselsGetRequest-4`

**类型：** `string<date-time>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Scheduled-vesselsGetRequest-5`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-Bookings-bookingNumber-Delete200ApplicationOctet-streamResponse`

**类型：** `string<binary>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-Bookings-bookingNumber-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-Bookings-bookingNumber-DeleteRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-Bookings-bookingNumber-GetRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-Bookings-bookingNumber-GetRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-BookingsGetRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-Containers-containerNumber-Delete200ApplicationOctet-streamResponse`

**类型：** `string<binary>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-Containers-containerNumber-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-Containers-containerNumber-DeleteRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-subscriptionId-GetRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-vessel-schedule-subscriptionId-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-vessel-schedule-subscriptionId-GetRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-vessel-schedule-subscriptionId-Lloydnumber-lloydNumber-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-vessel-schedule-subscriptionId-Lloydnumber-lloydNumber-DeleteRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-vessel-schedule-subscriptionId-VesselRef-vesselRef-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-vessel-schedule-subscriptionId-VesselRef-vesselRef-DeleteRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1Subscriptions-vessel-scheduleGet200ApplicationJsonResponse`

**类型：** `array<SubscriptionVesselScheduleV1>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V1SubscriptionsGet200ApplicationJsonResponse`

**类型：** `array<SubscriptionV1>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-Bookings-bookingNumber-Delete200ApplicationOctet-streamResponse`

**类型：** `string<binary>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-Bookings-bookingNumber-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-Bookings-bookingNumber-DeleteRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-Bookings-bookingNumber-GetRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-Bookings-bookingNumber-GetRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-BookingsGetRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-Containers-containerNumber-Delete200ApplicationOctet-streamResponse`

**类型：** `string<binary>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-Containers-containerNumber-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-Containers-containerNumber-DeleteRequest-1`

**类型：** `string`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-DeleteRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2Subscriptions-subscriptionId-GetRequest`

**类型：** `integer<int32>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `V2SubscriptionsGet200ApplicationJsonResponse`

**类型：** `array<SubscriptionV2>`  

该 Schema 为基本类型、数组或组合包装类型，没有独立字段表。

### `VesselStatuses`

**类型：** `string`  
**枚举值：** `None`, `Expected`, `Inport`, `Departed`


### `VesselTypes`

**类型：** `string`  
**枚举值：** `None`, `Cruise`, `Commercial`


## 附录 B：来源与限制

- PortConnect API 门户：[https://developer.portconnect.io/api-details#api=portconnect-api](https://developer.portconnect.io/api-details#api=portconnect-api)
- 抽取日期：2026-08-13（Pacific/Auckland）
- API Revision：19 — Added berth to vessel schedule API
- 本文未使用真实订阅密钥执行生产请求，因此示例用于说明请求格式，不代表实时业务数据。
- 门户未声明统一错误响应 Schema；接入方应在联调时确认 400、401、403、404、409、429 和 5xx 的实际响应。
