"""
Self-learning semantic event classifier for freight exception messages.

自主学习语义事件分类器

Two-stage design (adapted from 778 Project's freight_event_clustering notebook):

1. Cold start: messages are matched against a small set of hand-written section
   templates (few-shot anchors), so the system works before any data is seen.
2. Self-learning: every generated exception feeds its root-cause text + known
   exception type back into the classifier. Once enough examples accumulate,
   the classifier clusters the real message corpus with MiniBatchKMeans
   (unsupervised discovery of fine-grained wording patterns), names each
   cluster by the majority exception type (semi-supervised), and maps it to one
   of the six business sections. New messages are then routed to their nearest
   learned cluster, so unusual / newly-worded root causes are handled by the
   patterns actually seen in the data rather than hand-written templates.

The cluster-distance margin between the nearest and second-nearest cluster is
used as a confidence signal, routing low-confidence events to human review.
The classifier periodically refits as new data arrives, adapting over time.
"""
import os
import threading

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
REVIEW_THRESHOLD_TEMPLATE = 0.06   # cosine-similarity margin (cold start)
REVIEW_THRESHOLD_CLUSTER = 0.08    # relative euclidean-distance margin (learned)
REFIT_EVERY = 100                  # refit the KMeans clusters every N new examples
OOD_SIM_THRESHOLD = 0.45           # cold-start: max cosine similarity below this -> out-of-distribution
OOD_Z_THRESHOLD = 3.0              # learned: distance z-score above this -> out-of-distribution

# Disable learning in tests to keep them fast and deterministic.
LEARNING_ENABLED = os.environ.get("EVENT_CLASSIFIER_LEARNING", "true").lower() not in ("0", "false", "no", "off")

# 8 类权威异常分类（Kratos 文档口径）
SECTIONS = [
    "Delay",
    "Damage",
    "Mis-routing",
    "Customs Hold",
    "Lost/Missing",
    "Failed Delivery",
    "Tracking/Data",
    "Capacity/Transport",
]

# 10 类根因类别（Kratos 文档口径）
ROOT_CAUSE_CATEGORIES = [
    "weather-natural",
    "traffic-infrastructure",
    "equipment-failure",
    "capacity-scheduling",
    "human-error",
    "documentation-compliance",
    "packaging-loading",
    "receiving-site",
    "technology-connectivity",
    "security-theft",
]

# exception_type -> 8 类异常分类（semi-supervised cluster naming + rule mapping）
TYPE_TO_SECTION = {
    "delay": "Delay",
    "vessel_delay": "Delay",
    "ferry_delay": "Delay",
    "accident": "Delay",
    "road_closure": "Delay",
    "temp_excursion": "Damage",
    "damage": "Damage",
    "misroute": "Mis-routing",
    "diversion": "Mis-routing",
    "customs_hold": "Customs Hold",
    "biosecurity_hold": "Customs Hold",
    "dg_incident": "Customs Hold",
    "overweight": "Customs Hold",
    "lost": "Lost/Missing",
    "failed_delivery": "Failed Delivery",
    "tracking_gap": "Tracking/Data",
    "breakdown": "Capacity/Transport",
    "offload": "Capacity/Transport",
    "driver_hours": "Capacity/Transport",
    "service_cancelled": "Capacity/Transport",
    "port_congestion": "Capacity/Transport",
    "predicted_anomaly": "Delay",
}

# exception_type -> 10 类根因（默认值，reason_code 可覆盖）
TYPE_TO_ROOT_CAUSE = {
    "delay": "traffic-infrastructure",
    "vessel_delay": "weather-natural",
    "ferry_delay": "weather-natural",
    "accident": "traffic-infrastructure",
    "road_closure": "traffic-infrastructure",
    "temp_excursion": "equipment-failure",
    "damage": "packaging-loading",
    "misroute": "human-error",
    "diversion": "human-error",
    "customs_hold": "documentation-compliance",
    "biosecurity_hold": "documentation-compliance",
    "dg_incident": "documentation-compliance",
    "overweight": "documentation-compliance",
    "lost": "security-theft",
    "failed_delivery": "receiving-site",
    "tracking_gap": "technology-connectivity",
    "breakdown": "equipment-failure",
    "offload": "capacity-scheduling",
    "driver_hours": "capacity-scheduling",
    "service_cancelled": "capacity-scheduling",
    "port_congestion": "traffic-infrastructure",
    "predicted_anomaly": "traffic-infrastructure",
}

