# config.py
import sqlite3
from typing import List, Dict, Any


class Config:
    def __init__(self):
        # 结构化数据库路径（假设已通过任务一构建好）
        self.db_path = "data/stock.db"

        # 非结构化研报文件路径（附件5）
        self.individual_report_path = "data/个股研报.txt"
        self.sector_report_path = "data/行业研报.txt"

        # 向量检索参数
        self.embedding_model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        self.top_k_unstructured = 3

        # 其他配置
        self.debug = True

        # 连接数据库
        self._conn = None
        self._connect_db()

    def _connect_db(self):
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

    def execute_query(self, sql: str) -> List[Dict]:
        """执行SQL查询，返回字典列表"""
        cursor = self._conn.execute(sql)
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()


# 全局单例
config = Config()