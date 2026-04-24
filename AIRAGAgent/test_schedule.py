from rag.vector_store import VectorStoreService
from rag.rag_service import RagSummarizeService

print("=" * 50)
print("测试向量库检索")
print("=" * 50)

# 测试向量库服务
vs = VectorStoreService()
retriever = vs.get_retriever()

# 测试检索课表相关内容
test_queries = ['明天课程', '课表', '土木班', '课程安排']

for query in test_queries:
    print(f"\n检索查询：{query}")
    print("-" * 50)
    res = retriever.invoke(query)
    print(f'检索结果数量：{len(res)}')
    
    for i, r in enumerate(res, 1):
        print(f'{i}. {r.page_content[:200]}...')
        if 'metadata' in r.metadata:
            print(f'   来源：{r.metadata.get("source", "未知")}')

print("\n" + "=" * 50)
print("测试 RAG 总结服务")
print("=" * 50)

rag_summarize = RagSummarizeService()
result = rag_summarize.rag_summarize('明天有什么课程')
print(f"RAG 总结结果：{result}")
