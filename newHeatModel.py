class NewHeatModelAnalysis:
    def __init__(self):
        self.default_weights = {
            "job_num": 2,
            "indeed_num": 4,
            "apply": 0.12,
            "collect": 0.08,
            "search": 0.06,
            "browse": 0.04,
        }
        self.scaling_factors = {
            "browse": 2000,
            "apply": 400,
            "collect": 200,
            "search": 1000
        }

    def entrance(self, body):
        message_logs = []

        try:
            raw_data = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
            avg_score_parts, med_score_parts, weights = [], [], []

            for item in raw_data:
                type_id = item.get("type")

                if type_id == 1:
                    job_num = item.get("this_job_num")
                    total = item.get("total")
                    indeed_job_num = item.get("indeed_job_num")

                    w1 = self._get_valid_weight(item.get("this_weight"), self.default_weights["job_num"])
                    w2 = self._get_valid_weight(item.get("indeed_weight"), self.default_weights["indeed_num"])
                    weights.extend([w1, w2])

                    job_ratio = 0
                    urgent_ratio = 0

                    if self._is_number(job_num) and self._is_number(total) and job_num > total:
                        message_logs.append("当前工种岗位数量不能大于总岗位数量，该项的权重无效，默认为0")
                    elif self._is_number(indeed_job_num) and self._is_number(job_num) and indeed_job_num > job_num:
                        message_logs.append("当前工种急需岗位不能大于当前工种岗位数量，该项的权重无效，默认为0")
                    else:
                        if self._is_number(job_num) and self._is_number(total) and total > 0:
                            job_ratio = job_num / total
                        else:
                            message_logs.append("job_ratio 字段无效，设为0")
                        if self._is_number(indeed_job_num) and self._is_number(job_num) and job_num > 0:
                            urgent_ratio = indeed_job_num / job_num
                        else:
                            message_logs.append("urgent_ratio 字段无效，设为0")

                    avg_score_parts.extend([w1 * job_ratio, w2 * urgent_ratio])
                    med_score_parts.extend([w1 * job_ratio, w2 * urgent_ratio])

                elif type_id in [2, 3, 4, 5]:
                    prefix = self._get_prefix(type_id)
                    avg_val = item.get(f"{prefix}_avg")
                    med_val = item.get(f"{prefix}_med")
                    weight = self._get_valid_weight(item.get("weight"), self.default_weights[prefix])
                    weights.append(weight)
                    scaling_factor = self.scaling_factors.get(prefix, 1)

                    avg = avg_val / scaling_factor if self._is_number(avg_val) else 0
                    med = med_val / scaling_factor if self._is_number(med_val) else 0

                    if not self._is_number(avg_val):
                        message_logs.append(f"type {type_id}: {prefix}_avg 无效，设为0")
                    if not self._is_number(med_val):
                        message_logs.append(f"type {type_id}: {prefix}_med 无效，设为0")

                    avg_score_parts.append(weight * avg)
                    med_score_parts.append(weight * med)

            total_weight = sum(weights)
            if total_weight == 0:
                return {
                    "status_code": 200,
                    "result": 0.0,
                    "message": "没有有效的权重，默认设为0"
                }

            hotness_avg = sum(avg_score_parts) / total_weight
            hotness_med = sum(med_score_parts) / total_weight
            final_score = (hotness_avg + hotness_med) / 2
            normalized_score = round(max(0.0, min(1.0, final_score)), 6)

            return {
                "status_code": 200,
                "result": normalized_score,
                "message": "计算成功" if not message_logs else "warning: " + "; ".join(message_logs)
            }

        except Exception as e:
            return {
                "status_code": 500,
                "result": 0.0,
                "message": f"发生未知错误，结果默认为0: {str(e)}"
            }

    def _get_prefix(self, type_id):
        return {
            2: "browse",
            3: "apply",
            4: "collect",
            5: "search"
        }.get(type_id, "")

    def _is_number(self, value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _get_valid_weight(self, val, default):
        return val if isinstance(val, (int, float)) and not isinstance(val, bool) else default