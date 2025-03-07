# .\.venv\Scripts\Activate.ps1
# pip install pyperclip nbtlib watchdog pywin32

import os
import subprocess
import sys
import nbtlib
import tkinter as tk
from tkinter import ttk, Button, Label, messagebox, filedialog, StringVar, Radiobutton
import win32gui
import pyperclip
import re
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

world_folder_path = None
observer = None
monitor_active = False

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

global seed_button


def is_minecraft_active():
    try:
        active_window = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(active_window)
        return "Minecraft" in window_title
    except:
        return False


def monitor_clipboard():
    last_clipboard = ""
    global monitor_active
    while True:
        try:
            # print("debug1: " + str(monitor_active) + " " + str(is_minecraft_active()))
            # 只在 Minecraft 視窗開啟時才監控剪貼簿
            if monitor_active and is_minecraft_active():
                current_clipboard = pyperclip.paste()
                if current_clipboard != last_clipboard:
                    # 提取維度類型
                    dimension_match = re.search(
                        r"minecraft:([\w_]+)", current_clipboard
                    )
                    if dimension_match:
                        world_type = dimension_match.group(1)
                    if re.search(
                        r"/execute in minecraft:[\w_]+ run tp @s [-\d.]+ [-\d.]+ [-\d.]+ [-\d.]+ [-\d.]+",
                        current_clipboard,
                    ):
                        pattern = r"tp @s ([-\d.]+) [-\d.]+ ([-\d.]+)"
                        match = re.search(pattern, current_clipboard)
                        if match:
                            x_coord = match.group(1)
                            z_coord = match.group(2)
                            # 讀取檔案並處理內容
                            with open(
                                os.path.join(script_dir, "world_info.txt"), "r"
                            ) as f:
                                lines = [line.strip() for line in f.readlines()]

                            # print(f"目前行數: {len(lines)}")
                            # print(f"檔案內容: {lines}")

                            # 確保至少有4行
                            while len(lines) < 4:
                                lines.append("")

                            # 更新座標
                            lines[1] = x_coord
                            lines[2] = z_coord
                            lines[3] = world_type

                            # 寫入檔案
                            with open(
                                os.path.join(script_dir, "world_info.txt"), "w"
                            ) as f:
                                f.write("\n".join(lines) + "\n")
                    # 執行 find_sh_bt.exe
                    result = os.popen(
                        os.path.join(script_dir, "find_structure.exe")
                    ).read()

                    # 更新 structure_label
                    structure_label.config(text=result)

                    last_clipboard = current_clipboard
            time.sleep(0.2)
        except:
            pass


class WorldFolderHandler(FileSystemEventHandler):
    def on_created(self, event):
        global monitor_active
        if event.is_directory:
            time.sleep(2)  # 等待資料夾完全建立
            new_folder = event.src_path
            level_dat_path = os.path.join(new_folder, "level.dat")
            # 啟動監控剪貼簿
            monitor_active = True
            try:
                # 檢查是否存在 level.dat
                if os.path.exists(level_dat_path):
                    level_dat = nbtlib.load(level_dat_path)
                    seed = level_dat["Data"]["WorldGenSettings"]["dimensions"][
                        "minecraft:overworld"
                    ]["generator"]["seed"]

                    # 建立 world_seed.txt
                    with open(os.path.join(script_dir, "world_info.txt"), "w") as f:
                        # 使用正則表達式提取數字
                        seed_str = str(seed)
                        seed_number = re.search(r"-?\d+", seed_str).group()
                        f.write(seed_number)
                    # 執行 find_sh_bt.exe
                    result = os.popen(
                        os.path.join(script_dir, "find_structure.exe")
                    ).read()
                    # 更新 structure_label
                    structure_label.config(text=result)
            except Exception as e:
                print(f"Error: {e}")


def start_monitoring():
    global observer
    if not world_folder_path.get():
        messagebox.showwarning("警告", "請先選擇資料夾路徑")
        return

    event_handler = WorldFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, world_folder_path.get(), recursive=False)
    observer.start()


def open_file_dialog():
    global world_folder_path
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        # 更新路徑標籤
        path_label.config(text=folder_selected)
        # 儲存路徑
        world_folder_path = StringVar(value=folder_selected)
        # 建立 world_location.txt
        with open(os.path.join(script_dir, "world_location.txt"), "w") as f:
            f.write(folder_selected)


