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

## 5. 反偷懒自检
- [ ] 已读 wiki 入口
- [ ] 高价值候选都有锚点
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

## 5. 反偷懒自检
- 没有勾选框的普通条目
"""


def run() -> int:
    mod = _load()
    failures = []

    g_err, _ = mod.validate_dossier(GOOD)
    if g_err:
        failures.append(f"good fixture 本应通过，却报错: {g_err}")

    b_err, _ = mod.validate_dossier(BAD)
    expected = {"frontmatter 缺字段: updated", "HV-1 缺少上下文胶囊"}
    if not expected.issubset(set(b_err)):
        failures.append(
            f"bad fixture 漏掉预期错误 {expected - set(b_err)}；实得 {b_err}"
        )
    if not any("勾选" in e for e in b_err):
        failures.append(f"bad fixture 未检出自检无勾选框；实得 {b_err}")

    if failures:
        print("SELF-TEST FAIL")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("SELF-TEST PASS (good 通过, bad 检出全部预期错误)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
