# planner.py
import re
from typing import List, Dict, Any
from config import config
from knowledge_base import knowledge_base


class Planner:
    def __init__(self):
        # 意图识别规则（可扩展）
        self.intent_rules = {
            "financial_data": r"(营收|净利润|毛利率|ROE|市盈率|营业收入|利润)",
            "comparison": r"(对比|相比|高于|低于|大于|小于|优于|差于)",
            "trend": r"(趋势|增长|下降|同比|环比|变化)",
            "report_opinion": r"(研报|观点|评级|推荐|目标价|看好|看空)"
        }

    def parse_intents(self, query: str) -> List[str]:
        """返回识别到的意图列表"""
        intents = []
        for intent, pattern in self.intent_rules.items():
            if re.search(pattern, query):
                intents.append(intent)
        if not intents:
            intents = ["general"]
        return intents

    def decompose_tasks(self, intents: List[str], query: str) -> List[Dict]:
        """根据意图生成子任务列表，每个任务包含 id, type, params, dependencies"""
        tasks = []
        task_id = 0

        # 辅助函数：提取股票代码（假设6位数字）
        stock_code = self._extract_stock_code(query)
        # 提取指标
        metric = self._extract_metric(query)

        for intent in intents:
            if intent == "financial_data" and stock_code and metric:
                tasks.append({
                    "id": task_id,
                    "type": "sql",
                    "description": f"查询{stock_code}的{metric}",
                    "sql": f"SELECT {metric} FROM financial WHERE stock_code='{stock_code}'",
                    "dependencies": []
                })
                task_id += 1

            elif intent == "report_opinion":
                tasks.append({
                    "id": task_id,
                    "type": "unstructured",
                    "description": "检索研报观点",
                    "query_text": query,
                    "dependencies": []
                })
                task_id += 1

            elif intent == "comparison":
                # 对比任务依赖前面的数据任务
                tasks.append({
                    "id": task_id,
                    "type": "comparison",
                    "description": "对比分析",
                    "dependencies": [t["id"] for t in tasks if t["type"] in ("sql", "unstructured")]
                })
                task_id += 1

            # 其他意图类似...

        return tasks

    def execute_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """按依赖顺序执行子任务，返回结果列表（每个结果包含 task_id, result, source 等）"""
        # 简单拓扑排序执行
        executed_ids = set()
        results = []
        while len(executed_ids) < len(tasks):
            for task in tasks:
                if task["id"] in executed_ids:
                    continue
                if all(dep in executed_ids for dep in task["dependencies"]):
                    # 执行任务
                    if task["type"] == "sql":
                        res = config.execute_query(task["sql"])
                        source = "结构化数据库: financial表"
                    elif task["type"] == "unstructured":
                        res = knowledge_base.retrieve(task["query_text"])
                        source = "非结构化知识库: 研报向量检索"
                    elif task["type"] == "comparison":
                        # 依赖前面的结果进行简单比较
                        res = self._do_comparison(task, results)
                        source = "推理计算"
                    else:
                        res = []
                        source = "未知"

                    results.append({
                        "task_id": task["id"],
                        "type": task["type"],
                        "description": task["description"],
                        "result": res,
                        "source": source
                    })
                    executed_ids.add(task["id"])
        return results

    def _extract_stock_code(self, query: str) -> str:
        match = re.search(r'\b(\d{6})\b', query)
        return match.group(1) if match else ""

    def _extract_metric(self, query: str) -> str:
        mapping = {
            "营收": "revenue",
            "营业收入": "revenue",
            "净利润": "net_profit",
            "毛利率": "gross_margin",
            "ROE": "roe",
            "市盈率": "pe_ratio"
        }
        for key, val in mapping.items():
            if key in query:
                return val
        return ""

    def _do_comparison(self, task: Dict, previous_results: List[Dict]) -> str:
        """示例对比逻辑：比较查询到的数值与行业均值"""
        # 实际实现中需要根据 previous_results 中的 sql 结果进行计算
        return "对比结果：公司指标高于行业平均水平（基于研报观点）"


# 全局实例
planner = Planner()