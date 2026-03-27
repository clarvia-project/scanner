# Ortus Launch Preparation: Deep Research Report

**Date**: 2026-03-26
**Scope**: Multi-chain memecoin launchpad security, architecture, competition, and regulatory analysis

---

## 1. Multi-Chain Memecoin Launchpad Competitors

### Market Landscape

The memecoin launchpad market is dominated by Pump.fun but rapidly fragmenting. As of mid-2025, Pump.fun's market share dropped from 98% to approximately 57%, indicating real competitive pressure.

### Major Competitors

| Platform | Chain | Key Differentiator | Fee Model | Graduation Threshold |
|----------|-------|-------------------|-----------|---------------------|
| **Pump.fun** | Solana (+ Base) | First-mover, PumpSwap DEX | 0.95% scaling to 0.05% (Project Ascend) | ~$69K-$90K market cap |
| **Moonshot** | Solana | Mobile-only, no web UI | 0.5% (0.3% post-bonding) | Similar bonding curve |
| **Four.meme** | BNB Chain | BNB ecosystem native | Low fees (~$1.50 launch) | PancakeSwap migration |
| **SunPump** | TRON | Cheapest launches (~$1.50) | Minimal | SunSwap auto-migration |
| **LetsBonk/Launchlab** | Solana | Community-driven (BONK ecosystem) | Competitive | Raydium migration |
| **Believe** | Solana | Social media integration | Revenue sharing | Social-driven graduation |
| **Boop** | Solana | Novel fee-sharing mechanism | Fee redistribution | Community-driven |

### Pump.fun Architecture Deep Dive

- **Bonding Curve**: 800M of 1B total supply managed by bonding curve; price increases exponentially with demand
- **No Pre-allocation**: Zero dev tokens, zero early allocations (key trust factor)
- **Graduation**: When bonding curve reaches ~$69K market cap, token migrates to PumpSwap (previously Raydium)
- **PumpSwap**: Launched March 2025, constant product AMM (similar to Uniswap V2/Raydium V4), eliminated 6 SOL migration fee
- **Revenue**: $834M+ total revenue, ~$492M annualized run rate. ICO raised $1.3B in July 2025
- **Project Ascend** (Sept 2025): Dynamic fee scaling from 0.95% (<$300K mcap) down to 0.05% (>$20M mcap), plus creator revenue sharing

### Competitor Weaknesses

1. **Pump.fun**: Centralized control, single-chain origin, ex-employee exploit ($2M loss), no multi-chain native design
2. **Four.meme**: Two major exploits ($183K + $120K) from liquidity pool manipulation; poor migration security
3. **Moonshot**: Mobile-only limits professional/agent use; narrow market
4. **SunPump**: TRON ecosystem limitations, smaller developer community
5. **All competitors**: None have agent-first architecture or AI-native trading interfaces

### Ortus Competitive Advantages to Exploit

- **Agent-first design**: No competitor serves AI agent traders as primary users
- **Multi-chain from day one**: Most competitors are single-chain; Pump.fun added Base as afterthought
- **Security focus**: Competitor exploit history creates opportunity for "security-first" positioning
- **Creator revenue sharing**: Pump.fun only introduced this in Sept 2025; build it natively

---

## 2. Smart Contract Security for Token Launchpads

### Common Attack Vectors

#### A. Bonding Curve Exploits

1. **Sandwich Attacks on Bonding Curves**: Attackers detect pending buys, front-run with their own buy (pushing price up), let victim buy at inflated price, then sell. Over 72,000 sandwich attacks targeted 35,000+ victims on Ethereum in 30 days alone.

2. **Pre-calculated Pool Address Attack** (Four.meme exploit): Attacker pre-calculates the DEX liquidity pool address before token graduation, pre-seeds it with manipulated liquidity, then drains funds when token migrates. **Critical for Ortus**: Validate pool state before migration.

3. **Insider/Ex-employee Attack** (Pump.fun exploit): A former employee used flash loans to buy tokens across multiple bonding curves, forcing them to graduate, then accessed the liquidity. **Critical for Ortus**: Implement strict RBAC, multi-sig for all admin functions, remove single points of failure.

4. **Liquidity Migration Manipulation**: During the transition from bonding curve to DEX, attackers can manipulate the initial pool price. Four.meme was exploited twice via this vector.

#### B. General Smart Contract Attacks

