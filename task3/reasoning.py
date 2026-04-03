# main.py
import pandas as pd
from typing import List, Dict
from config import config
from knowledge_base import knowledge_base
from planner import planner
from reasoning import Reasoning


class SmartQAAgent:
    def __init__(self):
        self.config = config
        self.kb = knowledge_base
        self.planner = planner

    def auto_validate(self, final_answer: str, sub_results: List[Dict]) -> bool:
        """校验完整性、合理性、准确性，返回是否通过，若不通过可在答案中追加警告"""
        # 1. 完整性：检查是否有子任务结果为空或失败
        for res in sub_results:
            if not res["result"]:
                print(f"校验警告：子任务{res['task_id']}结果为空")
                return False
        # 2. 合理性：如果答案包含数字，检查是否超出合理范围（示例）
        import re
        numbers = re.findall(r'\d+\.?\d*', final_answer)
        for num in numbers:
            val = float(num)
            if val > 1e12 or val < -1e12:
                print(f"校验警告：数值{val}超出合理范围")
                return False
        # 3. 准确性：可对比历史数据或跨任务一致性（略）
        return True

    def synthesize_answer(self, query: str, sub_results: List[Dict]) -> str:
        """将子任务结果合成为自然语言回答"""
        parts = []
        for res in sub_results:
            if res["type"] == "sql" and res["result"]:
                # 假设结果是一个列表，每个元素是字典
                first_row = res["result"][0]
                value = list(first_row.values())[0] if first_row else "无数据"
                parts.append(f"{res['description']}为{value}")
            elif res["type"] == "unstructured" and res["result"]:
                # 取第一个检索片段的前80字
                snippet = res["result"][0]["text"][:80] + "..."
                parts.append(f"研报观点：{snippet}")
            elif res["type"] == "comparison" and res["result"]:
                parts.append(f"对比结论：{res['result']}")
        if not parts:
            return "未找到相关信息。"
        return "；".join(parts)

    def answer_question(self, query: str) -> Dict:
        """处理单个问题，返回 {answer, attribution}"""
        reasoning = Reasoning()

        # 1. 解析意图
        intents = self.planner.parse_intents(query)
        reasoning.record_step(
            step_name="意图解析",
            input_data=query,
            output_data=intents,
            source="规则匹配引擎",
            reasoning=f"根据正则规则匹配到意图：{intents}"
        )

        # 2. 分解任务
        tasks = self.planner.decompose_tasks(intents, query)
        reasoning.record_step(
            step_name="任务分解",
            input_data=intents,
            output_data=[t["description"] for t in tasks],
            source="任务模板库",
            reasoning=f"生成{len(tasks)}个子任务，依赖关系为{[t['dependencies'] for t in tasks]}"
        )

        # 3. 执行子任务
        sub_results = self.planner.execute_tasks(tasks)
        for res in sub_results:
            reasoning.record_step(
                step_name=f"执行任务: {res['description']}",
                input_data=res["description"],
                output_data=res["result"][:2] if res["result"] else [],
                source=res["source"],
                reasoning=f"通过{res['type']}方式获得{len(res['result'])}条结果"
            )

        # 4. 合成答案
        answer = self.synthesize_answer(query, sub_results)

        # 5. 自动校验
        if not self.auto_validate(answer, sub_results):
            answer += " [警告：结果可能不完整或异常，请核实]"

        # 6. 生成归因文本
        attribution = reasoning.get_trace_text()

        return {"answer": answer, "attribution": attribution}

    def close(self):
        self.config.close()


def main():
    # 读取附件6的问题（假设文件名为 "附件6.xlsx"，包含列 'question_id', 'question_text'）
    questions_df = pd.read_excel("data/附件6.xlsx")
    agent = SmartQAAgent()

    output_records = []
    for idx, row in questions_df.iterrows():
        qid = row['question_id']
        qtext = row['question_text']
        print(f"处理问题 {qid}: {qtext}")
        result = agent.answer_question(qtext)
        output_records.append({
            "问题ID": qid,
            "答案": result["answer"],
            "归因分析": result["attribution"]
        })

    # 按附件7表5格式输出
    output_df = pd.DataFrame(output_records)
    output_df.to_excel("output_表5.xlsx", index=False)
    print("所有问题处理完成，结果已保存至 output_表5.xlsx")

    agent.close()


if __name__ == "__main__":
    main()