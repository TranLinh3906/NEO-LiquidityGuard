"""Conditional, non-predictive explanation for a completed calculation."""
from __future__ import annotations
from typing import Any


def explain(metrics: dict[str, Any], simulation: dict[str, Any] | None = None) -> str:
    if not metrics.get("is_eligible"): return "Không phân tích/mô phỏng được: " + "; ".join(metrics.get("rejection_reasons", []))
    parts = ["Chỉ số phản ánh ba mức sổ lệnh quan sát được, không phải dự báo giá hoặc khuyến nghị đầu tư."]
    if simulation and simulation.get("unfilled_qty"): parts.append("Khối lượng yêu cầu vượt độ sâu ba mức; phần chưa đáp ứng không được gán giá.")
    return " ".join(parts)