5. **Reentrancy**: Classic DeFi attack; less common on Solana (account model helps) but still possible via CPI callbacks
6. **Flash Loan Exploitation**: Borrow large amounts, manipulate prices/governance, repay in same transaction
7. **Integer Overflow/Underflow**: Especially dangerous in fee calculations and bonding curve math
8. **Oracle Manipulation**: If bonding curve references external price feeds
9. **Front-running**: Block producers or MEV searchers execute trades before users

#### C. Rug Pull Vectors (Platform Must Prevent)

10. **Mint Authority Retention**: Creator keeps ability to mint infinite tokens
11. **Hidden Fee Mechanisms**: Contract contains hidden transfer taxes or fee drains
12. **Liquidity Removal**: Creator removes liquidity after graduation
13. **Proxy Upgrade Attacks**: Upgradeable contracts swapped to malicious versions

### Best Practices for Bonding Curve Contracts

1. **Immutable bonding curve parameters**: No admin can change curve formula after deployment
2. **Locked liquidity**: Auto-lock LP tokens for minimum 6 months post-graduation
3. **Mint authority revocation**: Automatically revoke mint authority at token creation
4. **Freeze authority revocation**: Cannot freeze individual holder accounts
5. **Maximum slippage enforcement**: On-chain slippage limits, not just client-side
6. **Minimum output validation**: Enforce minimum token output in swap instructions
7. **Atomic migration**: Graduation to DEX must be atomic (all-or-nothing transaction)
8. **Pool price validation**: Verify DEX pool price matches bonding curve price at migration

### Audit Firms and Costs

| Tier | Firms | Cost Range | Timeline |
|------|-------|-----------|----------|
| **Tier 1** | Trail of Bits, OtterSec, Halborn, Zellic, Neodyme | $100K-$500K+ | 4-12 weeks |
| **Tier 2** | Sec3, MadShield, Soteria, Ackee Blockchain | $50K-$150K | 3-8 weeks |
| **Tier 3** | Smaller/newer firms | $7K-$50K | 2-4 weeks |

**Solana-specific premium**: 20-30% higher than equivalent EVM audits due to scarcity of Rust/Solana auditors.

**Recommendation**: Get minimum 2 audits from different firms (one Tier 1, one Tier 2). Budget $150K-$250K total.

### Known Exploits Summary

| Platform | Date | Loss | Vector |
|----------|------|------|--------|
| Pump.fun | May 2024 | $2M | Insider flash loan attack on bonding curves |
| Four.meme | Feb 2025 | $183K | Pre-calculated pool address, liquidity manipulation |
| Four.meme | Mar 2025 | $120K+ | Transfer restriction bypass via sandwich attack |

---

## 3. Multi-Chain Architecture Patterns

### Recommended Architecture for Ortus

#### Phase 1: Solana Native (Launch)
- Full bonding curve + graduation on Solana
- PumpSwap-equivalent native AMM (or integrate with Raydium/Orca)
- Agent trading API and MCP tools

#### Phase 2: EVM Expansion (Base, Arbitrum, BSC)
- Deploy equivalent contracts on each EVM chain
- Use cross-chain messaging for unified token registry
- Shared agent identity across chains

#### Phase 3: Cross-Chain Liquidity
- Bridge graduated tokens between chains
- Unified liquidity pools via bridge protocol

### Cross-Chain Messaging Protocols

| Protocol | Architecture | Chains | Best For |
|----------|-------------|--------|----------|
| **LayerZero** | Ultra-Light Nodes + DVN | 150+ chains | Speed, widest chain coverage, 75% market share |
| **Wormhole** | Guardian network (19 validators, 13/19 multisig) | 30+ chains | Solana-native, trust minimization |
| **Chainlink CCIP** | Decentralized oracle network | 20+ chains | Enterprise grade, oracle integration |
| **Axelar** | Proof-of-Stake validator network | 50+ chains | Balance of speed and decentralization |

**Recommendation for Ortus**: Start with **Wormhole** for Solana-to-EVM bridges (native Solana support, strong security model). Add **LayerZero** for broader EVM-to-EVM coverage in Phase 3.

### Token Bridge Patterns

1. **Lock-and-Mint** (Recommended for Phase 2):
   - Lock tokens on source chain in escrow contract
   - Mint equivalent wrapped tokens on destination chain
   - Simple, proven, auditable
   - Risk: Bridge contract becomes single point of failure

