"""
RAG项目——合并入口（在线问答 + 离线知识库管理）
布局：主区域 = 智能客服聊天；侧边栏 = 知识库上传与管理
原 app_qa.py / app_file_upload.py 保留为独立调试入口，本文件不修改它们
"""
import streamlit as st
from rag import RagService
from knowledge_base import KnowledgeBaseService
import config_data as config

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="RAG 智能客服",
    page_icon="🤖",
    layout="wide",   # 宽屏，给侧边栏留更多空间
)

# ==================== 服务初始化（仅首次） ====================
if "rag" not in st.session_state:
    st.session_state["rag"] = RagService()
if "kb_service" not in st.session_state:
    st.session_state["kb_service"] = KnowledgeBaseService()
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "你好，有什么我可以帮助你的吗？"}]


# ==================== 侧边栏：知识库管理 ====================
with st.sidebar:
    st.header("📚 知识库管理")
    st.divider()

    # ---------- 提示消息 ----------
    flash = st.session_state.pop("kb_flash", None)
    if flash:
        getattr(st, flash["kind"])(flash["text"])

    # ---------- 文件上传 ----------
    st.subheader("📤 上传文件")
    uploaded_file = st.file_uploader("选择 txt 文件", type=["txt"], key="kb_uploader")

    if uploaded_file is not None:
        file_name = uploaded_file.name
        file_size = uploaded_file.size / 1024
        st.caption(f"{file_name}（{file_size:.1f}KB）")
        text = uploaded_file.getvalue().decode("utf-8")
        # 预览前 200 字符
        preview = text[:200] + ("..." if len(text) > 200 else "")
        st.text_area("内容预览", preview, height=80, disabled=True)

        if st.button("写入知识库", type="primary", use_container_width=True):
            with st.spinner("处理中..."):
                result = st.session_state["kb_service"].upload_by_str(text, file_name)
            if result.startswith("【成功】"):
                st.session_state["kb_flash"] = {"kind": "success", "text": result}
            elif result.startswith("【跳过】"):
                st.session_state["kb_flash"] = {"kind": "info", "text": result}
            else:
                st.session_state["kb_flash"] = {"kind": "error", "text": result}
            st.rerun()

    # ---------- 库内文档列表 ----------
    st.subheader("📋 库内文档")
    documents = st.session_state["kb_service"].list_documents()

    if not documents:
        st.info("知识库为空")
    else:
        for name, item in sorted(documents.items()):
            st.caption(f"• {name}  |  {item['chunks']}个片段  |  {item['create_time'] or '未知时间'}")

        # ---------- 按文件名删除 ----------
        st.markdown("---")
        st.subheader("🗑 删除文档")
        target = st.selectbox("选择文档", sorted(documents), key="kb_delete_select")
        confirm_text = st.text_input("输入完整文件名确认", key="kb_delete_confirm")
        if st.button("执行删除", use_container_width=True):
            if confirm_text.strip() != target:
                st.session_state["kb_flash"] = {
                    "kind": "warning",
                    "text": f"确认文本与【{target}】不一致，已取消"
                }
            else:
                chunks = st.session_state["kb_service"].delete_by_filename(target)
                st.session_state["kb_flash"] = {
                    "kind": "success",
                    "text": f"已删除【{target}】的{chunks}个片段"
                }
                st.session_state["kb_delete_confirm"] = ""
            st.rerun()

    # ---------- 清空整库 ----------
    st.markdown("---")
    if st.button("⚠️ 清空整个知识库", use_container_width=True):
        st.session_state["confirm_clear"] = True

    if st.session_state.get("confirm_clear"):
        st.error("此操作不可恢复，确认清空？")
        col_yes, col_no = st.columns(2)
        if col_yes.button("确认", type="primary"):
            removed = st.session_state["kb_service"].delete_all()
            st.session_state["confirm_clear"] = False
            st.session_state["kb_flash"] = {
                "kind": "success",
                "text": f"已清空：删除{removed}个片段及全部md5记录"
            }
            st.rerun()
        if col_no.button("取消"):
            st.session_state["confirm_clear"] = False
            st.rerun()


# ==================== 主区域：智能客服聊天 ====================
st.title("🤖 智能客服")
st.caption("基于本地知识库的 RAG 问答 | 侧边栏可管理知识库文档")
st.divider()

# 渲染历史消息
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 用户输入（始终在页面底部）
prompt = st.chat_input("请输入您的问题")

if prompt:
    # 显示并记录用户消息
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})

    # 流式输出 AI 回答
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            res = st.session_state["rag"].chain.stream(
                {"input": prompt}, config.session_config
            )
            ai_text = st.write_stream(res)
    st.session_state["messages"].append({"role": "assistant", "content": ai_text})
