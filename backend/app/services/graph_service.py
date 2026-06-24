"""
Entity Relationship Graph Service — Phase 4
Neo4j-powered in Phase 5. Deterministic demo graph for Phase 4.
"""
import hashlib
from typing import Any


NODE_TYPES = {
    "person":  {"color": "#3B82F6", "icon": "user"},
    "email":   {"color": "#10B981", "icon": "mail"},
    "phone":   {"color": "#F59E0B", "icon": "phone"},
    "upi":     {"color": "#EF4444", "icon": "qrcode"},
    "wallet":  {"color": "#F97316", "icon": "currency-bitcoin"},
    "social":  {"color": "#EC4899", "icon": "brand-instagram"},
    "domain":  {"color": "#14B8A6", "icon": "world"},
    "ip":      {"color": "#8B5CF6", "icon": "server"},
    "company": {"color": "#6366F1", "icon": "building"},
    "device":  {"color": "#84CC16", "icon": "device-laptop"},
}


def build_entity_graph(entity_id: str, entity_type: str, depth: int = 2) -> dict[str, Any]:
    """Build entity relationship graph. Full Neo4j in Phase 5."""
    h     = int(hashlib.md5(entity_id.encode()).hexdigest(), 16)
    nodes = []
    edges = []

    # Centre node
    nodes.append({
        "id":         "centre",
        "type":       entity_type,
        "label":      entity_id[:25] + ("…" if len(entity_id) > 25 else ""),
        "full_label": entity_id,
        "risk_score": round(0.4 + (h % 50) / 100, 2),
        "is_centre":  True,
        **NODE_TYPES.get(entity_type, NODE_TYPES["person"]),
    })

    # Layer 1 connections
    layer1 = _get_layer1(entity_id, entity_type, h)
    for node in layer1:
        nodes.append(node)
        edges.append({
            "source":       "centre",
            "target":       node["id"],
            "relationship": node.get("relationship", "LINKED_TO"),
            "strength":     round(0.5 + (h % 40) / 100, 2),
        })

    # Layer 2 connections (if depth >= 2)
    if depth >= 2:
        for l1_node in layer1[:3]:
            layer2 = _get_layer2(l1_node["id"], l1_node["type"], h)
            for node in layer2:
                if not any(n["id"] == node["id"] for n in nodes):
                    nodes.append(node)
                edges.append({
                    "source":       l1_node["id"],
                    "target":       node["id"],
                    "relationship": node.get("relationship", "ASSOCIATED"),
                    "strength":     round(0.3 + (h % 30) / 100, 2),
                })

    # Stats
    high_risk = [n for n in nodes if n.get("risk_score", 0) > 0.7]
    return {
        "entity_id":   entity_id,
        "entity_type": entity_type,
        "depth":       depth,
        "nodes":       nodes,
        "edges":       edges,
        "stats": {
            "total_nodes":   len(nodes),
            "total_edges":   len(edges),
            "high_risk":     len(high_risk),
            "node_types":    list(set(n["type"] for n in nodes)),
        },
    }