2. **Burn-and-Mint** (LayerZero OFT Standard):
   - Burn tokens on source, mint on destination
   - No wrapped tokens, cleaner UX
   - Requires token contract to support burn/mint across chains
   - Best for tokens designed multi-chain from inception

3. **Liquidity Pool Bridge** (Stargate model):
   - Unified liquidity pools across chains
   - No wrapped tokens, instant finality
   - Complex to implement, requires significant initial liquidity

**Recommendation**: Design token contracts from day one with OFT-compatible interfaces even if launching Solana-only. This avoids costly migrations later.

### Architecture Decision: Hub-and-Spoke vs. Full Mesh

**Hub-and-Spoke** (Recommended for Ortus):
- Solana as canonical chain (hub)
- EVM chains as spokes
- All token creation happens on Solana
- Cross-chain messages propagate state to spokes
- Simpler security model, clear source of truth

**Full Mesh** (Future consideration):
- Any chain can create tokens
- Complex state synchronization
- Higher bridge risk surface
- Better for mature multi-chain protocols

---

## 4. Solana-Specific Security

### Critical Solana Program Vulnerabilities

#### A. Account Validation (Most Common)

1. **Missing Owner Checks**: Program doesn't verify account ownership, allowing attacker substitution. Anchor's `Account<>` type handles this, but raw Solana programs must check manually.

2. **Missing Signer Checks**: Instructions that should require signing authority don't verify `is_signer`. In Anchor, use `Signer<'info>` type.

3. **PDA Seed Collisions**: Different inputs produce same PDA address. Mitigation: Use unique prefixes per PDA type, include type discriminators in seeds.

4. **Bump Seed Manipulation**: PDAs can have multiple valid bumps. Always use `find_program_address` canonical bump and store/validate it. Anchor's `bump` constraint handles this.

5. **Account Type Confusion**: Program treats one account type as another. Anchor's discriminator (8-byte prefix) prevents this, but ensure all accounts have discriminators.

#### B. Arithmetic and Logic

6. **Integer Overflow/Underflow**: Rust panics on overflow in debug mode but wraps in release mode. Use `checked_*` operations everywhere: `checked_add`, `checked_mul`, `checked_div`, `checked_sub`.

7. **Precision Loss**: Division before multiplication causes rounding errors. Critical in bonding curve price calculations. Always multiply before dividing.

8. **Incorrect Decimal Handling**: SOL has 9 decimals, SPL tokens have variable decimals. Mismatch causes catastrophic pricing errors.

#### C. CPI and State

9. **CPI Account Reloading**: Anchor doesn't auto-refresh deserialized accounts after CPI. If you modify an account via CPI and then read it, you get stale data. Call `reload()` explicitly.

10. **Arbitrary CPI**: Program makes CPI calls to attacker-controlled program IDs. Always hardcode or validate program IDs for CPI targets.

11. **Closing Account Vulnerability**: Closed accounts can be resurrected within the same transaction. Use Anchor's `close` constraint which zeroes the discriminator.

12. **Duplicate Mutable Accounts**: Same account passed as two different mutable parameters. Use Anchor's `constraint` to ensure accounts are distinct.

### Anchor Framework Security Patterns

```
// Recommended patterns for Ortus programs

// 1. Always validate PDA seeds with bump
#[account(
    seeds = [b"bonding_curve", token_mint.key().as_ref()],
    bump = bonding_curve.bump,
)]
pub bonding_curve: Account<'info, BondingCurve>,

// 2. Use has_one for relational validation
#[account(
    has_one = authority,
    has_one = token_mint,
)]
pub pool: Account<'info, Pool>,

// 3. Require signer for privileged operations
pub authority: Signer<'info>,

// 4. Use close for account cleanup
#[account(
    mut,
    close = authority,
)]
pub temp_account: Account<'info, TempState>,

