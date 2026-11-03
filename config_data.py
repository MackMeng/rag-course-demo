
md5_path= "./md5.text"

#Chroma数据库的配置
collection_name='rag'   #向量数据库的集合名称
persist_directory='./chroma_db'     #向量库存的目录

#splitter的配置
chunk_size=1000
chunk_overlap=100
separators=['\n\n','\n','.','!','?','？','！','？','。',' ','']
max_split_char_number=1000

#
retriever_k=2   #检索返回的文档数量

embedding_model='text-embedding-v4'
chat_model_name="qwen-max"

session_config={"configurable":{"session_id":"user_001"}}
