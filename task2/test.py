# 直接复用你的类和函数，测试你的原SQL
import pymysql
from typing import Optional, List, Dict


# 你的数据库查询类（完整保留）
class DatabaseQuerier:
    def __init__(self):
        self.connection = None
        # 你的数据库配置（请补充你自己的DB_CONFIG）
        self.db_config = {
            "host": "localhost",
            "user": "root",
            "password": "340841",
            "database": "teddy_cup_financial",
            "port": 3306
        }

    def connect(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(**self.db_config)
            print("[OK] 数据库连接成功")
            return True
        except Exception as e:
            print(f"[ERROR] 数据库连接失败: {e}")
            return False

    # 你的原查询函数，一字不改！
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


# ===================== 测试你的原SQL =====================
if __name__ == '__main__':
    # 你的原SQL，一字不改！
    YOUR_SQL = """
    SELECT total_operating_revenue 
    FROM core_performance_indicators_sheet 
    WHERE stock_code = '600080' AND report_year = '2024';
    """

    querier = DatabaseQuerier()
    # 执行查询
    data = querier.execute_query(YOUR_SQL)

    # 打印结果，看能不能查到数据
    print("=" * 50)
    print(f"执行的SQL：\n{YOUR_SQL}")
    print("=" * 50)
    print(f"查询结果：{data}")
    print(f"结果类型：{type(data)}")
    if data is None:
        print("❌ 结果：SQL执行失败（语法/权限/表不存在）")
    elif len(data) == 0:
        print("✅ 结果：SQL执行成功，但【没有查到任何数据】")
    else:
        print(f"✅ 结果：查到 {len(data)} 条数据！")
        for row in data:
            print(f"营业收入：{row['total_operating_revenue']}")