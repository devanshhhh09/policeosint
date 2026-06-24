"""
Phase 7 — Comprehensive unit tests
Tests all OSINT services, security, and API logic
"""
import pytest
import asyncio


# ── Identity service ──────────────────────────────────────────────────────────
class TestIdentityService:
    def test_disposable_email_detection(self):
        from app.services.osint.identity import DISPOSABLE
        assert "mailinator.com" in DISPOSABLE
        assert "gmail.com" not in DISPOSABLE

    def test_risk_score_disposable(self):
        from app.services.osint.identity import _calc_risk
        score = _calc_risk({"email_analysis": {"is_disposable": True}})
        assert score == 25

    def test_risk_score_breach(self):
        from app.services.osint.identity import _calc_risk
        score = _calc_risk({"hibp": {"breach_count": 3}})
        assert score == 45

    def test_risk_score_max_100(self):
        from app.services.osint.identity import _calc_risk
        score = _calc_risk({
            "hibp": {"breach_count": 10},
            "email_analysis": {"is_disposable": True},
            "username_enumeration": {"found_count": 8},
        })
        assert score <= 100

    @pytest.mark.asyncio
    async def test_email_analysis(self):
        from app.services.osint.identity import _email_analysis
        r = await _email_analysis("test1994@mailinator.com")
        assert r["email_analysis"]["is_disposable"] is True
        assert r["email_analysis"]["possible_birth_year"] == "1994"

    @pytest.mark.asyncio
    async def test_phone_lookup_valid(self):
        from app.services.osint.identity import _phone_lookup
        r = await _phone_lookup("+919876543210")
        assert "phone" in r
        assert r["phone"].get("valid") is True

    @pytest.mark.asyncio
    async def test_phone_lookup_invalid(self):
        from app.services.osint.identity import _phone_lookup
        r = await _phone_lookup("notaphone")
        assert "error" in r["phone"] or r["phone"].get("valid") is False


# ── IP service ─────────────────────────────────────────────────────────────────
class TestIPService:
    def test_private_ip_ranges(self):
        from app.services.osint.ip import _is_private
        assert _is_private("192.168.1.1")   is True
        assert _is_private("10.0.0.1")      is True
        assert _is_private("172.16.0.1")    is True
        assert _is_private("127.0.0.1")     is True
        assert _is_private("169.254.1.1")   is True

    def test_public_ip_not_private(self):
        from app.services.osint.ip import _is_private
        assert _is_private("8.8.8.8")       is False
        assert _is_private("1.1.1.1")       is False
        assert _is_private("45.33.32.156")  is False

    @pytest.mark.asyncio
    async def test_private_ip_early_return(self):
        from app.services.osint.ip import investigate_ip
        r = await investigate_ip("192.168.1.100")
        assert r["risk_score"] == 0
        assert "error" in r["sources"]

    def test_risk_tor_exit(self):
        from app.services.osint.ip import _calc_risk
        score = _calc_risk({"ipinfo": {"is_tor": True, "is_proxy": False, "is_vpn": False}})
        assert score == 30

    def test_risk_malicious_vt(self):
        from app.services.osint.ip import _calc_risk
        score = _calc_risk({"virustotal": {"malicious": 20, "abuse_score": 80}})
        assert score > 0

    def test_risk_max_100(self):
        from app.services.osint.ip import _calc_risk
        score = _calc_risk({
            "ipinfo":     {"is_tor": True, "is_proxy": True, "is_vpn": True},
            "virustotal": {"malicious": 50, "abuse_score": 100},
            "shodan":     {"vuln_count": 20, "port_count": 50},
        })
        assert score <= 100


