import os
import sys
import requests
import base64
import asyncio
import aiohttp
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading


class OCRRenameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR图片批量重命名工具")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        
        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')
        
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="百度OCR图片批量重命名工具", 
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # 作者信息
        author_label = ttk.Label(main_frame, text=" - by 22智媒饶能 | 版本: v1.0", 
                                font=('Arial', 9), foreground='gray')
        author_label.grid(row=0, column=0, columnspan=3, pady=(25, 5))
        
        # API Key
        ttk.Label(main_frame, text="API Key:", font=('Arial', 10)).grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.api_key_entry = ttk.Entry(main_frame, width=50)
        self.api_key_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Secret Key
        ttk.Label(main_frame, text="Secret Key:", font=('Arial', 10)).grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.secret_key_entry = ttk.Entry(main_frame, width=50)
        self.secret_key_entry.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 文件夹路径
        ttk.Label(main_frame, text="图片文件夹:", font=('Arial', 10)).grid(
            row=3, column=0, sticky=tk.W, pady=5)
        self.folder_entry = ttk.Entry(main_frame, width=40)
        self.folder_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        browse_btn = ttk.Button(main_frame, text="浏览", command=self.browse_folder)
        browse_btn.grid(row=3, column=2, padx=(5, 0), pady=5)
        
        # 进度条
        ttk.Label(main_frame, text="处理进度:", font=('Arial', 10)).grid(
            row=4, column=0, sticky=tk.W, pady=(20, 5))
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 5))
        
        # 日志输出区域
        ttk.Label(main_frame, text="运行日志:", font=('Arial', 10)).grid(
            row=5, column=0, sticky=tk.W, pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=70, 
                                                   font=('Consolas', 9))
        self.log_text.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=(20, 0))
        
        self.start_btn = ttk.Button(button_frame, text="开始处理", 
                                     command=self.start_processing, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(button_frame, text="清空日志", 
                                     command=self.clear_log, width=15)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self.exit_btn = ttk.Button(button_frame, text="退出", 
                                    command=self.root.quit, width=15)
        self.exit_btn.pack(side=tk.LEFT, padx=5)
        
    def browse_folder(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
    
    def log(self, message):
        """在日志区域显示消息"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def start_processing(self):
        """开始处理"""
        api_key = self.api_key_entry.get().strip()
        secret_key = self.secret_key_entry.get().strip()
        folder_path = self.folder_entry.get().strip()
        
        # 验证输入
        if not api_key:
            messagebox.showerror("错误", "请输入 API Key")
            return
        if not secret_key:
            messagebox.showerror("错误", "请输入 Secret Key")
            return
        if not folder_path:
            messagebox.showerror("错误", "请选择图片文件夹")
            return
        if not os.path.isdir(folder_path):
            messagebox.showerror("错误", "文件夹路径不存在")
            return
        
        # 禁用按钮
        self.start_btn.config(state='disabled')
        self.progress.start()
        
        # 在新线程中运行处理
        thread = threading.Thread(target=self.run_processing, 
                                   args=(api_key, secret_key, folder_path))
        thread.daemon = True
        thread.start()
    
    def run_processing(self, api_key, secret_key, folder_path):
        """在后台线程运行异步处理"""
        try:
            asyncio.run(self.process_images(api_key, secret_key, folder_path))
        except Exception as e:
            self.log(f"处理出错: {str(e)}")
            messagebox.showerror("错误", f"处理失败: {str(e)}")
        finally:
            self.progress.stop()
            self.start_btn.config(state='normal')
    
    async def process_images(self, api_key, secret_key, folder_path):
        """异步处理所有图片"""
        self.log("=" * 60)
        self.log("开始处理...")
        self.log(f"文件夹: {folder_path}")
        
        # 获取 access_token
        try:
            access_token = self.get_access_token(api_key, secret_key)
            self.log("✓ 成功获取 Access Token")
        except Exception as e:
            self.log(f"✗ 获取 Access Token 失败: {str(e)}")
            return
        
        # 统计文件
        image_files = [f for f in os.listdir(folder_path) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        total = len(image_files)
        self.log(f"找到 {total} 个图片文件")
        self.log("-" * 60)
        
        if total == 0:
            self.log("文件夹中没有图片文件")
            messagebox.showinfo("提示", "文件夹中没有图片文件")
            return
        
        unknown_counter = [1]
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for file_name in image_files:
                image_path = os.path.join(folder_path, file_name)
                tasks.append(self.process_image(session, access_token, 
                                               image_path, folder_path, unknown_counter))
            await asyncio.gather(*tasks)
        
        # 后处理
        self.log("-" * 60)
        self.log("执行后处理...")
        self.post_process(folder_path)
        
        self.log("-" * 60)
        self.log("✓ 全部处理完成！")
        self.log("=" * 60)
        messagebox.showinfo("完成", f"成功处理 {total} 个文件！")
    
    def get_access_token(self, api_key, secret_key):
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
        response = requests.get(url)
        data = response.json()
        if 'access_token' not in data:
            raise Exception(f"获取token失败: {data.get('error_description', '未知错误')}")
        return data['access_token']
    
    def read_image(self, image_path):
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    async def recognize_text(self, session, access_token, image_base64):
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'image': image_base64, 'image_type': 'BASE64'}
        async with session.post(url, headers=headers, data=data) as resp:
            result = await resp.json()
            if 'error_code' in result:
                return None
            return result.get('words_result', [])
    
    def extract_name(self, words_result):
        for i, line in enumerate(words_result):
            text = line.get('words', '').strip()

            # --- 情况1：常见格式 “姓名张三” ---
            if '姓名' in text:
                name = text.replace('姓名', '').strip()
                if name:
                    return name
                # 下行可能是姓名
                if i + 1 < len(words_result):
                    next_line = words_result[i + 1].get('words', '').strip()
                    if next_line:
                        return next_line

            # --- 情况2：“姓”“名”分行 ---
            if text in ('姓', '姓：', '姓:'):
                # 向下两行查找“名”之后的姓名
                if i + 1 < len(words_result):
                    next_text = words_result[i + 1].get('words', '').strip()
                    if next_text in ('名', '名：', '名:') and i + 2 < len(words_result):
                        # 第三行应该是姓名
                        real_name = words_result[i + 2].get('words', '').strip()
                        if real_name:
                            return real_name
        return None

    
    def make_unique_filename(self, folder, base_name, ext):
        candidate = f"{base_name}{ext}"
        if not os.path.exists(os.path.join(folder, candidate)):
            return os.path.join(folder, candidate)
        
        counter = 1
        while os.path.exists(os.path.join(folder, f"{base_name}_{counter}{ext}")):
            counter += 1
        return os.path.join(folder, f"{base_name}_{counter}{ext}")
    
    async def process_image(self, session, access_token, image_path, output_folder, unknown_counter):
        file_name = os.path.basename(image_path)
        self.log(f"处理: {file_name}")
        
        image_base64 = self.read_image(image_path)
        words_result = await self.recognize_text(session, access_token, image_base64)
        
        # 重试机制
        retry_count = 0
        while words_result is None and retry_count < 10:
            await asyncio.sleep(5)
            words_result = await self.recognize_text(session, access_token, image_base64)
            retry_count += 1
        
        ext = os.path.splitext(image_path)[1]
        
        if words_result:
            name = self.extract_name(words_result)
        else:
            name = None
        
        if name:
            new_path = self.make_unique_filename(output_folder, name, ext)
            self.log(f"  识别姓名: {name}")
        else:
            name = f"未识别"
            new_path = self.make_unique_filename(output_folder, f"{name}_{unknown_counter[0]}", ext)
            unknown_counter[0] += 1
            self.log(f"  未识别到姓名")
        
        if os.path.abspath(image_path) != os.path.abspath(new_path):
            os.rename(image_path, new_path)
            self.log(f"  重命名为: {os.path.basename(new_path)}")
        else:
            self.log(f"  保持原名")
    
    def post_process(self, folder):
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
                        self.log(f"还原: {f} -> {base_name + ext}")


def main():
    root = tk.Tk()
    app = OCRRenameApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()