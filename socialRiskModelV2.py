"""
socialModel.py（精简与修正版：仅 1/2/3 三项 + 覆盖逻辑修正 + 支持多组）
社保基金稽核风险模型（权重相对放大 + 缺失项权重置零 + 新接口：3个指标字典）

type 映射：
- 1: 人数差异比例（|社保实际缴纳人数 - 社保缴纳人数| / 社保缴纳人数） -> head_ratio
- 2: 单月延迟天数（max(本月社保缴费日期 - 本月法定社保缴费日期, 0)） -> delay_days
- 3: 有效工单数量（值越大越风险） -> tickets

输入支持两种模式：
1) 单组（推荐）：{"data": [ {type:1,...}, {type:2,...}, {type:3,...} ]}
2) 多组：{"data": [ [组1的3条], [组2的3条], ... ]}

覆盖规则（重要）：
- 只有当你在某个指标字典里**显式提供**了“直判阈值 / 当前项权重”时，才会覆盖默认配置；
- 否则沿用默认的 hard_limits / weights_init。
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from copy import deepcopy
import json
import math
import numpy as np
import pandas as pd


class SocialAuditModel2:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # —— 默认配置（仅保留 head_ratio / delay_days / tickets）——
        default_conf: Dict[str, Any] = {
            # 归一化阈值（超过视为1.0）
            "thresholds": {
                "head_ratio": 0.15,   # 人数差异比例满分阈值
                "delay_days": 8.0,    # 单月/多月平均延迟天数满分阈值
                "tickets":    3.0,    # 有效工单数量满分阈值
            },
            # 规则直判硬阈值（命中任一即高风险）
            "hard_limits": {
                "head_ratio": 0.15,
                "delay_days": 12.0,   # 单月/多月平均延迟天数直判阈值
                "tickets":    3.0,
            },
            # 非直判分级阈值（RiskScore 基于 0~100）
            "grading": {"high": 70, "mid": 40},

            # 单月日期字段名（type=2 用）；也支持数组或数组JSON字符串
            "date_fields": {
                "actual_one": "本月社保缴费日期",
                "legal_one":  "本月法定社保缴费日期",
            },

            # 初始权重（和=1）：[S_head, S_delay, S_ticket]
            "weights_init": [0.40, 0.30, 0.30],

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

    # === 新增：把“单个日期 / 列表 / JSON字符串列表”统一为 datetime 列表 ===
    @staticmethod
    def _parse_date_single(s: Any) -> Optional[datetime]:
        if s is None:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(str(s), fmt)
            except Exception:
                continue
        return None

    @classmethod
    def _coerce_date_list(cls, v: Any) -> List[datetime]:
        """
        输入可以是：
          - 单个日期字符串："2025-09-01"
          - 日期字符串列表：["2025-09-01","2025-09-05", ...]
          - JSON字符串形式的日期数组："[\"2025-09-01\",\"2025-09-05\"]"
        返回：已成功解析的 datetime 列表（失败/空 -> []）
        """
        if v is None:
            return []

        # 如果是字符串，尝试先按 JSON 数组解析；失败则当做单个日期字符串
        if isinstance(v, str):
            parsed = None
            try:
                j = json.loads(v)
                if isinstance(j, list):
                    parsed = j
            except Exception:
                parsed = None

            if parsed is None:
                dt = cls._parse_date_single(v)
                return [dt] if dt else []
            else:
                out: List[datetime] = []
                for item in parsed:
                    dt = cls._parse_date_single(item)
                    if dt:
                        out.append(dt)
                return out

        # 如果是列表，逐个解析
        if isinstance(v, list):
            out: List[datetime] = []
            for item in v:
                dt = cls._parse_date_single(item)
                if dt:
                    out.append(dt)
            return out

        # 其它类型：尝试当做单个日期
        dt = cls._parse_date_single(v)
        return [dt] if dt else []

    @staticmethod
    def _renorm(v: np.ndarray) -> np.ndarray:
        v = np.maximum(v, 0.0)
        s = v.sum()
        return v / s if s > 0 else np.ones_like(v) / len(v)

    # ---------- 单/月延迟（支持多月，取正延迟的平均天数） ----------
    def _avg_delay_days(self, actual_val, legal_val) -> Tuple[float, bool]:
        """
        返回：(正延迟天数的平均值, 是否缺失)
        - 支持单个日期或“多个日期”的数组（或其 JSON 字符串表示）
        - 对齐策略：按最小长度配对 actual[i] 与 legal[i]
        - delay = max((actual - legal).days, 0)；仅统计 >0 的天数
        - 若无任何有效配对，返回 (0.0, True)
        """
        actual_list = self._coerce_date_list(actual_val)
        legal_list  = self._coerce_date_list(legal_val)

        n = min(len(actual_list), len(legal_list))
        if n <= 0:
            return 0.0, True

        delays: List[float] = []
        for i in range(n):
            da, dl = actual_list[i], legal_list[i]
            if not da or not dl:
                continue
            d = (da - dl).days
            if d > 0:
                delays.append(float(d))

        if len(delays) == 0:
            # 有输入，但没有任何正延迟；业务上视作“无延迟数据有效”，仍标记缺失为 False？
            # 为了更稳妥：当存在有效日期配对但无正延迟时，返回 0.0 且 is_missing=False
            return 0.0, False

        avg_delay = float(np.mean(delays))
        return avg_delay, False

    # ---------- 归一化（基于阈值） ----------
    def _normalize_scores(self, indic: Dict[str, float], cfg: Dict[str, Any]) -> Dict[str, float]:
        T = cfg["thresholds"]
        return {
            "S_head":   min(1.0, indic.get("head_ratio", 0.0) / max(1e-9, T["head_ratio"])),
            "S_delay":  min(1.0, indic.get("delay_days", 0.0) / max(1e-9, T["delay_days"])),
            "S_ticket": min(1.0, indic.get("tickets", 0.0)    / max(1e-9, T["tickets"])),
        }

    # ---------- 规则直判 ----------
    def _hard_judgement(self, indic: Dict[str, float], cfg: Dict[str, Any]) -> Tuple[bool, List[str]]:
        H = cfg["hard_limits"]
        hits: List[str] = []
        if indic.get("head_ratio", 0.0) >= H["head_ratio"]: hits.append("人数差异过大")
        if indic.get("delay_days", 0.0) >= H["delay_days"]: hits.append("延迟天数过长")
        if indic.get("tickets", 0.0)    >= H["tickets"]:    hits.append("有效工单过多")
        return (len(hits) > 0, hits)

    # ---------- RiskScore（命中项权重相对放大 + 缺失项权重=0） ----------
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

        # 索引顺序：[head, delay, ticket]
        idx_map = {"head": 0, "delay": 1, "ticket": 2}
        if miss.get("head_missing"):   w[idx_map["head"]] = 0.0
        if miss.get("delay_missing"):  w[idx_map["delay"]] = 0.0
        if miss.get("ticket_missing"): w[idx_map["ticket"]] = 0.0

        hit_map = {"人数差异过大": 0, "延迟天数过长": 1, "有效工单过多": 2}
        for h in hits:
            if h in hit_map and w.sum() > 0:
                w[hit_map[h]] *= amp

        w_used = self._renorm(w)
        s_vec = np.array([S["S_head"], S["S_delay"], S["S_ticket"]], dtype=float)
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
    def _evaluate_one_group(self,
                            data_group: List[Dict[str, Any]],
                            cfg_used: Dict[str, Any]) -> Dict[str, Any]:
        """
        对一组（3条，type=1/2/3）的指标进行评估，返回单组结果与消息。
        """
        # 指标&缺失标记
        indic: Dict[str, float] = {}
        miss: Dict[str, bool] = {
            "head_missing": True,
            "delay_missing": True,
            "ticket_missing": True,
        }

        # 初始权重从配置克隆（顺序 [head, delay, ticket]）
        weights_init = list(cfg_used["weights_init"])

        # 直判阈值覆盖（仅在显式传入时才覆盖）
        hard_overrides: Dict[str, float] = {}

        # 解析各项
        for item in data_group:
            t = item.get("type")

            # --- 权重：仅当显式提供时覆盖 ---
            if "当前项权重" in item and str(item.get("当前项权重")) != "":
                w_val = self._safe_float(item.get("当前项权重"))
                if not math.isnan(w_val):
                    if t == 1:   weights_init[0] = float(w_val)
                    elif t == 2: weights_init[1] = float(w_val)
                    elif t == 3: weights_init[2] = float(w_val)

            # --- 直判阈值：仅当显式提供时覆盖 ---
            if "直判阈值" in item and str(item.get("直判阈值")) != "":
                thr_val = self._safe_float(item.get("直判阈值"))
                if not math.isnan(thr_val):
                    if t == 1:   hard_overrides["head_ratio"] = float(thr_val)
                    elif t == 2: hard_overrides["delay_days"] = float(thr_val)
                    elif t == 3: hard_overrides["tickets"]    = float(thr_val)

            # --- 指标值计算 ---
            if t == 1:
                # 人数差异比例
                head = self._safe_int(item.get("社保实际缴纳人数"))
                tax_head = self._safe_int(item.get("社保缴纳人数"))
                if tax_head > 0:
                    val = abs(head - tax_head) / float(tax_head)
                    miss["head_missing"] = False
                else:
                    val = 0.0
                    miss["head_missing"] = True
                indic["head_ratio"] = float(val)

            elif t == 2:
                # 多月平均延迟天数（也兼容单月）
                actual_key = cfg_used["date_fields"]["actual_one"]
                legal_key  = cfg_used["date_fields"]["legal_one"]
                delay_avg, is_missing = self._avg_delay_days(
                    item.get(actual_key),
                    item.get(legal_key)
                )
                indic["delay_days"] = float(delay_avg)
                miss["delay_missing"] = bool(is_missing)

            elif t == 3:
                # 有效工单数量
                tickets = self._safe_float(item.get("有效工单数量"))
                if math.isnan(tickets):
                    indic["tickets"] = 0.0
                    miss["ticket_missing"] = True
                else:
                    indic["tickets"] = float(tickets)
                    miss["ticket_missing"] = False

            else:
                # 未知 type 忽略
                continue

        # 应用阈值覆盖
        cfg_tmp = deepcopy(cfg_used)
        cfg_tmp["hard_limits"].update(hard_overrides)

        # 若权重全为 0，则回退默认配置
        if sum(weights_init) <= 0:
            weights_init = list(cfg_used["weights_init"])

        # 归一化权重（初始）
        w0_used = self._normalize_w(weights_init)

        # 归一化各指标分数
        S = self._normalize_scores(indic, cfg_tmp)

        # 直判
        is_hard, hits = self._hard_judgement(indic, cfg_tmp)

        # 计算风控分（缺失置零 + 命中放大）
        score, _ = self._risk_score_with_boost_and_missing(
            S, hits, miss, w0_used=w0_used, cfg=cfg_tmp
        )
        level = 2 if is_hard else self._grade_by_score(score, cfg_tmp)

        # 缺失提示
        miss_names = []
        if miss.get("head_missing"):   miss_names.append("人数差异项（社保缴纳人数缺失）")
        if miss.get("delay_missing"):  miss_names.append("延迟天数项（日期缺失或无法匹配）")
        if miss.get("ticket_missing"): miss_names.append("工单项（有效工单数量缺失）")

        msg_parts = []
        if miss_names:
            msg_parts.append(f"缺失指标：{', '.join(miss_names)}（已将缺失项权重置0并重分配）")
        if is_hard and hits:
            msg_parts.append(f"直判命中：{'、'.join(hits)}")
        final_msg = "；".join(msg_parts) if msg_parts else "计算成功"

        return {
            "status_code": 200,
            "result": [{
                "风险等级": level,                   # 2高 / 1中 / 0低
                "RiskScore": score,                 # 0~100
                "是否直判高风险": bool(is_hard),
                "预警信息": "、".join(hits) if hits else ""
            }],
            "message": final_msg
        }

    # ---------- 面向接口：单组或多组 ----------
    def evaluate_payload(self,
                         payload_or_data: Union[Dict[str, Any], List[Dict[str, Any]]],
                         config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        入参（推荐）：
          单组：{"data": [ {type:1,...}, {type:2,...}, {type:3,...} ]}
          多组：{"data": [ [组1的3条], [组2的3条], ... ]}
        兼容：直接传 data list 也可（单组）。

        type=2 日期字段支持：
          - 单个字符串："2025-09-05"
          - 字符串数组：["2025-09-05","2025-10-05",...]
          - JSON数组字符串："[\"2025-09-05\",\"2025-10-05\"]"
        计算逻辑：按索引配对与法定日期比，取正延迟的平均值。
        """
        try:
            # 解析 data
            if isinstance(payload_or_data, dict):
                data = payload_or_data.get("data", None)
            else:
                data = payload_or_data

            if not isinstance(data, list) or len(data) == 0:
                return {"status_code": 500, "result": [], "message": "入参为空或格式错误，应为 {'data': [...]} 或直接传列表"}

            cfg_used = self._merged_config_for_request(config)

            # 多组模式：data 的第 1 个元素还是 list
            if isinstance(data[0], list):
                all_results = []
                messages = []
                for idx, group in enumerate(data):
                    res = self._evaluate_one_group(group, cfg_used)
                    # 给每组结果打上组号（可选）
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


