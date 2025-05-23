import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, Menu
import os
import json # For config file
import collections
from decompressor import extract_archive

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    print("tkinterdnd2 library not found. Please install it using: pip install tkinterdnd2")
    TkinterDnD = None

ARCHIVE_EXTENSIONS = {".rar", ".zip", ".7z", ".tar", ".gz", ".tgz"}
CONFIG_FILE = "config.json"
DEFAULT_WINRAR_PATH = "C:/Program Files/WinRAR/WinRAR.exe"


class App(TkinterDnD.Tk if TkinterDnD else tk.Tk):
    def __init__(self):
        super().__init__()
        self.processed_archives = set()
        self.extraction_queue = collections.deque()
        self.winrar_path = DEFAULT_WINRAR_PATH # Initialize with default

        self._load_config() # Load config first

        self.title("自动解压缩工具")
        self.geometry("450x350") # Slightly larger for menu

        self._setup_menu()

        # File listbox
        self.file_listbox = tk.Listbox(self, selectmode=tk.MULTIPLE)
        self.file_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.original_dnd_bind_id = None

        if TkinterDnD:
            self.file_listbox.drop_target_register(DND_FILES)
            self.original_dnd_bind_id = self.file_listbox.dnd_bind('<<Drop>>', self.on_drop)

        self.start_button = ttk.Button(self, text="开始解压", command=self.start_decompression)
        self.start_button.pack(pady=5)

        self.status_label = tk.Label(self, text="正在初始化...")
        self.status_label.pack(pady=5, fill=tk.X, side=tk.BOTTOM)
        
        self._check_winrar_availability() # Check after path is potentially loaded


    def _setup_menu(self):
        menubar = Menu(self)
        self.config(menu=menubar)

        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="配置WinRAR路径", command=self._configure_winrar_path)

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
                    loaded_path = config_data.get('winrar_path')
                    if loaded_path and isinstance(loaded_path, str):
                        self.winrar_path = loaded_path
                        print(f"从 {CONFIG_FILE} 加载 WinRAR 路径: {self.winrar_path}")
                    else:
                        print(f"{CONFIG_FILE} 中未找到有效的 'winrar_path'。将使用默认路径。")
            else:
                print(f"配置文件 {CONFIG_FILE} 未找到。将使用默认WinRAR路径并尝试创建配置文件。")
                self._save_config() # Save default path to create config file
        except (IOError, json.JSONDecodeError) as e:
            print(f"读取配置文件 {CONFIG_FILE} 失败: {e}。将使用默认路径。")
            # self.status_label.config(text=f"读取配置文件失败，使用默认WinRAR路径。") # Status bar not ready yet

    def _save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'winrar_path': self.winrar_path}, f, indent=4)
            print(f"WinRAR 路径已保存到 {CONFIG_FILE}: {self.winrar_path}")
            if hasattr(self, 'status_label'): # Check if status_label exists
                 self.status_label.config(text=f"WinRAR路径已更新并保存。")
        except IOError as e:
            print(f"保存配置文件 {CONFIG_FILE} 失败: {e}")
            if hasattr(self, 'status_label'):
                 self.status_label.config(text=f"错误：保存WinRAR路径失败！")

    def _configure_winrar_path(self):
        # On Windows, filter for .exe; on other OS, perhaps no filter or filter for common script/binary types
        filetypes = [("WinRAR Executable", "WinRAR.exe"), ("All files", "*.*")] if os.name == 'nt' else [("All files", "*.*")]
        
        new_path = filedialog.askopenfilename(
            title="请选择 WinRAR.exe",
            filetypes=filetypes,
            initialfile="WinRAR.exe" # Suggests the filename
        )
        if new_path:
            self.winrar_path = new_path
            self._save_config()
            self._check_winrar_availability() # Re-check with new path

    def _check_winrar_availability(self):
        if not os.path.exists(self.winrar_path):
            self.status_label.config(text=f"警告：WinRAR未找到于 '{self.winrar_path}'。请通过“设置”菜单配置。")
        else:
            self.status_label.config(text="请拖拽或添加压缩文件开始解压。WinRAR路径已配置。")


    def on_drop(self, event):
        # The event.data string can contain multiple files, often space-separated
        # and each enclosed in curly braces. Example: '{/path/to/file1} {/path/to/file2}'
        # Or sometimes just space separated without braces.
        # We need to parse this string carefully.
        files_string = event.data
        # A common format is files enclosed in curly braces: {path1} {path2}
        # Let's try to split by '}' and then clean up.
        potential_files = files_string.split('}')
        for f_part in potential_files:
            f_part = f_part.strip()
            if not f_part:
                continue
            # Remove leading '{' if present
            if f_part.startswith('{'):
                f_part = f_part[1:]
            
            # Sometimes paths might be quoted if they contain spaces,
            # but tkinterdnd2 usually handles this by giving the raw path.
            # If files are not in braces, they might just be space separated.
            # This basic split might need refinement based on actual event.data format.
            if not f_part.startswith('{') and ' {' in files_string: # Heuristic for space separated paths without individual braces
                 actual_files = files_string.split()
            else:
                 actual_files = [f_part] # Treat as single file or already correctly split part

            for file_path in actual_files:
                file_path = file_path.strip() # Clean whitespace
                if file_path: # Ensure it's not an empty string
                    self.file_listbox.insert(tk.END, file_path)
        
        if self.file_listbox.size() > 0:
            self.status_label.config(text="文件已添加，准备解压。")
        else:
            self.status_label.config(text="请拖拽压缩文件到上方列表或点击下方按钮选择文件")

    def _set_controls_state(self, state):
        """Helper function to enable/disable controls."""
        if state == tk.DISABLED:
            self.start_button.config(state=tk.DISABLED)
            self.file_listbox.config(state=tk.DISABLED)
            # Attempt to unbind drag-and-drop
            if TkinterDnD and self.original_dnd_bind_id:
                self.file_listbox.dnd_unbind('<<Drop>>', self.original_dnd_bind_id)
        else: # tk.NORMAL
            self.start_button.config(state=tk.NORMAL)
            self.file_listbox.config(state=tk.NORMAL)
            # Re-bind drag-and-drop
            if TkinterDnD:
                 # Re-register just in case, and rebind.
                self.file_listbox.drop_target_register(DND_FILES)
                self.original_dnd_bind_id = self.file_listbox.dnd_bind('<<Drop>>', self.on_drop)


    def start_decompression(self):
        all_files_in_listbox = self.file_listbox.get(0, tk.END)
        if not all_files_in_listbox:
            self.status_label.config(text="列表为空，请先添加压缩文件。")
            return

        self.processed_archives.clear()
        self.extraction_queue.clear()

        for item_path in all_files_in_listbox:
            abs_path = os.path.abspath(item_path)
            # Check processed_archives here if you want to avoid duplicates from the initial list itself,
            # though `_process_extraction_queue` already checks it.
            # For now, allow duplicates in queue if they were in listbox multiple times,
            # `processed_archives` will prevent re-extraction.
            self.extraction_queue.append(item_path)
        
        self.file_listbox.delete(0, tk.END) # Clear listbox

        if not self.extraction_queue: # Should not happen if listbox had items
            self.status_label.config(text="未能添加任何文件到解压队列。")
            return
            
        self.status_label.config(text=f"已添加 {len(self.extraction_queue)} 个文件到队列。开始解压...")
        self._set_controls_state(tk.DISABLED)
        self.update_idletasks()
        
        # Start processing the queue using self.after to keep GUI responsive
        self.after(100, self._process_extraction_queue)


    def _scan_and_enqueue_nested_archives(self, parent_output_directory, parent_archive_name):
        self.status_label.config(text=f"扫描解压目录 '{parent_archive_name}' 查找嵌套压缩包...")
        self.update_idletasks()
        found_nested_count = 0
        for root, _, files in os.walk(parent_output_directory):
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file_path)
                if ext.lower() in ARCHIVE_EXTENSIONS:
                    abs_path = os.path.abspath(file_path)
                    if abs_path not in self.processed_archives:
                        self.extraction_queue.append(file_path)
                        found_nested_count += 1
                        print(f"已加入嵌套压缩包到队列: {file_path}")
                    else:
                        print(f"跳过已处理的嵌套压缩包: {file_path}")
        
        if found_nested_count > 0:
            self.status_label.config(text=f"找到 {found_nested_count} 个嵌套压缩包，已加入队列。")
        else:
            self.status_label.config(text=f"'{parent_archive_name}' 中未找到新的嵌套压缩包。")
        self.update_idletasks()


    def _process_extraction_queue(self):
        if not self.extraction_queue:
            self.status_label.config(text="所有解压任务均已处理完毕。")
            self._set_controls_state(tk.NORMAL)
            self.update_idletasks()
            return

        current_archive_path = self.extraction_queue.popleft()
        abs_current_archive_path = os.path.abspath(current_archive_path)

        if abs_current_archive_path in self.processed_archives:
            print(f"跳过已处理文件: {current_archive_path}")
            self.status_label.config(text=f"跳过已处理: {os.path.basename(current_archive_path)}")
            self.after(0, self._process_extraction_queue) # Process next immediately
            return

        self.processed_archives.add(abs_current_archive_path)
        
        archive_name = os.path.basename(current_archive_path)
        output_directory = f"./extracted_{archive_name}_{len(self.processed_archives)}/" # Unique enough for this app

        self.status_label.config(text=f"准备解压: {archive_name} (队列剩余: {len(self.extraction_queue)})")
        self.update_idletasks()

        current_password = None
        max_retries = 3 # Password retries for the current archive
        retries_count = 0

        # This inner loop for password attempts can remain synchronous as it involves user interaction
        # or quick checks. The GUI update is handled by `simpledialog`.
        while True: 
            if retries_count == 0:
                self.status_label.config(text=f"开始解压: {archive_name}...")
            else:
                self.status_label.config(text=f"使用密码重试 ({retries_count}/{max_retries}): {archive_name}...")
            self.update_idletasks()

            status, message = extract_archive(abs_current_archive_path, output_directory, 
                                              winrar_path=self.winrar_path, password=current_password)
            print(f"解压尝试: {abs_current_archive_path}, 状态: {status}, 信息: {message}, 使用密码: {'是' if current_password else '否'}, WinRAR路径: {self.winrar_path}")

            if status == 'success':
                self.status_label.config(text=f"成功: {archive_name} 已解压。")
                self.update_idletasks()
                self._scan_and_enqueue_nested_archives(output_directory, archive_name)
                break # Breaks password loop, then proceeds to next item in queue via self.after
            elif status == 'password_needed' or status == 'wrong_password':
                if retries_count >= max_retries:
                    self.status_label.config(text=f"失败: {archive_name} 达到最大密码尝试次数。")
                    break 
                
                prompt_title = "需要密码" if status == 'password_needed' else "密码错误或无效"
                prompt_message = f"压缩文件 '{archive_name}' 需要密码:" if status == 'password_needed' \
                                 else f"密码错误或压缩文件损坏。请为 '{archive_name}' 输入正确密码:"
                
                current_password = simpledialog.askstring(prompt_title, prompt_message, parent=self)
                
                if current_password is None: # User cancelled dialog
                    self.status_label.config(text=f"用户取消: {archive_name} 的密码输入。")
                    break 
                retries_count += 1
            elif status == 'failure':
                # Log full message for debugging first
                print(f"详细错误 for {archive_name}: {message}")

                # Define message_short based on the current 'message'
                if "磁盘已满" in message or "空间不足" in message:
                     message_short = f"磁盘空间不足或权限问题导致写入文件失败。"
                elif "损坏" in message or "CRC" in message.upper(): # CRC often implies corruption
                     message_short = f"文件可能已损坏或格式不支持。"
                elif "权限不足" in message:
                     message_short = f"文件/目录权限不足。"
                else:
                     # Ensure message is not None before calling splitlines, provide a default.
                     message_short = message.splitlines()[0] if message else "未知错误。"
                
                self.status_label.config(text=f"失败: {archive_name} - {message_short}")
                break
            else: # Unknown status
                self.status_label.config(text=f"未知状态: {archive_name} - {message}")
                break
        
        # Schedule next item from queue
        self.after(100, self._process_extraction_queue)


if __name__ == "__main__":
    app = App()
    app.mainloop()
