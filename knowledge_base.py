"""
RAG项目离线流程————本地知识库写入与管理服务
功能：接收app_file_upload.py上传的文件内容，切分并向量化写入Chroma向量库；
     同时提供按文件名删除、清空整库的能力，形成"写入-更新-删除"的完整生命周期
注意：
    1、写入和在线检索必须使用同一个嵌入模型，统一从config.embedding_model获取
    2、md5去重记录的格式为`md5|文件名`，删除文档时必须同步清除对应记录，
       否则记录残留会导致同名文件重新上传时被永久"跳过"
    3、同名文件重新上传按"先删旧片段、再写新片段"的更新语义处理，避免新旧两版同时被检索到
"""
import argparse
import os
import datetime
import config_data as config
import hashlib
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

#历史遗留记录（纯md5、无文件名）无法回溯来源，聚合展示时归入该占位名
UNKNOWN_SOURCE = "<未知来源>"


# ==================== md5去重记录（格式：md5|文件名）====================
def get_string_md5(input_str:str,encoding='utf-8'):
    """将传入的字符串，转换为md5字符串，返回md5字符串"""
    #将字符串转换为字节数组
    str_bytes=input_str.encode(encoding=encoding)
    #创建md5对象
    md5_obj=hashlib.md5()   #hashlib.md5()得到的是一个md5对象
    md5_obj.update(str_bytes)   #更新md5对象，将字节数组添加到md5对象中
    md5_hex=md5_obj.hexdigest()   #hexdigest()方法返回的是一个32位的十六进制字符串
    return md5_hex

#加载去重记录
def load_md5_records():
    """读取全部去重记录，返回[(md5字符串,文件名),...]；文件不存在返回空列表"""
    if not os.path.exists(config.md5_path):
        #如果文件不存在，表示还没有处理过任何数据
        return []
    records=[]
    with open(config.md5_path,'r',encoding='utf-8') as f:   #用with保证句柄关闭
        for line in f:
            line=line.strip()   #处理字符串前后的空格和回车
            if not line:
                continue

            #line.partition('|')返回的是3个元素的元组，分别是：(前缀，分隔符，后缀)
            md5_hex,separator,filename=line.partition('|')
            #没有分隔符的旧格式记录，文件名兜底为占位来源
            records.append((md5_hex,filename if separator else UNKNOWN_SOURCE))
    return records


def _write_md5_records(records):
    """将[(md5,文件名),...]全量重写回记录文件"""
    with open(config.md5_path,'w',encoding='utf-8') as f:
        for md5_hex,filename in records:
            f.write(f"{md5_hex}|{filename}\n")


def check_md5(md5_str:str,filename:str):
    """检查"内容+文件名"是否已经处理过了

    同一份内容上传到不同文件名时不算重复，否则后一个文件的source元数据会丢失
    """
    return any(item_md5==md5_str and item_name==filename
               for item_md5,item_name in load_md5_records())


def save_md5(md5_str:str,filename:str):
    """将传入的md5字符串连同文件名，记录到文件内容中保存"""
    with open(config.md5_path,'a',encoding='utf-8') as f:    #以追加模式打开文件
        f.write(f"{md5_str}|{filename}\n")


def remove_md5_by_filename(filename:str):
    """删除某个文件名的所有去重记录，返回删除条数"""
    records=load_md5_records()
    kept=[(item_md5,item_name) for item_md5,item_name in records if item_name!=filename]
    removed=len(records)-len(kept)
    if removed:
        _write_md5_records(kept)
    return removed


def clear_md5_records():
    """清空所有去重记录"""
    with open(config.md5_path,'w',encoding='utf-8') as f:   #不存在会自动创建，存在则截断
        pass