# delay_reason_code -> 10 类根因（细粒度覆盖）
REASON_TO_ROOT_CAUSE = {
    "weather": "weather-natural",
    "congestion": "traffic-infrastructure",
    "port_congestion": "traffic-infrastructure",
    "road_closure": "traffic-infrastructure",
    "accident": "traffic-infrastructure",
    "mechanical": "equipment-failure",
    "breakdown": "equipment-failure",
    "berth_unavailable": "capacity-scheduling",
    "labour": "capacity-scheduling",
    "driver_hours": "capacity-scheduling",
    "ferry": "weather-natural",
}


def map_exception_to_categories(exception_type, reason_code=None):
    """Map an exception type (+ optional reason) to (category, root_cause)."""
    category = TYPE_TO_SECTION.get(exception_type, "Delay")
    root_cause = REASON_TO_ROOT_CAUSE.get(reason_code) or TYPE_TO_ROOT_CAUSE.get(exception_type, "human-error")
    return category, root_cause


# 8 类异常的恢复 playbook（Kratos Task 3 速查表）
RECOVERY_PLAYBOOK = {
    "Delay": ["priority_loading", "rebook_next_service", "switch_route_or_mode", "customer_contingency"],
    "Damage": ["inspection", "repacking", "salvage", "replace_or_reship", "insurance_claim"],
    "Mis-routing": ["corrected_routing", "intercept", "transfer_correct_lane", "relabel_or_rebook"],
    "Customs Hold": ["submit_documents", "duty_payment", "coordinate_inspection", "broker_escalation"],
    "Lost/Missing": ["network_trace", "stop_wrong_delivery", "replacement", "alternate_supply"],
    "Failed Delivery": ["correct_instructions", "new_appointment", "redelivery", "depot_collection"],
    "Tracking/Data": ["correct_master_data", "resend_event", "integration_ticket", "manual_milestone"],
    "Capacity/Transport": ["substitute_equipment", "split_or_prioritise", "rebook_or_reroute", "expedite_critical"],
}

# exception_type -> 预测下游影响（Kratos Task 6 异常链）
DOWNSTREAM_IMPACT = {
    "delay": "missed delivery window -> possible SLA breach",
    "vessel_delay": "missed sailing connection -> delayed discharge -> SLA risk",
    "ferry_delay": "missed road connection -> delayed delivery -> SLA risk",
    "accident": "lane closure -> congestion -> delay -> SLA risk",
    "road_closure": "detour -> missed connection -> delay -> SLA risk",
    "temp_excursion": "spoilage risk -> replacement -> customer dissatisfaction",
    "damage": "inspection/repack -> replacement -> insurance claim",
    "misroute": "extra handling -> delay -> added cost",
    "diversion": "off-schedule routing -> delay -> added cost",
    "customs_hold": "clearance delay -> missed sailing -> SLA breach -> customer escalation",
    "biosecurity_hold": "inspection delay -> missed delivery -> SLA breach",
    "dg_incident": "safety exposure -> quarantine -> escalation",
    "overweight": "rework/reweigh -> delay -> added cost",
    "lost": "replacement/reship -> customer disruption -> claim",
    "failed_delivery": "redelivery -> added cost -> customer complaint",
    "tracking_gap": "uncertain status -> late notification -> avoidable escalation",
    "breakdown": "substitute vehicle -> delay -> added cost",
    "offload": "rebook next service -> delay -> SLA risk",
    "driver_hours": "mandatory rest -> delay -> SLA risk",
    "service_cancelled": "rebooking -> delay -> SLA risk",
    "port_congestion": "berth delay -> discharge delay -> SLA risk",
    "predicted_anomaly": "potential congestion -> delay risk -> proactive monitoring",
}

