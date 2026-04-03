# knowledge_base.py
import os
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


class KnowledgeBase:
    def __init__(self, config):
        self.config = config
        self.model = SentenceTransformer(config.embedding_model_name)
        self.index = None
        self.chunks = []  # 存储文本块内容
        self.metadata = []  # 存储每个块对应的来源文件及段落编号

        self._build_index()

    def _load_reports(self) -> str:
        """读取个股研报和行业研报，返回合并文本"""
        all_text = ""
        # 个股研报
        if os.path.exists(self.config.individual_report_path):
            with open(self.config.individual_report_path, 'r', encoding='utf-8') as f:
                all_text += "【个股研报】\n" + f.read() + "\n\n"
        # 行业研报
        if os.path.exists(self.config.sector_report_path):
            with open(self.config.sector_report_path, 'r', encoding='utf-8') as f:
                all_text += "【行业研报】\n" + f.read()
        return all_text

    def _chunk_text(self, text: str) -> List[str]:
        """简单分块：按双换行分隔段落，过滤空串"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        # 如果段落太长（>512 token），可以进一步切分，这里简化为直接返回
        return paragraphs

    def _build_index(self):
        """构建向量索引"""
        full_text = self._load_reports()
        self.chunks = self._chunk_text(full_text)
        if not self.chunks:
            print("警告：未加载到任何研报内容")
            return

        # 生成向量
        embeddings = self.model.encode(self.chunks, show_progress_bar=False)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(np.array(embeddings).astype('float32'))

        # 构建元数据（简单标记来源）
        for i, chunk in enumerate(self.chunks):
            if "【个股研报】" in chunk:
                source = "个股研报"
            elif "【行业研报】" in chunk:
                source = "行业研报"
            else:
                source = "未知"
            self.metadata.append({"source": source, "chunk_id": i})

    def retrieve(self, query: str, top_k: int = None) -> List[dict]:
        """检索最相关的研报片段，返回列表，每个元素包含 text 和 metadata"""
        if top_k is None:
            top_k = self.config.top_k_unstructured
        if self.index is None or not self.chunks:
            return []

        q_vec = self.model.encode([query])
        distances, indices = self.index.search(np.array(q_vec).astype('float32'), top_k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.chunks):
                results.append({
                    "text": self.chunks[idx],
                    "metadata": self.metadata[idx],
                    "score": float(distances[0][i])
                })
        return results


# 全局单例（需传入 config）
from config import config

knowledge_base = KnowledgeBase(config)