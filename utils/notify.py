import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def send_email(
    smtp_server,
    smtp_port,
    sender_email,
    sender_password,
    receiver_email,
    subject,
    body,
    attachment_path=None
):
    """
    发送邮件函数，根据端口自动切换 SSL 或 TLS
    """
    
    # 1. 创建邮件容器
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # 2. 添加正文
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    # 3. 处理附件
    if attachment_path and os.path.exists(attachment_path):
        try:
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(part)
        except Exception as e:
            print(f"附件处理错误: {e}")
            return

    server = None
    try:
        # --- 核心修改：根据端口切换连接方式 ---
        if smtp_port == 465:
            # 端口 465：使用 SMTP_SSL (全程加密)
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # 端口 587 或其他：使用普通 SMTP + starttls
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.set_debuglevel(1)
            server.starttls()

        # 登录并发送
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print("邮件发送成功")
        
    except smtplib.SMTPException as e:
        print(f"SMTP错误: {e}")
    except Exception as e:
        print(f"发送失败: {e}")
    finally:
        if server:
            server.quit()

# --- 您的原始内容 ---
html_content = """
<h2>最新成绩通知</h2>
<p>检测到您的成绩有更新，详情如下：</p>
<table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;">
    <thead>
        <tr style="background-color: #f2f2f2;">
            <th style="border: 1px solid #dddddd; text-align: left; padding: 8px;">课程名称</th>
            <th style="border: 1px solid #dddddd; text-align: left; padding: 8px;">成绩</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">高等数学</td>
            <td style="border: 1px solid #dddddd; text-align: left; padding: 8px; color: red;">98</td>
        </tr>
    </tbody>
</table>
<p>请登录教务系统查看完整信息。</p>
"""

# --- 使用示例 ---
if __name__ == "__main__":
    # 配置信息
    SMTP_HOST = "smtp.xx.com"
    SMTP_PORT = 465                 # 更改此处测试：465 或 587
    MY_EMAIL = "xx@xx.com"
    MY_PASS = "xx"    
    TO_EMAIL = "xx@xx.com"

    send_email(
        smtp_server=SMTP_HOST,
        smtp_port=SMTP_PORT,
        sender_email=MY_EMAIL,
        sender_password=MY_PASS,
        receiver_email=TO_EMAIL,
        subject="Python 邮件测试",
        body=html_content,
    )