"""
UPI Fraud Cluster Analysis — Phase 4
Maps mule account networks, transaction flows, scam categories
"""
import hashlib
from typing import Any


def build_upi_cluster(upi_id: str) -> dict[str, Any]:
    """
    Build a mule account cluster graph for a UPI ID.
    Production: connect to NPCI fraud API and bank transaction data.
    Demo: deterministic heuristic based on UPI ID hash.
    """
    h     = int(hashlib.md5(upi_id.encode()).hexdigest(), 16)
    nodes = []
    edges = []

    # Centre node
    local, handle = (upi_id.split("@") + ["upi"])[:2]
    nodes.append({
        "id":    "centre",
        "label": upi_id,
        "type":  "upi",
        "risk":  0.94,
        "flags": ["primary_suspect"],
    })

    # Mule accounts (layer 1)
    mule_count = (h % 5) + 2
    banks = ["paytm","ybl","okaxis","okhdfcbank","oksbi","apl","upi"]
    for i in range(mule_count):
        hh    = int(hashlib.md5(f"{upi_id}_mule_{i}".encode()).hexdigest(), 16)
        mnode = f"mule_{i}"
        phone = f"9{7+(hh%3)}{hh%10000000:07d}"
        nodes.append({
            "id":    mnode,
            "label": f"{phone}@{banks[hh % len(banks)]}",
            "type":  "mule",
            "risk":  round(0.6 + (hh % 30) / 100, 2),
            "flags": ["mule_account"],
        })
        edges.append({
            "from":   "centre",
            "to":     mnode,
            "label":  f"₹{(hh%50+5)}K transferred",
            "weight": round((hh % 50 + 5) * 1000),
        })

    # Aggregator (layer 2)
    agg_id   = f"agg_{h%3}"
    agg_bank = banks[(h+2) % len(banks)]
    nodes.append({
        "id":    agg_id,
        "label": f"aggregator@{agg_bank}",
        "type":  "aggregator",
        "risk":  0.82,
        "flags": ["high_volume","aggregator"],
    })
    for i in range(min(mule_count, 3)):
        edges.append({
            "from":   f"mule_{i}",
            "to":     agg_id,
            "label":  "funds consolidated",
            "weight": 0,
        })

    # Final destination
    destinations = ["crypto_exchange", "foreign_account", "cash_withdrawal"]
    dest_type    = destinations[h % 3]
    nodes.append({
        "id":    "destination",
        "label": dest_type.replace("_"," ").title(),
        "type":  "destination",
        "risk":  0.95,
        "flags": ["money_laundering_risk"],
    })
    edges.append({
        "from":   agg_id,
        "to":     "destination",
        "label":  "final transfer",
        "weight": 0,
    })

    # Victim nodes
    victim_count = (h % 4) + 1
    for i in range(victim_count):
        hh = int(hashlib.md5(f"{upi_id}_victim_{i}".encode()).hexdigest(), 16)
        nodes.append({
            "id":    f"victim_{i}",
            "label": f"Victim {i+1} (+91-{9000000000 + hh%999999999})",
            "type":  "victim",
            "risk":  0.0,
            "flags": ["victim"],
        })
        edges.append({
            "from":   f"victim_{i}",
            "to":     "centre",
            "label":  f"₹{(hh%200+10)}K lost",
            "weight": (hh % 200 + 10) * 1000,
        })

    total_lost = sum(e["weight"] for e in edges if e["weight"] > 0 and
                     any(n["id"] == e["from"] and n["type"] == "victim" for n in nodes))

    return {
        "upi_id":       upi_id,
        "cluster_size": len(nodes),
        "nodes":        nodes,
        "edges":        edges,
        "mule_count":   mule_count,
        "victim_count": victim_count,
        "total_lost":   total_lost,
        "scam_type":    ["KYC Scam","Investment Scam","Loan Scam","Remote Access Scam"][h % 4],
        "recommended_freeze": [n["label"] for n in nodes if "mule" in n.get("type","")],
    }
