# HubStudio 自动化控制库 (HubStudio Automated Control Library)

一个用于通过 Selenium 与 HubStudio 客户端 API 交互来自动化 Web 任务的 Python 库包，集成了 EVM 钱包操作和 Google Sheets 数据交互功能。

## 特性

-   **HubStudio 集成 (通过 `hubstudio_automated_control.hub_selenium` 模块):**
    -   列出可用的 HubStudio 容器。
    -   打开 HubStudio 容器并连接 Selenium WebDriver。
    -   关闭 HubStudio 容器。
-   **Selenium WebDriver 操作 (通过 `hubstudio_automated_control.hub_selenium` 模块):**
    -   打开 URL、新页面/标签页。
    -   管理浏览器窗口 (关闭其他窗口)。
    -   填充输入字段、点击元素、从下拉列表中选择选项。
-   **EVM 钱包功能 (通过 `hubstudio_automated_control.hub_selenium` 模块):**
    -   生成新的 EVM 钱包 (地址、私钥、助记词)。
    -   通过 RPC 查询 EVM 钱包地址的余额。
-   **Google Sheets 集成 (通过 `hubstudio_automated_control.google_sheets_helper` 模块):**
    -   从 Google Sheets 读取数据。
    -   向 Google Sheets 写入数据 (支持在写入前清除范围)。
    -   向工作表末尾追加行。
    -   确保工作表存在指定的表头。
-   **工具函数 (通过 `hubstudio_automated_control.hub_selenium` 模块):**
    -   从本地文本文件读取结构化数据 (例如，账户信息、名称)。
    -   从通用文本文件读取所有行。
    -   从元素列表中随机选择并组合成字符串。
-   **外部 API 交互 (通过 `hubstudio_automated_control.hub_selenium` 模块):**
    -   从可配置的 API 端点获取验证码。

## 先决条件

-   Python 3.7 或更高版本。
-   HubStudio 客户端已安装并正在运行。
-   ChromeDriver 可执行文件可访问 (其路径可在库的 `config.json` 中配置，或在调用时指定)。
-   **对于 Google Sheets 功能：**
    -   一个 Google Cloud Project，并已为该项目启用 "Google Sheets API"。
    -   一个服务账户 (Service Account) 及其 JSON 格式的密钥文件。
    -   目标 Google Sheet 必须已与该服务账户的电子邮件地址共享，并授予 "编辑者" 权限。

## 安装

1.  **克隆本仓库:**
    ```bash
    git clone https://github.com/wdc1209/hubstudio-automated-control.git
    cd hubstudio-automated-control
    ```
    本仓库的根目录 (`hubstudio_automated_control`) 即为一个 Python 包。

2.  **安装所需的 Python 依赖包:**
    *   **核心依赖:**
        ```bash
        pip install requests selenium eth-account web3 python-dotenv
        ```
        (`python-dotenv` 用于从 `.env` 文件加载环境变量，方便管理敏感配置。)
    *   **Google Sheets 功能所需额外依赖:**
        ```bash
        pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
        ```
        (注意: `pandas` 库对于直接操作 Google Sheets API 不是必需的，但如果你在处理从 Sheets 读取或写入表格数据时进行复杂的数据转换，它会非常有用。)

## 配置指南

本库的模块 (`hub_selenium.py`, `google_sheets_helper.py`) 会尝试从其**自身所在目录**（即 `hubstudio_automated_control` 包内）的 `config.json` 文件和项目根目录的 `.env` 文件加载默认配置。

**为了在你的项目中使用此库 (例如在 `zan_faucet_script.py` 中)：**

