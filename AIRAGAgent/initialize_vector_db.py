#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化向量数据库，将数据文件加载到向量存储中
"""

from AIRAGAgent.rag.vector_store import VectorStoreService

def initialize_vector_database():
    """
    初始化向量数据库，加载所有文档
    """
    print("正在初始化向量数据库...")
    vs = VectorStoreService()
    
    print("开始加载文档到向量数据库...")
    vs.load_document()
    print("文档加载完成！")
    
    # 测试检索功能
    print("\n测试检索功能...")
    retriever = vs.get_retriever()
    
    # 使用一个简单的查询进行测试
    test_results = retriever.invoke("Word文档如何自动填充")

    if test_results:
        print(f"找到 {len(test_results)} 个相关文档片段:")
        for i, doc in enumerate(test_results):
            print(f"\n文档 {i+1}:")
            print(f"内容预览: {doc.page_content[:100]}...")
            print(f"元数据: {doc.metadata}")
    else:
        print("警告: 没有找到任何相关文档，请检查数据文件是否正确加载。")

if __name__ == "__main__":
    initialize_vector_database()