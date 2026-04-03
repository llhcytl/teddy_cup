"""
财报智能问数助手 - 命令行界面
支持多轮对话、历史记录、结果展示、可视化图表、意图澄清
"""
import sys
import os
from typing import List, Dict, Any
from text2sql import Text2SQL
from visualization import ChartGenerator, DataAnalyzer
from clarification_handler import ClarificationHandler


class ConversationHistory:
    """对话历史管理"""

    def __init__(self, max_history: int = 20):
        """初始化"""
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history

    def add(self, question: str, sql: str, result: Dict[str, Any]):
        """添加对话记录"""
        self.history.append({
            "question": question,
            "sql": sql,
            "result": result
        })
        # 限制历史长度
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get(self, n: int = 5) -> List[Dict[str, Any]]:
        """获取最近n条历史"""
        return self.history[-n:]

    def clear(self):
        """清空历史"""
        self.history = []

    def show(self, n: int = 5):
        """显示历史记录"""
        recent = self.get(n)
        if not recent:
            print("暂无历史记录")
            return

        print(f"\n=== 最近{len(recent)}条对话 ===")
        for i, item in enumerate(recent, 1):
            print(f"\n[{i}] 问题: {item['question']}")
            print(f"    SQL: {item['sql']}")
            if item['result'].get('success'):
                count = item['result'].get('count', 0)
                print(f"    结果: {count}条记录")
            else:
                print(f"    结果: 查询失败")


class ResultFormatter:
    """结果格式化器"""

    @staticmethod
    def format_table(data: List[Dict]) -> str:
        """格式化为表格"""
        if not data:
            return "无数据"

        # 获取所有列名
        columns = list(data[0].keys())

        # 计算每列宽度
        col_widths = {}
        for col in columns:
            col_widths[col] = max(
                len(str(col)),
                max(len(str(row.get(col, ""))) for row in data)
            )

        # 构建分隔线
        separator = "+" + "+".join("-" * (col_widths[col] + 2) for col in columns) + "+"

        # 构建表头
        header = "|" + "|".join(f" {col.ljust(col_widths[col])} " for col in columns) + "|"

        # 构建数据行
        rows = []
        for row in data:
            row_str = "|" + "|".join(
                f" {str(row.get(col, '')).ljust(col_widths[col])} " for col in columns
            ) + "|"
            rows.append(row_str)

        # 组合
        result = [separator, header, separator]
        result.extend(rows)
        result.append(separator)

        return "\n".join(result)

    @staticmethod
    def format_summary(data: List[Dict]) -> str:
        """格式化为摘要"""
        if not data:
            return "无数据"

        lines = []
        for i, row in enumerate(data, 1):
            line_parts = [f"[{i}]"]
            for key, value in row.items():
                if value is not None:
                    line_parts.append(f"{key}={value}")
            lines.append(" ".join(line_parts))

        return "\n".join(lines)

    @staticmethod
    def format_json(data: List[Dict]) -> str:
        """格式化为JSON"""
        import json
        return json.dumps(data, ensure_ascii=False, indent=2)


