"""
Text2SQL 模块 - 自然语言转SQL
支持多种实现方式：
1. 基于规则的备用方案
2. LLM生成（Qwen/DeepSeek等）
3. API调用方式
4. 多轮对话上下文支持
"""
import re
import json
import pymysql
from typing import Optional, List, Dict, Any
from config import DB_CONFIG, DATABASE_SCHEMA, MODEL_CONFIG
from context_handler import ContextHandler


class RuleBasedSQLGenerator:
    """基于规则的SQL生成器（备用方案）"""

    def __init__(self):
        """初始化规则生成器"""
        # 表名映射
        self.table_mapping = {
            "核心业绩": "core_performance_indicators_sheet",
            "业绩指标": "core_performance_indicators_sheet",
            "资产负债": "balance_sheet",
            "现金流量": "cash_flow_sheet",
            "利润": "income_sheet"
        }

        # 字段映射
        self.field_mapping = {
            "营业收入": "total_operating_revenue",
            "净利润": "net_profit_10k_yuan",
            "每股收益": "eps",
            "总资产": "asset_total_assets",
            "负债": "liability_total_liabilities",
            "权益": "equity_total_equity",
            "经营现金流": "operating_cf_net_amount",
            "投资现金流": "investing_cf_net_amount",
            "筹资现金流": "financing_cf_net_amount",
            "营业利润": "operating_profit"
        }

        # 表名和字段对应关系
        self.table_fields = {
            "core_performance_indicators_sheet": ["total_operating_revenue", "net_profit_10k_yuan", "eps"],
            "balance_sheet": ["asset_total_assets", "liability_total_liabilities", "equity_total_equity"],
            "cash_flow_sheet": ["operating_cf_net_amount", "investing_cf_net_amount", "financing_cf_net_amount"],
            "income_sheet": ["total_operating_revenue", "operating_profit", "net_profit"]
        }

        # 公司映射
        self.company_mapping = {
            "金花": "金花股份",
            "600080": "金花股份",
            "华润": "华润三九",
            "000999": "华润三九"
        }

    def generate(self, question: str) -> str:
        """
        根据问题生成SQL

        Args:
            question: 用户问题

        Returns:
            SQL语句
        """
        question = question.lower()

        # 解析问题
        companies = self._extract_companies(question)
        fields = self._extract_fields(question)
        periods = self._extract_periods(question)
        table = self._determine_table(question, fields)

        # 构建SQL
        sql = self._build_sql(companies, fields, periods, table)
        return sql

    def _extract_companies(self, question: str) -> List[str]:
        """提取公司名称"""
        companies = []
        for key, value in self.company_mapping.items():
            if key in question:
                companies.append(value)
        return companies if companies else ["金花股份", "华润三九"]

    def _extract_fields(self, question: str) -> List[str]:
        """提取字段"""
        fields = []
        for key, value in self.field_mapping.items():
            if key in question:
                fields.append(value)
        return fields if fields else ["*"]

    def _extract_periods(self, question: str) -> Dict[str, Any]:
        """提取报告期，返回year和period条件"""
        condition = {}

        # 提取年份
        year_match = re.search(r'20(22|23|24|25)', question)
        if year_match:
            year = int(year_match.group(0))
            condition["report_year"] = year

            # 判断报告类型
            if "年度" in question:
                condition["report_period"] = ["FY"]
            elif "半年度" in question or "中期" in question:
                condition["report_period"] = ["HY"]
            elif "一季度" in question or "q1" in question:
                condition["report_period"] = ["Q1"]
            elif "三季度" in question or "q3" in question:
                condition["report_period"] = ["Q3"]
            else:
                # 默认查询所有
                condition["report_period"] = ["FY", "HY", "Q1", "Q3"]

        return condition

    def _determine_table(self, question: str, fields: List[str]) -> str:
        """确定查询表"""
        # 根据字段确定表
        for field in fields:
            if field in ["operating_cf_net_amount", "investing_cf_net_amount", "financing_cf_net_amount"]:
                return "cash_flow_sheet"
            elif field in ["asset_total_assets", "liability_total_liabilities", "equity_total_equity"]:
                return "balance_sheet"
            elif field == "operating_profit":
                return "income_sheet"
            elif field in ["total_operating_revenue", "net_profit_10k_yuan", "eps"]:
                # 默认用核心业绩指标表
                return "core_performance_indicators_sheet"

        # 根据问题关键词确定表
        for key, table in self.table_mapping.items():
            if key in question:
                return table

        return "core_performance_indicators_sheet"  # 默认表

    def _build_sql(self, companies: List[str], fields: List[str],
                   periods: Dict[str, Any], table: str) -> str:
        """构建SQL语句"""
        # 选择字段
        if "*" in fields:
            select_fields = "stock_abbr, report_year, report_period, *"
        else:
            # 根据表确定实际字段名
            actual_fields = []
            for f in fields:
                # 从对应表中查找实际字段名
                for tab, flds in self.table_fields.items():
                    if f in flds and tab == table:
                        actual_fields.append(f)
                        break
            select_fields = ", ".join(["stock_abbr", "report_year", "report_period"] + list(set(actual_fields)))

        # 构建查询
        sql = f"SELECT {select_fields} FROM {table}"

        # WHERE条件
        conditions = []

        # 公司条件 - 使用stock_abbr
        if len(companies) == 1:
            conditions.append(f"stock_abbr = '{companies[0]}'")
        elif len(companies) > 1:
            company_list = ", ".join([f"'{c}'" for c in companies])
            conditions.append(f"stock_abbr IN ({company_list})")

        # 年份条件
        if "report_year" in periods:
            conditions.append(f"report_year = {periods['report_year']}")

        # 期间条件
        if "report_period" in periods:
            period_list = periods["report_period"]
            if len(period_list) == 1:
                conditions.append(f"report_period = '{period_list[0]}'")
            else:
                period_str = ", ".join([f"'{p}'" for p in period_list])
                conditions.append(f"report_period IN ({period_str})")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        # 排序
        sql += " ORDER BY stock_abbr, report_year, report_period"

        return sql + ";"


