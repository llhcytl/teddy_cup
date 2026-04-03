"""
数据可视化模块
支持多种图表类型：柱状图、折线图、饼图等
"""
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from typing import List, Dict, Any, Optional
import io
import base64

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False


class ChartGenerator:
    """图表生成器"""

    def __init__(self):
        """初始化"""
        self.fig_size = (10, 6)
        self.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                      '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

    def generate_bar_chart(self, data: List[Dict], x_field: str, y_field: str,
                          title: str = "", xlabel: str = "", ylabel: str = "", save_path: str = None) -> str:
        """
        生成柱状图

        Args:
            data: 数据列表
            x_field: X轴字段
            y_field: Y轴字段
            title: 图表标题
            xlabel: X轴标签
            ylabel: Y轴标签

        Returns:
            Base64编码的图片
        """
        if not data:
            return self._generate_empty_chart("无数据")

        fig, ax = plt.subplots(figsize=self.fig_size)

        x_values = [str(row.get(x_field, '')) for row in data]
        # 处理 None 值
        y_values = []
        for row in data:
            y_value = row.get(y_field)
            if y_value is not None:
                try:
                    y_values.append(float(y_value))
                except (ValueError, TypeError):
                    y_values.append(0.0)
            else:
                y_values.append(0.0)

        bars = ax.bar(x_values, y_values, color=self.colors[:len(x_values)])

        # 添加数值标签
        for bar, y in zip(bars, y_values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{y:,.0f}',
                   ha='center', va='bottom', fontsize=9)

        ax.set_xlabel(xlabel or x_field)
        ax.set_ylabel(ylabel or y_field)
        ax.set_title(title)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        return self._fig_to_base64(fig, save_path)

    def generate_line_chart(self, data: List[Dict], x_field: str, y_field: str,
                           group_field: Optional[str] = None,
                           title: str = "", xlabel: str = "", ylabel: str = "", save_path: str = None) -> str:
        """
        生成折线图

        Args:
            data: 数据列表
            x_field: X轴字段
            y_field: Y轴字段
            group_field: 分组字段（可选）
            title: 图表标题
            xlabel: X轴标签
            ylabel: Y轴标签

        Returns:
            Base64编码的图片
        """
        if not data:
            return self._generate_empty_chart("无数据")

        fig, ax = plt.subplots(figsize=self.fig_size)

        if group_field:
            # 分组绘图
            groups = {}
            for row in data:
                group = row.get(group_field, 'unknown')
                if group not in groups:
                    groups[group] = {'x': [], 'y': []}
                groups[group]['x'].append(str(row.get(x_field, '')))
                # 处理 None 值
                y_value = row.get(y_field)
                if y_value is not None:
                    try:
                        groups[group]['y'].append(float(y_value))
                    except (ValueError, TypeError):
                        groups[group]['y'].append(0.0)
                else:
                    groups[group]['y'].append(0.0)

            # 排序x轴
            for group in groups.values():
                sorted_pairs = sorted(zip(group['x'], group['y']))
                group['x'], group['y'] = zip(*sorted_pairs) if sorted_pairs else ([], [])

            # 绘制每组数据
            for i, (group_name, group_data) in enumerate(groups.items()):
                ax.plot(group_data['x'], group_data['y'],
                       marker='o', label=group_name,
                       color=self.colors[i % len(self.colors)], linewidth=2)

            ax.legend()
        else:
            # 单一折线
            x_values = []
            y_values = []
            for row in data:
                x_values.append(str(row.get(x_field, '')))
                # 处理 None 值
                y_value = row.get(y_field)
                if y_value is not None:
                    try:
                        y_values.append(float(y_value))
                    except (ValueError, TypeError):
                        y_values.append(0.0)
                else:
                    y_values.append(0.0)

            # 排序
            sorted_pairs = sorted(zip(x_values, y_values))
            x_values, y_values = zip(*sorted_pairs) if sorted_pairs else ([], [])

            ax.plot(x_values, y_values, marker='o', color=self.colors[0], linewidth=2)

            # 添加数值标签
            for x, y in zip(x_values, y_values):
                ax.text(x, y, f'{y:,.0f}', ha='center', va='bottom', fontsize=9)

        ax.set_xlabel(xlabel or x_field)
        ax.set_ylabel(ylabel or y_field)
        ax.set_title(title)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        return self._fig_to_base64(fig, save_path)

    def generate_pie_chart(self, data: List[Dict], label_field: str,
                          value_field: str, title: str = "", save_path: str = None) -> str:
        """
        生成饼图

        Args:
            data: 数据列表
            label_field: 标签字段
            value_field: 数值字段
            title: 图表标题

        Returns:
            Base64编码的图片
        """
        if not data:
            return self._generate_empty_chart("无数据")

        fig, ax = plt.subplots(figsize=self.fig_size)

        labels = [str(row.get(label_field, '')) for row in data]
        values = [float(row.get(value_field, 0)) for row in data]

        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                          colors=self.colors[:len(labels)],
                                          startangle=90)

        # 美化文字
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')

        ax.set_title(title)
        plt.tight_layout()

        return self._fig_to_base64(fig, save_path)

    def generate_comparison_chart(self, data: List[Dict], category_field: str,
                                 value_field: str, title: str = "", save_path: str = None) -> str:
        """
        生成对比柱状图（适用于多公司对比）

        Args:
            data: 数据列表
            category_field: 分类字段（如公司名）
            value_field: 数值字段
            title: 图表标题

        Returns:
            Base64编码的图片
        """
        if not data:
            return self._generate_empty_chart("无数据")

        fig, ax = plt.subplots(figsize=self.fig_size)

        # 按分类分组
        groups = {}
        for row in data:
            category = str(row.get(category_field, ''))
            period = str(row.get('report_period', ''))
            key = f"{category}_{period}"
            if category not in groups:
                groups[category] = []
            groups[category].append((period, float(row.get(value_field, 0))))

        # 绘制
        categories = list(groups.keys())
        periods = sorted(set(row[0] for rows in groups.values() for row in rows))

        x = np.arange(len(periods))
        width = 0.35

        for i, (category, category_data) in enumerate(groups.items()):
            values = [dict(category_data).get(p, 0) for p in periods]
            offset = (i - len(categories)/2 + 0.5) * width
            ax.bar(x + offset, values, width, label=category,
                  color=self.colors[i % len(self.colors)])

        ax.set_xlabel('报告期')
        ax.set_ylabel(value_field)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(periods)
        ax.legend()
        plt.tight_layout()

        return self._fig_to_base64(fig, save_path)

    def generate_multi_metric_chart(self, data: List[Dict],
                                   x_field: str,
                                   y_fields: List[str],
                                   title: str = "", save_path: str = None) -> str:
        """
        生成多指标图表

        Args:
            data: 数据列表
            x_field: X轴字段
            y_fields: Y轴字段列表
            title: 图表标题

        Returns:
            Base64编码的图片
        """
        if not data or not y_fields:
            return self._generate_empty_chart("无数据")

        fig, ax = plt.subplots(figsize=self.fig_size)

        x_values = [str(row.get(x_field, '')) for row in data]

        for i, field in enumerate(y_fields):
            y_values = [float(row.get(field, 0)) for row in data]
            ax.plot(x_values, y_values, marker='o', label=field,
                   color=self.colors[i % len(self.colors)], linewidth=2)

        ax.set_xlabel(x_field)
        ax.set_ylabel('数值')
        ax.set_title(title)
        ax.legend()
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        return self._fig_to_base64(fig, save_path)

    def _fig_to_base64(self, fig, save_path: str = None) -> str:
        """将图表转为Base64编码，可选保存到文件"""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()

        # 如果指定了保存路径，也保存为文件
        if save_path:
            fig.savefig(save_path, format='png', dpi=100, bbox_inches='tight')
            print(f"[图表已保存] {save_path}")

        plt.close(fig)
        return image_base64

    def _generate_empty_chart(self, message: str, save_path: str = None) -> str:
        """生成空图表"""
        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.text(0.5, 0.5, message, ha='center', va='center',
               fontsize=16, color='gray')
        ax.axis('off')
        return self._fig_to_base64(fig, save_path)

    def save_chart(self, data: List[Dict], chart_type: str, save_path: str,
                   x_field: str = None, y_field: str = None,
                   group_field: str = None, title: str = "") -> bool:
        """
        直接保存图表到文件（推荐使用）

        Args:
            data: 数据列表
            chart_type: 图表类型 (bar, line, pie, comparison)
            save_path: 保存路径
            x_field: X轴字段
            y_field: Y轴字段
            group_field: 分组字段
            title: 图表标题

        Returns:
            是否成功
        """
        try:
            if chart_type == "bar":
                self.generate_bar_chart(data, x_field, y_field, title, save_path=save_path)
            elif chart_type == "line":
                self.generate_line_chart(data, x_field, y_field, group_field, title, save_path=save_path)
            elif chart_type == "comparison":
                self.generate_comparison_chart(data, group_field, y_field, title, save_path=save_path)
            elif chart_type == "pie":
                self.generate_pie_chart(data, x_field, y_field, title, save_path=save_path)
            return True
        except Exception as e:
            print(f"[ERROR] 图表保存失败: {e}")
            return False