// 5. Constraint to prevent duplicate accounts
#[account(
    constraint = account_a.key() != account_b.key()
)]
```

### Security Tooling for Solana (2026 State)

1. **Soteria** (sec3.dev): Static analyzer for Solana programs, catches common vulnerability patterns
2. **Trident** (Ackee): Rust-based fuzzing framework for Anchor programs
3. **Xray** (sec3.dev): Runtime security monitoring
4. **cargo-audit**: Dependency vulnerability scanning
5. **Anchor's built-in checks**: Discriminators, owner checks, signer validation

**Critical Stat**: Over 70% of exploited contracts in 2025 had undergone at least one professional audit. Continuous security (fuzzing, monitoring, bug bounty) is essential, not just one-time audits.

---

## 5. Agent-Driven Trading Security

### Threat Model for Autonomous Agent Trading

1. **Agent Compromise**: Malicious instructions cause agent to drain its own wallet
2. **Prompt Injection via Token Metadata**: Malicious token names/descriptions inject trading instructions
3. **Runaway Trading**: Agent enters infinite buy/sell loop, draining fees
4. **Coordinated Attack**: Multiple agents manipulated simultaneously
5. **Key Exposure**: Agent private keys leaked or stolen

### Security Architecture for Agent Trading

#### A. Wallet Security

- **Hierarchical wallet structure**: Master wallet (cold) -> Sub-wallets (hot, per-agent)
- **Per-agent spending limits**: On-chain enforcement via program constraints
- **Time-locked withdrawals**: Large withdrawals require time delay
- **Multi-sig for admin operations**: 2-of-3 minimum for parameter changes

#### B. Rate Limiting (Layered Approach)

| Layer | Mechanism | Limit Example |
|-------|-----------|---------------|
| **Per-transaction** | Max trade size | 1% of agent portfolio per trade |
| **Per-minute** | Cooldown between trades | Max 5 trades/minute |
| **Per-hour** | Rolling hour limit | Max 50 trades/hour |
| **Per-day** | Daily spending cap | Max 10% of portfolio/day |
| **Per-token** | Concentration limit | Max 20% of portfolio in single token |

#### C. Slippage Protection

- **Hard slippage cap**: On-chain enforcement, reject trades exceeding X% slippage
- **Dynamic slippage**: Use Jupiter-style dynamic slippage calculation
- **Minimum output validation**: Transaction-level minimum token output
- **Price impact check**: Reject if trade moves price more than threshold

#### D. MEV Protection on Solana

1. **Jito DontFront**: Add `jitodontfront` pubkey as read-only account to prevent sandwich attacks. Transaction must appear at index 0 in any bundle.

2. **Jito Bundle Submission**: Submit transactions as Jito bundles with tips. Minimum 1000 lamports tip. Use 70/30 split between priority fee and Jito tip.

3. **Jito MEV Protection Mode**: Route all agent transactions through Jito block engine only. Reduces sandwich risk at cost of slightly higher fees.

4. **Declarative Swaps**: Use Jito bundle-based declarative swaps that guarantee quote at signing time while recalculating optimal route before execution.

5. **Private Mempool**: Submit transactions directly to validators via Jito, bypassing public mempool where searchers can see pending transactions.

#### E. Agent Guardrail Architecture

```
Risk Tier System:
  LOW RISK (auto-execute):
    - Buy/sell within normal parameters
    - Portfolio rebalancing within limits

  MEDIUM RISK (notify + execute):
    - Trades exceeding 5% of portfolio
    - New token positions
    - Unusual market conditions detected

  HIGH RISK (require approval):
    - Trades exceeding 10% of portfolio
    - Interacting with unverified contracts
    - Bridge operations
    - Withdrawals to external wallets
