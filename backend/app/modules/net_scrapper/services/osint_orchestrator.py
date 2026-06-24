"""
OSINT Repository Orchestrator
Wraps CLI tools: TheHarvester, Sherlock, Maigret, Holehe
"""
import asyncio, subprocess, json, re, logging
from typing import Any

logger = logging.getLogger(__name__)


async def _run_tool(cmd: list[str], timeout: int = 60) -> tuple[str, str, int]:
    """Run a CLI tool and return (stdout, stderr, returncode)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode(), stderr.decode(), proc.returncode
    except asyncio.TimeoutError:
        return "", f"Timeout after {timeout}s", -1
    except FileNotFoundError:
        return "", f"Tool not found: {cmd[0]}", -1
    except Exception as e:
        return "", str(e), -1


async def run_sherlock(username: str) -> dict[str, Any]:
    """Run Sherlock username search across social platforms."""
    stdout, stderr, code = await _run_tool(
        ["sherlock", username, "--print-found", "--timeout", "10"],
        timeout=120
    )
    if code == -1:
        return _demo_sherlock(username, stderr)

    found = []
    for line in stdout.splitlines():
        if "[+]" in line:
            parts = line.split(": ")
            if len(parts) >= 2:
                found.append({"platform": parts[0].replace("[+]","").strip(), "url": parts[1].strip()})

    return {
        "tool":      "sherlock",
        "username":  username,
        "found_on":  found,
        "count":     len(found),
        "raw":       stdout[:2000],
        "status":    "completed",
    }


async def run_maigret(username: str) -> dict[str, Any]:
    """Run Maigret for detailed username OSINT."""
    stdout, stderr, code = await _run_tool(
        ["maigret", username, "--no-recursion", "--timeout", "10"],
        timeout=120
    )
    if code == -1:
        return _demo_maigret(username, stderr)

    found = []
    for line in stdout.splitlines():
        if "Found" in line or "[+]" in line:
            found.append(line.strip())

    return {
        "tool":     "maigret",
        "username": username,
        "results":  found,
        "count":    len(found),
        "status":   "completed",
    }


async def run_holehe(email: str) -> dict[str, Any]:
    """Run Holehe to find accounts linked to an email."""
    stdout, stderr, code = await _run_tool(
        ["holehe", email, "--no-color"],
        timeout=120
    )
    if code == -1:
        return _demo_holehe(email, stderr)

    found = []
    for line in stdout.splitlines():
        if "[+]" in line:
            found.append(line.replace("[+]","").strip())

    return {
        "tool":    "holehe",
        "email":   email,
        "found_on":found,
        "count":   len(found),
        "status":  "completed",
    }


async def run_theharvester(domain: str, sources: str = "google,bing,linkedin") -> dict[str, Any]:
    """Run TheHarvester for domain/email reconnaissance."""
    stdout, stderr, code = await _run_tool(
        ["theHarvester", "-d", domain, "-b", sources, "-l", "100"],
        timeout=120
    )
    if code == -1:
        return _demo_harvester(domain, stderr)

    emails  = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", stdout)
    hosts   = re.findall(r"\b(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}\b", stdout)

    return {
        "tool":    "theharvester",
        "domain":  domain,
        "emails":  list(set(emails))[:20],
        "hosts":   list(set(hosts))[:20],
        "status":  "completed",
    }


# ── Demo responses when tools not installed ───────────────────────────────────
def _demo_sherlock(username: str, error: str) -> dict:
    platforms = ["Instagram","Twitter","GitHub","Reddit","TikTok","Pinterest","Telegram"]
    import hashlib
    h = int(hashlib.md5(username.encode()).hexdigest(), 16)
    found = [{"platform": p, "url": f"https://{p.lower()}.com/{username}"}
             for p in platforms[:h%5+1]]
    return {
        "tool":      "sherlock",
        "username":  username,
        "found_on":  found,
        "count":     len(found),
        "status":    "demo",
        "note":      f"Demo data. Install sherlock: pip install sherlock-project. Error: {error[:100]}",
    }

def _demo_maigret(username: str, error: str) -> dict:
    return {
        "tool":     "maigret",
        "username": username,
        "results":  [f"Found: https://instagram.com/{username}", f"Found: https://github.com/{username}"],
        "count":    2,
        "status":   "demo",
        "note":     f"Demo data. Install maigret: pip install maigret. Error: {error[:100]}",
    }

def _demo_holehe(email: str, error: str) -> dict:
    domain = email.split("@")[1] if "@" in email else ""
    return {
        "tool":     "holehe",
        "email":    email,
        "found_on": ["Instagram","Twitter","Spotify"] if "gmail" in domain else ["LinkedIn"],
        "count":    3,
        "status":   "demo",
        "note":     f"Demo data. Install holehe: pip install holehe. Error: {error[:100]}",
    }

def _demo_harvester(domain: str, error: str) -> dict:
    return {
        "tool":    "theharvester",
        "domain":  domain,
        "emails":  [f"admin@{domain}", f"contact@{domain}", f"info@{domain}"],
        "hosts":   [f"mail.{domain}", f"www.{domain}", f"smtp.{domain}"],
        "status":  "demo",
        "note":    f"Demo data. Install theHarvester: pip install theHarvester. Error: {error[:100]}",
    }