class DataAnalyzer:
    """数据分析器"""

    @staticmethod
    def suggest_chart_type(data: List[Dict], question: str) -> str:
        """
        根据数据和问题建议图表类型

        Returns:
            chart_type: bar, line, pie, comparison, multi_metric
        """
        if not data:
            return "bar"

        question_lower = question.lower()

        # 对比类问题
        if "对比" in question or "比较" in question or "两家" in question:
            return "comparison"

        # 占比类问题
        if "占比" in question or "比例" in question:
            return "pie"

        # 检测是否为时间序列数据（季度/年度数据应该用折线图）
        if 'report_period' in data[0] or 'report_year' in data[0]:
            # 如果有多条记录且有时间字段，优先用折线图
            if len(data) > 1:
                return "line"

        # 趋势类问题（显式关键词）
        if "趋势" in question or "变化" in question:
            return "line"

        # 多指标
        if len(data) > 1 and len(data[0]) > 4:
            return "multi_metric"

        # 默认柱状图（适合单一分类对比）
        return "bar"

    @staticmethod
    def extract_fields_for_chart(data: List[Dict], question: str) -> Dict[str, Any]:
        """
        从问题和数据中提取图表需要的字段

        Returns:
            {
                'x_field': str,
                'y_field': str or list,
                'group_field': str or None,
                'title': str
            }
        """
        if not data:
            return {'x_field': '', 'y_field': '', 'title': '无数据'}

        fields = list(data[0].keys())

        # 根据问题推断字段
        question_lower = question.lower()

        # X轴字段
        if 'report_period' in fields:
            x_field = 'report_period'
        elif 'report_year' in fields and 'report_period' in fields:
            x_field = 'report_period'  # 需要组合year和period
        else:
            x_field = fields[0]

        # Y轴字段 - 找数值字段
        numeric_fields = [f for f in fields if f not in
                         ['id', 'serial_number', 'stock_code', 'stock_abbr',
                          'report_period', 'report_year', 'created_at', 'updated_at']]

        if not numeric_fields:
            y_field = fields[-1]
        else:
            # 根据问题关键词选择
            if "营业收入" in question and "total_operating_revenue" in numeric_fields:
                y_field = "total_operating_revenue"
            elif "净利润" in question:
                y_field = "net_profit_10k_yuan" if "net_profit_10k_yuan" in numeric_fields else "net_profit"
            elif "总资产" in question and "asset_total_assets" in numeric_fields:
                y_field = "asset_total_assets"
            elif "现金流" in question and "operating_cf_net_amount" in numeric_fields:
                y_field = "operating_cf_net_amount"
            else:
                y_field = numeric_fields[0]

        # 分组字段
        group_field = 'stock_abbr' if 'stock_abbr' in fields and len(data) > 4 else None

        # 标题
        title = question

        return {
            'x_field': x_field,
            'y_field': y_field,
            'group_field': group_field,
            'title': title
        }


