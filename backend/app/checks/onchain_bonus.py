"""Onchain Bonus checks (up to +25 points).

Sub-factors:
- Transaction Success Rate (10 pts) — RPC endpoint health for blockchain services
- Real Volume / Chain Coverage (10 pts) — number of supported chains + WebSocket
- Staking / Commitment (5 pts) — SLA, uptime, enterprise signals

Non-blockchain services receive applicable=False and score 0.
"""

import asyncio
import time
from typing import Any
from urllib.parse import urlparse

import aiohttp

# ---------------------------------------------------------------------------
# Blockchain service detection
# ---------------------------------------------------------------------------

_BLOCKCHAIN_DOMAIN_KEYWORDS = frozenset({
    "alchemy", "infura", "helius", "moralis", "quicknode", "getblock",
    "ankr", "chainstack", "nodereal", "nownodes", "blast",
    "solana", "ethereum", "polygon", "avalanche", "arbitrum",
    "optimism", "fantom", "near", "aptos", "sui",
    "blockchain", "web3", "rpc", "chain", "node",
    "etherscan", "solscan", "blockfrost", "tatum", "thirdweb",
    "drpc", "llamarpc", "pokt", "grove", "figment",
})

_CHAIN_NAMES: list[str] = [
    "ethereum", "polygon", "arbitrum", "optimism", "base",
    "solana", "avalanche", "bsc", "binance", "fantom",
    "gnosis", "celo", "moonbeam", "harmony", "cronos",
    "near", "aptos", "sui", "cosmos", "polkadot",
    "zksync", "scroll", "linea", "mantle", "blast",
    "starknet", "sei", "injective", "flow", "tron",
]

_COMMITMENT_KEYWORDS: list[str] = [
    "staking", "stake", "commitment", "sla",
    "uptime guarantee", "uptime", "99.9", "99.99",
    "enterprise", "dedicated node", "dedicated endpoint",
    "premium", "professional", "business plan",
    "free tier", "free plan", "pricing",
    "signup", "sign up", "get started", "create account",
    "api key", "dashboard",
]

_TIMEOUT = aiohttp.ClientTimeout(total=5)


def _is_blockchain_service(base_url: str) -> bool:
    """Determine if the target URL belongs to a blockchain API service."""
    parsed = urlparse(base_url)
    domain = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    full = f"{domain}{path}"
    return any(kw in full for kw in _BLOCKCHAIN_DOMAIN_KEYWORDS)


# ---------------------------------------------------------------------------
# Sub-factor 1: Transaction Success Rate (10 pts)
# ---------------------------------------------------------------------------

