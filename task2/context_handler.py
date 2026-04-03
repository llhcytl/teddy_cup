"""
多轮对话上下文处理器
处理代词、省略、指代等问题
"""
import re
from typing import Dict, Any, Optional, List


class ContextHandler:
    """对话上下文处理器"""

    # 代词和指代词映射
    PRONOUNS = {
        "它": "company",  # 指代公司
        "他": "company",
        "这家": "company",
        "那家": "company",
        "该公司": "company",
        "这个": "company",
        "那个": "company",
        "其": "company"
    }

    # 时间指代词
    TIME_REFERENCES = {
        "上一年": "previous_year",
        "去年": "previous_year",
        "前一年": "previous_year",
        "下一年": "next_year",
        "今年": "current_year",
        "当年": "current_year",
        "同年度": "same_year",
        "同年": "same_year"
    }

    # 数量指代词
    QUANTITY_REFERENCES = {
        "两家公司": ["金花股份", "华润三九"],
        "两家": ["金花股份", "华润三九"],
        "全部": ["金花股份", "华润三九"],
        "所有": ["金花股份", "华润三九"]
    }

    def __init__(self):
        """初始化上下文处理器"""
        self.context: Dict[str, Any] = {}

    def extract_context(self, question: str, sql_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        从问题和SQL结果中提取上下文

        Args:
            question: 用户问题
            sql_result: SQL查询结果

        Returns:
            上下文信息
        """
        context = {
            "question": question,
            "companies": self._extract_companies(question),
            "year": self._extract_year(question),
            "period": self._extract_period(question),
            "fields": self._extract_fields(question)
        }

        # 从SQL结果中获取更多信息
        if sql_result.get("success") and sql_result.get("data"):
            data = sql_result["data"][0]
            context["last_companies"] = data.get("stock_abbr", "")
            context["last_year"] = data.get("report_year", "")
            context["last_period"] = data.get("report_period", "")

        return context

    def _extract_companies(self, question: str) -> List[str]:
        """提取公司名称"""
        companies = []

        if "金花" in question or "600080" in question:
            companies.append("金花股份")
        if "华润" in question or "000999" in question:
            companies.append("华润三九")

        return companies if companies else []

    def _extract_year(self, question: str) -> Optional[int]:
        """提取年份"""
        match = re.search(r'20(22|23|24|25)', question)
        if match:
            return int(match.group(0))
        return None

    def _extract_period(self, question: str) -> Optional[str]:
        """提取报告期"""
        if "年度" in question:
            return "FY"
        elif "半年度" in question or "中期" in question:
            return "HY"
        elif "一季度" in question or "Q1" in question:
            return "Q1"
        elif "三季度" in question or "Q3" in question:
            return "Q3"
        return None

    def _extract_fields(self, question: str) -> List[str]:
        """提取字段名"""
        fields = []

        field_keywords = {
            "营业收入": "total_operating_revenue",
            "净利润": "net_profit",
            "每股收益": "eps",
            "总资产": "asset_total_assets",
            "负债": "liability_total_liabilities",
            "权益": "equity_total_equity",
            "经营现金流": "operating_cf_net_amount",
            "投资现金流": "investing_cf_net_amount",
            "筹资现金流": "financing_cf_net_amount",
            "营业利润": "operating_profit"
        }

        for keyword, field in field_keywords.items():
            if keyword in question:
                fields.append(field)

        return fields

    def resolve_reference(self, current_question: str,
                         previous_context: Dict[str, Any]) -> str:
        """
        解析指代关系，将当前问题转换为完整问题

        Args:
            current_question: 当前问题
            previous_context: 上一次对话的上下文

        Returns:
            解析后的完整问题
        """
        if not previous_context:
            return current_question

        resolved = current_question
        has_reference = False
        last_question = previous_context.get("question", "")

        # 1. 处理公司指代
        for pronoun, _ in self.PRONOUNS.items():
            if pronoun in current_question:
                has_reference = True
                last_company = previous_context.get("last_companies", "")
                if last_company:
                    resolved = resolved.replace(pronoun, last_company)
                    break

        # 2. 处理时间指代
        for time_ref, ref_type in self.TIME_REFERENCES.items():
            if time_ref in current_question:
                has_reference = True
                last_year = previous_context.get("last_year", "")
                if last_year:
                    if ref_type == "previous_year":
                        resolved = resolved.replace(time_ref, str(last_year - 1))
                    elif ref_type == "next_year":
                        resolved = resolved.replace(time_ref, str(last_year + 1))
                    elif ref_type == "same_year":
                        resolved = resolved.replace(time_ref, str(last_year))
                    break

        # 3. 处理数量指代
        for qty_ref, companies in self.QUANTITY_REFERENCES.items():
            if qty_ref in current_question:
                has_reference = True
                if len(companies) == 2:
                    resolved = resolved.replace(qty_ref, "金花股份和华润三九")
                break

        # 4. 处理省略情况（如"它去年的呢？" - 需要从上一次问题中提取字段）
        if "呢" in current_question or "是多少" in current_question:
            # 从上一次问题中提取字段名
            last_fields = self._extract_fields(last_question)
            if last_fields and not self._extract_fields(current_question):
                has_reference = True
                # 将字段名添加到当前问题
                for field_name, keyword in {
                    "total_operating_revenue": "营业收入",
                    "net_profit": "净利润",
                    "eps": "每股收益",
                    "asset_total_assets": "总资产"
                }.items():
                    if field_name in last_fields and keyword not in resolved:
                        resolved = resolved.replace("呢", f"{keyword}呢")
                        resolved = resolved.replace("是多少", f"{keyword}是多少")
                        break

        # 5. 处理纯省略（只有字段名）
        if len(current_question) < 15:
            # 短问题，可能是省略了公司和年份
            if not self._extract_companies(current_question):
                has_reference = True
                last_company = previous_context.get("last_companies", "")
                if last_company:
                    resolved = f"{last_company}{resolved}"

        if has_reference:
            print(f"[上下文] 解析问题: {current_question}")
            print(f"[上下文] 解析为: {resolved}")

        return resolved

    def is_followup_question(self, question: str) -> bool:
        """
        判断是否为追问

        Args:
            question: 用户问题

        Returns:
            是否为追问
        """
        # 检查是否包含指代词
        for pronoun in self.PRONOUNS.keys():
            if pronoun in question:
                return True

        # 检查是否包含时间指代
        for time_ref in self.TIME_REFERENCES.keys():
            if time_ref in question:
                return True

        # 检查是否为短问题（可能是省略）
        if len(question) < 10:
            return True

        return False


# 测试
if __name__ == "__main__":
    handler = ContextHandler()

    # 模拟第一次对话
    q1 = "金花股份2024年的营业收入是多少？"
    print(f"问题1: {q1}")

    # 模拟第一次的上下文
    context1 = {
        "question": q1,
        "last_companies": "金花股份",
        "last_year": 2024,
        "last_period": "FY"
    }

    # 测试追问
    followups = [
        "它去年的营业收入呢？",
        "上一年是多少？",
        "它2023年的净利润",
        "华润三九的呢"
    ]

    for q in followups:
        resolved = handler.resolve_reference(q, context1)
        is_followup = handler.is_followup_question(q)
        print(f"\n追问: {q}")
        print(f"是否追问: {is_followup}")
        print(f"解析后: {resolved}")
