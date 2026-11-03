"""
RAG项目离线流程————本地知识库更新服务
功能：用户上传文件，服务端将文件内容存储到本地知识库中
实现：使用streamlit框架开发WEB网页服务，用户通过浏览器上传文件，服务端将文件内容存储到本地知识库中
"""
import time
import streamlit as st
from knowledge_base import KnowledgeBaseSergvice

#添加标题
st.title("知识库更新服务")
#文件上传框
uploaded_file = st.file_uploader("上传文件", type=["txt"])

# session_state就是字典，可以存储一些数据，比如文件内容
#为了避免页面每次刷新都创建新的服务对象，导致知识库重复创建
#streamlit提供了session_state，可以存储一些数据
if 'service' not in st.session_state:
    st.session_state['service'] = KnowledgeBaseSergvice()

if uploaded_file is not None:
    # 读取文件内容
    file_name=uploaded_file.name
    file_type=uploaded_file.type
    file_size=uploaded_file.size/1024
    st.subheader(f"文件名：{file_name}")
    st.write(f"文件格式：{file_type} | 文件大小：{file_size:.2f}KB")
    text=uploaded_file.getvalue().decode('utf-8')

    # 调用服务，上传文件内容
    with st.spinner("上传中..."):
        time.sleep(1)
        result = st.session_state['service'].upload_by_str(text, file_name)
        st.write(result)
        st.write("-----------------")
        st.write(text)

