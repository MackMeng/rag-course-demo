"""
在线流程————历史会话存储服务
功能：负责将用户的历史对话记录存储到文件中
返回历史对话记录用于加入chain中
"""
import json
import os
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, message_to_dict

def get_history(session_id):
    """获取指定会话id的历史对话记录"""
    return FileChatMessageHistory(session_id,"./chat_history")

class FileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self,session_id,storage_path):
        self.session_id=session_id  #会话id
        self.storage_path=storage_path   #不同会话id，所在的文件夹路径
        #完整的路径
        self.file_path=os.path.join(self.storage_path,self.session_id+".jsonl")
        #确保写入的文件存在
        os.makedirs(os.path.dirname(self.file_path),exist_ok=True)

    def add_messages(self,messages):
        all_messages=list(self.messages)    #已有的消息列表
        all_messages.extend(messages)                     #合并新的消息
        #将合并后的消息列表写入文件
        #为了方便，将Basemessage消息转化为字典，再写入文件
        new_messages=[message_to_dict(msg) for msg in all_messages]
        with open(self.file_path,"w",encoding="utf-8") as f:
            json.dump(new_messages,f,ensure_ascii=False,indent=2)

    @property
    def messages(self)->list[BaseMessage]:
        # 文件不存在 或 内容为空/损坏 → 视为没有历史对话
        try:
            with open(self.file_path,"r",encoding="utf-8") as f:
                return messages_from_dict(json.load(f))
        except FileNotFoundError:
            return []

    def clear(self) -> None:
        with open(self.file_path,"w",encoding="utf-8") as f:
            json.dump([],f,ensure_ascii=False,indent=2)