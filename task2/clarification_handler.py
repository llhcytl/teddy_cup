"""
意图澄清处理器
当用户查询模糊时，主动询问澄清
"""
import re
from typing import Dict, Any, Optional, List
from enum import Enum


class AmbiguityType(Enum):
    """模糊类型"""
    NO_COMPANY = "no_company"  # 缺少公司
    NO_YEAR = "no_year"  # 缺少年份
    NO_FIELD = "no_field"  # 缺少字段
    MULTIPLE_POSSIBLE = "multiple_possible"  # 多种可能


class ClarificationHandler:
    """意图澄清处理器"""

    # 公司列表
    COMPANIES = ["金花股份", "华润三九"]

    # 支持的年份范围
    YEARS = [2022, 2023, 2024, 2025]

    # 支持的报告期
    PERIODS = ["年度", "半年度", "一季度", "三季度"]

    # 字段映射
    FIELD_MAPPING = {
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

    def __init__(self):
        """初始化"""
        self.pending_clarifications: Dict[str, Any] = {}

    def detect_ambiguity(self, question: str) -> List[AmbiguityType]:
        """
        检测问题中的模糊点

        Args:
            question: 用户问题

        Returns:
            模糊类型列表
        """
        ambiguities = []

        # 1. 检查是否缺少公司
        has_company = any(
            company in question or str(code) in question
            for company, code in [("金花", "600080"), ("华润", "000999")]
        )
        # 如果问题中完全没有公司相关词，则认为模糊
        # 但如果是"两家公司"这类说法，则不模糊
        if not has_company and "两家" not in question and "全部" not in question and "所有" not in question:
            ambiguities.append(AmbiguityType.NO_COMPANY)

        # 2. 检查是否缺少年份
        has_year = bool(re.search(r'20(22|23|24|25)', question))
        # 如果没有明确的年份，且不是"最新"、"最近"这类说法
        if not has_year and "最新" not in question and "最近" not in question:
            ambiguities.append(AmbiguityType.NO_YEAR)

        # 3. 检查是否缺少字段
        has_field = any(keyword in question for keyword in self.FIELD_MAPPING.keys())
        if not has_field:
            ambiguities.append(AmbiguityType.NO_FIELD)

        return ambiguities

    def generate_clarification_question(self, ambiguities: List[AmbiguityType]) -> str:
        """
        生成澄清问题

        Args:
            ambiguities: 模糊类型列表

        Returns:
            澄清问题
        """
        if not ambiguities:
            return ""

        questions = []

        for ambiguity in ambiguities:
            if ambiguity == AmbiguityType.NO_COMPANY:
                questions.append(f"请问您要查询哪家公司的数据？(支持: {'/'.join(self.COMPANIES)})")
            elif ambiguity == AmbiguityType.NO_YEAR:
                questions.append(f"请问您要查询哪一年的数据？(支持: {', '.join(map(str, self.YEARS))})")
            elif ambiguity == AmbiguityType.NO_FIELD:
                field_list = "、".join(list(self.FIELD_MAPPING.keys())[:5])
                questions.append(f"请问您要查询什么指标？(支持: {field_list}等)")

        return "\n".join(questions)

    def clarify_with_user(self, question: str, ambiguities: List[AmbiguityType]) -> Dict[str, Any]:
        """
        与用户交互以澄清意图

        Args:
            question: 原始问题
            ambiguities: 模糊类型列表

        Returns:
            澄清后的信息
        """
        clarification_data = {
            "original_question": question,
            "ambiguities": ambiguities,
            "clarified": False
        }

        print("\n" + "=" * 50)
        print("您的查询有些地方不够明确，请补充以下信息:")
        print("=" * 50)

        # 收集澄清信息
        for ambiguity in ambiguities:
            if ambiguity == AmbiguityType.NO_COMPANY:
                company = self._ask_company()
                clarification_data["company"] = company
            elif ambiguity == AmbiguityType.NO_YEAR:
                year = self._ask_year()
                clarification_data["year"] = year
            elif ambiguity == AmbiguityType.NO_FIELD:
                field = self._ask_field()
                clarification_data["field"] = field

        clarification_data["clarified"] = True
        return clarification_data

    def _ask_company(self) -> str:
        """询问公司"""
        while True:
            response = input("\n请输入公司名称 (金花股份/华润三九): ").strip()
            if "金花" in response or "600080" in response:
                return "金花股份"
            elif "华润" in response or "000999" in response:
                return "华润三九"
            elif "两家" in response or "全部" in response:
                return "all"
            else:
                print("请输入有效的公司名称")

    def _ask_year(self) -> int:
        """询问年份"""
        while True:
            response = input(f"\n请输入年份 ({'/'.join(map(str, self.YEARS))}): ").strip()
            try:
                year = int(response)
                if year in self.YEARS:
                    return year
                else:
                    print(f"请输入{self.YEARS[0]}-{self.YEARS[-1]}之间的年份")
            except ValueError:
                print("请输入有效的年份")

    def _ask_field(self) -> str:
        """询问字段"""
        field_list = list(self.FIELD_MAPPING.keys())
        while True:
            print(f"\n支持的指标: {'/'.join(field_list[:6])}")
            response = input("请输入要查询的指标: ").strip()
            for keyword in field_list:
                if keyword in response:
                    return keyword
            print("请输入有效的指标名称")

    def reconstruct_question(self, original: str, clarification: Dict[str, Any]) -> str:
        """
        根据澄清信息重构问题

        Args:
            original: 原始问题
            clarification: 澄清信息

        Returns:
            重构后的问题
        """
        reconstructed = original

        # 替换公司
        if "company" in clarification:
            company = clarification["company"]
            if company == "all":
                reconstructed = f"两家公司{reconstructed}"
            else:
                reconstructed = f"{company}{reconstructed}"

        # 替换年份
        if "year" in clarification:
            year = clarification["year"]
            reconstructed += f"{year}年"

        # 替换字段
        if "field" in clarification:
            field = clarification["field"]
            reconstructed += f"{field}"

        return reconstructed

    def should_clarify(self, question: str) -> bool:
        """
        判断是否需要澄清

        Args:
            question: 用户问题

        Returns:
            是否需要澄清
        """
        # 如果问题太短，可能需要澄清
        if len(question) < 5:
            return True

        ambiguities = self.detect_ambiguity(question)

        # 如果有多个模糊点，建议澄清
        return len(ambiguities) >= 2


# 测试
if __name__ == "__main__":
    handler = ClarificationHandler()

    test_questions = [
        "营业收入是多少？",  # 缺少公司和年份
        "金花股份的净利润",  # 缺少年份
        "2024年的总资产",  # 缺少公司
        "金花股份2024年营业收入",  # 完整
        "两家公司2024年对比"  # 完整
    ]

    for q in test_questions:
        print(f"\n问题: {q}")
        ambiguities = handler.detect_ambiguity(q)
        if ambiguities:
            print(f"模糊点: {[a.value for a in ambiguities]}")
            print(f"澄清问题: {handler.generate_clarification_question(ambiguities)}")
        else:
            print("[OK] 问题清晰")