class DatabaseQuerier:
    """数据库查询执行器"""

    def __init__(self, db_config: Optional[Dict] = None):
        """初始化查询器"""
        self.db_config = db_config or DB_CONFIG
        self.connection = None

    def connect(self) -> bool:
        """连接数据库"""
        try:
            self.connection = pymysql.connect(**self.db_config)
            print("[OK] 数据库连接成功")
            return True
        except Exception as e:
            print(f"[ERROR] 数据库连接失败: {e}")
            return False

    def execute_query(self, sql: str) -> Optional[List[Dict]]:
        """执行查询"""
        if self.connection is None:
            if not self.connect():
                return None

        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
                return result
        except Exception as e:
            print(f"[ERROR] 查询执行失败: {e}")
            print(f"SQL: {sql}")
            return None

    def execute_sql_with_result(self, sql: str) -> Dict[str, Any]:
        """执行SQL并返回结构化结果"""
        result = self.execute_query(sql)
        if result is None:
            return {"success": False, "error": "查询失败"}
        if not result:
            return {"success": True, "data": [], "message": "未查询到数据"}

        return {
            "success": True,
            "data": result,
            "count": len(result),
            "sql": sql
        }

    def get_table_schema(self, table_name: str) -> Optional[List[Dict]]:
        """获取表结构"""
        sql = f"DESCRIBE {table_name}"
        return self.execute_query(sql)

    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()
            print("[OK] 数据库连接已关闭")


