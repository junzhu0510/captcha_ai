import requests
import pytesseract
from PIL import Image, ImageFont, ImageEnhance
from io import BytesIO
import time
import re
import os
import sys
import random

# 设置pytesseract路径（请修改为你的Tesseract OCR安装路径）
# 默认Windows安装路径通常是 'C:\Program Files\Tesseract-OCR\tesseract.exe'
# 如果你的Tesseract安装在其他位置，请修改下面的路径
pytesseract.pytesseract.tesseract_cmd = r'D:\captcha_login_ai\tesseract-5.5.1\tesseract.exe'

# 登录URL
LOGIN_URL = 'http://127.0.0.1:5000/login'
CAPTCHA_URL = 'http://127.0.0.1:5000/captcha'
MAIN_URL = 'http://127.0.0.1:5000/'

# 登录凭据
USERNAME = 'admin'
PASSWORD = '123456'

# 统计数据
total_attempts = 0
successful_logins = 0
captcha_accuracy = 0

def check_tesseract_installed():
    """
    检查Tesseract OCR是否已安装
    """
    try:
        # 尝试执行tesseract命令
        import subprocess
        subprocess.run([pytesseract.pytesseract.tesseract_cmd, '--version'], 
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def save_debug_image(img, filename="debug_captcha.png"):
    """
    保存图像用于调试
    """
    try:
        img.save(filename)
        print(f"已保存调试图像到: {filename}")
    except Exception as e:
        print(f"保存调试图像失败: {str(e)}")

def recognize_captcha(session):
    """
    获取并识别验证码
    """
    # 检查Tesseract是否已安装
    if not check_tesseract_installed():
        print("\n错误: Tesseract OCR未安装或路径设置不正确!")
        print("\n请按照以下步骤安装Tesseract OCR:")
        print("1. 从https://github.com/UB-Mannheim/tesseract/wiki下载并安装Tesseract")
        print("2. 确保安装时选择'添加到系统PATH'选项")
        print("3. 修改脚本中的pytesseract.pytesseract.tesseract_cmd变量为你的安装路径")
        print("   例如: pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'")
        print("\n如果已安装但仍然出现此错误，请检查路径是否正确设置。")
        sys.exit(1)
    
    try:
        # 获取验证码图片
        response = session.get(CAPTCHA_URL)
        img = Image.open(BytesIO(response.content))
        
        # 保存原始图像用于调试
        save_debug_image(img, "original_captcha.png")
        
        # 增强图像预处理以提高OCR准确率
        # 转换为灰度图
        img = img.convert('L')
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)  # 增强对比度
        
        # 二值化处理，使用更适合数字识别的阈值
        threshold = 150  # 调整阈值以获得更好的结果
        img = img.point(lambda x: 0 if x < threshold else 255, '1')
        
        # 保存预处理后的图像用于调试
        save_debug_image(img, "preprocessed_captcha.png")
        
        # 使用多种PSM模式尝试识别
        psm_modes = [7, 8, 6, 10]  # 不同的页面分割模式
        captcha_results = []
        
        for psm in psm_modes:
            # 使用pytesseract识别验证码，尝试不同的配置
            config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
            result = pytesseract.image_to_string(img, config=config).strip()
            
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

def attempt_login():
    """
    尝试登录一次
    """
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
        captcha_text = recognize_captcha(session)
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
        if "登录成功" in response.text:
            successful_logins += 1
            print("登录成功!")
            return True
        else:
            print("登录失败!")
            # 保存响应内容用于调试
            with open("login_response.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("已保存登录响应到login_response.html")
            return False
    except Exception as e:
        print(f"登录过程中出现错误: {str(e)}")
        return False

def main():
    """
    主函数，执行多次登录尝试并统计结果
    """
    print("开始自动化登录测试...")
    print("确保Flask应用正在运行于 http://127.0.0.1:5000/")
    print("注意: 将保存验证码图像用于调试")
    
    num_attempts = 10  # 尝试次数
    
    for i in range(num_attempts):
        print(f"\n尝试 #{i+1}:")
        success = attempt_login()
        if success is None:  # 如果遇到严重错误，退出循环
            break
        time.sleep(1)  # 避免请求过于频繁
    
    # 打印统计结果
    success_rate = (successful_logins / total_attempts) * 100 if total_attempts > 0 else 0
    print(f"\n测试完成!")
    print(f"总尝试次数: {total_attempts}")
    print(f"成功登录次数: {successful_logins}")
    print(f"登录成功率: {success_rate:.2f}%")

if __name__ == "__main__":
    main()