# exception_type -> 基础恢复成本（NZD，Task 11 直接成本）
RECOVERY_BASE_COST = {
    "delay": 400, "vessel_delay": 700, "ferry_delay": 500, "accident": 700,
    "road_closure": 500, "temp_excursion": 1200, "damage": 1500,
    "misroute": 650, "diversion": 800, "customs_hold": 300, "biosecurity_hold": 300,
    "dg_incident": 500, "overweight": 400, "lost": 2000, "failed_delivery": 150,
    "tracking_gap": 100, "breakdown": 800, "offload": 900, "driver_hours": 400,
    "service_cancelled": 900, "port_congestion": 600, "predicted_anomaly": 300,
}


def estimate_recovery_cost(exception_type, cargo_value):
    """Estimate recovery cost = base cost + small fraction of cargo value."""
    base = RECOVERY_BASE_COST.get(exception_type, 300)
    return round(base + (cargo_value or 0) * 0.01, 2)

# Cold-start representative templates (used until the classifier has learned).
SECTION_TEMPLATES = {
    "Delay": [
        "service delayed by hours after port congestion near Auckland",
        "scheduled departure missed because of severe weather",
        "shipment has not moved for hours at Tauranga",
        "Cook Strait ferry sailing was cancelled; delivery ETA shifted by hours",
        "road closure means the linehaul service will arrive hours late",
        "vessel delayed due to severe weather",
        "vessel delayed due to port congestion",
        "flight delayed due to weather conditions",
        "road trip delayed due to traffic congestion",
        "ferry sailing cancelled due to strong winds",
        "traffic incident causing lane closure on the corridor",
    ],
    "Damage": [
        "packaging was crushed and goods were damaged during handling at Auckland",
        "temperature sensor recorded degrees outside the permitted range",
        "water entered the container and damaged packaged freight",
        "reefer probe exceeded the safe temperature range and product condition is at risk",
        "cartons were crushed during terminal handling and goods may be damaged",
        "temperature excursion outside the permitted range during transit",
        "container damage detected during discharge",
        "refrigeration unit failed and temperature-sensitive goods spoiled",
    ],
    "Mis-routing": [
        "shipment scanned at the wrong depot in Hamilton",
        "GPS shows a route deviation toward Christchurch",
        "container was loaded onto a service bound for Wellington instead of Dunedin",
        "planned transfer at Picton was skipped and freight followed the wrong route",
        "consignment is moving away from its planned destination near Napier",
        "pallet intended for Auckland was scanned at the Hamilton depot",
        "consignment was sorted onto the wrong outbound linehaul instead of Dunedin",
        "cargo offloaded at the incorrect destination",
    ],
    "Customs Hold": [
        "customs placed the shipment on hold pending document review",
        "commercial invoice is missing and clearance cannot proceed",
        "declared HS code does not match the invoice description",
        "MPI inspection is required before the cargo can be released",
        "dangerous goods declaration is incomplete or inconsistent",
        "tariff code conflicts with the goods declaration and customs release is blocked",
        "customs placed the shipment on hold for inspection",
        "MPI biosecurity inspection hold at arrival",
    ],
    "Lost/Missing": [
        "a pallet is absent at transfer and cannot be located in the tracking network",
        "the shipment or a handling unit cannot be located and expected scans are absent",
        "one pallet has no arrival scan and the terminal cannot locate it",
        "items are missing after suspected unauthorised access",
        "the container cannot be found at the destination terminal",
        "part of the consignment is missing at handover",
    ],
    "Failed Delivery": [
        "delivery attempt failed because the receiving site was closed",
        "receiver was unavailable during the booked delivery window",
        "delivery address is incorrect and the driver cannot complete handover",
        "site access restrictions prevented unloading at Auckland",
        "consignee refused the freight due to an order discrepancy",
        "driver could not unload because the receiving warehouse was closed",
        "recipient was not available for the final delivery appointment",
        "street address is invalid and delivery handover cannot be completed",
    ],
    "Tracking/Data": [
        "no valid tracking event has been received for hours",
        "carrier API timed out and the latest shipment status is unavailable",
        "duplicate scan events created conflicting shipment statuses",
        "GPS location has not updated since the shipment left Auckland",
        "proof of delivery was not uploaded because of a network failure",
        "no carrier scan or tracking event has arrived for hours",
        "integration API endpoint is failing and the shipment status is stale",
        "duplicate proof of delivery records show conflicting tracking states",
    ],
    "Capacity/Transport": [
        "the planned vehicle or equipment became unavailable",
        "a truck is unavailable and the collection cannot proceed",
        "a rail service was cancelled and no alternative slot is available",
        "a vessel sailing was omitted and the booked container has no slot",
        "vehicle broke down en route and recovery was dispatched",
        "driver exceeded legal work-time limits and must rest",
        "planned transport capacity is unavailable due to overbooking",
    ],
}


