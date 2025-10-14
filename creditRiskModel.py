"""
WageArrearsRiskModel（基于你的社保稽核模型改造版）
—— 去掉延迟天数；type 顺序固定为 1/2/3/4；支持单组与多组；可覆盖权重与直判阈值

type 映射（按顺序 1,2,3,4）：
1: 参保人数差异比例       -> head_ratio = |社保实际缴纳人数 - 社保缴纳人数| / 社保缴纳人数
2: 社保缴纳金额差异比例   -> amount_ratio = |本期社保缴纳金额 - 对比期社保缴纳金额| / 对比期社保缴纳金额
3: 工资流水金额差异比例   -> wage_ratio = |本期工资流水金额 - 对比期工资流水金额| / 对比期工资流水金额
4: 有效工单数量（值越大风险越高） -> tickets

覆盖规则：
- 仅当在某个“指标字典”里显式提供“当前项权重”或“直判阈值”时，才覆盖默认配置；
- 否则沿用默认 weights_init / hard_limits；
- 缺失项的权重会被置 0，然后对剩余项重归一化；
- 命中直判项会按 weight_amp_factor 放大其权重（若命中多项则平均摊放大倍数），再整体重归一化。
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from copy import deepcopy
import numpy as np
import pandas as pd
import math
import json


class creditRiskModel:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # —— 默认配置（4 项）——
        default_conf: Dict[str, Any] = {
            # 归一化阈值（超过视为1.0）
            "thresholds": {
                "head_ratio":   0.40,  # 参保人数差异比例满分阈值
                "amount_ratio": 0.40,  # 社保金额差异比例满分阈值
                "wage_ratio":   0.40,  # 工资流水金额差异比例满分阈值
                "tickets":      3.0,   # 有效工单数量满分阈值
            },
            # 规则直判硬阈值（命中任一即高风险）
            "hard_limits": {
                "head_ratio":   0.40,
                "amount_ratio": 0.40,
                "wage_ratio":   0.40,
                "tickets":      3.0,
            },
            # 非直判分级阈值（RiskScore 基于 0~100）
            "grading": {"high": 70, "mid": 40},

            # 初始权重（和=1）：[S_head, S_amount, S_wage, S_ticket]
            "weights_init": [0.25, 0.20, 0.25, 0.30],

            # 命中项“权重相对放大”的因子（>1 表示放大）
            "weight_amp_factor": 10.0,
        }

        self._default_conf: Dict[str, Any] = deepcopy(default_conf)
        if config:
            self.update_config(config)

    # ---------- 配置 ----------
    def update_config(self, cfg: Dict[str, Any]):
        for k, v in cfg.items():
            if isinstance(v, dict) and isinstance(self._default_conf.get(k), dict):
                self._default_conf[k].update(v)
            else:
                self._default_conf[k] = v

    def _merged_config_for_request(self, override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        cfg = deepcopy(self._default_conf)
        if not override:
            return cfg
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
        return cfg

    # ---------- 工具 ----------
    @staticmethod
    def _safe_float(x) -> float:
        try:
            if pd.isna(x):
                return float("nan")
            return float(x)
        except Exception:
            return float("nan")

    @staticmethod
    def _safe_int(x) -> int:
        try:
            if pd.isna(x):
                return 0
            return int(x)
        except Exception:
            return 0

    @staticmethod
    def _normalize_w(weights_init: List[float]) -> np.ndarray:
        w = np.array(weights_init, dtype=float)
        w = np.maximum(w, 0.0)
        s = w.sum()
        return (w / s) if s > 0 else np.ones_like(w) / len(w)

    @staticmethod
    def _renorm(v: np.ndarray) -> np.ndarray:
        v = np.maximum(v, 0.0)
        s = v.sum()
        return v / s if s > 0 else np.ones_like(v) / len(v)

    # ---------- 归一化（基于阈值） ----------
    def _normalize_scores(self, indic: Dict[str, float], cfg: Dict[str, Any]) -> Dict[str, float]:
        T = cfg["thresholds"]
        return {
            "S_head":   min(1.0, indic.get("head_ratio",   0.0) / max(1e-9, T["head_ratio"])),
            "S_amount": min(1.0, indic.get("amount_ratio", 0.0) / max(1e-9, T["amount_ratio"])),
            "S_wage":   min(1.0, indic.get("wage_ratio",   0.0) / max(1e-9, T["wage_ratio"])),
            "S_ticket": min(1.0, indic.get("tickets",      0.0) / max(1e-9, T["tickets"])),
        }

    # ---------- 规则直判 ----------
    def _hard_judgement(self, indic: Dict[str, float], cfg: Dict[str, Any]) -> Tuple[bool, List[str]]:
        H = cfg["hard_limits"]
        hits: List[str] = []
        if indic.get("head_ratio",   0.0) >= H["head_ratio"]:   hits.append("参保人数差异过大")
        if indic.get("amount_ratio", 0.0) >= H["amount_ratio"]: hits.append("社保金额差异过大")
        if indic.get("wage_ratio",   0.0) >= H["wage_ratio"]:   hits.append("工资流水金额差异过大")
        if indic.get("tickets",      0.0) >= H["tickets"]:      hits.append("有效工单过多")
        return (len(hits) > 0, hits)

    # ---------- RiskScore（命中项权重相对放大 + 缺失项权重=0） ----------
    def _risk_score_with_boost_and_missing(
        self,
        S: Dict[str, float],
        hits: List[str],
        miss: Dict[str, bool],
        w0_used: np.ndarray,
        cfg: Dict[str, Any]
    ) -> Tuple[float, np.ndarray]:
        """
        返回：(RiskScore, 最终权重向量 w_used)
        - 缺失项：对应权重置 0
        - 命中项：对应权重 *= weight_amp_factor（若命中多项则平均摊放大倍数）
        - 归一化后与 S 点积得到 0~1，再 ×100
        """
        w = w0_used.astype(float).copy()
        amp = float(cfg.get("weight_amp_factor", 8.0))

        # 索引顺序：[head, amount, wage, ticket]
        idx_map = {"head": 0, "amount": 1, "wage": 2, "ticket": 3}
        if miss.get("head_missing"):   w[idx_map["head"]] = 0.0
        if miss.get("amount_missing"): w[idx_map["amount"]] = 0.0
        if miss.get("wage_missing"):   w[idx_map["wage"]] = 0.0
        if miss.get("ticket_missing"): w[idx_map["ticket"]] = 0.0

        hit_map = {
            "参保人数差异过大":     idx_map["head"],
            "社保金额差异过大":     idx_map["amount"],
            "工资流水金额差异过大": idx_map["wage"],
            "有效工单过多":       idx_map["ticket"],
        }
        for h in hits:
            if h in hit_map and w.sum() > 0:
                w[hit_map[h]] *= amp

        w_used = self._renorm(w)
        s_vec = np.array([S["S_head"], S["S_amount"], S["S_wage"], S["S_ticket"]], dtype=float)
        score01 = float(np.dot(w_used, s_vec))
        return round(100.0 * score01, 4), w_used

    def _grade_by_score(self, score: float, cfg: Dict[str, Any]) -> int:
        g = cfg["grading"]
        if score >= g["high"]:
            return 2
        if score >= g["mid"]:
            return 1
        return 0

    # ---------- 单组评估核心 ----------
    def _evaluate_one_group(self, data_group: List[Dict[str, Any]], cfg_used: Dict[str, Any]) -> Dict[str, Any]:
        """
        对一组（4条，type=1/2/3/4）的指标进行评估，返回单组结果与消息。
        """
        indic: Dict[str, float] = {}
        miss: Dict[str, bool] = {
            "head_missing":   True,
            "amount_missing": True,
            "wage_missing":   True,
            "ticket_missing": True,
        }

        # 初始权重（顺序 [head, amount, wage, ticket]）
        weights_init = list(cfg_used["weights_init"])

        # 直判阈值的“显式覆盖”
        hard_overrides: Dict[str, float] = {}

        # 逐项解析
        for item in data_group:
            t = item.get("type")

            # --- 权重覆盖：仅当显式提供时 ---
            if "当前项权重" in item and str(item.get("当前项权重")) != "":
                w_val = self._safe_float(item.get("当前项权重"))
                if not math.isnan(w_val):
                    if t == 1:
                        weights_init[0] = float(w_val)
                    elif t == 2:
                        weights_init[1] = float(w_val)
                    elif t == 3:
                        weights_init[2] = float(w_val)
                    elif t == 4:
                        weights_init[3] = float(w_val)

            # --- 直判阈值覆盖：仅当显式提供时 ---
            if "直判阈值" in item and str(item.get("直判阈值")) != "":
                thr_val = self._safe_float(item.get("直判阈值"))
                if not math.isnan(thr_val):
                    if t == 1:
                        hard_overrides["head_ratio"] = float(thr_val)
                    elif t == 2:
                        hard_overrides["amount_ratio"] = float(thr_val)
                    elif t == 3:
                        hard_overrides["wage_ratio"] = float(thr_val)
                    elif t == 4:
                        hard_overrides["tickets"] = float(thr_val)

            # --- 指标值计算 ---
            if t == 1:
                # 参保人数差异比例
                head_real = self._safe_int(item.get("社保实际缴纳人数"))
                head_tax = self._safe_int(item.get("社保缴纳人数"))
                if head_tax > 0:
                    indic["head_ratio"] = abs(head_real - head_tax) / float(head_tax)
                    miss["head_missing"] = False
                else:
                    indic["head_ratio"] = 0.0
                    miss["head_missing"] = True

            elif t == 2:
                # 社保缴纳金额差异比例
                amt_cur = self._safe_float(item.get("本期社保缴纳金额"))
                amt_cmp = self._safe_float(item.get("对比期社保缴纳金额"))
                if not math.isnan(amt_cur) and not math.isnan(amt_cmp) and abs(amt_cmp) > 0:
                    indic["amount_ratio"] = abs(amt_cur - amt_cmp) / abs(amt_cmp)
                    miss["amount_missing"] = False
                else:
                    indic["amount_ratio"] = 0.0
                    miss["amount_missing"] = True

            elif t == 3:
                # 工资流水金额差异比例
                wage_cur = self._safe_float(item.get("本期工资流水金额"))
                wage_cmp = self._safe_float(item.get("对比期工资流水金额"))
                if not math.isnan(wage_cur) and not math.isnan(wage_cmp) and abs(wage_cmp) > 0:
                    indic["wage_ratio"] = abs(wage_cur - wage_cmp) / abs(wage_cmp)
                    miss["wage_missing"] = False
                else:
                    indic["wage_ratio"] = 0.0
                    miss["wage_missing"] = True

            elif t == 4:
                # 有效工单数量
                tickets = self._safe_float(item.get("有效工单数量"))
                if math.isnan(tickets):
                    indic["tickets"] = 0.0
                    miss["ticket_missing"] = True
                else:
                    indic["tickets"] = float(tickets)
                    miss["ticket_missing"] = False

            else:
                # 未知 type 跳过
                continue

        # 应用直判阈值覆盖
        cfg_tmp = deepcopy(cfg_used)
        cfg_tmp["hard_limits"].update(hard_overrides)

        # 若权重全为 0，则回退默认
        if sum(weights_init) <= 0:
            weights_init = list(cfg_used["weights_init"])

        # 归一化权重（初始）
        w0_used = self._normalize_w(weights_init)

        # 归一化各指标分
        S = self._normalize_scores(indic, cfg_tmp)

        # 直判
        is_hard, hits = self._hard_judgement(indic, cfg_tmp)

        # 计算风险分（缺失置零 + 命中放大且平均摊）
        score, _ = self._risk_score_with_boost_and_missing(
            S, hits, miss, w0_used=w0_used, cfg=cfg_tmp
        )
        level = 2 if is_hard else self._grade_by_score(score, cfg_tmp)

        # 缺失提示
        miss_names = []
        if miss.get("head_missing"):
            miss_names.append("人数差异项（社保缴纳人数缺失/为0）")
        if miss.get("amount_missing"):
            miss_names.append("社保金额项（对比期社保金额缺失/为0）")
        if miss.get("wage_missing"):
            miss_names.append("工资流水项（对比期工资金额缺失/为0）")
        if miss.get("ticket_missing"):
            miss_names.append("工单项（有效工单数量缺失）")

        msg_parts = []
        if miss_names:
            msg_parts.append(f"缺失指标：{', '.join(miss_names)}（已将缺失项权重置0并重分配）")
        if is_hard and hits:
            msg_parts.append(f"直判命中：{'、'.join(hits)}")
        final_msg = "；".join(msg_parts) if msg_parts else "计算成功"

        return {
            "status_code": 200,
            "result": [{
                "风险等级": int(level),          # 2高 / 1中 / 0低
                "RiskScore": float(score),      # 0~100
                "是否直判高风险": bool(is_hard),
                "预警信息": "、".join(hits) if hits else ""
            }],
            "message": final_msg
        }

    # ---------- 面向接口：单组或多组 ----------
    def evaluate_payload(
        self,
        payload_or_data: Union[Dict[str, Any], List[Dict[str, Any]]],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        入参（推荐）：
          单组：{"data": [ {type:1,...}, {type:2,...}, {type:3,...}, {type:4,...} ]}
          多组：{"data": [ [组1的4条], [组2的4条], ... ]}
        兼容：直接传 data list 也可（单组）。

        返回（单组为一条，多组为多条，均在同一个 result 数组里）：
          {
            "status_code": 200/500,
            "result": [
              { "风险等级": 2/1/0, "RiskScore": float, "是否直判高风险": bool, "预警信息": "..." },
              ...
            ],
            "message": "..."
          }
        """
        try:
            # 解析 data
            if isinstance(payload_or_data, dict):
                data = payload_or_data.get("data", None)
            else:
                data = payload_or_data

            if not isinstance(data, list) or len(data) == 0:
                return {
                    "status_code": 500,
                    "result": [],
                    "message": "入参为空或格式错误，应为 {'data': [...]} 或直接传列表"
                }

            cfg_used = self._merged_config_for_request(config)

            # 多组模式
            if isinstance(data[0], list):
                all_results = []
                messages = []
                for idx, group in enumerate(data):
                    res = self._evaluate_one_group(group, cfg_used)
                    for r in res.get("result", []):
                        r["组号"] = idx + 1
                    all_results.extend(res.get("result", []))
                    messages.append(f"组{idx+1}: {res.get('message', '计算成功')}")
                return {
                    "status_code": 200 if all_results else 500,
                    "result": all_results,
                    "message": "；".join(messages) if messages else "计算成功"
                }

            # 单组模式
            return self._evaluate_one_group(data, cfg_used)

        except Exception as e:
            return {"status_code": 500, "result": [], "message": f"系统异常：{repr(e)}"}


