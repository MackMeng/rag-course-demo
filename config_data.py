import os

#本文件作为基准，abspath()返回绝对路径，dirname()切掉文件名，得到该项目的根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
md5_path = os.path.join(BASE_DIR, "md5.text")   # 去重记录，格式：md5|文件名

# Chroma数据库的配置
collection_name = 'rag'   # 向量数据库的集合名称
persist_directory = os.path.join(BASE_DIR, 'chroma_db')     # 向量库存的目录

# 历史会话的存储目录
chat_history_dir = os.path.join(BASE_DIR, "chat_history")

# splitter的配置
chunk_size = 1000
chunk_overlap = 100
separators = ['\n\n', '\n', '.', '!', '?', '？', '！', '。', ' ', '']   # 已去除重复的'？'
max_split_char_number = 1000

retriever_k = 2   # 检索返回的文档数量

embedding_model = 'text-embedding-v4'
chat_model_name = "qwen-max"

session_config = {"configurable": {"session_id": "user_001"}}