```

#### F. Circuit Breakers

- **Portfolio drawdown**: Halt all trading if portfolio drops >15% in 1 hour
- **Market anomaly**: Pause if token price moves >50% in 5 minutes
- **Network congestion**: Reduce trading frequency when Solana fees spike
- **Coordinated movement**: Alert if multiple agents take correlated positions

---

## 6. Regulatory Landscape 2025-2026

### United States

#### SEC Position (February 2025 - Landmark)
- **Memecoins are NOT securities**: SEC Division of Corporation Finance stated meme coins generally do not meet the Howey test
- **Rationale**: No pooling of funds, no investment contract, value derived from market sentiment not managerial efforts
- **Dissent**: Commissioner Crenshaw argued the definition is unclear and many self-proclaimed meme coins may still qualify as securities
- **Implication for Ortus**: Favorable for memecoin launchpad, but NOT a blanket safe harbor

#### Regulatory Shift
- **Gary Gensler resigned** January 2025; Paul Atkins (pro-crypto) became 34th SEC Chair April 2025
- **Enforcement pivot**: From "regulation by enforcement" to "enabling compliance and fostering innovation"
- **Withdrawn actions**: Multiple crypto enforcement actions withdrawn under new leadership

#### CFTC Jurisdiction
- Memecoins likely classified as **commodities** under the Commodity Exchange Act
- CFTC retains enforcement authority over fraud and manipulation
- **Implication**: Anti-manipulation provisions still apply to launchpad operations

#### Key Risks for Ortus
- **Fraud liability**: Even if memecoins aren't securities, fraudulent conduct is prosecutable by CFTC, DOJ, and state AGs
- **Money transmission**: Operating a DEX/AMM may trigger money transmitter registration requirements (FinCEN)
- **OFAC compliance**: Must screen wallets against OFAC SDN list
- **State laws**: Vary significantly; NY BitLicense still applies

### European Union (MiCA)

#### MiCA Implementation (Fully Live 2025)
- **Phase 1** (June 2024): Stablecoin provisions
- **Phase 2** (December 2024): CASP (Crypto-Asset Service Provider) licensing
- **50+ firms** licensed as of 2025
- **Transitional periods are finite**: ESMA warned firms not to treat grandfathering as permanent

#### MiCA Impact on Ortus
- If serving EU users, may need CASP license
- Memecoins not explicitly covered as a category but general crypto-asset rules apply
- Marketing to EU retail users requires specific disclosures
- **Recommendation**: Geo-block EU until legal clarity obtained or CASP license secured

### Global Regulatory Notes

- **UK**: FCA crypto registration required for marketing to UK consumers
- **Singapore**: MAS licensing for Digital Payment Token services
- **Japan**: Strict exchange registration requirements
- **UAE**: Dubai VARA framework relatively favorable for crypto platforms
- **Hong Kong**: SFC licensing for virtual asset trading platforms

### Recommendations for Ortus

1. **Get a legal opinion** from crypto-specialized law firm (Anderson Kill, Debevoise, DLA Piper, or Fenwick & West)
2. **Focus on agent-to-agent** trading to reduce retail consumer protection concerns
3. **Implement KYC/AML** at minimum for fiat on-ramps and large withdrawals
4. **OFAC screening** is non-negotiable for any US-touching operations
5. **Terms of Service** must clearly disclaim securities status and warn of speculative nature
6. **Geo-fence** restricted jurisdictions (initially: EU, UK, Canada, Japan, China, Singapore, South Korea)
7. **Register as MSB** (Money Services Business) with FinCEN if operating DEX in US market
8. **Structure the entity** in a crypto-friendly jurisdiction (BVI, Cayman, or UAE/Dubai)

---

## 7. Launch Checklist

### Pre-Launch (Must Complete)

#### Security
- [ ] **Smart contract audit #1**: Tier 1 firm (OtterSec, Zellic, or Neodyme for Solana)
- [ ] **Smart contract audit #2**: Tier 2 firm (different from #1)
- [ ] **Formal verification** of bonding curve math
- [ ] **Fuzz testing**: Minimum 1M iterations with Trident
- [ ] **Economic audit**: Separate review of tokenomics and bonding curve parameters
- [ ] **Penetration testing**: API, frontend, infrastructure
- [ ] **Bug bounty program launch**: Immunefi or HackenProof, $50K-$500K reward pool
- [ ] **Incident response plan**: Documented runbook for hack/exploit scenarios
- [ ] **Admin key management**: Multi-sig (3-of-5 minimum), hardware wallets, geographic distribution
- [ ] **Upgrade authority**: Timelock on program upgrades (48h minimum delay)
- [ ] **Emergency pause**: Circuit breaker that halts trading platform-wide

#### Infrastructure
- [ ] **RPC infrastructure**: Dedicated validators or premium RPC (Helius, QuickNode, Triton)
- [ ] **Monitoring**: On-chain transaction monitoring (Sec3 Watchtower, custom alerts)
- [ ] **Logging**: Complete audit trail of all platform transactions
- [ ] **Backup and recovery**: Database backups, state snapshots
- [ ] **DDoS protection**: Cloudflare or equivalent for API/frontend
- [ ] **Uptime SLA**: 99.9% target with status page

#### Legal
- [ ] **Legal opinion letter**: From qualified crypto attorney on platform and token status
- [ ] **Terms of Service**: Comprehensive, reviewed by legal counsel
- [ ] **Privacy Policy**: GDPR-compliant if serving non-US users
- [ ] **Risk disclosures**: Clear warnings about speculative nature of memecoins
- [ ] **Entity structure**: Offshore entity for platform operations
- [ ] **OFAC compliance**: Wallet screening integration (Chainalysis, TRM Labs, Elliptic)
- [ ] **FinCEN MSB registration**: If US operations

#### Financial Safety
- [ ] **Insurance fund**: Allocate 5-10% of protocol revenue to safety fund
- [ ] **Protocol insurance**: Consider Nexus Mutual or similar coverage ($190M capital pool available)
- [ ] **Treasury management**: Multi-sig treasury, no single-person access
- [ ] **Revenue splitting**: Automated fee distribution to insurance fund, team, treasury

#### Product
- [ ] **Token creation flow**: Tested with 1000+ token launches on devnet
- [ ] **Bonding curve**: Mathematically verified, edge case tested (0 liquidity, max supply, etc.)
- [ ] **Graduation mechanism**: Atomic migration tested under network congestion
- [ ] **Trading interface**: Load tested for concurrent agent traffic
- [ ] **API documentation**: Complete, versioned, with rate limit documentation
- [ ] **MCP tools**: All 47+ tools tested with real agent workflows
- [ ] **Wallet integration**: Phantom, Solflare, Backpack tested
- [ ] **Mobile responsiveness**: If applicable

### Launch Day

- [ ] **Gradual rollout**: Whitelist-based access, expand over 48-72 hours
- [ ] **Team on-call**: 24/7 coverage for first 2 weeks
- [ ] **Real-time monitoring dashboard**: TVL, trades/sec, error rates, unusual patterns
- [ ] **Communication channels**: Discord, Telegram, Twitter ready for incident communication
- [ ] **Seed liquidity**: Platform-controlled initial liquidity for first tokens
- [ ] **Rate limiting**: Conservative initial limits, expand based on stability

### Post-Launch (First 30 Days)

- [ ] **Continuous monitoring**: Automated alerts for unusual transaction patterns
- [ ] **Bug bounty responses**: 24h response time for critical submissions
- [ ] **Performance tuning**: Optimize based on real traffic patterns
- [ ] **Community feedback**: Structured feedback collection and prioritization
- [ ] **Security retainer**: Ongoing engagement with audit firm for new features
- [ ] **Regulatory monitoring**: Track any new enforcement actions or guidance

---

## Appendix A: Cost Estimates

| Item | Cost Range | Priority |
|------|-----------|----------|
| Audit #1 (Tier 1) | $80K-$180K | P0 |
| Audit #2 (Tier 2) | $40K-$80K | P0 |
| Legal opinion | $20K-$50K | P0 |
| Bug bounty pool | $50K-$500K | P0 |
| Insurance fund seed | $50K-$200K | P1 |
| RPC infrastructure | $2K-$10K/month | P0 |
| Monitoring tools | $1K-$5K/month | P0 |
| Penetration testing | $15K-$40K | P1 |
| OFAC screening service | $1K-$5K/month | P0 |
| Entity formation + legal | $10K-$30K | P0 |
| **Total pre-launch** | **$270K-$1.1M** | |

## Appendix B: Key Architectural Decisions for Ortus

### Decision 1: Bonding Curve Design
**Recommendation**: Modified constant product curve with these Ortus-specific features:
- Anti-snipe window: First 30 seconds of trading have enforced max buy limit
- Progressive fee curve: Fees decrease as market cap grows (similar to Pump.fun's Project Ascend)
- Graduation threshold: Set at $50K-$100K market cap (configurable per token)
- LP lock: Auto-lock for 180 days minimum post-graduation

### Decision 2: Agent Authentication
**Recommendation**: On-chain agent registry with:
- Agent identity NFT (non-transferable)
- Spending limits encoded in PDA
- Rate limits enforced at program level
- Risk tier assignment based on agent history

### Decision 3: Multi-chain Strategy
**Recommendation**: Hub-and-spoke starting with Solana:
1. Launch Solana-only with full feature set
2. Add Base (Coinbase ecosystem, cheapest EVM chain) in Phase 2
3. Add Arbitrum (DeFi ecosystem) in Phase 3
4. Use Wormhole for Solana<->EVM bridges
5. Design token interfaces as OFT-compatible from day one

### Decision 4: Revenue Model
**Recommendation**: Blended model:
- Token creation fee: 0.02 SOL (low barrier)
- Trading fee: 0.8% (below Pump.fun's 0.95%, competitive advantage)
- Graduation fee: 0 SOL (eliminate Pump.fun's old pain point)
- Revenue split: 50% treasury, 30% insurance fund, 10% creator revenue share, 10% agent rewards
