"""
RAG项目离线流程————本地知识库更新服务
功能：用户上传文件，服务端将文件内容存储到本地知识库中；
     同时提供"查看库内文档 / 按文件名删除 / 清空整库"的管理面板
实现：使用streamlit框架开发WEB网页服务，用户通过浏览器上传文件，服务端将文件内容存储到本地知识库中
"""
import streamlit as st
from knowledge_base import KnowledgeBaseService

MAX_PREVIEW_CHARS = 500    #原文预览最多展示的字符数，避免大文件刷屏

#添加标题
st.title("知识库更新服务")
st.divider()

# session_state就是字典，可以存储一些数据，比如文件内容
#为了避免页面每次刷新都创建新的服务对象，导致知识库重复创建
#streamlit提供了session_state，可以存储一些数据
if 'service' not in st.session_state:
    st.session_state['service'] = KnowledgeBaseService()

def set_flash(kind, text):
    """暂存一条操作结果提示；st.rerun()会丢弃当次输出，所以提示先存后取"""
    st.session_state["flash"] = {"kind": kind, "text": text}

def show_flash():
    """取出并展示上一次操作的提示"""
    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash["kind"])(flash["text"])

def on_delete_document(target):
    """删除按钮的回调：回调在下次脚本执行前运行，此时修改widget状态才是安全的"""
    typed = st.session_state.get("delete_confirm", "").strip()
    if typed != target:
        set_flash("warning", f"确认文本与所选文件名【{target}】不一致，已取消删除")
        return
    chunks = st.session_state['service'].delete_by_filename(target)
    st.session_state["delete_confirm"] = ""
    set_flash("success", f"已删除【{target}】的{chunks}个片段及其md5去重记录，同名文件现在可以重新上传")

def on_clear_all():
    """清空整库按钮的回调"""
    removed = st.session_state['service'].delete_all()
    st.session_state["confirm_clear"] = False
    set_flash("success", f"知识库已清空，共删除{removed}个片段及全部md5去重记录")

# ==================== 上传区 ====================
uploaded_file = st.file_uploader("上传文件", type=["txt"])

if uploaded_file is not None:
    # 读取文件内容
    file_name = uploaded_file.name
    file_type = uploaded_file.type
    file_size = uploaded_file.size / 1024
    st.subheader(f"文件名：{file_name}")
    st.write(f"文件格式：{file_type} | 文件大小：{file_size:.2f}KB")
    text = uploaded_file.getvalue().decode('utf-8')

    st.write(f"内容预览（共{len(text)}字符，最多展示{MAX_PREVIEW_CHARS}个）：")
    st.text(text[:MAX_PREVIEW_CHARS] + ("..." if len(text) > MAX_PREVIEW_CHARS else ""))

    #选中文件后需要手动点击写入：file_uploader在每次页面刷新时都会重新持有上次的文件，
    #自动写入会让"删除文档"之后的页面刷新，把刚删掉的文件又写回知识库
    if st.button("写入知识库", type="primary"):
        with st.spinner("上传中..."):
            result = st.session_state['service'].upload_by_str(text, file_name)
        if result.startswith("【成功】"):
            set_flash("success", f"{file_name} → {result}")
            st.rerun()
        elif result.startswith("【跳过】"):
            set_flash("info", f"{file_name} → {result}")
            st.rerun()
        else:
            #失败时直接就地展示，方便用户改文件后原样重试
            st.error(result)
    else:
        st.caption("点击「写入知识库」才会真正处理，未点击不会改动知识库")

# ==================== 知识库管理区 ====================
#放在上传逻辑之后渲染，保证列表取到的是最新状态
with st.expander("知识库管理（查看 / 删除已上传文档）", expanded=True):
    show_flash()
    documents = st.session_state['service'].list_documents()

    if not documents:
        st.info("知识库为空：上传文件并点击「写入知识库」后，这里会列出所有已入库的文档")
    else:
        st.dataframe(
            [{"文件名": name, "片段数": item["chunks"], "最近写入": item["create_time"] or "未知"}
             for name, item in sorted(documents.items())],
            use_container_width=True, hide_index=True)

        # ---------- 按文件名删除 ----------
        st.subheader("按文件名删除")
        target = st.selectbox("选择要删除的文档", sorted(documents))
        st.text_input("输入完整文件名以确认（含扩展名）", key="delete_confirm")
        st.button("删除该文档", on_click=on_delete_document, args=(target,))

    # ---------- 清空整个知识库 ----------
    st.subheader("清空整个知识库")
    if st.session_state.get("confirm_clear"):
        st.error("此操作会删除向量库中的全部片段，并清空md5去重记录，且无法恢复")
        col_yes, col_no = st.columns(2)
        col_yes.button("确认清空", type="primary", on_click=on_clear_all)
        col_no.button("取消", on_click=lambda: st.session_state.update(confirm_clear=False))
    else:
        st.button("清空整个知识库",
                  on_click=lambda: st.session_state.update(confirm_clear=True))
