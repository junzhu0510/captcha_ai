from flask import Flask, render_template, request, session, redirect, url_for, make_response
from io import BytesIO
import random
import string
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 用户数据（实际应用中应使用数据库）
users = {
    'admin': '123456',
    'user': 'password'
}

# 生成验证码图片
def generate_captcha(length=4):
    # 生成随机数字
    captcha_text = ''.join(random.choices(string.digits, k=length))
    
    # 创建图片
    width, height = 120, 50
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 使用默认字体，但尝试使用更清晰的字体大小
    try:
        # 尝试加载系统字体
        font_path = None
        if os.name == 'nt':  # Windows
            font_path = 'C:\Windows\Fonts\Arial.ttf'
        elif os.name == 'posix':  # Linux/Mac
            font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
            if not os.path.exists(font_path):
                font_path = '/System/Library/Fonts/Helvetica.ttc'  # Mac
        
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 30)  # 使用更大的字体
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    # 绘制文本
    text_width = 80
    text_height = 30
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # 绘制每个字符，位置更加固定，减少随机性
    for i, char in enumerate(captcha_text):
        pos = (x + i * 20, y)
        draw.text(pos, char, fill=(0, 0, 0), font=font)
    
    # 减少干扰线数量，使其更容易识别
    for _ in range(2):  # 减少干扰线
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        draw.line([start, end], fill=(200, 200, 200))  # 使用浅灰色
    
    # 减少噪点数量，使其更容易识别
    for _ in range(100):  # 减少噪点
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=(200, 200, 200))  # 使用浅灰色
    
    # 打印生成的验证码，用于调试
    print(f"生成的验证码: {captcha_text}")
    
    return captcha_text, image

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        captcha = request.form['captcha']
        
        # 验证用户名和密码
        if username in users and users[username] == password:
            # 验证验证码
            if 'captcha' in session and captcha == session['captcha']:
                session['logged_in'] = True
                session['username'] = username
                return render_template('login.html', message='登录成功')
            else:
                error = '验证码错误'
        else:
            error = '用户名或密码错误'
    
    # 生成新的验证码
    captcha_text, _ = generate_captcha()
    session['captcha'] = captcha_text
    
    return render_template('login.html', error=error)

@app.route('/captcha')
def captcha():
    # 生成验证码图片
    captcha_text, image = generate_captcha()
    session['captcha'] = captcha_text
    
    # 将图片转换为响应
    buffer = BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'image/jpeg'
    return response

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)