# ==================== 知识库服务类 ====================
#初始化向量库，创建向量库对象，设置向量库的集合名称，嵌入模型，本地存储文件夹
class KnowledgeBaseService(object):
    def __init__(self):
        #如果文件夹不存在，创建文件夹
        os.makedirs(config.persist_directory,exist_ok=True)
        os.makedirs(os.path.dirname(config.md5_path),exist_ok=True)

        self.chroma = Chroma(
            collection_name=config.collection_name,  #数据库的名字
            embedding_function=DashScopeEmbeddings(model=config.embedding_model),
            persist_directory=config.persist_directory  #数据库的本地存储文件夹
        )   #向量存储的实例Chroma的向量库对象

        self.splitter=RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,   #分割后的文本段最大长度
            chunk_overlap=config.chunk_overlap,   #连续分割后的文本段之间的重叠长度
            separators=config.separators,   #自然段落划分的符号
            length_function=len,   #计算文本段的长度的函数
        )  #文本分割器的实例

    # ---------- 查询 ----------
    def list_documents(self):
        """按source聚合当前库内文档，返回{文件名:{"chunks":片段数,"create_time":最近写入时间}}"""
        datas=self.chroma.get(include=['metadatas'])
        stats={}
        for metadata in (datas.get('metadatas') or []):
            metadata=metadata or {}
            source=metadata.get('source') or UNKNOWN_SOURCE
            item=stats.setdefault(source,{"chunks":0,"create_time":""})
            item["chunks"]+=1
            #时间戳是"%Y-%m-%d_%H:%M:%S"格式，字符串比较即等价于时间比较
            create_time=metadata.get('create_time') or ""
            if create_time>item["create_time"]:
                item["create_time"]=create_time
        return stats

    # ---------- 写入（更新语义：同名文档先删后写）----------
    def upload_by_str(self,data,filename):
        """将传入的字符串，进行向量化，存入向量数据库中"""
        if not data or not data.strip():
            return "【失败】文件内容为空，未写入知识库"

        #先得到md5字符串
        md5_hex=get_string_md5(data)
        if check_md5(md5_hex,filename):
            return "【跳过】数据已经存在，无需重复处理"

        if len(data) > config.max_split_char_number:
            knowledge_chunks:list[str]=self.splitter.split_text(data)
        else:
            knowledge_chunks:list[str]=[data]
        if not knowledge_chunks:
            return "【失败】文本切分后为空，未写入知识库"

        metadata={
            "source":filename,
            "create_time":datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),
            "operator":"Mack"
        }

        #同名文档重新上传视为内容更新：先清除旧片段，避免新旧两版同时被检索到
        old_chunks=self.delete_by_filename(filename,purge_md5=True)

        try:
            self.chroma.add_texts(  #将文本段添加到知识库中
                knowledge_chunks,
                metadatas=[metadata for _ in knowledge_chunks]
            )
        except Exception as exc:
            #写入失败时不记录md5，保证去重记录与向量库内容始终一致
            hint=f"（同名文档的{old_chunks}个旧片段已一并清除，需重新上传）" if old_chunks else ""
            return f"【失败】写入向量库出错：{exc}{hint}"

        save_md5(md5_hex,filename)
        head=f"【成功】已替换同名文档的{old_chunks}个旧片段，" if old_chunks else "【成功】"
        return f"{head}数据处理完成，共写入{len(knowledge_chunks)}个片段"

    # ---------- 删除 ----------
    def delete_by_filename(self,filename:str,purge_md5:bool=True):
        """按文件名删除向量库中该文档的全部片段，并同步清理md5记录，返回删除的片段数"""
        matched=self.chroma.get(where={'source':filename})
        ids=matched.get('ids') or []
        if ids:
            self.chroma.delete(ids=ids)
        if purge_md5:
            remove_md5_by_filename(filename)
        return len(ids)

    def delete_all(self):
        """清空整个知识库：删除向量库中的全部片段并清空md5记录，返回清除的片段数

        只清空片段、保留collection本身：
        1、比手动rm -rf chroma_db安全，Windows下目录常被进程占用删不掉
        2、reset_collection会删掉并新建collection（新id），而在线服务app_qa持有的是同一
           collection的句柄，换掉后其他进程会继续查已删除的旧collection并报NotFoundError
        """
        ids=self.chroma.get(include=['metadatas']).get('ids') or []
        if ids:
            self.chroma.delete(ids=ids)
        clear_md5_records()
        return len(ids)


def _build_parser():
    """知识库管理命令行参数"""
    parser=argparse.ArgumentParser(description="本地知识库管理：查看/删除/清空")
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--list',action='store_true',help="列出库内文档及各文档的片段数")
    group.add_argument('--delete',metavar='文件名',help="删除指定文件名的全部片段并清理对应md5记录")
    group.add_argument('--clear',action='store_true',help="清空整个知识库及全部md5记录")
    return parser


if __name__=='__main__':
    parser=_build_parser()
    args=parser.parse_args()
    service = KnowledgeBaseService()

    if args.list:
        documents=service.list_documents()
        if not documents:
            print("知识库为空")
        for name,item in sorted(documents.items()):
            print(f"{name}\t片段数={item['chunks']}\t最近写入={item['create_time']}")
    elif args.delete:
        #先删片段时不顺手清记录，改为单独删除以便统计条数
        chunks=service.delete_by_filename(args.delete,purge_md5=False)
        removed_md5=remove_md5_by_filename(args.delete)
        print(f"【{args.delete}】已删除{chunks}个片段、{removed_md5}条md5记录")
    elif args.clear:
        chunks=service.delete_all()
        print(f"已清空知识库：删除{chunks}个片段，md5记录已全部清除")
    else:
        #默认只打印帮助：避免误运行脚本就往真实库里写入测试数据
        parser.print_help()