# ── Domain service ─────────────────────────────────────────────────────────────
class TestDomainService:
    def test_clean_domain_https(self):
        from app.services.osint.domain import _clean
        assert _clean("https://www.google.com/search?q=test") == "www.google.com"

    def test_clean_domain_http(self):
        from app.services.osint.domain import _clean
        assert _clean("http://EXAMPLE.COM") == "example.com"

    def test_clean_domain_trailing_slash(self):
        from app.services.osint.domain import _clean
        assert _clean("  example.com/  ") == "example.com"

    def test_calc_risk_new(self):
        from app.services.osint.domain import _calc_risk
        score = _calc_risk({"whois": {"is_new_domain": True, "privacy_protected": True}})
        assert score >= 40

    def test_calc_risk_malicious(self):
        from app.services.osint.domain import _calc_risk
        score = _calc_risk({"virustotal": {"malicious": 10}})
        assert score >= 40

    def test_calc_risk_max_100(self):
        from app.services.osint.domain import _calc_risk
        score = _calc_risk({
            "whois":      {"is_new_domain": True, "privacy_protected": True},
            "virustotal": {"malicious": 30},
            "ssl":        {"expired": True, "expiring_soon": True},
        })
        assert score <= 100


# ── UPI service ────────────────────────────────────────────────────────────────
class TestUPIService:
    @pytest.mark.asyncio
    async def test_invalid_upi_format(self):
        from app.services.osint.upi import _analyse_upi_id
        r = await _analyse_upi_id("invaliddomain")
        assert r["upi_analysis"]["valid"] is False

    @pytest.mark.asyncio
    async def test_valid_upi_paytm(self):
        from app.services.osint.upi import _analyse_upi_id
        r = await _analyse_upi_id("user123@paytm")
        assert r["upi_analysis"]["valid"] is True
        assert r["upi_analysis"]["bank"] == "Paytm Payments Bank"

    @pytest.mark.asyncio
    async def test_suspicious_keyword_sbi(self):
        from app.services.osint.upi import _analyse_upi_id
        r = await _analyse_upi_id("sbihelpdeskofficial@paytm")
        assert r["upi_analysis"]["is_suspicious"] is True
        assert r["upi_analysis"]["severity"] == "HIGH"

    @pytest.mark.asyncio
    async def test_suspicious_keyword_kyc(self):
        from app.services.osint.upi import _analyse_upi_id
        r = await _analyse_upi_id("kyc.verify@ybl")
        assert r["upi_analysis"]["is_suspicious"] is True

    @pytest.mark.asyncio
    async def test_fraud_pattern_kyc_scam(self):
        from app.services.osint.upi import _fraud_pattern_check
        r = await _fraud_pattern_check("kyc@paytm", {"note": "KYC expire block verify"})
        matches = r["fraud_patterns"]["matches"]
        assert any(p["pattern_id"] == "kyc_scam" for p in matches)

    @pytest.mark.asyncio
    async def test_fraud_pattern_remote_access(self):
        from app.services.osint.upi import _fraud_pattern_check
        r = await _fraud_pattern_check("user@paytm", {"note": "install anydesk remote"})
        matches = r["fraud_patterns"]["matches"]
        assert any(p["pattern_id"] == "remote_access" for p in matches)

    @pytest.mark.asyncio
    async def test_qr_code_parse_valid(self):
        from app.services.osint.upi import _parse_qr
        qr = "upi://pay?pa=suspect@paytm&pn=Test+User&am=5000&cu=INR"
        r  = await _parse_qr(qr)
        assert r["qr_analysis"]["is_upi_qr"] is True
        assert r["qr_analysis"]["vpa"]    == "suspect@paytm"
        assert r["qr_analysis"]["amount"] == "5000"

    @pytest.mark.asyncio
    async def test_qr_code_parse_invalid(self):
        from app.services.osint.upi import _parse_qr
        r = await _parse_qr("not-a-upi-code")
        assert r["qr_analysis"]["is_upi_qr"] is False

    def test_recommend_actions_high_risk(self):
        from app.services.osint.upi import _recommend_actions
        actions = _recommend_actions(90, [])
        assert any("Flag" in a for a in actions)
        assert any("freeze" in a.lower() or "Freeze" in a for a in actions)

    def test_upi_risk_suspicious(self):
        from app.services.osint.upi import _calc_risk
        score = _calc_risk({"upi_analysis": {"is_suspicious": True, "psp_risk": "medium"}})
        assert score >= 25