class FinancialQAAssistant:
    """财报智能问数助手"""

    def __init__(self, use_llm: bool = False, model_path: str = None, enable_chart: bool = True, enable_clarify: bool = True):
        """初始化助手"""
        self.text2sql = Text2SQL(use_llm=use_llm, model_path=model_path)
        self.history = ConversationHistory()
        self.formatter = ResultFormatter()
        self.chart_generator = ChartGenerator() if enable_chart else None
        self.data_analyzer = DataAnalyzer() if enable_chart else None
        self.enable_chart = enable_chart
        self.clarification_handler = ClarificationHandler() if enable_clarify else None
        self.enable_clarify = enable_clarify
        self.chart_dir = "charts"
        self._ensure_chart_dir()

        print("=" * 60)
        print("     财报智能问数助手")
        print("=" * 60)
        print("\n支持的查询类型:")
        print("  - 营业收入、净利润等业绩指标")
        print("  - 资产负债情况")
        print("  - 现金流量")
        print("  - 多公司对比")
        print("\n支持的公司: 金花股份(600080)、华润三九(000999)")
        print("\n命令:")
        print("  history / h  - 查看历史记录")
        print("  clear / c    - 清空历史")
        print("  chart / ch   - 为最近查询生成图表")
        print("  export / e   - 导出最近结果")
        print("  quit / q     - 退出")
        print("=" * 60)

    def _ensure_chart_dir(self):
        """确保图表目录存在"""
        if not os.path.exists(self.chart_dir):
            os.makedirs(self.chart_dir)
            print(f"[OK] 已创建图表目录: {self.chart_dir}/")

    def query(self, question: str) -> Dict[str, Any]:
        """执行查询"""
        result = self.text2sql.query(question)

        # 保存历史
        self.history.add(question, result.get("sql", ""), result)

        return result

    def query_with_clarification(self, question: str) -> Dict[str, Any]:
        """执行查询（带意图澄清）"""
        actual_question = question

        # 检查是否需要澄清
        if self.enable_clarify and self.clarification_handler:
            ambiguities = self.clarification_handler.detect_ambiguity(question)

            # 如果有多个模糊点，主动澄清
            if len(ambiguities) >= 2:
                clarification = self.clarification_handler.clarify_with_user(question, ambiguities)
                if clarification.get("clarified"):
                    actual_question = self.clarification_handler.reconstruct_question(
                        question, clarification
                    )
                    print(f"\n[澄清] 解析问题为: {actual_question}")

        # 执行查询
        result = self.query(actual_question)

        # 在历史中保存原始问题
        result["original_question"] = question

        return result

    def display_result(self, result: Dict[str, Any]):
        """显示结果"""
        print("\n" + "=" * 60)

        if not result.get("success"):
            print(f"[ERROR] 查询失败: {result.get('error', '未知错误')}")
            print("=" * 60)
            return

        data = result.get("data", [])
        count = result.get("count", 0)
        sql = result.get("sql", "")
        question = result.get("question", "")

        print(f"[OK] 查询成功 (共{count}条记录)")
        print(f"\nSQL语句:\n{sql}")
        print(f"\n查询结果:")

        if count == 0:
            print("  (无数据)")
        elif count <= 10:
            # 少量数据显示表格
            print(self.formatter.format_table(data))
        else:
            # 大量数据显示前5条
            print(f"  (显示前5条，共{count}条)")
            print(self.formatter.format_table(data[:5]))

        # 提示生成图表
        if self.enable_chart and count > 0:
            print(f"\n[提示] 输入 'chart' 或 'ch' 可为本次查询生成图表")

        print("=" * 60)

    def generate_chart_for_last_query(self):
        """为最近查询生成图表"""
        if not self.history.history:
            print("[ERROR] 暂无查询记录")
            return

        last = self.history.history[-1]
        question = last["question"]
        data = last["result"].get("data", [])

        if not data:
            print("[ERROR] 最近查询无数据，无法生成图表")
            return

        print(f"\n正在为查询生成图表...")
        print(f"问题: {question}")

        # 获取图表建议
        chart_type = self.data_analyzer.suggest_chart_type(data, question)
        chart_params = self.data_analyzer.extract_fields_for_chart(data, question)

        print(f"建议图表类型: {chart_type}")

        # 生成图表
        try:
            if chart_type == "bar":
                img = self.chart_generator.generate_bar_chart(
                    data,
                    chart_params['x_field'],
                    chart_params['y_field'],
                    chart_params['title']
                )
            elif chart_type == "line":
                img = self.chart_generator.generate_line_chart(
                    data,
                    chart_params['x_field'],
                    chart_params['y_field'],
                    chart_params.get('group_field'),
                    chart_params['title']
                )
            elif chart_type == "comparison":
                img = self.chart_generator.generate_comparison_chart(
                    data,
                    chart_params.get('group_field', 'stock_abbr'),
                    chart_params['y_field'],
                    chart_params['title']
                )
            elif chart_type == "pie":
                img = self.chart_generator.generate_pie_chart(
                    data,
                    chart_params['x_field'],
                    chart_params['y_field'],
                    chart_params['title']
                )
            else:
                # 默认使用柱状图
                img = self.chart_generator.generate_bar_chart(
                    data,
                    chart_params['x_field'],
                    chart_params['y_field'],
                    chart_params['title']
                )

            # 保存图表
            import base64
            filename = f"{self.chart_dir}/chart_{len(self.history.history)}.png"
            with open(filename, "wb") as f:
                f.write(base64.b64decode(img))

            print(f"[OK] 图表已保存到: {filename}")
            print(f"[提示] 可以使用图片查看器打开该文件")

        except Exception as e:
            print(f"[ERROR] 图表生成失败: {e}")

    def export_last_result(self):
        """导出最近结果"""
        if not self.history.history:
            print("[ERROR] 暂无结果可导出")
            return

        last = self.history.history[-1]
        data = last["result"].get("data", [])

        if not data:
            print("[ERROR] 最近查询无数据")
            return

        filename = f"query_result_{len(self.history.history)}.json"
        try:
            import json
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"[OK] 结果已导出到: {filename}")
        except Exception as e:
            print(f"[ERROR] 导出失败: {e}")

    def run(self):
        """运行交互式界面"""
        while True:
            try:
                # 获取用户输入
                user_input = input("\n请输入问题 > ").strip()

                if not user_input:
                    continue

                # 处理命令
                cmd = user_input.lower()

                if cmd in ["quit", "q", "exit"]:
                    print("\n感谢使用，再见!")
                    break

                elif cmd in ["history", "h"]:
                    self.history.show()

                elif cmd in ["clear", "c"]:
                    self.history.clear()
                    self.text2sql.reset_context()  # 同时重置上下文
                    print("✓ 历史记录已清空")

                elif cmd in ["chart", "ch"]:
                    self.generate_chart_for_last_query()

                elif cmd in ["export", "e"]:
                    self.export_last_result()

                else:
                    # 执行查询（带意图澄清）
                    result = self.query_with_clarification(user_input)
                    self.display_result(result)

            except KeyboardInterrupt:
                print("\n\n使用 'quit' 或 'q' 退出")
            except Exception as e:
                print(f"[ERROR] 发生错误: {e}")

        # 清理
        self.text2sql.close()

    def close(self):
        """关闭连接"""
        self.text2sql.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="财报智能问数助手")
    parser.add_argument("--llm", action="store_true", help="使用LLM生成SQL")
    parser.add_argument("--model", type=str, help="LLM模型路径")

    args = parser.parse_args()

    # 创建助手
    assistant = FinancialQAAssistant(
        use_llm=args.llm,
        model_path=args.model
    )

    # 运行
    assistant.run()


if __name__ == "__main__":
    main()