def _get_layer1(entity_id: str, entity_type: str, h: int) -> list:
    layers: dict[str, list] = {
        "person": [
            {"id": "email_1",  "type": "email",  "label": f"user{h%9000+1000}@gmail.com",   "relationship": "USES_EMAIL",    "risk_score": round(0.3+(h%30)/100,2)},
            {"id": "phone_1",  "type": "phone",  "label": f"+91-9{h%900000000+100000000}",  "relationship": "USES_PHONE",    "risk_score": round(0.2+(h%20)/100,2)},
            {"id": "upi_1",    "type": "upi",    "label": f"user{h%999}@paytm",             "relationship": "OWNS_UPI",      "risk_score": round(0.7+(h%25)/100,2)},
            {"id": "social_1", "type": "social", "label": f"@user{h%9999}",                 "relationship": "HAS_PROFILE",   "risk_score": round(0.3+(h%20)/100,2)},
            {"id": "device_1", "type": "device", "label": f"Android {h%10+8}.0",            "relationship": "USES_DEVICE",   "risk_score": round(0.2+(h%15)/100,2)},
        ],
        "email": [
            {"id": "person_1", "type": "person", "label": f"R**ul Sh***a",                  "relationship": "OWNED_BY",      "risk_score": round(0.6+(h%30)/100,2)},
            {"id": "domain_1", "type": "domain", "label": entity_id.split("@")[-1] if "@" in entity_id else "gmail.com", "relationship": "MAIL_DOMAIN", "risk_score": 0.1},
            {"id": "upi_1",    "type": "upi",    "label": f"{entity_id.split('@')[0]}@paytm" if "@" in entity_id else "suspect@paytm", "relationship": "LINKED_UPI", "risk_score": round(0.5+(h%40)/100,2)},
        ],
        "upi": [
            {"id": "person_1", "type": "person", "label": f"R**ul Sh***a",                  "relationship": "OWNED_BY",      "risk_score": round(0.8+(h%15)/100,2)},
            {"id": "phone_1",  "type": "phone",  "label": f"+91-9{h%900000000+100000000}",  "relationship": "LINKED_PHONE",  "risk_score": round(0.4+(h%20)/100,2)},
            {"id": "wallet_1", "type": "wallet", "label": f"1A2b{h%9999:04d}…BTC",          "relationship": "FUNDS_CRYPTO",  "risk_score": round(0.7+(h%25)/100,2)},
            {"id": "company_1","type": "company","label": f"QuickLoan Pvt Ltd",              "relationship": "MERCHANT",      "risk_score": round(0.6+(h%30)/100,2)},
        ],
        "ip": [
            {"id": "domain_1", "type": "domain", "label": f"site{h%999}.com",               "relationship": "HOSTS_DOMAIN",  "risk_score": round(0.5+(h%30)/100,2)},
            {"id": "person_1", "type": "person", "label": f"Unknown operator",               "relationship": "OPERATED_BY",   "risk_score": round(0.4+(h%40)/100,2)},
        ],
        "domain": [
            {"id": "ip_1",     "type": "ip",     "label": f"{h%220+10}.{h%250}.{h%250}.{h%250}", "relationship": "RESOLVES_TO", "risk_score": round(0.4+(h%30)/100,2)},
            {"id": "company_1","type": "company","label": f"Registrant Corp",                "relationship": "REGISTERED_BY", "risk_score": round(0.3+(h%20)/100,2)},
        ],
    }
    return layers.get(entity_type, layers["person"])


def _get_layer2(parent_id: str, parent_type: str, h: int) -> list:
    hh = int(hashlib.md5(parent_id.encode()).hexdigest(), 16)
    defaults = {
        "email":   [{"id": f"breach_{hh%999}","type":"domain","label":f"BreachedSite{hh%99}.com","relationship":"FOUND_IN","risk_score":0.7}],
        "phone":   [{"id": f"carrier_{hh%9}","type":"company","label":f"Jio/Airtel/BSNL","relationship":"CARRIER","risk_score":0.1}],
        "upi":     [{"id": f"victim_{hh%99}","type":"person","label":f"Victim {hh%9+1}","relationship":"DEFRAUDED","risk_score":0.0}],
        "wallet":  [{"id": f"exchange_{hh%5}","type":"company","label":"WazirX Exchange","relationship":"DEPOSITED_TO","risk_score":0.5}],
        "social":  [{"id": f"network_{hh%3}","type":"person","label":f"Follower/Contact","relationship":"CONNECTED","risk_score":0.2}],
        "company": [{"id": f"director_{hh%9}","type":"person","label":f"Director/Owner","relationship":"MANAGED_BY","risk_score":0.6}],
        "device":  [{"id": f"location_{hh%5}","type":"ip","label":f"{hh%220+10}.{hh%250}.{hh%250}.1","relationship":"CONNECTED_FROM","risk_score":0.4}],
        "domain":  [{"id": f"subdomain_{hh%9}","type":"domain","label":f"sub.domain{hh%99}.com","relationship":"SUBDOMAIN","risk_score":0.5}],
        "ip":      [{"id": f"asn_{hh%99}","type":"company","label":f"AS{hh%65000} ISP","relationship":"HOSTED_BY","risk_score":0.2}],
        "person":  [{"id": f"assoc_{hh%9}","type":"person","label":f"Associate {hh%9+1}","relationship":"ASSOCIATED_WITH","risk_score":round(0.3+(hh%40)/100,2)}],
    }
    return defaults.get(parent_type, [])
