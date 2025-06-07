import requests
import time
import random
import sys
import os
import re
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from datetime import datetime
from io import BytesIO

# 设置URL
MAIN_URL = "http://127.0.0.1:5000/"
LOGIN_URL = "http://127.0.0.1:5000/login"
CAPTCHA_URL = "http://127.0.0.1:5000/captcha"
DASHBOARD_URL = "http://127.0.0.1:5000/dashboard"

# 登录凭据
USERNAME = "admin"
PASSWORD = "123456"

# 设置Tesseract OCR路径
# 默认安装路径，根据实际情况修改
TESSERACT_PATH = r"D:\captcha_login_ai\tesseract-5.5.1\tesseract.exe"

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

def save_debug_image(image, filename):
    """保存图像用于调试"""
    image.save(filename)
    print(f"已保存图像到 {filename}")
    return filename

def recognize_captcha(session):
    """获取并识别验证码"""
    try:
        # 获取验证码图片
        response = session.get(CAPTCHA_URL)
        if response.status_code != 200:
            print(f"获取验证码失败，状态码: {response.status_code}")
            return ''.join([str(random.randint(0, 9)) for _ in range(4)])
        
        # 保存原始验证码图片
        image = Image.open(BytesIO(response.content))
        save_debug_image(image, "original_captcha.png")
        
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
        save_debug_image(binary_image, "preprocessed_captcha.png")
        
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

def extract_flag(html_content):
    """从HTML内容中提取flag"""
    flag_pattern = r'flag\{[^}]*\}'
    match = re.search(flag_pattern, html_content)
    if match:
        return match.group(0)
    return None

def attempt_login_and_get_flag():
    """尝试登录并获取flag，只测试一次"""
    try:
        # 检查Tesseract是否已安装
        if not check_tesseract_installed():
            print("Tesseract OCR未正确安装，无法继续测试")
            return False, None
            
        # 创建会话以保持cookie
        session = requests.Session()
        
        # 访问主页以获取会话
        try:
            session.get(MAIN_URL)
        except requests.exceptions.ConnectionError:
            print("错误: 无法连接到Flask服务器，请确保服务器正在运行于http://127.0.0.1:5000/")
            print("请先运行 'python app.py' 启动Flask应用，然后再运行此脚本。")
            return False, None
        
        # 识别验证码
        captcha_text = recognize_captcha(session)
        print(f"最终使用的验证码: {captcha_text}")
        
        # 提交登录表单
        login_data = {
            'username': USERNAME,
            'password': PASSWORD,
            'captcha': captcha_text
        }
        
        response = session.post(LOGIN_URL, data=login_data, allow_redirects=True)
        
        # 保存响应内容用于分析
        with open("login_response.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # 验证登录是否成功
        if "登录成功" in response.text or response.url.endswith('/dashboard'):
            print("登录成功!")
            
            # 如果登录成功但被重定向，需要访问dashboard页面获取flag
            if not response.url.endswith('/dashboard'):
                dashboard_response = session.get(DASHBOARD_URL)
                dashboard_content = dashboard_response.text
            else:
                dashboard_content = response.text
            
            # 提取flag
            flag = extract_flag(dashboard_content)
            if flag:
                print(f"成功获取flag: {flag}")
                return True, flag
            else:
                print("登录成功但未找到flag")
                return True, None
        else:
            print("登录失败!")
            
            # 分析失败原因
            failure_reason = "未知原因"
            if "验证码错误" in response.text:
                failure_reason = "验证码错误"
            elif "用户名或密码错误" in response.text:
                failure_reason = "用户名或密码错误"
            
            print(f"失败原因: {failure_reason}")
            return False, None
    except Exception as e:
        print(f"登录过程中出现错误: {str(e)}")
        return False, None

def main():
    """主函数，只执行一次登录尝试"""
    print("开始自动化登录测试...")
    print("确保Flask应用正在运行于 http://127.0.0.1:5000/")
    
    success, flag = attempt_login_and_get_flag()
    
    if success:
        print("\n测试结果: 成功")
        if flag:
            print(f"获取的flag: {flag}")
    else:
        print("\n测试结果: 失败")
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()