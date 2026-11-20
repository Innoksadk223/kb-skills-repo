#!/usr/bin/env python3
"""Self-test for validate_dossier.py: a good fixture passes, a bad one fails."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "validate_dossier", SCRIPT_DIR / "validate_dossier.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GOOD = """---
title: 测试材料深读档案
type: reading_dossier
source_raw:
  - wiki/raw/test.md
trigger: explicit_source
user_intent: ""
status: draft
target: karpathy-wiki
created: 2026-06-26
updated: 2026-06-26
compiled_to: []
confidence: medium
raw_lines: 260
---

# 测试材料深读档案

## 1. 阅读地图
全文问题与放弃清单。

## 2. 候选节点池
### 候选 Concepts
| 概念 | 用法 | 边界 | raw 锚点 | 建议 |
|---|---|---|---|---|
| a | x | y | wiki/raw/test.md | 新建 |
| b | x | y | wiki/raw/test.md | 新建 |
### 候选 Claims
| 命题 | 类型 | 支撑 | raw 锚点 | 价值 |
|---|---|---|---|---|
| c1 | main | z | wiki/raw/test.md | 高 |

## 3. 高价值点深挖
### HV-1: 概念边界
#### 上下文胶囊
- raw 锚点：wiki/raw/test.md
### HV-2: 核心命题
#### 上下文胶囊
- raw 锚点：wiki/raw/test.md
### HV-3: 反方
#### 上下文胶囊
- raw 锚点：wiki/raw/test.md

## 4. wiki 交接清单
建议新建与必查锚点。

## 5. 硬门禁自检
- [x] 1. 不是摘要：通过 — 有放弃清单、有逐字摘录锚点
- [x] 2. 足够丰富：通过 — 配额豁免：测试 fixture，全文仅 260 行且来源窄（行 1-260）
- [x] 3. 结构可追溯：通过
- [x] 4. 胶囊完整：通过
- [x] 5. 交接可执行：通过
- [x] 6. 对抗性自问：最大批评是档案太短，但信息密度足够，无灌水
"""

# Missing `updated` field; HV-1 has no capsule; self-check has no checkbox.
BAD = """---
title: 坏档案
type: reading_dossier
source_raw:
  - wiki/raw/test.md
trigger: explicit_source
status: draft
target: karpathy-wiki
created: 2026-06-26
compiled_to: []
---

# 坏档案

## 1. 阅读地图
x

## 2. 候选节点池
y

## 3. 高价值点深挖
### HV-1: 残缺候选
只有一句释义，既没有胶囊块也没有 raw 路径。

## 4. wiki 交接清单
z

## 5. 硬门禁自检
- 没有勾选框的普通条目
"""

# raw_lines=3000（第三档：HV>=8/概念>=12/claims>=24），只有 1 个 HV、
# 无配额豁免、且自检有未勾选项 → 应报分档配额错误 + 未勾选错误。
BAD_QUOTA = """---
title: 配额不足档案
type: reading_dossier
source_raw:
  - wiki/raw/test.md
trigger: explicit_source
status: draft
target: karpathy-wiki
created: 2026-06-26
updated: 2026-06-26
compiled_to: []
confidence: low
raw_lines: 3000
---

# 配额不足档案

## 1. 阅读地图
x

## 2. 候选节点池
### 候选 Claims
| 命题 | 类型 | 支撑 | raw 锚点 | 价值 |
|---|---|---|---|---|
| c1 | main | z | wiki/raw/test.md | 高 |

## 3. 高价值点深挖
### HV-1: 唯一候选
#### 上下文胶囊
- raw 锚点：wiki/raw/test.md

## 4. wiki 交接清单
z

## 5. 硬门禁自检
- [x] 1. 不是摘要：通过
- [ ] 2. 足够丰富：不通过 — 且没有写豁免声明
"""


GOOD_PDF = """---
title: 肖群忠孝论深读档案
type: reading_dossier
source_raw:
  - 02-学术研究/孝为仁礼之本论_肖群忠.pdf
trigger: explicit_source
user_intent: ""
status: draft
target: karpathy-wiki
created: 2026-11-20
updated: 2026-11-20
compiled_to: []
confidence: high
source_pages: 10
---

# 肖群忠孝论深读档案

## 1. 阅读地图
全文问题与放弃清单。

## 2. 候选节点池
### 候选 Concepts
| 概念 | 用法 | 边界 | 来源锚点 | 建议 |
|---|---|---|---|---|
| 孝本论 | x | y | 02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.12 | 新建 |
### 候选 Claims
| 命题 | 类型 | 支撑 | 来源锚点 | 价值 |
|---|---|---|---|---|
| 孝是仁的情感根源 | main | z | 02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.12 | 高 |

## 3. 高价值点深挖
### HV-1: 孝与仁
#### 上下文胶囊
- 来源锚点：02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.12
### HV-2: 孝与礼
#### 上下文胶囊
- 来源锚点：02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.13
### HV-3: 反方回应
#### 上下文胶囊
- 来源锚点：02-学术研究/孝为仁礼之本论_肖群忠.pdf#p.15

## 4. wiki 交接清单
建议新建与必查锚点。

## 5. 硬门禁自检
- [x] 1. 不是摘要：通过
- [x] 2. 足够丰富：通过 — 配额豁免：单篇 10 页论文 fixture（p.1-10）
- [x] 3. 结构可追溯：通过
- [x] 4. 胶囊完整：通过
- [x] 5. 交接可执行：通过
- [x] 6. 对抗性自问：通过
"""


def run() -> int:
    mod = _load()
    failures = []

    g_err, _ = mod.validate_dossier(GOOD)
    if g_err:
        failures.append(f"good fixture 本应通过，却报错: {g_err}")

    pdf_err, pdf_warn = mod.validate_dossier(GOOD_PDF)
    if pdf_err:
        failures.append(f"direct PDF fixture 本应通过，却报错: {pdf_err}")
    if any("wiki/raw/" in w for w in pdf_warn):
        failures.append(f"direct PDF fixture 不应再对非 wiki/raw/ 路径告警，实得: {pdf_warn}")

    b_err, _ = mod.validate_dossier(BAD)
    expected = {
        "frontmatter 缺字段: updated",
        "frontmatter 缺字段: confidence",
        "HV-1 缺少上下文胶囊",
    }
    if not expected.issubset(set(b_err)):
        failures.append(
            f"bad fixture 漏掉预期错误 {expected - set(b_err)}；实得 {b_err}"
        )
    if not any("勾选" in e for e in b_err):
        failures.append(f"bad fixture 未检出自检无勾选框；实得 {b_err}")

    q_err, _ = mod.validate_dossier(BAD_QUOTA)
    if not any("未勾选" in e for e in q_err):
        failures.append(f"quota fixture 未检出未勾选项；实得 {q_err}")
    if not any("分档配额" in e for e in q_err):
        failures.append(f"quota fixture 未检出分档配额不足；实得 {q_err}")

    if failures:
        print("SELF-TEST FAIL")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("SELF-TEST PASS (good 通过, bad 检出全部预期错误)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