1.  **在你的项目根目录下创建 `.env` 文件:**
    *   此文件用于存放敏感信息，如 API 密钥、服务账户文件名等。**此文件不应提交到 Git 仓库。**
    *   你可以参考库内提供的 `hubstudio_automated_control/.env.example` 文件作为模板。
    *   **示例 `.env` (放在你的项目根目录，例如与 `zan_faucet_script.py` 同级):**
        ```env
        # 项目根目录的 .env 文件
        GOOGLE_SHEETS_SERVICE_ACCOUNT_FILENAME="turnkey-banner-391102-08c5b5a176e3.json"
        INFURA_PROJECT_ID="your_infura_project_id_here"
        # 其他你项目中可能需要的敏感变量
        ```
    *   **将你的服务账户 JSON 密钥文件** (例如 `turnkey-banner-391102-08c5b5a176e3.json`) 放置在你的项目根目录下。

2.  **在你的项目根目录下创建 `config.json` 文件 (可选，用于覆盖库的默认配置或定义应用级配置):**
    *   此文件用于存放非敏感的、应用级别的配置，或者覆盖库模块内部 `config.json` 中的默认值。
    *   库模块 (`hub_selenium.py`, `google_sheets_helper.py`) 内部也有一个 `config.json`，包含它们的通用默认设置。你的项目级 `config.json` 可以为你的特定应用提供定制。
    *   **示例 `config.json` (放在你的项目根目录):**
        ```json
        {
          "AppInfo": {
            "appName": "我的自动化脚本"
          },
          "ZanFaucetGoogleSheets": { // 应用特定的 Sheets 配置
            "spreadsheet_id": "1_D_cxqC8hxOgBjPEdzoGlwsdwG-9h_43WllycCvuC7o",
            "results_sheet_name": "sepolia_领水结果"
          },
          "AppHubStudio": { // 可选：覆盖库中 HubStudio 的默认路径
            "extension_path": "C:\\path\\to\\my\\specific\\extension.crx",
            "chromedriver_path": null // null 表示使用库的默认值
          },
          "AppEVM": { // 可选：覆盖库中 EVM 的默认 RPC
            "rpc_url": "https://your-custom-sepolia-rpc.com"
          }
        }
        ```

### 库内部默认配置说明

*   **`hubstudio_automated_control/config.json`:**
    *   **`HubStudio`**: 包含 `default_extension_path`, `default_chromedriver_path`, `base_api_url`。
    *   **`EVM`**: 包含 `default_rpc_url_template` (其中的 `{INFURA_PROJECT_ID}` 会从 `.env` 文件替换), `default_chain_id`, `default_request_timeout_seconds`。
    *   **`ExternalAPIs`**: 包含 `get_code_api_url_default`。
    *   **`GoogleSheets`** (在 `google_sheets_helper.py` 的 `config.json` 中，如果它有的话，但通常它主要依赖 `.env` 和函数参数): 可能包含 `default_scopes`。
    *   路径通常是示例或通用路径，用户应根据自己的环境在项目级 `config.json` 中覆盖或直接在调用函数时传递参数。

*   **`hubstudio_automated_control/google_sheets_helper.py` 的 `DEFAULT_SERVICE_ACCOUNT_FILE` 常量:**
    默认为 `'your_service_account_key.json'` (占位符)。实际使用的文件名会优先从你项目根目录 `.env` 文件的 `GOOGLE_SHEETS_SERVICE_ACCOUNT_FILENAME` 变量中读取。

## 使用示例

假设你的项目结构如下：
Use code with caution.
Markdown
my_project/
├── zan_faucet_script.py (你的主脚本)
├── .env (你的项目敏感配置)
├── config.json (你的项目普通配置)
├── your_service_account_key.json (Google服务账户密钥文件)
└── hubstudio_automated_control/ (克隆下来的库包)
├── init.py
├── hub_selenium.py
├── google_sheets_helper.py
├── config.json (库的默认配置)
└── .env.example (库的.env模板)
**在 `zan_faucet_script.py` 中:**

