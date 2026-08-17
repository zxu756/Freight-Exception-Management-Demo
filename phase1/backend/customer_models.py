"""
Customer master data - one coherent directory of NZ freight customers.
客户主数据 - 新西兰货运客户的统一目录（基本信息 + 联系方式）。

三种运输方式共用同一客户目录。每位客户保存：等级、联系人、
职务、邮箱、电话、手机、地址、城市/区域、偏好通知渠道（email/sms），
供异常主动通知（通知谁、发到哪）和上帝视角客户目录使用。
"""
import hashlib
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from database import Base


class Customer(Base):
    """Customer master data (shared across sea / air / road)."""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    tier = Column(String(20), nullable=False)  # VIP / high / medium / low
    contact_name = Column(String(100), nullable=False)
    contact_title = Column(String(100), nullable=True)
    email = Column(String(200), nullable=False)
    phone = Column(String(30), nullable=True)
    mobile = Column(String(30), nullable=True)
    address_line = Column(String(200), nullable=True)
    city = Column(String(50), nullable=True)
    region = Column(String(50), nullable=True)
    preferred_channel = Column(String(10), nullable=False, default="email")  # email / sms
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 三种运输方式客户名单的并集 (name, tier)
CUSTOMER_MASTER = [
    ("Fonterra", "VIP"), ("Silver Fern Farms", "VIP"), ("Zespri International", "high"),
    ("Fisher & Paykel Healthcare", "VIP"), ("Fisher & Paykel Appliances", "high"),
    ("Sanford Limited", "high"), ("Sealord Group", "high"), ("Mount Cook Alpine Salmon", "high"),
    ("Manuka Health", "high"), ("Cloudy Bay Vineyards", "medium"), ("Wools of New Zealand", "medium"),
    ("Mainfreight", "medium"), ("Foodstuffs NZ", "medium"), ("Countdown Supermarkets", "high"),
    ("NZ Post", "low"), ("Toyota NZ", "medium"), ("Fletcher Building", "medium"),
    ("Goodman Fielder", "medium"), ("Coca-Cola Amatil NZ", "medium"), ("Pharmac NZ", "VIP"),
    ("Kmart NZ", "low"), ("The Warehouse Group", "low"), ("Briscoe Group", "medium"),
    ("PlaceMakers", "medium"), ("Steel & Tube", "medium"), ("Gallagher Group", "high"),
    ("Rocket Lab", "high"), ("Air New Zealand Engineering", "high"), ("Russell McVeagh", "high"),
    ("Southern DHB", "high"), ("Pacific Produce Imports", "low"), ("Pacific Fresh Foods", "medium"),
    ("Plant & Food Research", "high"), ("Comvita", "medium"),
]

_FIRST = ["Sarah", "James", "Emma", "Liam", "Olivia", "Noah", "Ava", "Oliver", "Mia", "Jack",
         "Isla", "Thomas", "Sophie", "Daniel", "Grace", "Ben", "Hannah", "Lucas", "Amelia", "Ryan"]
_LAST = ["Mitchell", "Carter", "Walker", "Ngata", "Patel", "Fraser", "Thompson", "Wilson",
         "Harris", "Lee", "Anderson", "Clarke", "Bennett", "Harrison", "Stewart", "Kaur"]
_TITLES = ["Logistics Manager", "Supply Chain Manager", "Import Coordinator", "Operations Lead",
           "Distribution Manager", "Customs & Trade Manager", "Freight & Logistics Lead"]
_STREETS = ["Queen Street", "Customs Street East", "Victoria Street", "Harbour View Road",
            "Airport Business Park", "Port Road", "Great South Road", "Blenheim Road",
            "Waterloo Quay", "Fitzherbert Avenue"]
_CITIES = ["Auckland", "Auckland", "Auckland", "Wellington", "Christchurch", "Tauranga",
           "Hamilton", "Dunedin", "Napier", "Nelson", "Palmerston North", "Invercargill"]
_REGIONS = {"Auckland": "Auckland", "Wellington": "Wellington", "Christchurch": "Canterbury",
            "Tauranga": "Bay of Plenty", "Hamilton": "Waikato", "Dunedin": "Otago",
            "Napier": "Hawke's Bay", "Nelson": "Nelson", "Palmerston North": "Manawatu-Whanganui",
            "Invercargill": "Southland"}


