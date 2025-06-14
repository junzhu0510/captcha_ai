import requests
import time
import random
import sys
import os
import re
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
# import cv2  # 注释掉cv2导入，因为它不是必需的
# import numpy as np  # 注释掉numpy导入，因为它不是必需的
from datetime import datetime
from io import BytesIO

# 设置URL
MAIN_URL = "http://127.0.0.1:5000/"
LOGIN_URL = "http://127.0.0.1:5000/login"
CAPTCHA_URL = "http://127.0.0.1:5000/captcha"

# 登录凭据
USERNAME = "admin"
PASSWORD = "123456"

# 设置Tesseract OCR路径
# 默认安装路径，根据实际情况修改
TESSERACT_PATH = r"D:\captcha_login_ai\tesseract-5.5.1\tesseract.exe"

# 统计变量
total_attempts = 0
successful_logins = 0

# 创建实验记录目录
def create_experiment_dir():
    """创建实验记录目录"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_dir = f"experiment_{timestamp}"
    os.makedirs(exp_dir, exist_ok=True)
    return exp_dir

def check_tesseract_installed():
    """检查Tesseract是否已安装"""
    try:
        # 尝试设置Tesseract路径
        if os.path.exists(TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
            print(f"已设置Tesseract路径: {TESSERACT_PATH}")
        else:
            print(f"警告: 指定的Tesseract路径不存在: {TESSERACT_PATH}")
            print("尝试使用系统默认路径...")
            
        # 测试Tesseract是否可用
        pytesseract.get_tesseract_version()
        print("Tesseract OCR 已成功安装和配置")
        return True
    except Exception as e:
        print(f"错误: Tesseract OCR 未正确安装或配置: {str(e)}")
        print("\n请按照以下步骤安装Tesseract OCR:")
        print("1. 从 https://github.com/UB-Mannheim/tesseract/wiki 下载并安装Tesseract")
        print("2. 确保将Tesseract添加到系统PATH中")
        print("3. 或者在脚本中设置正确的TESSERACT_PATH变量")
        print("\n如果已安装，请检查路径是否正确。默认路径通常为:")
        print("Windows: C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        print("Linux/Mac: /usr/bin/tesseract")
        return False

def save_debug_image(image, filename, exp_dir):
    """保存图像用于调试"""
    filepath = os.path.join(exp_dir, filename)
    image.save(filepath)
    print(f"已保存图像到 {filepath}")
    return filepath

def recognize_captcha(session, exp_dir, attempt_num):
    """获取并识别验证码"""
    try:
        # 获取验证码图片
        response = session.get(CAPTCHA_URL)
        if response.status_code != 200:
            print(f"获取验证码失败，状态码: {response.status_code}")
            return ''.join([str(random.randint(0, 9)) for _ in range(4)])
        
        # 保存原始验证码图片
        image = Image.open(BytesIO(response.content))
        original_path = save_debug_image(image, f"original_captcha_{attempt_num}.png", exp_dir)
        
        # 图像预处理
        # 转换为灰度图
        gray_image = image.convert('L')
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(gray_image)
        enhanced_image = enhancer.enhance(2.0)
        
        # 二值化处理
        threshold = 150
        binary_image = enhanced_image.point(lambda x: 255 if x > threshold else 0, '1')
        
        # 保存预处理后的图片
        preprocessed_path = save_debug_image(binary_image, f"preprocessed_captcha_{attempt_num}.png", exp_dir)
        
        # 使用多种PSM模式尝试识别
        psm_modes = [7, 8, 6, 10, 13]  # 不同的页面分割模式
        captcha_results = []
        
        for psm in psm_modes:
            config = f"--psm {psm} --oem 3 -c tessedit_char_whitelist=0123456789"
            result = pytesseract.image_to_string(binary_image, config=config).strip()
            
            # 清理识别结果，只保留数字
            result = re.sub(r'\D', '', result)
            
            if result and len(result) > 0:
                captcha_results.append(result)
                print(f"PSM {psm} 识别结果: '{result}'")
        
        # 如果有任何有效结果，使用最长的一个
        if captcha_results:
            captcha_text = max(captcha_results, key=len)
            if len(captcha_text) > 4:
                captcha_text = captcha_text[:4]  # 截取前4位
            elif len(captcha_text) < 4:
                # 如果识别的数字少于4位，补全到4位
                captcha_text = captcha_text.ljust(4, '0')
        else:
            print("所有PSM模式均未能识别出数字，使用随机猜测")
            captcha_text = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        
        return captcha_text
    except Exception as e:
        print(f"验证码识别过程中出现错误: {str(e)}")
        return ''.join([str(random.randint(0, 9)) for _ in range(4)])

def attempt_login(exp_dir, attempt_num):
    """尝试登录一次"""
    global total_attempts, successful_logins
    
    try:
        # 创建会话以保持cookie
        session = requests.Session()
        
        # 访问主页以获取会话
        try:
            session.get(MAIN_URL)
        except requests.exceptions.ConnectionError:
            print("错误: 无法连接到Flask服务器，请确保服务器正在运行于http://127.0.0.1:5000/")
            print("请先运行 'python app.py' 启动Flask应用，然后再运行此脚本。")
            sys.exit(1)
        
        # 识别验证码
        captcha_text = recognize_captcha(session, exp_dir, attempt_num)
        print(f"最终使用的验证码: {captcha_text}")
        
        # 提交登录表单
        login_data = {
            'username': USERNAME,
            'password': PASSWORD,
            'captcha': captcha_text
        }
        
        response = session.post(LOGIN_URL, data=login_data)
        
        # 检查登录结果
        total_attempts += 1
        
        # 保存响应内容用于分析
        response_path = os.path.join(exp_dir, f"login_response_{attempt_num}.html")
        with open(response_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # 验证登录是否成功
        if "登录成功" in response.text:
            successful_logins += 1
            print("登录成功!")
            
            # 保存成功登录的响应
            success_path = os.path.join(exp_dir, f"login_success_{attempt_num}.html")
            with open(success_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # 记录成功的验证码和图像
            success_log_path = os.path.join(exp_dir, "successful_logins.log")
            with open(success_log_path, "a", encoding="utf-8") as f:
                f.write(f"尝试 #{attempt_num}: 成功登录 - 验证码: {captcha_text}\n")
            
            return True
        else:
            print("登录失败!")
            
            # 分析失败原因
            failure_reason = "未知原因"
            if "验证码错误" in response.text:
                failure_reason = "验证码错误"
            elif "用户名或密码错误" in response.text:
                failure_reason = "用户名或密码错误"
            
            # 记录失败信息
            failure_log_path = os.path.join(exp_dir, "failed_logins.log")
            with open(failure_log_path, "a", encoding="utf-8") as f:
                f.write(f"尝试 #{attempt_num}: 登录失败 - 原因: {failure_reason} - 验证码: {captcha_text}\n")
            
            print(f"失败原因: {failure_reason}")
            print(f"已保存登录响应到 {response_path}")
            return False
    except Exception as e:
        print(f"登录过程中出现错误: {str(e)}")
        
        # 记录错误信息
        error_log_path = os.path.join(exp_dir, "errors.log")
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(f"尝试 #{attempt_num}: 错误 - {str(e)}\n")
        
        return False

def main():
    """主函数，执行多次登录尝试并统计结果"""
    # 检查Tesseract是否已安装
    if not check_tesseract_installed():
        sys.exit(1)
    
    # 创建实验记录目录
    exp_dir = create_experiment_dir()
    print(f"实验记录将保存在目录: {exp_dir}")
    
    print("开始自动化登录测试...")
    print("确保Flask应用正在运行于 http://127.0.0.1:5000/")
    
    # 记录实验开始时间和配置
    experiment_log_path = os.path.join(exp_dir, "experiment.log")
    with open(experiment_log_path, "w", encoding="utf-8") as f:
        f.write(f"实验开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"用户名: {USERNAME}\n")
        f.write(f"密码: {PASSWORD}\n")
        f.write(f"Tesseract路径: {TESSERACT_PATH}\n")
        f.write("-----------------------------------\n")
    
    num_attempts = 10  # 尝试次数
    
    for i in range(num_attempts):
        print(f"\n尝试 #{i+1}:")
        success = attempt_login(exp_dir, i+1)
        if success is None:  # 如果遇到严重错误，退出循环
            break
        time.sleep(1)  # 避免请求过于频繁
    
    # 打印统计结果
    success_rate = (successful_logins / total_attempts) * 100 if total_attempts > 0 else 0
    result_summary = f"\n测试完成!\n总尝试次数: {total_attempts}\n成功登录次数: {successful_logins}\n登录成功率: {success_rate:.2f}%"
    print(result_summary)
    
    # 保存统计结果
    with open(os.path.join(exp_dir, "results.txt"), "w", encoding="utf-8") as f:
        f.write(result_summary)
    
    # 更新实验日志
    with open(experiment_log_path, "a", encoding="utf-8") as f:
        f.write(f"\n实验结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(result_summary)
    
    print(f"\n实验记录已保存到目录: {exp_dir}")
    print("可以查看以下文件了解详细信息:")
    print(f"- {os.path.join(exp_dir, 'experiment.log')} - 实验配置和总结")
    print(f"- {os.path.join(exp_dir, 'successful_logins.log')} - 成功登录记录")
    print(f"- {os.path.join(exp_dir, 'failed_logins.log')} - 失败登录记录")
    print(f"- {os.path.join(exp_dir, 'errors.log')} - 错误记录")
    print(f"- {os.path.join(exp_dir, 'results.txt')} - 结果统计")
    print(f"- 各验证码图像和登录响应HTML文件")

if __name__ == "__main__":
    main()