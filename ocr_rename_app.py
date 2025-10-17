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
uploaded_files = st.file_uploader("选择要处理的图片（可多选）", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

start_btn = st.button("开始处理")

progress_bar = st.progress(0)
log_box = st.empty()

async def recognize_text(session, access_token, image_base64):
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'image': image_base64}
    async with session.post(url, headers=headers, data=data) as resp:
        result = await resp.json()
        return result.get('words_result', [])

def extract_name(words_result):
    for i, line in enumerate(words_result):
        text = line.get('words', '').strip()
        if '姓名' in text:
            name = text.replace('姓名', '').strip()
            if name:
                return name
            if i + 1 < len(words_result):
                next_line = words_result[i + 1].get('words', '').strip()
                if next_line:
                    return next_line
    return None

def get_access_token(api_key, secret_key):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    response = requests.get(url)
    data = response.json()
    if 'access_token' not in data:
        raise Exception(f"Token获取失败: {data}")
    return data['access_token']

async def process_images(api_key, secret_key, uploaded_files):
    temp_dir = tempfile.mkdtemp()
    log_messages = []
    log_messages.append(f"创建临时目录: {temp_dir}")

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
            new_name = f"{name}.jpg"
            os.rename(img_path, os.path.join(temp_dir, new_name))
            log_messages.append(f"✅ {file.name} → {new_name}")
            progress_bar.progress((i+1)/total)
            log_box.text("\n".join(log_messages))
    zip_path = shutil.make_archive(temp_dir, 'zip', temp_dir)
    return zip_path

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