async def _check_transaction_success_rate(
    session: aiohttp.ClientSession, base_url: str,
) -> tuple[int, dict[str, Any]]:
    """Probe RPC endpoints with JSON-RPC calls to measure responsiveness."""
    parsed = urlparse(base_url)
    domain = parsed.hostname or ""
    bare = domain.replace("www.", "")

    # Candidate RPC endpoints
    rpc_candidates = [
        f"https://{bare}",
        f"https://api.{bare}",
        f"https://{bare}/rpc",
        f"https://{bare}/v1",
        f"https://{bare}/v2",
        f"https://{bare}/api/v1",
        base_url,
        f"{base_url}/rpc",
        f"{base_url}/v1",
    ]
    # Deduplicate while preserving order
    seen: set[str] = set()
    endpoints: list[str] = []
    for ep in rpc_candidates:
        normalized = ep.rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            endpoints.append(normalized)

    # JSON-RPC payloads to try
    eth_payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    sol_payload = {"jsonrpc": "2.0", "method": "getSlot", "params": [], "id": 1}

    # Detect which chain family based on domain
    domain_lower = f"{bare} {base_url}".lower()
    is_solana = any(kw in domain_lower for kw in ("solana", "helius", "sol"))
    payloads = [sol_payload, eth_payload] if is_solana else [eth_payload, sol_payload]

    best_score = 0
    best_evidence: dict[str, Any] = {"reason": "No RPC endpoint responded"}

    for endpoint in endpoints:
        for payload in payloads:
            try:
                start = time.monotonic()
                async with session.post(
                    endpoint,
                    json=payload,
                    timeout=_TIMEOUT,
                    ssl=False,
                    headers={"Content-Type": "application/json"},
                ) as resp:
                    elapsed_ms = round((time.monotonic() - start) * 1000)
                    body_text = await resp.text()

                    if resp.status == 200:
                        # Try to parse JSON-RPC response
                        try:
                            import json
                            body = json.loads(body_text)
                            has_result = "result" in body
                            has_error = "error" in body
                            is_jsonrpc = body.get("jsonrpc") == "2.0"
                        except Exception:
                            has_result = False
                            has_error = False
                            is_jsonrpc = False

                        if is_jsonrpc and has_result:
                            # Full success
                            score = 10
                            evidence = {
                                "reason": "RPC endpoint returned valid JSON-RPC response",
                                "endpoint": endpoint,
                                "method": payload["method"],
                                "response_time_ms": elapsed_ms,
                                "block_or_slot": str(body.get("result", ""))[:32],
                            }
                            return (score, evidence)
                        elif is_jsonrpc and has_error:
                            # JSON-RPC error (auth required, method not found, etc.)
                            err_msg = ""
                            if isinstance(body.get("error"), dict):
                                err_msg = body["error"].get("message", "")[:80]
                            elif isinstance(body.get("error"), str):
                                err_msg = body["error"][:80]
                            score = 6
                            evidence = {
                                "reason": "RPC endpoint active but returned JSON-RPC error",
                                "endpoint": endpoint,
                                "method": payload["method"],
                                "response_time_ms": elapsed_ms,
                                "error": err_msg,
                            }
                            if score > best_score:
                                best_score = score
                                best_evidence = evidence
                        else:
                            # 200 but not JSON-RPC
                            score = 4
                            evidence = {
                                "reason": "Endpoint responded 200 but not valid JSON-RPC",
                                "endpoint": endpoint,
                                "response_time_ms": elapsed_ms,
                            }
                            if score > best_score:
                                best_score = score
                                best_evidence = evidence
                    elif resp.status in (401, 403):
                        # Auth required — endpoint exists
                        score = 7
                        evidence = {
                            "reason": "RPC endpoint exists, requires authentication",
                            "endpoint": endpoint,
                            "status": resp.status,
                            "response_time_ms": elapsed_ms,
                        }
                        if score > best_score:
                            best_score = score
                            best_evidence = evidence
                    elif resp.status == 405:
                        # Method not allowed (POST not accepted? try next)
                        score = 3
                        evidence = {
                            "reason": "Endpoint responded 405 (method not allowed)",
                            "endpoint": endpoint,
                            "response_time_ms": elapsed_ms,
                        }
                        if score > best_score:
                            best_score = score
                            best_evidence = evidence

            except (aiohttp.ClientError, asyncio.TimeoutError):
                # Timeout / connection error — try next
                continue

        # If we already found a perfect score, no need to continue
        if best_score >= 10:
            break

    return (best_score, best_evidence)


# ---------------------------------------------------------------------------
# Sub-factor 2: Real Volume / Chain Coverage (10 pts)
# ---------------------------------------------------------------------------