# 测试
if __name__ == "__main__":
    import os
    from text2sql import Text2SQL

    # 确保图表目录存在
    chart_dir = "charts"
    if not os.path.exists(chart_dir):
        os.makedirs(chart_dir)
        print(f"[OK] 已创建图表目录: {chart_dir}/")

    generator = ChartGenerator()
    analyzer = DataAnalyzer()

    # 测试查询
    t2s = Text2SQL()

    test_cases = [
        "金花股份2024年各季度营业收入",
        "两家公司2024年总资产对比",
        "华润三九净利润趋势"
    ]

    print("=" * 60)
    print("图表生成测试")
    print("=" * 60)

    for i, question in enumerate(test_cases, 1):
        print(f"\n[{i}] 问题: {question}")
        print("-" * 50)

        result = t2s.query(question)
        if not result.get("success") or not result.get("data"):
            print("无数据")
            continue

        data = result["data"]
        count = result.get("count", 0)
        print(f"查询成功: {count}条记录")

        # 获取图表建议
        chart_type = analyzer.suggest_chart_type(data, question)
        chart_params = analyzer.extract_fields_for_chart(data, question)

        print(f"图表类型: {chart_type}")

        # 保存图表
        filename = f"{chart_dir}/test_{i}.png"
        success = generator.save_chart(
            data,
            chart_type,
            filename,
            x_field=chart_params['x_field'],
            y_field=chart_params['y_field'],
            group_field=chart_params.get('group_field'),
            title=chart_params['title']
        )

        if success:
            print(f"图表已保存: {filename}")
        else:
            print("图表保存失败")

    print("\n" + "=" * 60)
    print(f"完成！请查看 {chart_dir}/ 文件夹")
    print("=" * 60)

    t2s.close()