def get_seed():
    # 檢查是否已選擇資料夾
    global monitor_active
    if not world_folder_path.get():
        messagebox.showwarning("警告", "請先選擇資料夾路徑")
        return

    # 讀取 level.dat 檔案
    level_dat_path = os.path.join(world_folder_path.get(), "level.dat")
    try:
        # 檢查是否存在 level.dat
        if os.path.exists(level_dat_path):
            level_dat = nbtlib.load(level_dat_path)
            seed = level_dat["Data"]["WorldGenSettings"]["dimensions"][
                "minecraft:overworld"
            ]["generator"]["seed"]

            # 建立 world_info.txt
            with open(os.path.join(script_dir, "world_info.txt"), "w") as f:
                # 使用正則表達式提取數字
                seed_str = str(seed)
                seed_number = re.search(r"-?\d+", seed_str).group()
                f.write(seed_number)
            # 執行 find_sh_bt.exe
            result = os.popen(os.path.join(script_dir, "find_structure.exe")).read()
            # 更新 structure_label
            structure_label.config(text=result)
            # 啟動監控剪貼簿
            monitor_active = True
    except Exception as e:
        print(f"Error: {e}")


def toggle_seed_button(*args):
    global seed_button, observer
    if mode.get() == "existing":
        seed_button.pack(pady=10)
        if observer:
            observer.stop()
            observer.join()
        # 重置監控狀態
        monitor_active = False
        structure_label.config(text="等待世界生成 或 f3+c")
    else:
        seed_button.pack_forget()
        start_monitoring()
        # 重置監控狀態
        monitor_active = False
        structure_label.config(text="等待世界生成 或 f3+c")


# done
def toggle_topmost():
    global window
    if window.attributes("-topmost"):
        window.attributes("-topmost", False)
        topmost_button.config(text="置頂: 關")
    else:
        window.attributes("-topmost", True)
        topmost_button.config(text="置頂: 開")


if __name__ == "__main__":

    window = tk.Tk()

    # 配置 ttk 主題
    world_folder_path = StringVar()
    style = ttk.Style(window)

    # 設定自定義樣式的字型
    myFont = ("Microsoft JhengHei", 11)

    # 創建自定義樣式
    style.configure("My.TButton", font=myFont)
    style.configure("My.TLabel", font=myFont)
    style.configure("My.TRadiobutton", font=myFont)

    window.attributes("-topmost", True)
    topmost_button = ttk.Button(
        window, text="視窗置頂: 開", style="My.TButton", command=toggle_topmost
    )
    topmost_button.pack(pady=(10, 5))

    # 创建一个按钮，点击时会触发open_folder_dialog函数
    choose_button = ttk.Button(
        window, text="選擇路徑", style="My.TButton", command=open_file_dialog
    )
    choose_button.pack(pady=5)

    path_label = ttk.Label(window, text="", style="My.TLabel", wraplength=300)
    path_label.pack(pady=(5, 0))
    if world_folder_path.get():
        path_label.config(text=world_folder_path.get())

    # 檢查並讀取 world_location.txt
    world_location_file = os.path.join(script_dir, "world_location.txt")
    if os.path.exists(world_location_file):
        with open(world_location_file, "r") as f:
            saved_path = f.read().strip()
            if os.path.exists(saved_path):  # 確認路徑真的存在
                world_folder_path.set(saved_path)
                path_label.config(text=saved_path)
                start_monitoring()  # 移到這裡

    # 使用 style.theme_names() 查看可用主題
    # print(style.theme_names())
    style.theme_use("vista")  # 更改為您想要的主題
    window.title("structure_finder")
    window.geometry("320x400")  # 宽度x高度

    mode = StringVar(value="new")
    mode.trace("w", toggle_seed_button)

    row_frame = ttk.Frame(window)
    row_frame.pack(pady=0)

    ttk.Radiobutton(
        row_frame,  # 改為 row_frame
        text="選擇現有世界資料夾",
        variable=mode,
        value="existing",
        style="My.TRadiobutton",
    ).pack(
        side="left", padx=5
    )  # 使用 side='left'

    seed_button = ttk.Button(
        row_frame,  # 改為 row_frame
        text="取得結構座標",
        style="My.TButton",
        command=get_seed,
    )
    seed_button.pack_forget()

    ttk.Radiobutton(
        window,
        text="在saves偵測新生成的世界",
        variable=mode,
        value="new",
        style="My.TRadiobutton",
    ).pack(pady=0)

    structure_label = ttk.Label(
        window, text="等待世界生成 或 f3+c", style="My.TLabel", wraplength=300
    )
    structure_label.pack(pady=5)

    clipboard_thread = threading.Thread(target=monitor_clipboard, daemon=True)
    clipboard_thread.start()

    # 運行視窗
    window.mainloop()
