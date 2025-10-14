# -*- coding: utf-8 -*-
"""
socialModel.py
社保基金稽核风险模型（权重相对放大 + 缺失项权重置零 + 总额/人均口径切换）

功能要点：
1) 指标：基数差异比例、人数差异比例、单月延迟天数、有效工单数量
2) 规则直判：命中任一硬阈值 => 高风险（并触发预警信息）
3) RiskScore：100 * (w' · S)，其中：
   - S 为各指标归一化分数（0~1）
   - w' 在“命中项权重相对放大 + 缺失项权重置零”后再归一
4) 缺失项（该项无法计算）⇒ 该项权重置 0，其他项按比例抬升，并在 message 中提示
5) 输出格式固定：{"status_code": 200/500, "result": [...], "message": "..."}
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from copy import deepcopy
import json
import math
import numpy as np
import pandas as pd


class SocialAuditModel:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # —— 默认配置（无行业差异项）——
        default_conf: Dict[str, Any] = {
            # 归一化阈值（超过视为1.0）
            "thresholds": {
                "base_ratio": 0.15,   # 基数差异比例满分阈值
                "head_ratio": 0.10,   # 人数差异比例满分阈值
                "delay_days": 8.0,   # 单月延迟天数满分阈值
                "tickets":    2.0,    # 有效工单数量满分阈值
            },
            # 规则直判硬阈值（命中任一即高风险）
            "hard_limits": {
                "base_ratio": 0.20,
                "head_ratio": 0.15,
                "delay_days": 12.0,
                "tickets":    3.0,
            },
            # 非直判分级阈值（RiskScore 基于 0~100）
            "grading": {"high": 70, "mid": 40},

            # 工资→对比基数折算系数（用于口径转换）
            "salary_to_base_factor": 1.0,

            # 对比口径：'total' 用总额对比；'per_capita' 用人均对比
            "comparison_mode": "total",

            # 单月日期字段
            "date_fields": {
                "actual_one": "本月社保缴费日期",
                "legal_one":  "本月法定社保缴费日期",
            },

            # 列名映射
            "cols": {
                "id":         "企业/个体id",
                "base":       "社保缴费基数",             # 这里存“社保基数总额”（total 口径）
                "head":       "社保缴费人数/参保人数",
                "tax_salary": "个税申报工资总额",
                "tax_head":   "个税申报人数",
                "tickets":    "有效工单数量",
            },

            # 初始权重（和=1）：[S_base, S_head, S_delay, S_ticket]
            "weights_init": [0.30, 0.25, 0.20, 0.25],

            # 命中项“权重相对放大”的因子（>1 表示放大；如 10.0）
            "weight_amp_factor": 10.0,
        }

        # 保存“一份永远不被污染的默认配置”
        self._default_conf: Dict[str, Any] = deepcopy(default_conf)

        # 如需修改“默认配置”，构造时允许传入并更新默认配置
        if config:
            self.update_config(config)

    # ---------- 配置 ----------
    def update_config(self, cfg: Dict[str, Any]):
        """更新模型的默认配置（用于改变未来请求的默认值）。"""
        for k, v in cfg.items():
            # 浅层合并：字典则 update，非字典直接覆盖
            if isinstance(v, dict) and isinstance(self._default_conf.get(k), dict):
                self._default_conf[k].update(v)
            else:
                self._default_conf[k] = v

    def _merged_config_for_request(self, override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """基于默认配置生成“本次请求”的临时配置，不回写到实例状态。"""
        cfg = deepcopy(self._default_conf)
        if not override:
            return cfg
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
        return cfg

    @staticmethod
    def _normalize_w(weights_init: List[float]) -> np.ndarray:
        w = np.array(weights_init, dtype=float)
        w = np.maximum(w, 0.0)
        s = w.sum()
        return (w / s) if s > 0 else np.ones_like(w) / len(w)

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
    def _parse_date(s: str) -> Optional[datetime]:
        if s is None:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(str(s), fmt)
            except Exception:
                continue
        return None

    @staticmethod
    def _winsorize_ratio(x: float, low=0.0, high=5.0) -> float:
        if math.isnan(x):
            return 0.0
        return max(low, min(high, x))

    @staticmethod
    def _renorm(v: np.ndarray) -> np.ndarray:
        v = np.maximum(v, 0.0)
        s = v.sum()
        return v / s if s > 0 else np.ones_like(v) / len(v)

    # ---------- 单月延迟 ----------
    def _one_month_delay_days(self, actual_val, legal_val) -> Tuple[float, bool]:
        """
        返回：(正延迟天数, 是否缺失)
        若任一日期缺失或解析失败 => 缺失 True，天数记 0
        """
        # 兼容传 list/JSON 的情况：取第一对
        def _first(v):
            if isinstance(v, str):
                try:
                    arr = json.loads(v)
                    if isinstance(arr, list) and arr:
                        return str(arr[0])
                except Exception:
                    return v
            if isinstance(v, list) and v:
                return str(v[0])
            return v

        a = _first(actual_val)
        l = _first(legal_val)
        da, dl = self._parse_date(a), self._parse_date(l)
        if not da or not dl:
            return 0.0, True
        diff = (da - dl).days
        return (float(diff) if diff > 0 else 0.0), False

    # ---------- 指标 & 缺失 ----------
    def _compute_indicators(self, row_like: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, bool]]:
        """
        返回：(指标字典, 缺失标记字典)
        缺失标记包含：base_missing/head_missing/delay_missing/ticket_missing
        """
        c = cfg["cols"]
        d = cfg["date_fields"]

        base = self._safe_float(row_like.get(c["base"]))
        head = self._safe_int(row_like.get(c["head"]))
        tax_salary = self._safe_float(row_like.get(c["tax_salary"]))
        tax_head = self._safe_int(row_like.get(c["tax_head"]))
        tickets = self._safe_float(row_like.get(c["tickets"]))

        actual_one = row_like.get(d["actual_one"])
        legal_one  = row_like.get(d["legal_one"])

        s2b  = cfg["salary_to_base_factor"]
        mode = cfg.get("comparison_mode", "total")

        # —— 基数差异比例（支持 total / per_capita 两种口径）——
        base_missing = False
        if mode == "total":
            denom = (tax_salary * s2b) if (tax_salary == tax_salary and tax_salary > 0) else float("nan")
            if denom == denom and denom > 0 and base == base:
                base_ratio = abs(base - denom) / denom
            else:
                base_ratio = 0.0
                base_missing = True
        else:
            # 人均对比
            tax_base = (tax_salary / max(1, tax_head)) * s2b if tax_salary == tax_salary else float("nan")
            if tax_base and tax_base > 0 and base == base:
                base_ratio = abs(base - tax_base) / tax_base
            else:
                base_ratio = 0.0
                base_missing = True

        # —— 人数差异比例 ——（需 tax_head 可用）
        if tax_head > 0:
            head_ratio = abs(head - tax_head) / float(tax_head)
            head_missing = False
        else:
            head_ratio = 0.0
            head_missing = True

        # —— 单月延迟 ——（任一日期缺失则记缺失）
        delay_days, delay_missing = self._one_month_delay_days(actual_one, legal_one)

        # —— 有效工单 ——（NaN 记缺失）
        if math.isnan(tickets):
            tickets_val = 0.0
            ticket_missing = True
        else:
            tickets_val = float(tickets)
            ticket_missing = False

        # 轻度截尾
        base_ratio = self._winsorize_ratio(base_ratio)
        head_ratio = self._winsorize_ratio(head_ratio)

        indic = {
            "base_ratio": float(base_ratio),
            "head_ratio": float(head_ratio),
            "delay_days": float(delay_days),
            "tickets":    float(tickets_val),
        }
        miss = {
            "base_missing": base_missing,
            "head_missing": head_missing,
            "delay_missing": delay_missing,
            "ticket_missing": ticket_missing,
        }
        return indic, miss

    def _normalize_scores(self, indic: Dict[str, float], cfg: Dict[str, Any]) -> Dict[str, float]:
        T = cfg["thresholds"]
        return {
            "S_base":   min(1.0, indic["base_ratio"] / max(1e-9, T["base_ratio"])),
            "S_head":   min(1.0, indic["head_ratio"] / max(1e-9, T["head_ratio"])),
            "S_delay":  min(1.0, indic["delay_days"] / max(1e-9, T["delay_days"])),
            "S_ticket": min(1.0, indic["tickets"]    / max(1e-9, T["tickets"])),
        }

    # ---------- 规则直判 ----------
    def _hard_judgement(self, indic: Dict[str, float], cfg: Dict[str, Any]) -> Tuple[bool, List[str]]:
        H = cfg["hard_limits"]
        hits: List[str] = []
        if indic["base_ratio"] >= H["base_ratio"]: hits.append("基数差异过大")
        if indic["head_ratio"] >= H["head_ratio"]: hits.append("人数差异过大")
        if indic["delay_days"] >= H["delay_days"]: hits.append("延迟天数过长")
        if indic["tickets"]    >= H["tickets"]:    hits.append("有效工单过多")
        return (len(hits) > 0, hits)

    # ---------- 计算 RiskScore（命中项权重相对放大 + 缺失项权重=0） ----------
    def _risk_score_with_boost_and_missing(self,
                                           S: Dict[str, float],
                                           hits: List[str],
                                           miss: Dict[str, bool],
                                           w0_used: np.ndarray,
                                           cfg: Dict[str, Any]) -> Tuple[float, np.ndarray]:
        """
        返回：(RiskScore, 最终权重向量 w_used)
        - 基于传入的 w0_used
        - 缺失项：对应权重置 0
        - 命中项：对应权重 *= weight_amp_factor
        - 归一化后与 S 点积得到 0~1，再 ×100
        """
        w = w0_used.astype(float).copy()
        amp = float(cfg.get("weight_amp_factor", 3.0))

        idx_map = {"base": 0, "head": 1, "delay": 2, "ticket": 3}
        if miss.get("base_missing"):   w[idx_map["base"]] = 0.0
        if miss.get("head_missing"):   w[idx_map["head"]] = 0.0
        if miss.get("delay_missing"):  w[idx_map["delay"]] = 0.0
        if miss.get("ticket_missing"): w[idx_map["ticket"]] = 0.0

        hit_map = {"基数差异过大": 0, "人数差异过大": 1, "延迟天数过长": 2, "有效工单过多": 3}
        for h in hits:
            if h in hit_map and w.sum() > 0:
                w[hit_map[h]] *= amp

        w_used = self._renorm(w)
        s_vec = np.array([S["S_base"], S["S_head"], S["S_delay"], S["S_ticket"]], dtype=float)
        score01 = float(np.dot(w_used, s_vec))
        return round(100.0 * score01, 4), w_used

    def _grade_by_score(self, score: float, cfg: Dict[str, Any]) -> int:
        g = cfg["grading"]
        if score >= g["high"]:
            return 2
        if score >= g["mid"]:
            return 1
        return 0

    # ---------- 对外：单条（显式传入 w0 与 cfg） ----------
    def score_one_with_w0(self, sample: Dict[str, Any], w0_used: np.ndarray, cfg: Dict[str, Any]) -> Dict[str, Any]:
        indic, miss = self._compute_indicators(sample, cfg)
        S = self._normalize_scores(indic, cfg)
        is_hard, hits = self._hard_judgement(indic, cfg)
        score, _ = self._risk_score_with_boost_and_missing(S, hits, miss, w0_used=w0_used, cfg=cfg)
        level = 2 if is_hard else self._grade_by_score(score, cfg)
        warn_msg = "、".join(hits) if is_hard else ""
        return {
            "指标值": indic,
            "归一化": S,
            "风险系数": score,
            "是否直判高风险": bool(is_hard),
            "直判命中规则": "、".join(hits),
            "风险等级": level,
            "预警信息": warn_msg,
            "缺失标记": miss
        }

    # ---------- 面向接口：JSON 负载（最终输出格式） ----------
    def evaluate_payload(self,
                         data: List[Dict[str, Any]],
                         config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        入参：
          - data: List[Dict] 每条记录的字段名需与 默认/覆盖 配置中的 cols/date_fields 一致
          - config: 可选的阈值或放大因子/口径覆盖；不传使用“默认配置”
        返回：
          {
            "status_code": 200/500,
            "result": [
              {
                "企业或个体id": ...,
                "风险等级": 2/1/0,  # 2高/1中/0低
                "RiskScore": float,
                "是否直判高风险": bool,
                "预警信息": "..."
              }, ...
            ],
            "message": "缺失项提示或错误信息；正常计算时为'计算成功'"
          }
        """
        try:
            # ✅ 本次请求的临时配置（不污染默认）
            cfg_used = self._merged_config_for_request(config)

            if not isinstance(data, list) or len(data) == 0:
                return {"status_code": 500, "result": [], "message": "入参为空或格式错误"}

            id_col = cfg_used["cols"]["id"]
            results: List[Dict[str, Any]] = []
            msg_lines: List[str] = []

            # 💡 每次请求即时生成默认权重（或来自 override 的权重）
            w0_used = self._normalize_w(cfg_used["weights_init"])

            # 每条评估
            for idx, rec in enumerate(data):
                try:
                    res = self.score_one_with_w0(rec, w0_used, cfg_used)

                    rid = rec.get(id_col, f"row_{idx}")
                    results.append({
                        "企业或个体id": rid,
                        "风险等级": res["风险等级"],
                        "RiskScore": float(res["风险系数"]),
                        "是否直判高风险": res["是否直判高风险"],
                        "预警信息": res["预警信息"] or ""
                    })

                    # 缺失项提示（写在 message，不放 result）
                    miss = res["缺失标记"]
                    miss_names = []
                    if miss.get("base_missing"):   miss_names.append("基数差异项（工资/基数口径数据缺失）")
                    if miss.get("head_missing"):   miss_names.append("人数差异项（纳税人数缺失）")
                    if miss.get("delay_missing"):  miss_names.append("延迟天数项（当月日期缺失）")
                    if miss.get("ticket_missing"): miss_names.append("工单项（有效工单缺失）")
                    if miss_names:
                        msg_lines.append(f"[{rid}] 缺失指标：{', '.join(miss_names)}（已自动将缺失项权重置0并重分配）")

                except Exception as e_row:
                    rid = rec.get(id_col, f"row_{idx}")
                    msg_lines.append(f"[{rid}] 计算异常：{repr(e_row)}")

            if not results:
                return {"status_code": 500, "result": [], "message": "无可计算记录"}

            final_msg = "计算成功" if not msg_lines else "；".join(msg_lines)
            return {"status_code": 200, "result": results, "message": final_msg}

        except Exception as e:
            return {"status_code": 500, "result": [], "message": f"系统异常：{repr(e)}"}