```python
import os
import json
from dotenv import load_dotenv
import time

# --- 1. 加载项目配置 ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

APP_CONFIG = {}
app_config_path = os.path.join(PROJECT_ROOT, 'config.json')
if os.path.exists(app_config_path):
    with open(app_config_path, 'r', encoding='utf-8') as f:
        APP_CONFIG = json.load(f)

# --- 2. 导入库模块 ---
from hubstudio_automated_control import hub_selenium as hs_ctl
from hubstudio_automated_control import google_sheets_helper as gs_helper

# --- 3. 使用库 ---

# HubStudio 示例
container_id = "some_container_id_from_your_source"
# 从你的项目配置中获取路径，如果未配置，则库函数会使用其内部默认值
app_extension_path = APP_CONFIG.get('AppHubStudio', {}).get('extension_path')
app_driver_path = APP_CONFIG.get('AppHubStudio', {}).get('chromedriver_path')

# driver = hs_ctl.open_container(
#     container_id,
#     extension_path=app_extension_path, # 如果为 None, open_container 使用其默认
#     chromedriver_executable_path=app_driver_path # 如果为 None, open_container 使用其默认
# )
# if driver:
#     hs_ctl.open_url(driver, "https://example.com")
#     # ... 其他操作 ...
#     hs_ctl.close_container(container_id)

# EVM 钱包示例
new_wallet = hs_ctl.generate_evm_wallet()
if new_wallet:
    print(f"新钱包地址: {new_wallet['address']}")
    app_rpc_url = APP_CONFIG.get('AppEVM', {}).get('rpc_url')
    balance_data = hs_ctl.get_evm_balance(new_wallet['address'], rpc_url=app_rpc_url) # 如果 app_rpc_url 为 None, 使用库的默认RPC
    if balance_data['error'] is None:
        print(f"钱包余额: {balance_data['balance_eth']} ETH")

# Google Sheets 示例
gs_service = None
sa_filename = os.getenv('GOOGLE_SHEETS_SERVICE_ACCOUNT_FILENAME')
if sa_filename:
    sa_full_path = os.path.join(PROJECT_ROOT, sa_filename)
    if os.path.exists(sa_full_path):
        gs_service = gs_helper.get_sheets_service(service_account_file_path=sa_full_path)

if not gs_service: # 如果上述未能初始化，尝试让 gs_helper 使用其内部默认
    gs_service = gs_helper.get_sheets_service()

if gs_service:
    my_spreadsheet_id = APP_CONFIG.get('ZanFaucetGoogleSheets', {}).get('spreadsheet_id')
    my_sheet_name = APP_CONFIG.get('ZanFaucetGoogleSheets', {}).get('results_sheet_name', 'Sheet1')

    if my_spreadsheet_id:
        # 确保表头
        headers = ["钱包地址", "私钥", "助记词", "余额", "时间戳", "状态"]
        gs_helper.ensure_sheet_headers(my_spreadsheet_id, my_sheet_name, headers, service_obj=gs_service)
        
        # 追加数据
        row_to_add = [new_wallet['address'], "******", "******", balance_data['balance_eth'], time.strftime("%Y-%m-%d %H:%M:%S"), "成功"]
        gs_helper.append_rows_to_sheet([row_to_add], my_spreadsheet_id, my_sheet_name, service_obj=gs_service)
        print("数据已追加到 Google Sheet。")
    else:
        print("警告: 未在项目 config.json 中配置 spreadsheet_id。")
else:
    print("错误: 无法初始化 Google Sheets 服务。")
Use code with caution.
主要模块及功能
包名: hubstudio_automated_control
模块: hub_selenium.py (建议在导入时使用别名如 hs_ctl)
open_container(...), close_container(...): 管理 HubStudio 容器。
open_url(...), fill_input_field(...), click_element(...): Selenium 网页操作。
generate_evm_wallet(): 生成 EVM 钱包。
get_evm_balance(...): 查询 EVM 钱包余额。
以及其他文件读取、随机输入等辅助函数。
模块: google_sheets_helper.py (建议在导入时使用别名如 gs_helper)
get_sheets_service(...): 初始化 Google Sheets API 服务。
read_sheet_data(...): 从表格读取数据。
write_sheet_data(...): 向表格写入数据（可覆盖）。
append_rows_to_sheet(...):向表格末尾追加数据行。
ensure_sheet_headers(...): 确保表格存在指定的表头。
