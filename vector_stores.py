"""
在线流程————向量数据库存储服务
功能：负责向量数据库的初始化，检索等操作
返回检索结果用于加入chain中
"""
from langchain_chroma import Chroma
import config_data as config

class VectorStoreService(object):
    def __init__(self, embedding):
        self.embedding = embedding
        self.vector_store = Chroma(
            collection_name=config.collection_name,     #向量数据库的集合名称
            embedding_function=self.embedding,      # 嵌入模型
            persist_directory=config.persist_directory,    # 向量库存储目录
        )

    def get_retriever(self):
        #把向量库对象，包装成一个标准的Langchain的Retriever检索器
        """返回向量检索器，方便加入chain中"""
        return self.vector_store.as_retriever(search_kwargs={'k': config.retriever_k})

if __name__=='__main__':
    from langchain_community.embeddings import DashScopeEmbeddings
    retriever = VectorStoreService(DashScopeEmbeddings(model='text-embedding-v4')).get_retriever()
    res=retriever.invoke("我的身高180cm，体重80kg，尺码推荐")
    print(res[0].page_content)
