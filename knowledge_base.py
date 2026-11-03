"""
RAG项目离线历程————加载文件到知识库中
功能：接受app_file_upload.py上传的文件内容，将其加载到知识库中
实现：使用Chroma数据库，将文件内容存储到数据库中
注意：要检查文件是否已经处理过了，避免重复处理————用md5字符串记录：给文件生成一个唯一标识
"""
import os
import datetime
import config_data as config
import hashlib
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


def check_md5(md5_str:str):
    """检查传入的md5字符串是否已经处理过了"""
    if not os.path.exists(config.md5_path):
        #如果文件不存在，表示没有处理过
        open(config.md5_path,'w',encoding='utf-8').close()  #以写入模式打开文件，会自动创建文件
        return False
    else:
        #如果文件存在，表示已经处理过
        for line in open(config.md5_path,'r',encoding='utf-8').readlines():
            line=line.strip()   #处理字符串前后的空格和回车
            if line == md5_str:
                return True
        return False


def save_md5(md5_str:str):
    """将传入的md5字符串，记录到文件内容中保存"""
    with open(config.md5_path,'a',encoding='utf-8') as f:    #以追加模式打开文件
        f.write(md5_str+'\n')

def get_string_md5(input_str:str,encoding='utf-8'):
    """将传入的字符串，转换为md5字符串，返回md5字符串"""
    #将字符串转换为字节数组
    str_bytes=input_str.encode(encoding=encoding)
    #创建md5对象
    md5_obj=hashlib.md5()   #得到md5对象
    md5_obj.update(str_bytes)   #更新md5对象，将字节数组添加到md5对象中
    md5_hex=md5_obj.hexdigest()   #得到md5字符串(十六进制)
    return md5_hex

# 知识库服务类
#初始化向量库，创建向量库对象，设置向量库的集合名称，嵌入模型，本地存储文件夹
class KnowledgeBaseSergvice(object):
    def __init__(self):
        #如果文件夹不存在，创建文件夹
        os.makedirs(config.persist_directory,exist_ok=True)

        self.chroma = Chroma(
            collection_name=config.collection_name,  #数据库的名字
            embedding_function=DashScopeEmbeddings(model='text-embedding-v4'),
            persist_directory=config.persist_directory  #数据库的本地存储文件夹
        )   #向量存储的实例Chroma的向量库对象

        self.splitter=RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,   #分割后的文本段最大长度
            chunk_overlap=config.chunk_overlap,   #连续分割后的文本段之间的重叠长度
            separators=config.separators,   #自然段落划分的符号
            length_function=len,   #计算文本段的长度的函数
        )  #文本分割器的实例

    def upload_by_str(self,data,filename):
        """将传入的字符串，进行向量化，存入向量数据库中"""
        #先得到md5字符串
        md5_hex=get_string_md5(data)
        if check_md5(md5_hex):
            return "【跳过】数据已经存在，无需重复处理"
        if len(data) >config.max_split_char_number:
            knowledge_chunks:list[str]=self.splitter.split_text(data)
        else:
            knowledge_chunks:list[str]=[data]
        metadata={
            "source":filename,
            "create_time":datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),
            "operator":"Mack"
        }
        self.chroma.add_texts(  #将文本段添加到知识库中
            knowledge_chunks,
            metadatas=[metadata for _ in knowledge_chunks]
        )
        save_md5(md5_hex)
        return "【成功】数据处理完成"
if __name__=='__main__':
    service=KnowledgeBaseSergvice()
    result=service.upload_by_str("周杰伦","test.txt")
    print(result)