def _h(name):
    return int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)


def build_customer_profile(name, tier):
    """按客户名确定性生成基本信息 + 联系方式（同一客户每次生成结果一致）。"""
    h = _h(name)
    slug = "".join(ch for ch in name.lower() if ch.isalnum())
    first = _FIRST[h % len(_FIRST)]
    last = _LAST[(h // 7) % len(_LAST)]
    city = _CITIES[(h // 13) % len(_CITIES)]
    street = _STREETS[(h // 17) % len(_STREETS)]
    number = 2 + (h % 250)
    return dict(
        name=name, tier=tier, contact_name=f"{first} {last}",
        contact_title=_TITLES[(h // 29) % len(_TITLES)],
        email=f"{first.lower()}.{last.lower()}@{slug}.co.nz",
        phone=f"+64 9 {2000000 + h % 7000000}",
        mobile=f"+64 21 {10000000 + (h // 3) % 90000000}",
        address_line=f"{number} {street}",
        city=city, region=_REGIONS[city],
        preferred_channel="sms" if h % 7 == 0 else "email",
    )


def seed_customers(db):
    """幂等写入客户目录（按名称去重；已存在则跳过）。"""
    created = 0
    for i, (name, tier) in enumerate(sorted(CUSTOMER_MASTER, key=lambda x: x[0])):
        if db.query(Customer).filter(Customer.name == name).first():
            continue
        prof = build_customer_profile(name, tier)
        db.add(Customer(customer_code=f"CUS-{i + 1:03d}", **prof))
        created += 1
    if created:
        db.commit()
    return created


def get_customer(db, name):
    """按名称查客户（无则返回 None）。"""
    if not name:
        return None
    return db.query(Customer).filter(Customer.name == name).first()


def get_customer_contact(db, name):
    """返回可用于通知的客户联系方式字典（无则返回 None）。"""
    c = get_customer(db, name)
    if not c:
        return None
    return {"name": c.name, "contact_name": c.contact_name, "email": c.email,
            "phone": c.phone, "mobile": c.mobile, "channel": c.preferred_channel,
            "city": c.city}


class CustomerContact(Base):
    """客户来电/投诉等主动联系记录（Scenario 4 P0：度量"通知是否先于客户来电"）。"""
    __tablename__ = "customer_contacts"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(String(50), unique=True, nullable=False, index=True)
    mode = Column(String(10), nullable=True)  # sea/air/road（可为空）
    exception_id = Column(String(50), nullable=True, index=True)
    customer_name = Column(String(200), nullable=False, index=True)
    contact_type = Column(String(20), nullable=False, default='inbound_call')  # inbound_call/complaint/inquiry/other
    channel = Column(String(20), nullable=True)  # phone/email/portal
    note = Column(Text, nullable=True)
    proactive = Column(Boolean, default=False)  # True=联系前系统已主动通知该客户
    contacted_at = Column(DateTime, nullable=False)  # 模拟世界时间
    created_at = Column(DateTime, default=datetime.utcnow)


def record_customer_contact(db, body, now):
    """记录一次客户联系，并自动判定是否"系统通知先于客户联系"（主动通知）。"""
    import uuid
    from notification_models import ExceptionNotification

    customer_name = (body.get("customer_name") or "").strip()
    if not customer_name:
        raise ValueError("customer_name is required")

    query = db.query(ExceptionNotification).filter(
        ExceptionNotification.recipient == customer_name,
        ExceptionNotification.sent_at <= now,
    )
    if body.get("exception_id"):
        query = query.filter(ExceptionNotification.exception_id == body["exception_id"])
    proactive = query.first() is not None

    row = CustomerContact(
        contact_id=f"CC-{uuid.uuid4().hex[:10]}",
        mode=body.get("mode"),
        exception_id=body.get("exception_id"),
        customer_name=customer_name,
        contact_type=body.get("contact_type") or "inbound_call",
        channel=body.get("channel"),
        note=body.get("note"),
        proactive=proactive,
        contacted_at=now,
    )
    db.add(row)
    db.commit()
    return row