async def _check_chain_coverage(
    session: aiohttp.ClientSession, base_url: str,
) -> tuple[int, dict[str, Any]]:
    """Detect number of supported blockchain networks and WebSocket support."""
    parsed = urlparse(base_url)
    domain = (parsed.hostname or "").replace("www.", "")

    # Pages to scan for chain mentions
    scan_urls = [
        base_url,
        f"{base_url}/docs",
        f"{base_url}/chains",
        f"{base_url}/networks",
        f"{base_url}/supported-chains",
        f"{base_url}/docs/supported-networks",
        f"{base_url}/pricing",
    ]

    detected_chains: set[str] = set()
    has_websocket = False
    scanned_pages = 0

    for url in scan_urls:
        try:
            async with session.get(
                url, timeout=_TIMEOUT, allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status >= 400:
                    continue
                text = (await resp.text()).lower()
                scanned_pages += 1

                # Scan for chain names
                for chain in _CHAIN_NAMES:
                    if chain in text:
                        detected_chains.add(chain)

                # WebSocket check
                if "wss://" in text or "websocket" in text:
                    has_websocket = True

        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Also check for chain-specific endpoint patterns
    chain_endpoint_patterns = [
        (f"https://{domain}/eth", "ethereum"),
        (f"https://{domain}/sol", "solana"),
        (f"https://{domain}/polygon", "polygon"),
        (f"https://{domain}/arb", "arbitrum"),
        (f"https://{domain}/opt", "optimism"),
        (f"https://{domain}/base", "base"),
    ]

    async def _probe_chain_endpoint(url: str, chain: str) -> str | None:
        try:
            async with session.head(
                url, timeout=_TIMEOUT, allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status < 500:
                    return chain
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass
        return None

    ep_results = await asyncio.gather(
        *[_probe_chain_endpoint(u, c) for u, c in chain_endpoint_patterns]
    )
    for chain_name in ep_results:
        if chain_name:
            detected_chains.add(chain_name)

    # Check WebSocket endpoint directly
    if not has_websocket:
        wss_candidates = [
            f"wss://{domain}",
            f"wss://ws.{domain}",
        ]
        for wss_url in wss_candidates:
            try:
                async with session.get(
                    wss_url.replace("wss://", "https://"),
                    timeout=_TIMEOUT, ssl=False,
                ) as resp:
                    upgrade = resp.headers.get("Upgrade", "").lower()
                    if "websocket" in upgrade or resp.status == 426:
                        has_websocket = True
                        break
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue

    # Scoring
    n_chains = len(detected_chains)
    if n_chains >= 5:
        base_score = 10
    elif n_chains >= 3:
        base_score = 7
    elif n_chains >= 2:
        base_score = 5
    elif n_chains >= 1:
        base_score = 3
    else:
        base_score = 0

    # WebSocket bonus (cap at 10)
    ws_bonus = 2 if has_websocket else 0
    score = min(10, base_score + ws_bonus)

    evidence: dict[str, Any] = {
        "chains_detected": sorted(detected_chains),
        "chain_count": n_chains,
        "websocket_support": has_websocket,
        "pages_scanned": scanned_pages,
    }

    if n_chains == 0:
        evidence["reason"] = "No blockchain networks detected in documentation"
    else:
        evidence["reason"] = f"Detected {n_chains} chain(s); WebSocket={'yes' if has_websocket else 'no'}"

    return (score, evidence)


# ---------------------------------------------------------------------------
# Sub-factor 3: Staking / Commitment Signals (5 pts)
# ---------------------------------------------------------------------------

async def _check_commitment_signals(
    session: aiohttp.ClientSession, base_url: str,
) -> tuple[int, dict[str, Any]]:
    """Scan for enterprise commitment signals: SLA, pricing tiers, signup."""
    scan_urls = [
        base_url,
        f"{base_url}/pricing",
        f"{base_url}/enterprise",
        f"{base_url}/docs",
        f"{base_url}/signup",
        f"{base_url}/register",
        f"{base_url}/sla",
    ]

    signals_found: list[str] = []
    scanned_pages = 0

    for url in scan_urls:
        try:
            async with session.get(
                url, timeout=_TIMEOUT, allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status >= 400:
                    # Signup/register page returning 200 is itself a signal
                    continue
                text = (await resp.text()).lower()
                scanned_pages += 1

                for keyword in _COMMITMENT_KEYWORDS:
                    if keyword in text and keyword not in signals_found:
                        signals_found.append(keyword)

        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue

    # Scoring
    n_signals = len(signals_found)
    if n_signals >= 3:
        score = 5
    elif n_signals == 2:
        score = 3
    elif n_signals == 1:
        score = 2
    else:
        score = 0

    evidence: dict[str, Any] = {
        "signals_found": signals_found[:10],  # cap display
        "signal_count": n_signals,
        "pages_scanned": scanned_pages,
    }

    if n_signals == 0:
        evidence["reason"] = "No commitment/SLA signals detected"
    else:
        evidence["reason"] = f"Found {n_signals} commitment signal(s)"

    return (score, evidence)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_onchain_bonus(base_url: str) -> dict:
    """Evaluate onchain bonus for blockchain API services.

    Non-blockchain services receive applicable=False with score 0.
    Blockchain services are scored on RPC health, chain coverage, and commitment.
    """
    if not _is_blockchain_service(base_url):
        return {
            "score": 0,
            "max": 25,
            "applicable": False,
            "sub_factors": {
                "transaction_success_rate": {
                    "score": 0,
                    "max": 10,
                    "label": "Transaction Success Rate",
                    "evidence": {"reason": "Not a blockchain API service"},
                },
                "real_volume": {
                    "score": 0,
                    "max": 10,
                    "label": "Chain Coverage",
                    "evidence": {"reason": "Not a blockchain API service"},
                },
                "staking_commitment": {
                    "score": 0,
                    "max": 5,
                    "label": "Staking / Commitment",
                    "evidence": {"reason": "Not a blockchain API service"},
                },
            },
        }

    # Blockchain service — run all three sub-factors concurrently
    async with aiohttp.ClientSession(
        headers={"User-Agent": "Clarvia-AEO-Scanner/1.0"},
    ) as session:
        (rpc_score, rpc_ev), (chain_score, chain_ev), (commit_score, commit_ev) = (
            await asyncio.gather(
                _check_transaction_success_rate(session, base_url),
                _check_chain_coverage(session, base_url),
                _check_commitment_signals(session, base_url),
            )
        )

    total = rpc_score + chain_score + commit_score

    return {
        "score": total,
        "max": 25,
        "applicable": True,
        "sub_factors": {
            "transaction_success_rate": {
                "score": rpc_score,
                "max": 10,
                "label": "Transaction Success Rate",
                "evidence": rpc_ev,
            },
            "real_volume": {
                "score": chain_score,
                "max": 10,
                "label": "Chain Coverage",
                "evidence": chain_ev,
            },
            "staking_commitment": {
                "score": commit_score,
                "max": 5,
                "label": "Staking / Commitment",
                "evidence": commit_ev,
            },
        },
    }