# ── Crypto service ─────────────────────────────────────────────────────────────
class TestCryptoService:
    def test_detect_bitcoin_legacy(self):
        from app.services.osint.crypto import _detect_chain
        assert _detect_chain("1A2b3C4d5E6f7G8h9I0jKLMNoPQRsTuVwXyZ") == "bitcoin"

    def test_detect_bitcoin_bech32(self):
        from app.services.osint.crypto import _detect_chain
        assert _detect_chain("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh") == "bitcoin"

    def test_detect_ethereum(self):
        from app.services.osint.crypto import _detect_chain
        assert _detect_chain("0x742d35Cc6634C0532925a3b8D4C9b0a5F9a0b3e1") == "ethereum"

    def test_detect_tron(self):
        from app.services.osint.crypto import _detect_chain
        assert _detect_chain("TN7gqVCFWs9VTMNuGkBuGxNqFLpVQfEsHy") == "tron"

    def test_detect_unknown(self):
        from app.services.osint.crypto import _detect_chain
        assert _detect_chain("not_an_address_123") == "unknown"

    @pytest.mark.asyncio
    async def test_mixer_check_returns_score(self):
        from app.services.osint.crypto import _mixer_check
        r = await _mixer_check("1A2b3C4d5E6f7G8h9I0j", "bitcoin")
        assert "mixer_analysis" in r
        assert 0 <= r["mixer_analysis"]["mixer_score"] <= 99
        assert "patterns_detected" in r["mixer_analysis"]

    @pytest.mark.asyncio
    async def test_known_mixer_flagged(self):
        from app.services.osint.crypto import _mixer_check, KNOWN_MIXERS
        if KNOWN_MIXERS.get("ethereum"):
            mixer_addr = KNOWN_MIXERS["ethereum"][0]
            r = await _mixer_check(mixer_addr, "ethereum")
            assert r["mixer_analysis"]["is_known_mixer"] is True


