import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

def main():
    root = tk.Tk()
    root.withdraw() # Hide the main window
    root.attributes("-topmost", True) # Bring to foreground
    
    # Prompt user
    messagebox.showinfo("更換圖片", "因為目前的檔案似乎還沒有成功覆蓋，\n接下來會彈出一個檔案選擇視窗。\n請直接選擇您剛剛下載好的「貓咪圖片」！")
    
    file_path = filedialog.askopenfilename(
        title="選擇新的怪物圖片",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp")]
    )
    
    project_dir = r"C:\Users\user\.gemini\antigravity\scratch\3d-shooter"
    target_path = os.path.join(project_dir, "cat_face.png")
    
    if not file_path:
        messagebox.showwarning("取消", "您沒有選擇圖片，因此將打開原版遊戲喔！")
    else:
        try:
            shutil.copy2(file_path, target_path)
            messagebox.showinfo("成功", "圖片載入成功！即將為您重新打包遊戲，這大概需要幾十秒鐘，請按「確定」並稍候等視窗開啟。")
        except Exception as e:
            messagebox.showerror("錯誤", f"複製圖片失敗：{str(e)}")
            return
            
    # Rebuild
    try:
        os.chdir(project_dir)
        subprocess.run(["Stop-Process", "-Name", "玻璃欣模擬器", "-Force", "-ErrorAction", "SilentlyContinue"], shell=True)
        subprocess.run(["pyinstaller", "--noconfirm", "--clean", "玻璃欣模擬器.spec"], check=True)
        dist_path = os.path.join("dist", "玻璃欣模擬器.exe")
        shutil.copy2(dist_path, "玻璃欣模擬器.exe")
        subprocess.Popen(["玻璃欣模擬器.exe"])
    except Exception as e:
        messagebox.showerror("錯誤", f"打包或啟動失敗：{str(e)}")

if __name__ == "__main__":
    main()
