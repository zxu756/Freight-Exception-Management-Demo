"""AI advice engine - generates actionable recommendations."""
from datetime import datetime, timedelta


# 建议库 - 根据异常类型和情况生成具体建议
ADVICE_TEMPLATES = {
    "delay": [
        {
            "title": "联系客户更新ETA",
            "action": "立即联系客户，告知延误情况并提供更新后的ETA",
            "priority": "high",
            "estimated_cost": 0,
            "estimated_time_saved": "2-4小时",
            "reason": "主动沟通可以减少客户投诉，维护关系",
        },
        {
            "title": "改订下一班船期",
            "action": "联系船公司改订最近可用的船期",
            "priority": "medium",
            "estimated_cost": 500,
            "estimated_time_saved": "24-48小时",
            "reason": "当前船期延误严重，改订更快的船期可以缩短等待时间",
        },
        {
            "title": "申请优先卸货",
            "action": "向港口申请优先卸货位置",
            "priority": "medium",
            "estimated_cost": 300,
            "estimated_time_saved": "4-8小时",
            "reason": "优先卸货可以减少在港等待时间",
        },
    ],
    "customs_hold": [
        {
            "title": "补充商业发票",
            "action": "联系发货人提供完整的商业发票",
            "priority": "high",
            "estimated_cost": 0,
            "estimated_time_saved": "12-24小时",
            "reason": "商业发票不完整是海关扣留的常见原因",
        },
        {
            "title": "联系报关行加急",
            "action": "联系报关行加急处理清关手续",
            "priority": "high",
            "estimated_cost": 200,
            "estimated_time_saved": "6-12小时",
            "reason": "报关行可以协助加快清关流程",
        },
        {
            "title": "支付关税",
            "action": "确认并支付所需关税",
            "priority": "medium",
            "estimated_cost": None,  # 需要确认具体金额
            "estimated_time_saved": "4-8小时",
            "reason": "关税未支付会导致货物滞留",
        },
    ],
    "damage": [
        {
            "title": "安排联合检验",
            "action": "联系保险公司和承运人安排联合检验",
            "priority": "high",
            "estimated_cost": 400,
            "estimated_time_saved": "N/A",
            "reason": "及时检验可以固定证据，便于后续索赔",
        },
        {
            "title": "拍照取证",
            "action": "对损坏货物进行拍照取证",
            "priority": "high",
            "estimated_cost": 0,
            "estimated_time_saved": "N/A",
            "reason": "照片是索赔的重要证据",
        },
        {
            "title": "联系客户协商赔偿",
            "action": "联系客户协商赔偿方案",
            "priority": "medium",
            "estimated_cost": None,
            "estimated_time_saved": "N/A",
            "reason": "主动协商可以维护客户关系",
        },
    ],
    "misroute": [
        {
            "title": "立即纠正路由",
            "action": "联系承运人纠正货物路由",
            "priority": "high",
            "estimated_cost": 300,
            "estimated_time_saved": "12-24小时",
            "reason": "及时纠正可以避免货物被运到错误地点",
        },
        {
            "title": "拦截货物",
            "action": "在下一节点拦截货物",
            "priority": "high",
            "estimated_cost": 200,
            "estimated_time_saved": "6-12小时",
            "reason": "拦截货物可以防止进一步错运",
        },
    ],
}

# 客户等级影响建议
TIER_IMPACT = {
    "VIP": {
        "escalation": True,
        "response_time": "立即",
        "communication": "电话沟通",
    },
    "high": {
        "escalation": True,
        "response_time": "1小时内",
        "communication": "邮件+电话",
    },
    "medium": {
        "escalation": False,
        "response_time": "4小时内",
        "communication": "邮件",
    },
    "low": {
        "escalation": False,
        "response_time": "24小时内",
        "communication": "邮件",
    },
}


def generate_advice(exception_type, container_info, exception_info):
    """根据异常类型和货物信息生成处理建议"""
    templates = ADVICE_TEMPLATES.get(exception_type, ADVICE_TEMPLATES["delay"])
    customer_tier = container_info.get("customer_tier", "medium")
    tier_info = TIER_IMPACT.get(customer_tier, TIER_IMPACT["medium"])
    
    advice_list = []
    for i, template in enumerate(templates):
        advice = {
            "id": i + 1,
            "title": template["title"],
            "action": template["action"],
            "priority": template["priority"],
            "estimated_cost": template["estimated_cost"],
            "estimated_time_saved": template["estimated_time_saved"],
            "reason": template["reason"],
            "requires_approval": template["estimated_cost"] and template["estimated_cost"] > 200,
        }
        advice_list.append(advice)
    
    # 生成总结
    total_cost = sum(a["estimated_cost"] for a in advice_list if a["estimated_cost"])
    summary = {
        "exception_type": exception_type,
        "customer_tier": customer_tier,
        "customer_name": container_info.get("customer_name", "Unknown"),
        "container_number": container_info.get("container_number", "Unknown"),
        "total_estimated_cost": total_cost,
        "response_time": tier_info["response_time"],
        "communication_method": tier_info["communication"],
        "escalation_required": tier_info["escalation"],
        "advice_count": len(advice_list),
    }
    
    return {"summary": summary, "advice": advice_list}


def generate_quick_response(exception_type, severity, risk_score):
    """生成快速响应建议"""
    responses = {
        ("delay", "critical"): {
            "immediate_action": "立即联系客户并升级处理",
            "escalation": "通知Operations Manager",
            "timeline": "15分钟内响应",
        },
        ("delay", "high"): {
            "immediate_action": "联系客户更新ETA",
            "escalation": "通知Team Lead",
            "timeline": "30分钟内响应",
        },
        ("delay", "medium"): {
            "immediate_action": "邮件通知客户",
            "escalation": "无需升级",
            "timeline": "2小时内响应",
        },
        ("customs_hold", "high"): {
            "immediate_action": "联系报关行加急处理",
            "escalation": "通知客户可能的延误",
            "timeline": "1小时内响应",
        },
        ("damage", "high"): {
            "immediate_action": "安排联合检验",
            "escalation": "通知保险公司",
            "timeline": "立即响应",
        },
    }
    
    return responses.get((exception_type, severity), {
        "immediate_action": "监控情况发展",
        "escalation": "根据需要升级",
        "timeline": "4小时内响应",
    })


def estimate_recovery_cost(exception_type, cargo_value):
    """估算恢复成本"""
    base_costs = {
        "delay": 400,
        "customs_hold": 300,
        "damage": 1500,
        "misroute": 650,
    }
    base = base_costs.get(exception_type, 300)
    # 加上货物价值的1%
    total = base + (cargo_value or 0) * 0.01
    return round(total, 2)