# ---------------------------
# 可选：本地快速自测（运行本文件时）
# ---------------------------
if __name__ == "__main__":
    model = SocialAuditModel2()

    # —— 单组示例（不传阈值/权重 => 使用默认）——
    payload_single = {
        "data": [
            {"type": 1, "社保实际缴纳人数": 40, "社保缴纳人数": 42},
            # 单月示例
            {"type": 2, "本月社保缴费日期": "2025-09-05", "本月法定社保缴费日期": "2025-09-01"},
            {"type": 3, "有效工单数量": 3}
        ]
    }
    print("单组（单月）：")
    print(json.dumps(model.evaluate_payload(payload_single), ensure_ascii=False, indent=2))

    # —— 单组示例（多月平均，字符串数组）——
    payload_single_multi = {
        "data": [
            {"type": 1, "社保实际缴纳人数": 40, "社保缴纳人数": 42},
            {"type": 2,
             "本月社保缴费日期": ["2025-08-10", "2025-09-05", "2025-10-03"],
             "本月法定社保缴费日期": ["2025-08-01", "2025-09-01", "2025-10-08"]},
            {"type": 3, "有效工单数量": 2}
        ]
    }
    print("\n单组（多月平均）：")
    print(json.dumps(model.evaluate_payload(payload_single_multi), ensure_ascii=False, indent=2))

    # —— 多组示例（第二组显式覆盖阈值/权重 + 多月 JSON 字符串）——
    payload_multi = {
        "data": [
            [
                {"type": 1, "社保实际缴纳人数": 40, "社保缴纳人数": 42},
                {"type": 2,
                 "本月社保缴费日期": "[\"2025-09-05\",\"2025-10-05\"]",
                 "本月法定社保缴费日期": "[\"2025-09-01\",\"2025-10-01\"]"},
                {"type": 3, "有效工单数量": 3}
            ],
            [
                {"type": 1, "社保实际缴纳人数": 35, "社保缴纳人数": 42, "直判阈值": 0.2, "当前项权重": 0.5},
                {"type": 2,
                 "本月社保缴费日期": ["2025-09-10", "2025-10-12"],
                 "本月法定社保缴费日期": ["2025-09-01", "2025-10-01"],
                 "直判阈值": 10, "当前项权重": 0.3},
                {"type": 3, "有效工单数量": 4, "直判阈值": 4, "当前项权重": 0.2}
            ]
        ]
    }
    print("\n多组：")
    print(json.dumps(model.evaluate_payload(payload_multi), ensure_ascii=False, indent=2))