# ── Security ───────────────────────────────────────────────────────────────────
class TestSecurity:
    def test_hash_password(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("Inspector@1234")
        assert hashed != "Inspector@1234"
        assert verify_password("Inspector@1234", hashed) is True

    def test_wrong_password(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_create_decode_token(self):
        from app.core.security import create_access_token, decode_token
        data  = {"sub": "test-user-id", "role": "inspector", "badge": "GGN/001"}
        token = create_access_token(data)
        assert isinstance(token, str)
        decoded = decode_token(token)
        assert decoded["sub"]  == "test-user-id"
        assert decoded["role"] == "inspector"
        assert decoded["type"] == "access"

    def test_token_type_access(self):
        from app.core.security import create_access_token, decode_token
        token   = create_access_token({"sub": "123"})
        decoded = decode_token(token)
        assert decoded["type"] == "access"

    def test_refresh_token_type(self):
        from app.core.security import create_refresh_token, decode_token
        token   = create_refresh_token({"sub": "123"})
        decoded = decode_token(token)
        assert decoded["type"] == "refresh"

    def test_check_permission_inspector(self):
        from app.core.security import check_permission
        assert check_permission("inspector", "case:create")    is True
        assert check_permission("inspector", "case:read")      is True
        assert check_permission("inspector", "investigate:run") is True
        assert check_permission("inspector", "user:manage")    is False
        assert check_permission("inspector", "audit:view")     is False

    def test_check_permission_trainee(self):
        from app.core.security import check_permission
        assert check_permission("trainee", "case:read")     is True
        assert check_permission("trainee", "case:create")   is False
        assert check_permission("trainee", "case:delete")   is False
        assert check_permission("trainee", "report:generate") is False

    def test_check_permission_super_admin(self):
        from app.core.security import check_permission
        for perm in ["case:create","case:delete","user:manage","audit:view","report:generate"]:
            assert check_permission("super_admin", perm) is True


# ── Graph service ──────────────────────────────────────────────────────────────
class TestGraphService:
    def test_build_graph_upi(self):
        from app.services.graph_service import build_entity_graph
        g = build_entity_graph("suspect@paytm", "upi", depth=2)
        assert g["stats"]["total_nodes"] > 0
        assert g["stats"]["total_edges"] > 0
        assert any(n["is_centre"] for n in g["nodes"])

    def test_build_graph_email(self):
        from app.services.graph_service import build_entity_graph
        g = build_entity_graph("test@gmail.com", "email", depth=1)
        assert g["entity_type"] == "email"
        assert len(g["nodes"]) >= 2

    def test_centre_node_exists(self):
        from app.services.graph_service import build_entity_graph
        g = build_entity_graph("8.8.8.8", "ip", depth=1)
        centre = next((n for n in g["nodes"] if n.get("is_centre")), None)
        assert centre is not None
        assert centre["full_label"] == "8.8.8.8"


# ── UPI Cluster ────────────────────────────────────────────────────────────────
class TestUPICluster:
    def test_cluster_has_nodes(self):
        from app.services.osint.upi_cluster import build_upi_cluster
        c = build_upi_cluster("suspect@paytm")
        assert c["cluster_size"] > 0
        assert c["mule_count"] > 0
        assert c["victim_count"] > 0

    def test_cluster_has_recommended_freeze(self):
        from app.services.osint.upi_cluster import build_upi_cluster
        c = build_upi_cluster("kyc@paytm")
        assert isinstance(c["recommended_freeze"], list)
        assert len(c["recommended_freeze"]) > 0

    def test_cluster_scam_type(self):
        from app.services.osint.upi_cluster import build_upi_cluster
        c = build_upi_cluster("loan@paytm")
        scam_types = ["KYC Scam","Investment Scam","Loan Scam","Remote Access Scam"]
        assert c["scam_type"] in scam_types

    def test_cluster_edges_connect_nodes(self):
        from app.services.osint.upi_cluster import build_upi_cluster
        c = build_upi_cluster("test@paytm")
        node_ids = {n["id"] for n in c["nodes"]}
        for e in c["edges"]:
            assert e["from"] in node_ids
            assert e["to"]   in node_ids


# ── PDF Generator ─────────────────────────────────────────────────────────────
class TestPDFGenerator:
    def test_reportlab_available(self):
        try:
            import reportlab
            available = True
        except ImportError:
            available = False
        assert available, "reportlab must be installed: pip install reportlab==4.2.2"

    def test_fir_pdf_generates(self):
        from app.services.reports.pdf_generator import generate_fir_report
        pdf = generate_fir_report(
            case_data={"case_number": "CYB/2025/TEST"},
            fir_data={
                "case_details":   {"case_number":"CYB/2025/TEST","title":"Test case"},
                "victim_details": {"name":"Test Victim","phone":"9999999999"},
                "applicable_sections": [{"section":"419","description":"Cheating"}],
                "legal_provisions":    ["Section 419 IPC"],
                "digital_evidence_checklist": ["Screenshots with SHA256"],
                "recommended_actions": ["Freeze account"],
                "escalation": {"i4c": True},
                "notice_templates": {"bank_freeze": "Please freeze account CYB/2025/TEST"},
            },
            officer="GGN/CYB/2024/001",
        )
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000
        assert pdf[:4] == b"%PDF"  # Valid PDF magic bytes

    def test_intelligence_pdf_generates(self):
        from app.services.reports.pdf_generator import generate_intelligence_report
        pdf = generate_intelligence_report(
            case_data={"case_number": "CYB/2025/TEST"},
            investigations=[
                {"investigation_type":"ip","query":"8.8.8.8","risk_score":5,"summary":"Google DNS","sources_queried":["ipinfo"],"status":"completed"}
            ],
            officer="GGN/CYB/2024/001",
        )
        assert isinstance(pdf, bytes)
        assert pdf[:4] == b"%PDF"

    def test_suspect_pdf_generates(self):
        from app.services.reports.pdf_generator import generate_suspect_profile_pdf
        pdf = generate_suspect_profile_pdf(
            case_data={"case_number": "CYB/2025/TEST"},
            profile_data={
                "known_identifiers": {"upi_ids":["suspect@paytm"],"emails":[]},
                "risk_assessment":   {"overall_risk":85,"risk_label":"CRITICAL","investigation_count":5},
                "modus_operandi":    "KYC scam via UPI collect request",
                "arrest_grounds":    ["Prima facie evidence u/s 420 IPC"],
            },
            officer="GGN/CYB/2024/001",
        )
        assert isinstance(pdf, bytes)
        assert pdf[:4] == b"%PDF"
