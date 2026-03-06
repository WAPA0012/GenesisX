"""Metabolic ledger for resource tracking.

Implements reserve/spend/refund tracking for:
- cpu_tokens (支持无限模式)
- io_ops
- net_bytes
- money
- risk_score
"""
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class ResourceBudget:
    """Budget limits for a resource.

    支持无限模式: 当 unlimited=True 时，不检查预算限制。
    """

    total: float
    reserved: float = 0.0
    spent: float = 0.0
    unlimited: bool = False  # 新增: 无限模式标志

    def available(self) -> float:
        """Get available (unreserved and unspent) budget."""
        if self.unlimited:
            return float('inf')  # 无限资源
        return max(0.0, self.total - self.reserved - self.spent)

    def remaining(self) -> float:
        """Get remaining (after spent)."""
        if self.unlimited:
            return float('inf')
        return max(0.0, self.total - self.spent)

    def can_reserve(self, amount: float) -> bool:
        """Check if amount can be reserved."""
        if self.unlimited:
            return True  # 无限模式，总是允许
        return self.available() >= amount

    def reserve(self, amount: float) -> bool:
        """Reserve amount if available."""
        if not self.can_reserve(amount):
            return False
        self.reserved += amount
        return True

    def spend(self, amount: float):
        """Spend amount (reduce reserved, increase spent)."""
        self.reserved = max(0.0, self.reserved - amount)
        self.spent += amount

    def refund(self, amount: float):
        """Refund amount (decrease spent, increase available)."""
        self.spent = max(0.0, self.spent - amount)

    def normalize(self) -> float:
        """Get normalized utilization [0,1]."""
        if self.unlimited:
            return 0.0  # 无限模式显示为0%使用
        if self.total == 0:
            return 0.0
        return min(1.0, self.spent / self.total)

    def to_dict(self) -> Dict[str, float]:
        """Serialize to dict."""
        return {
            "total": self.total,
            "reserved": self.reserved,
            "spent": self.spent,
            "available": self.available(),
            "remaining": self.remaining(),
            "utilization": self.normalize(),
            "unlimited": self.unlimited,
        }


class MetabolicLedger:
    """Central ledger for resource tracking and budget control.

    Implements reserve→spend→refund flow with budget limits.

    新增: 支持无限模式配置，可通过 unlimited_resources 设置哪些资源不受限制。
    """

    def __init__(
        self,
        budgets: Optional[Dict[str, float]] = None,
        unlimited_resources: Optional[Set[str]] = None
    ):
        """Initialize ledger with budgets.

        Args:
            budgets: Dict of resource_name -> total_budget
            unlimited_resources: 资源名称集合，这些资源将不受限制（默认: {'cpu_tokens'}）
        """
        # 默认: cpu_tokens 无限模式（GLM MAX 套餐够用）
        if unlimited_resources is None:
            unlimited_resources = {'cpu_tokens'}

        default_budgets = {
            "cpu_tokens": 100000.0,   # 即使有预算，unlimited=True 时也不检查
            "io_ops": 1000.0,
            "net_bytes": 10000000.0,  # 10MB
            "money": 10.0,  # $10
            "risk_score": 0.5,  # Max cumulative risk
        }

        if budgets:
            default_budgets.update(budgets)

        self.resources = {
            name: ResourceBudget(
                total=total,
                unlimited=(name in unlimited_resources)
            )
            for name, total in default_budgets.items()
        }

        self.unlimited_resources = unlimited_resources

    def set_unlimited(self, resource: str, unlimited: bool = True):
        """动态设置资源是否无限。

        Args:
            resource: 资源名称
            unlimited: True=无限制, False=启用预算限制
        """
        if resource in self.resources:
            self.resources[resource].unlimited = unlimited
            if unlimited:
                self.unlimited_resources.add(resource)
            else:
                self.unlimited_resources.discard(resource)

    def is_unlimited(self, resource: str) -> bool:
        """检查资源是否为无限模式."""
        return self.resources.get(resource, ResourceBudget(0)).unlimited

    def can_reserve(self, resource: str, amount: float) -> bool:
        """Check if amount can be reserved."""
        if resource not in self.resources:
            return False  # Unknown resources are not allowed (prevent unbounded spending)
        return self.resources[resource].can_reserve(amount)

    def reserve(self, resource: str, amount: float) -> bool:
        """Reserve amount if available."""
        if resource not in self.resources:
            return False  # Unknown resources are not allowed
        return self.resources[resource].reserve(amount)

    def spend(self, resource: str, amount: float):
        """Spend amount."""
        if resource not in self.resources:
            return
        self.resources[resource].spend(amount)

    def refund(self, resource: str, amount: float):
        """Refund amount."""
        if resource not in self.resources:
            return
        self.resources[resource].refund(amount)

    def check_all_non_negative(self) -> bool:
        """Check invariant: no negative remaining budgets."""
        return all(res.remaining() >= 0 for res in self.resources.values())

    def normalize_all(self) -> Dict[str, float]:
        """Get normalized utilization for all resources."""
        return {name: res.normalize() for name, res in self.resources.items()}

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        """Get snapshot of all resources."""
        return {name: res.to_dict() for name, res in self.resources.items()}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ledger to dict."""
        return self.snapshot()

    def from_dict(self, data: Dict[str, Any]):
        """Restore ledger from dict."""
        for name, res_data in data.items():
            if name in self.resources:
                self.resources[name].total = res_data.get("total", 100000.0)
                self.resources[name].reserved = res_data.get("reserved", 0.0)
                self.resources[name].spent = res_data.get("spent", 0.0)