class EventClassifier:
    """Lazy-loading, self-learning classifier for freight exception messages."""

    def __init__(self, refit_every=REFIT_EVERY):
        self.refit_every = refit_every
        self._model = None
        self._anchors = None
        self._anchor_sections = None
        self._cluster_centers = None  # learned type prototypes (n, 384)
        self._cluster_sections = None  # learned prototype -> section mapping
        self._cluster_mean_dists = None  # per-type mean distance to prototype
        self._cluster_stds = None  # per-type std of distance to prototype
        self._corpus_messages = []
        self._corpus_types = []
        self._lock = threading.Lock()
        self._cache = {}
        self._n_learned = 0
        self._last_refit_size = 0

    @property
    def loaded(self):
        return self._model is not None

    @property
    def learned(self):
        return self._cluster_centers is not None

    @property
    def corpus_size(self):
        return len(self._corpus_messages)

    def _ensure_loaded(self):
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(MODEL_NAME)
            anchors = []
            sections = []
            for section in SECTIONS:
                embs = model.encode(SECTION_TEMPLATES[section], normalize_embeddings=True)
                for emb in embs:
                    anchors.append(emb)
                    sections.append(section)
            self._anchors = np.stack(anchors)
            self._anchor_sections = sections
            self._model = model

    # ----------------------------------------------------------
    # 自主学习：语料积累 + 聚类
    # ----------------------------------------------------------
    def learn(self, messages, exception_types):
        """Feed new (message, exception_type) examples into the classifier."""
        if not LEARNING_ENABLED or not messages:
            return
        self._ensure_loaded()
        with self._lock:
            self._corpus_messages.extend(messages)
            self._corpus_types.extend(exception_types)
            if len(self._corpus_messages) - self._last_refit_size >= self.refit_every:
                self._refit_locked()

    def _refit_locked(self):
        """Learn one semantic prototype per exception type from the corpus.

        Each exception type gets a prototype = the mean embedding of its
        messages, mapped to a business section. The per-type distance
        distribution (mean + std) is also stored so new messages can be scored
        with a Mahalanobis-style z-score for out-of-distribution detection.
        """
        from collections import defaultdict

        # Deduplicate on (message, type): the same root-cause text repeats once
        # per container on a delayed vessel, and the SAME text can legitimately
        # belong to different exception types (e.g. 'MPI biosecurity inspection
        # hold' is both air customs_hold and sea biosecurity_hold). Keying on
        # text alone would collapse one type into the other.
        unique = set()
        for msg, t in zip(self._corpus_messages, self._corpus_types):
            unique.add((msg, t))

        by_type = defaultdict(list)
        for msg, t in unique:
            by_type[t].append(msg)

        centers, sections, mean_dists, stds = [], [], [], []
        for t, mlist in by_type.items():
            embs = self._model.encode(mlist, normalize_embeddings=True)
            center = embs.mean(axis=0)
            center = center / (np.linalg.norm(center) + 1e-9)
            dists = 1.0 - (embs @ center)  # cosine distance to prototype
            centers.append(center)
            sections.append(TYPE_TO_SECTION.get(t, SECTIONS[0]))
            mean_dists.append(float(dists.mean()))
            stds.append(float(dists.std()) if len(dists) > 1 else 0.2)

        self._cluster_centers = np.stack(centers)
        self._cluster_sections = sections
        self._cluster_mean_dists = np.array(mean_dists)
        self._cluster_stds = np.array(stds)
        self._n_learned = len(self._corpus_messages)
        self._last_refit_size = len(self._corpus_messages)
        self._cache.clear()
        print(f"[classifier] learned {len(self._corpus_messages)} examples into {len(sections)} type prototypes")

    # ----------------------------------------------------------
    # 分类
    # ----------------------------------------------------------
    def classify(self, message):
        """Classify a single message, returning section + confidence + decision + OOD."""
        if not message:
            return {
                "business_section": None,
                "classification_confidence": 0.0,
                "classification_decision": "human_review",
                "ood_score": 1.0,
                "is_ood": True,
            }
        cached = self._cache.get(message)
        if cached is not None:
            return cached

        self._ensure_loaded()
        with self._lock:
            emb = self._model.encode([message], normalize_embeddings=True)[0]
            if self._cluster_centers is not None:
                result = self._classify_by_clusters(emb)
            else:
                result = self._classify_by_templates(emb)
        self._cache[message] = result
        return result

    def classify_and_learn(self, message, exception_type):
        """Classify a message and feed it back for learning."""
        result = self.classify(message)
        self.learn([message], [exception_type])
        return result

    @staticmethod
    def _finalize(business_section, margin, ood_score, is_ood):
        """Build the final result dict, routing out-of-distribution messages."""
        if is_ood:
            decision = "ood"
        elif margin >= REVIEW_THRESHOLD_TEMPLATE:
            decision = "automatic"
        else:
            decision = "human_review"
        return {
            "business_section": business_section,
            "classification_confidence": round(margin, 4),
            "classification_decision": decision,
            "ood_score": round(ood_score, 4),
            "is_ood": is_ood,
        }

    def _classify_by_templates(self, emb):
        sims = self._anchors @ emb
        nearest = int(np.argmax(sims))
        best_section = self._anchor_sections[nearest]
        other_max = max(
            float(sims[i])
            for i in range(len(self._anchor_sections))
            if self._anchor_sections[i] != best_section
        )
        margin = float(sims[nearest] - other_max)
        max_sim = float(sims[nearest])
        return self._finalize(best_section, margin, 1.0 - max_sim, max_sim < OOD_SIM_THRESHOLD)

    def _classify_by_clusters(self, emb):
        sims = self._cluster_centers @ emb  # cosine similarity to each type prototype
        order = np.argsort(-sims)
        nearest = int(order[0])
        second = int(order[1]) if len(sims) > 1 else nearest
        margin = float(sims[nearest] - sims[second])
        dist_nearest = 1.0 - float(sims[nearest])
        mean_d = float(self._cluster_mean_dists[nearest])
        std_d = max(float(self._cluster_stds[nearest]), 0.1)
        z = (dist_nearest - mean_d) / std_d
        if z > OOD_Z_THRESHOLD:
            # Template fallback: if it still matches a known section template,
            # it is a known pattern (not OOD) — fall back to template routing.
            anchor_sims = self._anchors @ emb
            anchor_nearest = int(np.argmax(anchor_sims))
            anchor_sim = float(anchor_sims[anchor_nearest])
            if anchor_sim > OOD_SIM_THRESHOLD:
                best_section = self._anchor_sections[anchor_nearest]
                other_max = max(
                    float(anchor_sims[i])
                    for i in range(len(self._anchor_sections))
                    if self._anchor_sections[i] != best_section
                )
                anchor_margin = float(anchor_sim - other_max)
                return self._finalize(best_section, anchor_margin, 1.0 - anchor_sim, False)
        return self._finalize(self._cluster_sections[nearest], margin, z, z > OOD_Z_THRESHOLD)


# 全局单例
classifier = EventClassifier()
