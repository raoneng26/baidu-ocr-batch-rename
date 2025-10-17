import streamlit as st
import os
import requests
import base64
import aiohttp
import asyncio
import tempfile
import shutil

st.set_page_config(page_title="OCR图片批量重命名工具", layout="centered")
st.title("📄 百度OCR图片批量重命名工具")
st.caption("by 22智媒饶能 | Streamlit版 v1.0")

# 输入部分
api_key = st.text_input("API Key", type="password")
secret_key = st.text_input("Secret Key", type="password")
uploaded_files = st.file_uploader(
    "选择要处理的图片（可多选）",
    accept_multiple_files=True,
    type=["jpg", "jpeg", "png"]
)

start_btn = st.button("开始处理")
progress_bar = st.progress(0)
log_box = st.empty()

# ---------------- OCR 调用 ----------------
async def recognize_text(session, access_token, image_base64, max_retries=10):
    """调用百度OCR并在失败时自动重试"""
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'image': image_base64}

    for attempt in range(max_retries):
        try:
            async with session.post(url, headers=headers, data=data) as resp:
                result = await resp.json()
                if 'words_result' in result:
                    return result['words_result']
                else:
                    print(f"⚠️ 第 {attempt+1}/{max_retries} 次重试：响应异常 {result}")
        except Exception as e:
            print(f"⚠️ 第 {attempt+1}/{max_retries} 次请求失败：{e}")
        await asyncio.sleep(5)
    return []

# ---------------- 姓名提取 ----------------
def extract_name(words_result):
    for i, line in enumerate(words_result):
        text = line.get('words', '').strip()
        # 情况1：姓名张三
        if '姓名' in text:
            name = text.replace('姓名', '').strip()
            if name:
                return name
            if i + 1 < len(words_result):
                next_line = words_result[i + 1].get('words', '').strip()
                if next_line:
                    return next_line
        # 情况2：姓 名 分行
        if text in ('姓', '姓：', '姓:'):
            if i + 1 < len(words_result):
                next_text = words_result[i + 1].get('words', '').strip()
                if next_text in ('名', '名：', '名:') and i + 2 < len(words_result):
                    real_name = words_result[i + 2].get('words', '').strip()
                    if real_name:
                        return real_name
    return None

# ---------------- 获取 AccessToken ----------------
def get_access_token(api_key, secret_key):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    response = requests.get(url)
    data = response.json()
    if 'access_token' not in data:
        raise Exception(f"Token获取失败: {data}")
    return data['access_token']

# ---------------- 文件名唯一化 ----------------
def make_unique_filename(folder, base_name, ext):
    candidate = f"{base_name}{ext}"
    if not os.path.exists(os.path.join(folder, candidate)):
        return os.path.join(folder, candidate)
    counter = 1
    while os.path.exists(os.path.join(folder, f"{base_name}_{counter}{ext}")):
        counter += 1
    return os.path.join(folder, f"{base_name}_{counter}{ext}")

# ---------------- 后处理去掉无意义 _1/_2 ----------------
def post_process(folder):
    files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    for f in files:
        name, ext = os.path.splitext(f)
        if "_" in name and name.split("_")[-1].isdigit():
            base_name = "_".join(name.split("_")[:-1])
            if base_name + ext not in files:
                old_path = os.path.join(folder, f)
                new_path = os.path.join(folder, base_name + ext)
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)

# ---------------- 异步处理 ----------------
async def process_images(api_key, secret_key, uploaded_files):
    temp_dir = tempfile.mkdtemp()
    log_messages = [f"创建临时目录: {temp_dir}"]

    access_token = get_access_token(api_key, secret_key)
    async with aiohttp.ClientSession() as session:
        total = len(uploaded_files)
        for i, file in enumerate(uploaded_files):
            img_path = os.path.join(temp_dir, file.name)
            with open(img_path, 'wb') as f:
                f.write(file.read())

            image_base64 = base64.b64encode(open(img_path, 'rb').read()).decode('utf-8')
            words = await recognize_text(session, access_token, image_base64)
            name = extract_name(words) or f"未识别_{i+1}"
            ext = os.path.splitext(file.name)[1]
            new_path = make_unique_filename(temp_dir, name, ext)
            os.rename(img_path, new_path)
            log_messages.append(f"✅ {file.name} → {os.path.basename(new_path)}")
            progress_bar.progress((i+1)/total)
            log_box.text("\n".join(log_messages))

    # 后处理：去掉无意义 _1/_2
    post_process(temp_dir)

    # 打包为 zip
    zip_path = shutil.make_archive(temp_dir, 'zip', temp_dir)
    return zip_path

# ---------------- Streamlit UI ----------------
if start_btn:
    if not api_key or not secret_key:
        st.error("请输入 API Key 和 Secret Key！")
    elif not uploaded_files:
        st.warning("请上传至少一张图片。")
    else:
        st.info("开始处理，请稍候...")
        zip_file = asyncio.run(process_images(api_key, secret_key, uploaded_files))
        st.success("全部处理完成！")
        with open(zip_file, "rb") as f:
            st.download_button("下载处理结果", f, file_name="重命名结果.zip")
