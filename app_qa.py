"""
在线流程————智能客服服务
功能：用户输入问题，客服根据问题，从向量数据库中检索相关文档，调用聊天模型生成回答，返回给用户
"""
import streamlit as st
from rag import RagService
import config_data as config

# 标题
st.title("智能客服")
st.divider()    #分割符

if "rag" not in st.session_state:
    st.session_state["rag"]=RagService()
if "message" not in st.session_state:
    st.session_state["message"]=[{"role":"assistant","content":"你好，有什么我可以帮助你的吗？"}]

for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

#在页面最下方提供用户输入框
session_config={"configurable":{"session_id":"user_001"}}
prompt=st.chat_input("请输入您的问题")

if prompt:
    #如果用户输入了问题，就显示用户输入的问题
    st.chat_message("user").write(prompt)   #有头像，有聊天框
    st.session_state["message"].append({"role":"user","content":prompt})

    # 流式输出大模型回答；write_stream 返回完整文本，存入历史后刷新即正常渲染
    with st.spinner("AI思考中"):
        res = st.session_state["rag"].chain.stream({"input": prompt}, config.session_config)
        ai_text = st.chat_message("assistant").write_stream(res)   # write_stream 返回完整文本
        st.session_state["message"].append({"role": "assistant", "content": ai_text})
