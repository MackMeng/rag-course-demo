"""
在线流程————RAG服务
功能：负责根据用户的问题，从向量数据库中检索相关文档，调用聊天模型生成回答
"""
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda
import config_data as config
from vector_stores import VectorStoreService
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.tongyi import ChatTongyi
from file_history_store import get_history

def print_prompt(prompt):
    print("="*50)
    print(prompt.to_string())
    print("="*50)
    return prompt

class RagService(object):
    def __init__(self):
        self.vector_service = VectorStoreService(DashScopeEmbeddings(model=config.embedding_model))
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
            ("system", "以我提供的资料为主，简洁和专业的回答用户的问题，参考资料：{context}"),
            ("system","并且我提供的历史对话记录:"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "请回答用户的问题{input}")
            ]
        )
        self.chat_model = ChatTongyi(model_name=config.chat_model_name)
        self.chain = self.__get_chain()

    def __get_chain(self):
        """获取最终地执行链"""
        retriever = self.vector_service.get_retriever()     #检索器提供参考资料
        def format_documents(docs):
            if not docs:
                return "无相关参考资料"
            formatted_str =""
            for doc in docs:
                formatted_str += f"文档片段：{doc.page_content}\n文档元素据：{doc.metadata}\n\n"
            return formatted_str

        def temp1(data:dict) -> str:
            return data["input"]

        def temp2(data: dict):
            new_data={}
            new_data["input"]=data["input"]["input"]
            new_data["history"]=data["input"]["history"]
            new_data["context"]=data["context"]
            return new_data

        chain = (
                    {
                        "input":RunnablePassthrough(),
                        "context":RunnableLambda(temp1)|retriever|format_documents
                    }
                )| RunnableLambda(temp2) | self.prompt_template  | print_prompt | self.chat_model  | StrOutputParser()

        #增强历史会话保存功能
        Conservation_chain=RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        return Conservation_chain

if __name__ == "__main__":
    session_config={"configurable":{"session_id":"user_001"}}
    res=RagService().chain.invoke({"input":"春天适合穿什么衣服"},session_config)
    print(res)

