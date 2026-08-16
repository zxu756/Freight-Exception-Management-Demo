"""
Customer notification model for freight exceptions.
客户通知模型 - 货运异常主动客户通知

Scenario 4 / Kratos SLA 文档要求主动通知应包含：受影响货物、延误原因、
修订 ETA、正在采取的行动、置信度和下次更新时间。异常生成时同步生成
一条 plain-English 客户通知。
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from database import Base


class ExceptionNotification(Base):
    """A proactive customer notification for a freight exception."""
    __tablename__ = "exception_notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(50), unique=True, nullable=False, index=True)
    mode = Column(String(10), nullable=False)  # 'sea', 'road', 'air'
    exception_id = Column(String(50), nullable=False, index=True)  # 关联异常
    reference = Column(String(50), nullable=False)  # 货物单号（awb/consignment/container）
    recipient = Column(String(200), nullable=False)  # 客户名
    recipient_email = Column(String(200), nullable=True)  # 实际收件邮箱（客户主数据）
    recipient_phone = Column(String(30), nullable=True)  # 实际收件电话（客户主数据）
    channel = Column(String(20), nullable=False, default='email')
    sent_status = Column(String(20), nullable=False, default='pending')  # pending/sent/failed/delivered
    external_message_id = Column(String(100), nullable=True)  # 邮件/SMS 网关回写的外部消息 ID
    sent_real_at = Column(DateTime, nullable=True)  # 真实外发时间（真实世界时间）
    # COM-003 人工审核：高风险/敏感客户通知必须人工确认后才能外发
    review_status = Column(String(20), nullable=False, default='approved')  # approved/pending_review/rejected
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    edited_message = Column(Text, nullable=True)  # 审核修改后的最终文案
    message = Column(Text, nullable=False)  # plain-English 通知
    revised_eta = Column(DateTime, nullable=True)
    confidence = Column(Float, nullable=True)  # AI 置信度
    next_update_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)


def build_customer_notification(
    customer_name, reference, category, root_cause, revised_eta, recovery, confidence, next_update_at
):
    """Build a plain-English customer notification message (Kratos SLA format)."""
    action = ", ".join(recovery) if recovery else "monitoring"
    eta = revised_eta.strftime("%d %b %H:%M") if revised_eta else "to be confirmed"
    nxt = next_update_at.strftime("%d %b %H:%M") if next_update_at else "within 2 hours"
    return (
        f"Hi {customer_name}, your freight {reference} has been affected by a {category}. "
        f"Cause: {root_cause or 'under investigation'}. "
        f"Revised ETA: {eta}. We are arranging: {action}. "
        f"Next update: {nxt}. (AI confidence {confidence:.0%})"
    )
