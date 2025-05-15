# HubStudio 自动化控制库 (HubStudio Automated Control Library)

一个用于通过 Selenium 与 HubStudio 客户端 API 交互来自动化 Web 任务的 Python 库，并包含 Google Sheets 集成功能。

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
-   **EVM 钱包功能 (在 `hubstudio_automated_control.py` 中):**
    -   生成新的 EVM 钱包 (地址、私钥、助记词)。
    -   查询 EVM 钱包地址的余额。
-   **Google Sheets 集成 (通过独立的 `google_sheets_helper.py` 模块):**
    -   从 Google Sheets 读取数据。
    -   向 Google Sheets 写入数据 (支持先清除再写入)。
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
-   **对于 Google Sheets 功能：**
    -   Google Cloud Project 及已启用的 Google Sheets API。
    -   服务账户 JSON 密钥文件。
    -   目标 Google Sheet 已共享给服务账户并授予编辑权限。

## 安装

1.  **克隆仓库:**
    ```bash
    git clone https://github.com/wdc1209/hubstudio-automated-control.git
    cd hubstudio-automated-control
    ```
    仓库中包含 `hubstudio_automated_control.py` (核心 HubStudio 和 Selenium 功能) 和 `google_sheets_helper.py` (Google Sheets 功能)。

2.  **安装所需的 Python 包:**
    *   **基础包:**
        ```bash
        pip install requests selenium eth-account web3
        ```
    *   **Google Sheets 功能所需额外包:**
        ```bash
        pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib pandas
        ```
        (Pandas 主要用于数据处理，`google_sheets_helper.py` 本身不强制依赖它进行API调用，但通常与表格数据处理一起使用)。

## 配置

### HubStudio 及通用配置 (`hubstudio_automated_control.py`)

某些函数具有可能需要调整的默认路径或 URL：

-   `open_container()`:
    -   `DEFAULT_EXTENSION_PATH`: 默认为 `r'C:\Users\Administrator\AppData\Roaming\hubstudio-client\UserExtension\nkbihfbeogaeaoehlefnkodbefgpgknn\11.7.4\nkbihfbeogaeaoehlefnkodbefgpgknn.crx'`
    -   `DEFAULT_CHROMEDRIVER_PATH`: 默认为 `r'C:\windows\chromedriver.exe'`
    这些路径是系统特定的，如果你的设置不同，应在使用时作为参数覆盖它们。

-   `get_verification_code_from_api()`:
    -   `GET_CODE_API_URL_DEFAULT`: 默认为一个特定的 Google Apps Script URL。如果你使用不同的 API 端点，请更改此项或在使用时作为参数传递。

-   `get_evm_balance()`:
    -   `DEFAULT_EVM_RPC_URL`: 默认为 Sepolia 测试网的 Infura URL。**请务必将其中的 `YOUR_INFURA_PROJECT_ID` 替换为你的 Infura 项目 ID**，或替换为其他 RPC URL。
    -   `DEFAULT_EVM_CHAIN_ID`: 默认为 Sepolia (11155111)。

### Google Sheets 配置 (`google_sheets_helper.py`)

`google_sheets_helper.py` 模块需要配置服务账户 JSON 密钥文件以进行身份验证。

1.  **获取服务账户 JSON 密钥文件：**
    *   在 Google Cloud Console 中为你的项目创建一个服务账户。
    *   确保为项目启用了 "Google Sheets API"。
    *   为服务账户生成一个 JSON 密钥文件并下载。
    *   **重要：将此 JSON 文件安全保存。切勿将其提交到公共 Git 仓库！**

2.  **配置脚本使用的密钥文件路径：**
    *   将下载的 JSON 密钥文件（例如 `my-project-12345-abcdef.json`）放置在你的项目目录中。
    *   `google_sheets_helper.py` 中的 `DEFAULT_SERVICE_ACCOUNT_FILE` 常量默认为 `'your_service_account_key.json'`。
    *   你有以下几种方式让脚本找到你的密钥文件：
        *   **推荐：** 在调用 `google_sheets_helper.py` 中的函数时，通过 `service_account_file_path` 参数传递你的 JSON 文件的实际路径。
        *   或者，将你的 JSON 文件重命名为 `your_service_account_key.json` 并与 `google_sheets_helper.py` 放在同一目录（如果你的项目脚本也在此目录）。
        *   或者，如果你直接修改 `google_sheets_helper.py` 供自己使用，可以修改其内部的 `DEFAULT_SERVICE_ACCOUNT_FILE` 常量值。

3.  **共享 Google Sheet：**
    *   打开你希望脚本操作的 Google Sheet。
    *   点击 "共享" (Share)。
    *   将你的服务账户的电子邮件地址（可以在 JSON 密钥文件的 `"client_email"` 字段找到）添加进去，并授予 "编辑者" (Editor) 权限。

## 使用示例

### 示例 1: HubStudio 和 Selenium 操作

```python
import time
import random
# 假设 hubstudio_automated_control.py 在 Python 路径中或同一目录
from hubstudio_automated_control import (
    open_container,
    close_container,
    open_url,
    fill_input_field,
    click_element,
    get_accounts_from_file,
    generate_evm_wallet, # 新增 EVM 功能
    get_evm_balance    # 新增 EVM 功能
)

# --- 配置 ---
# (与你之前的示例相同)
# ...

def main_hubstudio_example():
    # ... (你之前的 HubStudio 示例代码) ...

    # 示例：使用 EVM 功能
    new_wallet = generate_evm_wallet()
    if new_wallet:
        print(f"新生成钱包: {new_wallet['address']}")
        # 使用默认 RPC 查询新钱包余额 (通常为0)
        balance_info = get_evm_balance(new_wallet['address']) 
        if balance_info['error'] is None:
            print(f"余额: {balance_info['balance_eth']} ETH")
        else:
            print(f"查询余额失败: {balance_info['error']}")

if __name__ == "__main__":
    # main_hubstudio_example()
    pass
