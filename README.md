# HubStudio 自动化控制库 (HubStudio Automated Control Library)

一个用于通过 Selenium 与 HubStudio 客户端 API 交互来自动化 Web 任务的 Python 库。

## 特性

-   **HubStudio 集成:**
    -   列出可用的 HubStudio 容器。
    -   打开 HubStudio 容器并连接 Selenium WebDriver。
    -   关闭 HubStudio 容器。
-   **Selenium WebDriver 操作:**
    -   打开 URL、新页面/标签页。
    -   管理浏览器窗口 (关闭其他窗口)。
    -   填充输入字段。
    -   点击元素。
    -   从下拉列表中选择选项。
-   **工具函数:**
    -   从文本文件读取结构化数据 (例如，账户信息、名称)。
    -   从通用文本文件读取行。
    -   从元素列表生成随机输入字符串。
-   **外部 API 交互:**
    -   从可配置的 API 端点获取验证码。

## 先决条件

-   Python 3.7+
-   已安装并正在运行的 HubStudio 客户端。
-   ChromeDriver 可执行文件可访问 (其路径可配置)。

## 安装

1.  **克隆仓库或下载 `hubstudio-automated-control.py`:**
    ```bash
    # 如果你已经设置了 Git 仓库:
    git clone https://github.com/wdc1209/hubstudio-automated-control.git
    cd hubstudio-automated-control
    ```
    否则，只需将 `hubstudio-automated-control.py` 放入你的项目目录。

2.  **安装所需的 Python 包:**
    ```bash
    pip install requests selenium
    ```

## 配置

某些函数具有可能需要调整的默认路径或 URL：

-   `open_container()`:
    -   `extension_path`: 默认为 `r'C:\Users\Administrator\AppData\Roaming\hubstudio-client\UserExtension\nkbihfbeogaeaoehlefnkodbefgpgknn\11.7.4\nkbihfbeogaeaoehlefnkodbefgpgknn.crx'`
    -   `chromedriver_executable_path`: 默认为 `r'C:\windows\chromedriver.exe'`
    这些路径是系统特定的，如果你的设置不同，应覆盖它们。

-   `get_verification_code_from_api()`:
    -   `api_url`: 默认为一个特定的 Google Apps Script URL。如果你使用不同的 API 端点，请更改此项。

## 使用示例

```python
import time
import random # 在示例中添加
from hubstudio_automated_control import (
    open_container,
    close_container,
    open_url,
    fill_input_field,
    click_element,
    get_accounts_from_file
)

# --- 配置 ---
# 如果你的 ChromeDriver 不在库使用的默认位置，请指定其路径
CHROME_DRIVER_PATH = r"path/to/your/chromedriver.exe" 
# 如果你的 HubStudio 扩展不在默认位置，请指定其路径
HS_EXTENSION_PATH = r"path/to/your/hubstudio_extension.crx" 

ACCOUNTS_FILE = "my_accounts.txt" # 确保此文件存在且格式正确
# 根据你的账户文件结构定义字段
ACCOUNT_FIELDS = ['index', 'container_id', 'email', 'password', 'notes'] 

def main():
    accounts = get_accounts_from_file(ACCOUNTS_FILE, expected_fields=ACCOUNT_FIELDS)
    if not accounts:
        print("未找到账户或读取文件出错。")
        return

    for account in accounts:
        container_id = account.get('container_id')
        email = account.get('email')
        
        if not container_id:
            print(f"因缺少 container_id 跳过账户: {account}")
            continue

        print(f"正在处理账户: {email} (容器: {container_id})")
        
        driver = open_container(
            container_id,
            extension_path=HS_EXTENSION_PATH, # 如有必要，覆盖默认值
            chromedriver_executable_path=CHROME_DRIVER_PATH # 如有必要，覆盖默认值
        )

        if driver:
            try:
                open_url(driver, "https://example.com/login")
                time.sleep(2) # 允许页面加载

                fill_input_field(driver, "//input[@id='username']", email)
                fill_input_field(driver, "//input[@id='password']", account.get('password', ''))
                click_element(driver, "//button[@type='submit']")
                
                print(f"{email} 的登录尝试已完成。")
                time.sleep(5) # 观察结果或等待下一页

            except Exception as e:
                print(f"处理 {email} 时发生错误: {e}")
            finally:
                close_container(container_id)
                driver = None # 清除 driver 对象
                print(f"已关闭容器 {container_id}")
        else:
            print(f"为账户 {email} 打开容器 {container_id} 失败")
        
        print("-" * 30)
        time.sleep(random.randint(5,10)) # 账户间暂停

if __name__ == "__main__":
    main()