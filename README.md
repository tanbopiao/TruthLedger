# TruthLedger

> **Governance for an AI agent's truth store — firewall, provenance, immortality.**
>
> AI 记忆真值库的治理套件：白名单防火墙 + 溯源校验 + 多源不灭守卫。

[English](#english) | [中文](#中文)

---

## English

Autonomous agents accumulate a growing store of "truths" — rules, decisions, distilled facts they rely on. Three failure modes kill such stores: **forged keys** injected into the high-level rule space, **silent drift** between replicas, and **unverifiable provenance** (nobody can prove what was reported, when, or whether it rolled back).

TruthLedger addresses all three with four orthogonal primitives, distilled from the ZONGYUAN-ROOT governance kernel:

| Module | What it does |
|---|---|
| **`firewall`** | Client-side whitelist gate: high-level keys (`RULE.META*`, `PROTOCOL*`, `AXIOM*`…) not matching the local whitelist are treated as forged and refused |
| **`provenance`** | 5-dimension verification — existence, version (anti-rollback), timestamp, SHA256 content integrity, upload-receipt match |
| **`immortality`** | N-source registry consistency: snapshot / verify / restore against one authoritative copy, with an "immortality index" (0–100) |
| **`governance`** | 4-phase loop — audit (category/coverage analysis) → distill (weighted scoring, cloud-dedup) → purge (probe/test-key detection) → consolidate (JSON+Markdown ledger) |

### Security posture

- **Zero hardcoded credentials.** The upstream scripts carried embedded capture tokens and file-based token fallbacks; both were removed in distillation. Tokens come only from the environment (`TRUTHLEDGER_TOKEN` / `TRUTHLEDGER_ENDPOINT`), and a missing token is a hard error.
- `auth.redact()` masks tokens in any log output.
- Network transport is injectable — every verdict is unit-testable offline.

### 60-second tour

```python
from truthledger import Auth, TruthFirewall, ImmortalityGuard
from truthledger.governance import run_cycle

# 1. Firewall: refuse forged high-level keys
fw = TruthFirewall(auth=Auth.from_env(), whitelist_path="allowed_meta_keys.txt")
fw.check_one("RULE.META.SOMETHING")   # TRUSTED / SUSPECT / FETCH_FAIL

# 2. Governance: one audit → distill → purge → consolidate pass
report = run_cycle(
    cloud_keys=["RULE.A", "PROBE.X", "HEARTBEAT.1"],
    candidates=[{"key": "K1", "content": "a distilled insight", "score": 82}],
    out_dir="./reports",
)
print(report["verdict"])              # GOVERN_ACTIVE / GOVERN_IDLE

# 3. Immortality: keep replicas consistent with the authority
guard = ImmortalityGuard(
    sources={"authority": "reg_authoritative.json", "runtime": "reg_runtime.json"},
    authority="authority",
)
guard.snapshot(); guard.verify(); guard.restore()
print(guard.audit())                  # {"immortality_index": 97.5, ...}
```

Requirements: Python 3.10+, **zero dependencies**.

---

## 中文

自治智能体会不断积累「真值」——它赖以运行的规则、决策、蒸馏事实。三类失效会毁掉真值库：高层规则空间被**伪造注入**、多副本间**静默漂移**、**溯源不可验证**。TruthLedger 以四个正交原语应对（提炼自 ZONGYUAN-ROOT 治理内核）：

| 模块 | 机制 |
|---|---|
| **`firewall`** | 节点侧白名单防火墙：高层 key（`RULE.META*`/`PROTOCOL*`/`AXIOM*`…）不在白名单内即视为伪造，拒绝执行 |
| **`provenance`** | 五维溯源校验 — 存在性、版本（防回滚）、时间戳、SHA256 内容完整性、上报回执核对 |
| **`immortality`** | 多源注册表一致性：快照 / 校验 / 自动恢复（以权威源为准），输出「不灭指数」0–100 |
| **`governance`** | 四阶段闭环 — 体检（类别/覆盖率分析）→ 提炼（四维加权评分、云端去重）→ 净化（探针/测试 key 识别）→ 固化（JSON+Markdown 台账） |

### 安全姿态

- **零硬编码凭证**。上游脚本内嵌明文令牌并回退读取私有凭证文件，提炼时全部移除；令牌仅从环境变量注入（`TRUTHLEDGER_TOKEN` / `TRUTHLEDGER_ENDPOINT`），缺失即报错，不静默降级。
- `auth.redact()` 对日志输出中的令牌打码。
- 网络传输可注入，所有判定均可离线单测。

### 快速上手

```python
from truthledger import Auth, TruthFirewall, ImmortalityGuard
from truthledger.governance import run_cycle

fw = TruthFirewall(auth=Auth.from_env(), whitelist_path="allowed_meta_keys.txt")
fw.check_one("RULE.META.SOMETHING")   # TRUSTED / SUSPECT / FETCH_FAIL

report = run_cycle(
    cloud_keys=["RULE.A", "PROBE.X", "HEARTBEAT.1"],
    candidates=[{"key": "K1", "content": "一条有价值的蒸馏结论", "score": 82}],
    out_dir="./reports",
)

guard = ImmortalityGuard(
    sources={"authority": "reg_authoritative.json", "runtime": "reg_runtime.json"},
    authority="authority",
)
guard.snapshot(); guard.verify(); guard.restore()
guard.audit()
```

依赖：Python 3.10+，**零第三方依赖**。

---

## 来源与治理

- 本仓库从 [ZONGYUAN-ROOT](https://atomgit.com/zongyuangen/ZONGYUAN-ROOT)（branch `converge-20260928`）提炼：`07_代码与脚本/truth_firewall.py` · `truth_governance.py` · `truth_provenance_audit.py` · `truth_immortality_guard.py` · `truth_distill_engine.py`
- 遵循「元极恒一」治理规范：基准资产只读、衍生独立建库、提炼中移除全部明文凭证
- 许可：Apache-2.0
