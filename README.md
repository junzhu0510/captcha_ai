# 验证码登录系统实验

这个项目是一个带有验证码功能的简单登录系统，包括Web服务端和自动化攻击脚本。

## 文件结构

- `app.py`: Flask Web应用，提供登录页面和验证码功能
- `templates/login.html`: 登录页面模板
- `attack.py`: 自动化攻击脚本，使用OCR技术识别验证码
- `requirements.txt`: 项目依赖列表

## 安装依赖

1. 安装Python依赖包：

```bash
pip install -r requirements.txt
```

2. **安装Tesseract OCR**（必需）：

   自动化攻击脚本使用Tesseract OCR引擎来识别验证码。您必须安装它才能运行`attack.py`。

   ### Windows安装步骤：

   1. 从[UB-Mannheim的GitHub页面](https://github.com/UB-Mannheim/tesseract/wiki)下载Tesseract安装程序
   2. 运行安装程序，建议使用默认安装路径（`C:\Program Files\Tesseract-OCR`）
   3. 确保将Tesseract添加到系统PATH（安装程序通常会提供此选项）
   4. 如果安装到其他位置，请修改`attack.py`中的路径：
      ```python
      pytesseract.pytesseract.tesseract_cmd = r'你的安装路径\tesseract.exe'
      ```

   ### macOS安装步骤：

   使用Homebrew安装：
   ```bash
   brew install tesseract
   ```

   ### Linux安装步骤：

   Ubuntu/Debian：
   ```bash
   sudo apt update
   sudo apt install tesseract-ocr
   ```

   Fedora/RHEL/CentOS：
   ```bash
   sudo dnf install tesseract
   ```

## 运行项目

1. 启动Flask应用：

```bash
python app.py
```

2. 在浏览器中访问：http://127.0.0.1:5000/

3. 运行自动化攻击脚本：

```bash
python attack.py
```

## 登录凭据

- 用户名: `admin`
- 密码: `123456`

## 实验分析

通过运行自动化攻击脚本，可以分析验证码的有效性和OCR识别的准确率。脚本会尝试多次登录并统计成功率。

## 常见问题解决

### 1. Tesseract未找到错误

如果遇到以下错误：
```
pytesseract.pytesseract.TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```

解决方法：
- 确保已安装Tesseract OCR
- 检查`attack.py`中的路径设置是否正确
- 确认Tesseract已添加到系统PATH

### 2. 连接被拒绝错误

如果遇到连接被拒绝错误：
```
ConnectionRefusedError: [WinError 10061] 由于目标计算机积极拒绝，无法连接
```

解决方法：
- 确保Flask应用正在运行
- 检查端口是否被其他应用占用
- 确认防火墙设置允许本地连接