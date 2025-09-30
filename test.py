import os
import requests
import base64
import asyncio
import aiohttp

# ---------- 百度 OCR ----------
def get_access_token(api_key, secret_key):
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    response = requests.get(url)
    data = response.json()
    return data['access_token']

def read_image(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

async def recognize_text(session, access_token, image_base64):
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'image': image_base64, 'image_type': 'BASE64'}
    async with session.post(url, headers=headers, data=data) as resp:
        result = await resp.json()
        if 'error_code' in result:
            print(f"Error: {result['error_msg']}")
            return None
        return result.get('words_result', [])

# ---------- 姓名提取 ----------
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

# ---------- 生成唯一文件名 ----------
def make_unique_filename(folder, base_name, ext):
    """
    正常识别的姓名直接用 base_name.jpg
    如果文件已存在（重名或未识别）才加 _1, _2
    """
    candidate = f"{base_name}{ext}"
    if not os.path.exists(os.path.join(folder, candidate)):
        return os.path.join(folder, candidate)
    
    counter = 1
    while os.path.exists(os.path.join(folder, f"{base_name}_{counter}{ext}")):
        counter += 1
    return os.path.join(folder, f"{base_name}_{counter}{ext}")


# ---------- 异步处理单张图片 ----------
async def process_image(session, access_token, image_path, output_folder, unknown_counter):
    image_base64 = read_image(image_path)
    words_result = await recognize_text(session, access_token, image_base64)

    # 如果返回 QPS 限制错误，可以重试
    retry_count = 0
    while words_result is None and retry_count < 3:
        await asyncio.sleep(.5)  # 等待 1 秒再重试
        words_result = await recognize_text(session, access_token, image_base64)
        retry_count += 1

    ext = os.path.splitext(image_path)[1]

    # 提取姓名
    if words_result:
        name = extract_name(words_result)
    else:
        name = None

    if name:
        new_path = make_unique_filename(output_folder, name, ext)
    else:
        name = f"未识别"
        new_path = make_unique_filename(output_folder, f"{name}_{unknown_counter[0]}", ext)
        unknown_counter[0] += 1

    # 只有文件名确实变化时才重命名
    if os.path.abspath(image_path) != os.path.abspath(new_path):
        os.rename(image_path, new_path)
        print(f"Renamed {image_path} -> {new_path}")
    else:
        print(f"保持原名：{image_path}")

# ---------- 后处理：还原多余的 _1 ----------
def post_process(folder):
    files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    name_map = {}

    for f in files:
        name, ext = os.path.splitext(f)
        if "_" in name and name.split("_")[-1].isdigit():  # 带序号
            base_name = "_".join(name.split("_")[:-1])
            if base_name + ext not in files:  # 如果没有 base_name 文件
                old_path = os.path.join(folder, f)
                new_path = os.path.join(folder, base_name + ext)
                # 确认 new_path 不存在，避免覆盖
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    print(f"还原 {old_path} -> {new_path}")

# ---------- 异步处理文件夹 ----------
async def main():
    api_key = 'pOfvxg3GbJ4oEt0Ml6PRhb6J'
    secret_key = 'gNQKHnIahCfo4gaXDWRCudVK19pxdcSj'
    folder_path = r'C:\Users\86187\Desktop\autoname'  # 图片文件夹
    output_folder = folder_path  # 可改为其他输出文件夹
    access_token = get_access_token(api_key, secret_key)

    unknown_counter = [1]  # 未识别序号计数

    async with aiohttp.ClientSession() as session:
        tasks = []
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(folder_path, file_name)
                tasks.append(process_image(session, access_token, image_path, output_folder, unknown_counter))
        await asyncio.gather(*tasks)
    
    # --- 处理结束后做后处理 ---
    post_process(output_folder)

if __name__ == '__main__':
    asyncio.run(main())
