import subprocess
import os

def extract_archive(archive_path, output_directory, winrar_path="C:/Program Files/WinRAR/WinRAR.exe", password=None):
    """
    使用 WinRAR 解压压缩文件，支持密码。

    Args:
        archive_path (str): 压缩文件的路径。
        output_directory (str): 文件解压到的目录。
        winrar_path (str, optional): WinRAR.exe 的完整路径。
                                     默认为 "C:/Program Files/WinRAR/WinRAR.exe"。
        password (str, optional): 压缩文件的密码。默认为 None。

    Returns:
        tuple: (status: str, message: str)
               状态可能为: 'success', 'failure', 'password_needed', 'wrong_password'。
    """
    if not os.path.exists(winrar_path):
        return 'failure', f"错误：未找到 WinRAR 执行文件路径：{winrar_path}"

    try:
        os.makedirs(output_directory, exist_ok=True)
    except OSError as e:
        return 'failure', f"创建输出目录 {output_directory} 失败：{e} (可能是权限不足或磁盘已满)"

    # Command: WinRAR.exe x <archive_path> <output_directory>
    # Note: WinRAR expects the output directory to end with a backslash if it's a folder.
    # We ensure output_directory path format is suitable for WinRAR.
    if not output_directory.endswith(os.path.sep):
        output_directory += os.path.sep
        
    command = [winrar_path, "x"] # Base command
    
    if password:
        command.append(f"-p{password}")
    else:
        # 对于无密码的情况，不添加 -p 开关。
        # WinRAR -p- 开关用于提供空密码，这与不提供密码不同。
        pass

    command.extend([archive_path, output_directory])

    try:
        # 使用 creationflags=subprocess.CREATE_NO_WINDOW 来避免在 Windows 上弹出控制台窗口
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
        stdout, stderr = process.communicate()
        return_code = process.returncode

        if return_code == 0:
            return 'success', "解压成功。"
        else:
            # WinRAR Exit Codes:
            # 0  Success
            # 1  Warning (non-fatal error). For example, one or more files were locked during processing.
            # 2  Fatal error.
            # 3  CRC error (wrong password for encrypted file or corrupted file).
            # 4  Attempt to modify a locked archive.
            # 5  Write error (disk full?).
            # 6  Open file error.
            # 7  Wrong command line option.
            # 8  Not enough memory.
            # 9  Create file error.
            # 10 No files to extract found / Wrong password.
            # 11 Wrong password.
            # 255 User break.
            
            winrar_output = ""
            if stdout: winrar_output += f"标准输出: {stdout.strip()}\n"
            if stderr: winrar_output += f"错误输出: {stderr.strip()}"

            error_detail = f"WinRAR 解压失败，退出代码: {return_code}。"
            if winrar_output.strip():
                 error_detail += f" 详情: {winrar_output.strip()}"

            if return_code == 10 or return_code == 3: # Code 3 can be CRC error due to wrong password or corruption. Code 10 for "No files" or "Wrong password"
                if password:
                    return 'wrong_password', f"密码不正确或压缩文件已损坏。{error_detail}"
                else: # No password was tried
                    return 'password_needed', f"解压失败，可能需要密码或文件已损坏。{error_detail}"
            elif return_code == 5 or return_code == 9: # Write error or Create file error
                 return 'failure', f"写入文件失败，可能磁盘已满或权限不足。{error_detail}"
            else: # Other errors
                return 'failure', f"解压过程中发生未知错误。{error_detail}"
            
    except FileNotFoundError: # WinRAR.exe not found at specified path
        return 'failure', f"错误：启动 WinRAR 失败，未找到执行文件于 {winrar_path}。请检查路径配置。"
    except PermissionError:
        return 'failure', f"错误：启动 WinRAR 失败，权限不足。请检查文件权限：{winrar_path}"
    except Exception as e: # Other unexpected errors during Popen or communicate
        return 'failure', f"启动 WinRAR 或执行解压时发生未知错误: {e}"