class Text2SQL:
    """Text2SQL转换器"""

    def __init__(self, use_llm: bool = False, model_path: str = None):
        """
        初始化Text2SQL

        Args:
            use_llm: 是否使用LLM生成SQL
            model_path: LLM模型路径
        """
        self.use_llm = use_llm
        self.rule_generator = RuleBasedSQLGenerator()
        self.querier = DatabaseQuerier()
        self.context_handler = ContextHandler()
        self.last_context = None  # 保存上一次查询的上下文

        # LLM相关（后续实现）
        self.model = None
        self.tokenizer = None

        if use_llm and model_path:
            self._load_llm(model_path)

    def _load_llm(self, model_path: str):
        """加载LLM模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            print(f"正在加载模型: {model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True, local_files_only=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype="auto",
                device_map="auto",
                trust_remote_code=True,
                local_files_only=True
            )
            print("[OK] 模型加载成功")
        except Exception as e:
            print(f"[ERROR] 模型加载失败: {e}")
            print("将使用规则生成器")
            self.use_llm = False

    def generate_sql(self, question: str) -> str:
        """
        生成SQL语句

        Args:
            question: 用户问题

        Returns:
            SQL语句
        """
        if self.use_llm and self.model:
            return self._llm_generate(question)
        else:
            return self.rule_generator.generate(question)

    def _llm_generate(self, question: str) -> str:
        """使用LLM生成SQL"""
        prompt = f"""根据以下数据库schema，将用户问题转换为MySQL查询语句。

{DATABASE_SCHEMA}

用户问题: {question}
- 用户问题【未指定具体报告期】（如：2024年营收）→ 不添加 report_period 条件，仅按年份查询
- 用户问题【明确指定】（如：2024年度/一季报）→ 再添加对应 report_period 条件
只输出SQL语句，不要有其他内容:"""

        try:
            messages = [
                {"role": "system", "content": "你是一个专业的SQL生成助手。"},
                {"role": "user", "content": prompt}
            ]

            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

            generated_ids = self.model.generate(
                inputs.input_ids,
                max_new_tokens=512,
                temperature=0.1,
                do_sample=False
            )

            response = self.tokenizer.decode(generated_ids[0][inputs.input_ids.shape[1]:],
                                            skip_special_tokens=True)

            return self._extract_sql(response)

        except Exception as e:
            print(f"LLM生成失败: {e}，使用规则生成器")
            return self.rule_generator.generate(question)

    def _extract_sql(self, response: str) -> str:
        """从响应中提取SQL"""
        response = response.strip()
        for keyword in ["SELECT", "select"]:
            idx = response.find(keyword)
            if idx != -1:
                sql = response[idx:]
                for stop in ["```", "说明", "\n\n"]:
                    stop_idx = sql.find(stop)
                    if stop_idx != -1:
                        sql = sql[:stop_idx]
                return sql.strip()
        return response

    def query(self, question: str, use_context: bool = True) -> Dict[str, Any]:
        """
        执行完整查询流程

        Args:
            question: 用户问题
            use_context: 是否使用上下文处理追问

        Returns:
            查询结果
        """
        actual_question = question

        # 处理上下文（追问）
        if use_context and self.last_context:
            actual_question = self.context_handler.resolve_reference(
                question, self.last_context
            )

        # 生成SQL
        sql = self.generate_sql(actual_question)

        # 执行查询
        result = self.querier.execute_sql_with_result(sql)

        # 添加SQL信息
        result["sql"] = sql
        result["question"] = question
        result["actual_question"] = actual_question  # 解析后的完整问题
        result["is_followup"] = (actual_question != question)

        # 保存上下文
        if result.get("success") and result.get("data"):
            self.last_context = self.context_handler.extract_context(
                actual_question, result
            )

        return result

    def reset_context(self):
        """重置上下文（清空历史）"""
        self.last_context = None

    def close(self):
        """关闭连接"""
        self.querier.close()


# 测试
if __name__ == "__main__":
    #t2s = Text2SQL(use_llm=False)
    t2s = Text2SQL(use_llm=True, model_path=MODEL_CONFIG["model_path"])
    test_questions = [
        "金花股份2024年的营业收入是多少？",
        "华润三九2024年度的净利润是多少？",
        "两家公司2024年的总资产对比",
        "华润三近2024年一季度经营现金流"
    ]

    for q in test_questions:
        print(f"\n问题: {q}")
        print("-" * 50)
        result = t2s.query(q)
        print(f"SQL: {result['sql']}")
        if result["success"]:
            print(f"结果: {result['count']}条记录")
            for row in result["data"]:
                print(row)

    t2s.close()