if __name__ == '__main__':
    # 示例用法 (直接测试此模块)
    print("测试 decompressor.py...")
    print("请确保 WinRAR 已安装且路径可访问。")
    print("如果 'test_files' 目录不存在，将创建它。")
    os.makedirs("test_files", exist_ok=True)
    os.makedirs("test_files/extracted_no_pwd", exist_ok=True)
    os.makedirs("test_files/extracted_with_pwd", exist_ok=True)
    os.makedirs("test_files/extracted_wrong_pwd", exist_ok=True)
    os.makedirs("test_files/extracted_corrupted", exist_ok=True)


    dummy_content = "这是一个用于WinRAR测试的虚拟文件。"
    with open("test_files/dummy.txt", "w", encoding='utf-8') as f:
        f.write(dummy_content)

    print("\n重要提示：为使以下测试正常工作，您需要手动创建以下压缩包:")
    print("1. 'test_files/no_password.rar' 包含 'dummy.txt' (无密码).")
    print("2. 'test_files/with_password.rar' 包含 'dummy.txt' (密码: 'secret').")
    print("3. 'test_files/corrupted.rar' (一个已损坏的RAR文件).")
    print("您可以使用 WinRAR GUI 从 'test_files/dummy.txt' 创建这些压缩包。")

    # 测试 1: 无密码压缩包
    if os.path.exists("test_files/no_password.rar"):
        status, message = extract_archive("test_files/no_password.rar", "test_files/extracted_no_pwd/")
        print(f"\n测试 1 (no_password.rar, 未提供密码): 状态: {status}, 信息: {message}")
        if status == 'success' and os.path.exists("test_files/extracted_no_pwd/dummy.txt"):
            print("验证: dummy.txt 在 extracted_no_pwd 中找到。")
        elif status == 'success':
            print("验证: dummy.txt 未在 extracted_no_pwd 中找到。")
    else:
        print("\n跳过测试 1: 'test_files/no_password.rar' 未找到。")

    # 测试 2: 带密码压缩包，提供正确密码
    if os.path.exists("test_files/with_password.rar"):
        status, message = extract_archive("test_files/with_password.rar", "test_files/extracted_with_pwd/", password="secret")
        print(f"\n测试 2 (with_password.rar, 提供正确密码 'secret'): 状态: {status}, 信息: {message}")
        if status == 'success' and os.path.exists("test_files/extracted_with_pwd/dummy.txt"):
            print("验证: dummy.txt 在 extracted_with_pwd 中找到。")
        elif status == 'success':
            print("验证: dummy.txt 未在 extracted_with_pwd 中找到。")
    else:
        print("\n跳过测试 2: 'test_files/with_password.rar' 未找到。")

    # 测试 3: 带密码压缩包，未提供密码
    if os.path.exists("test_files/with_password.rar"):
        status, message = extract_archive("test_files/with_password.rar", "test_files/extracted_wrong_pwd/")
        print(f"\n测试 3 (with_password.rar, 未提供密码): 状态: {status}, 信息: {message}")
    else:
        print("\n跳过测试 3: 'test_files/with_password.rar' 未找到。")

    # 测试 4: 带密码压缩包，提供错误密码
    if os.path.exists("test_files/with_password.rar"):
        status, message = extract_archive("test_files/with_password.rar", "test_files/extracted_wrong_pwd/", password="wrongpassword")
        print(f"\n测试 4 (with_password.rar, 提供错误密码): 状态: {status}, 信息: {message}")
    else:
        print("\n跳过测试 4: 'test_files/with_password.rar' 未找到。")

    # 测试 5: 损坏的压缩包
    if os.path.exists("test_files/corrupted.rar"):
        status, message = extract_archive("test_files/corrupted.rar", "test_files/extracted_corrupted/")
        print(f"\n测试 5 (corrupted.rar, 尝试解压损坏文件): 状态: {status}, 信息: {message}")
    else:
        print("\n跳过测试 5: 'test_files/corrupted.rar' 未找到。")

    # 测试 6: WinRAR 路径无效 (可选, 手动测试通过修改 winrar_path)
    # status, message = extract_archive("test_files/no_password.rar", "./extracted_test", winrar_path="C:/无效路径/WinRAR.exe")
    # print(f"\n测试 6 (WinRAR 路径无效): 状态: {status}, 信息: {message}")
    
    print("\n注意: 对于 'password_needed' 和 'wrong_password' 状态，信息字段包含来自WinRAR的详细错误输出。")
    print("测试后可能需要手动清理 'test_files' 目录。")


def is_archive_winrar(filepath, winrar_path):
    """
    Checks if a file is a valid archive using WinRAR's test command.

    Args:
        filepath (str): Path to the file to check.
        winrar_path (str): Path to WinRAR.exe.

    Returns:
        bool: True if WinRAR recognizes it as an archive (even if passworded or corrupted), False otherwise.
    """
    if not os.path.exists(filepath):
        print(f"is_archive_winrar: File not found at {filepath}")
        return False # File itself doesn't exist

    command = [winrar_path, "t", "-y", "-p-", filepath]
    # Exit codes indicating WinRAR recognized it as some form of archive:
    # 0: Success (valid, non-passworded or empty password)
    # 1: Warning (non-fatal error, e.g., file locked, but still an archive)
    # 3: CRC error (corrupted data, but it's an archive)
    # 10: Incorrect password / No files found (implies it's an archive that's likely password-protected)
    # 11: Wrong password (explicitly a password-protected archive)
    recognized_archive_exit_codes = {0, 1, 3, 10, 11}

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
        
        if result.returncode in recognized_archive_exit_codes:
            # print(f"is_archive_winrar: '{filepath}' IS an archive. WinRAR exit code: {result.returncode}")
            return True
        else:
            # print(f"is_archive_winrar: '{filepath}' is NOT an archive or error. WinRAR exit code: {result.returncode}")
            # print(f"is_archive_winrar: Stderr: {result.stderr.decode(errors='replace').strip()}")
            return False
    except FileNotFoundError:
        # This would typically mean winrar_path is incorrect, but main.py should check winrar_path availability.
        # Or, less likely, filepath moved/deleted between os.path.exists and here.
        print(f"is_archive_winrar: Error - WinRAR executable not found at {winrar_path} or file '{filepath}' vanished.")
        return False
    except Exception as e:
        print(f"is_archive_winrar: An unexpected error occurred while testing archive '{filepath}': {e}")
        return False
