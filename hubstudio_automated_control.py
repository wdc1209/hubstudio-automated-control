# hubstudio-automated-control.py

import sys
import time
import traceback
import random
import json # 为 get_verification_code 添加
import decimal

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service

from eth_account import Account
from web3 import Web3
from web3.exceptions import TransactionNotFound, ContractLogicError, TimeExhausted


# --- 常量 (考虑将这些设为可配置项或参数) ---
GET_CODE_API_URL_DEFAULT = "https://script.google.com/macros/s/AKfycbwNL63gEfe8QQQ5uEVNAc0PateTv8-ZTFGQ_oG3vT4nlTBLs9OOQ_7lnlwTGN6tE93x5g/exec"
# 这个 EXTENSION_PATH 非常特定于你的设置。
# 对于通用库，这应该是一个参数或以其他方式处理。
DEFAULT_EXTENSION_PATH = r'C:\Users\Administrator\AppData\Roaming\hubstudio-client\UserExtension\nkbihfbeogaeaoehlefnkodbefgpgknn\11.7.4\nkbihfbeogaeaoehlefnkodbefgpgknn.crx'
DEFAULT_CHROMEDRIVER_PATH = r'C:\windows\chromedriver.exe' # 同样是系统特定的

# --- Constants (Consider making these configurable or parameters) ---
GET_CODE_API_URL_DEFAULT = "https://script.google.com/macros/s/AKfycbwNL63gEfe8QQQ5uEVNAc0PateTv8-ZTFGQ_oG3vT4nlTBLs9OOQ_7lnlwTGN6tE93x5g/exec"
DEFAULT_EXTENSION_PATH = r'C:\Users\Administrator\AppData\Roaming\hubstudio-client\UserExtension\nkbihfbeogaeaoehlefnkodbefgpgknn\11.7.4\nkbihfbeogaeaoehlefnkodbefgpgknn.crx'
DEFAULT_CHROMEDRIVER_PATH = r'C:\windows\chromedriver.exe'

# --- 新增：EVM 相关默认配置 (可以根据需要移到脚本开头或作为参数传入) ---
DEFAULT_EVM_RPC_URL = 'https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID' # 请替换为你自己的 Infura Project ID 或其他 RPC
DEFAULT_EVM_CHAIN_ID = 11155111 # Sepolia Chain ID, 更改 RPC 时记得同步修改
DEFAULT_EVM_REQUEST_TIMEOUT_SECONDS = 30

# --- 文件读取函数 ---
def get_name_info_from_file(filepath='names.txt', delimiter='	'):
    """
    从文件中读取名称信息。
    每行应包含由分隔符隔开的 first_name 和 last_name。
    参数:
        filepath (str): 名称文件的路径。
        delimiter (str): 文件中使用的分隔符。
    返回:
        list: 字典列表，每个字典包含 'first_name' 和 'last_name'。
    """
    names_info_list = []
    try:
        with open(filepath, "r", encoding='utf-8') as f: # 改为 utf-8，更通用
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(delimiter)
                if len(parts) > 1:
                    name_info = {
                        'first_name': parts[0],
                        'last_name': parts[1]
                    }
                    names_info_list.append(name_info)
    except FileNotFoundError:
        print(f"错误: 文件未找到 {filepath}")
    except Exception as e:
        print(f"读取名称文件 {filepath} 时出错: {e}")
    return names_info_list


def get_accounts_from_file(filepath, delimiter='	', skip_header=True, expected_fields=None):
    """
    从制表符分隔的文件中读取账户信息。
    参数:
        filepath (str): 账户信息文件的路径。
        delimiter (str): 分隔符字符串。默认为制表符。
        skip_header (bool): 是否跳过第一行（表头）。
        expected_fields (list, optional): 账户字典的键列表。
                                          如果为 None，则使用通用的 'field_0', 'field_1' 等。
    返回:
        list: 字典列表，每个字典代表一个账户。
    """
    accounts_info = []
    try:
        with open(filepath, "r", encoding='gbk') as f: # 保留了原始的 gbk，但可以考虑 utf-8
            if skip_header:
                f.readline()  # 跳过表头行
            
            for line_number, lines in enumerate(f, start=1 if skip_header else 0):
                if not lines.strip():
                    continue
                line_list = lines.strip('\n').split(delimiter)
                acc_info = {}
                if expected_fields:
                    if len(line_list) >= len(expected_fields):
                        for i, field_name in enumerate(expected_fields):
                            acc_info[field_name] = line_list[i]
                    else:
                        print(f"警告: 文件 {filepath} 中的第 {line_number+1} 行字段数少于预期。已跳过。")
                        continue
                else:
                    for i, item in enumerate(line_list):
                        acc_info[f'field_{i}'] = item
                accounts_info.append(acc_info)
    except FileNotFoundError:
        print(f"错误: 文件未找到 {filepath}")
    except Exception as e:
        print(f"读取账户文件 {filepath} 时出错: {e}")
    return accounts_info


def get_text_content(filename):
    """
    从文本文件中读取行到列表中，并去除空白。
    参数:
        filename (str): 文本文件的路径。
    返回:
        list: 字符串列表，每项是文件中的一个非空行。
    """
    text_content = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip(): # 忽略空行
                    text_content.append(line.strip())
    except FileNotFoundError:
        print(f"错误: 文件未找到 {filename}")
    except Exception as e:
        print(f"读取文本文件 {filename} 时出错: {e}")
    return text_content

# --- 工具函数 ---
def random_input_from_list(elements, min_selected, max_selected=None):
    """
    从列表中随机选择若干元素并将它们连接成字符串。
    参数:
        elements (list): 从中选择元素的列表。
        min_selected (int): 要选择的最小元素数量。
        max_selected (int, optional): 要选择的最大元素数量。
                                      默认为 len(elements)。
    返回:
        str: 由空格分隔的所选元素的字符串，或错误消息。
    """
    if not elements:
        return ""
    if min_selected <= 0:
        min_selected = 1
    if max_selected is None or max_selected > len(elements):
        max_selected = len(elements)
    if min_selected > len(elements):
        print("警告: min_selected 大于可用元素数量。将选择所有元素。")
        min_selected = len(elements)
    if min_selected > max_selected:
        print("警告: min_selected 大于 max_selected。将使用 max_selected作为 min_selected。")
        min_selected = max_selected
        
    num_elements_to_select = random.randint(min_selected, max_selected)
    selected_elements = random.sample(elements, num_elements_to_select)
    return ' '.join(selected_elements)

# --- HubStudio API 函数 ---
HUBSTUDIO_BASE_URL = "http://127.0.0.1:6873/api/v1"

def get_containers_list():
    """
    检索 HubStudio 环境列表。
    返回:
        dict: API 的 JSON 响应，如果失败则为 None。
    """
    url = f'{HUBSTUDIO_BASE_URL}/env/list'
    try:
        res = requests.post(url, json={}).json()
        return res
    except requests.exceptions.RequestException as e:
        print(f"获取容器列表时出错: {e}")
        return None

def open_container(container_id, extension_path=DEFAULT_EXTENSION_PATH, chromedriver_executable_path=DEFAULT_CHROMEDRIVER_PATH):
    """
    打开一个 HubStudio 容器并返回一个 Selenium WebDriver 实例。
    参数:
        container_id (str): 要打开的容器 ID。
        extension_path (str): HubStudio 的 CRX 扩展文件路径。
        chromedriver_executable_path (str): chromedriver.exe 的路径。
    返回:
        selenium.webdriver.Chrome or None: WebDriver 实例，如果失败则为 None。
    """
    url = f'{HUBSTUDIO_BASE_URL}/browser/start'
    open_data = {"containerCode": container_id}
    try:
        open_res = requests.post(url, json=open_data).json()
        if open_res.get('code') != 0:
            print(f"HubStudio: 环境 {container_id} 打开失败: {open_res.get('msg', '未知错误')}")
            return None
        
        # webdriver_path_from_api = open_res['data']['webdriver'] # 这通常是浏览器可执行文件本身
        debugging_port = open_res['data']['debuggingPort']

        service = Service(executable_path=chromedriver_executable_path)
        options = webdriver.ChromeOptions()
        if extension_path: # 仅当提供了路径时才添加扩展
             options.add_extension(extension_path)
        options.add_experimental_option("debuggerAddress", f'127.0.0.1:{debugging_port}')
        
        driver = webdriver.Chrome(service=service, options=options)
        print(f"HubStudio: 成功连接到容器 {container_id} (端口 {debugging_port})")
        # 可选：初始打开一个空白页
        # open_url(driver, 'about:blank') 
        return driver
    except requests.exceptions.RequestException as e:
        print(f"HubStudio: 打开容器 {container_id} 时请求错误: {e}")
    except KeyError as e:
        print(f"HubStudio: 打开 {container_id} 时 API 响应格式意外: 缺少键 {e}")
    except Exception as e:
        print(f"HubStudio: 打开容器 {container_id} 时发生常规错误: {e}")
    return None


def close_container(container_id):
    """
    关闭一个 HubStudio 容器。
    参数:
        container_id (str): 要关闭的容器 ID。
    返回:
        bool: 如果成功则为 True，否则为 False。
    """
    url = f'{HUBSTUDIO_BASE_URL}/browser/stop?containerCode={container_id}'
    retries = 3
    for i in range(retries):
        try:
            close_res = requests.get(url).json()
            if close_res.get('code') == 0:
                print(f"HubStudio: 环境 {container_id} 关闭成功。")
                return True
            else:
                print(f"HubStudio: 关闭环境 {container_id} 失败 (尝试 {i+1}/{retries}): {close_res.get('msg', '未知错误')}")
        except requests.exceptions.RequestException as e:
            print(f"HubStudio: 关闭容器 {container_id} 时请求错误 (尝试 {i+1}/{retries}): {e}")
        except Exception as e:
            print(f"HubStudio: 关闭容器 {container_id} 时发生常规错误 (尝试 {i+1}/{retries}): {e}")
        if i < retries - 1:
            time.sleep(5)
    print(f"HubStudio: 尝试 {retries} 次后放弃关闭容器 {container_id}。")
    return False

# --- Selenium WebDriver 操作函数 ---

def open_url(driver, url, wait_time=10):
    """
    让 WebDriver 导航到给定的 URL。
    参数:
        driver: Selenium WebDriver 实例。
        url (str): 要打开的 URL。
        wait_time (int): 导航后的隐式等待时间。
    """
    try:
        driver.get(url)
        driver.implicitly_wait(wait_time)
    except Exception as e:
        print(f"打开 URL {url} 时出错: {e}")

def open_new_page(driver, url, wait_time=10):
    """
    在新标签页/窗口中打开一个 URL 并将焦点切换到它。
    参数:
        driver: Selenium WebDriver 实例。
        url (str): 要在新标签页中打开的 URL。
        wait_time (int): 隐式等待时间。
    返回:
        str or None: 新页面的窗口句柄，如果出错则为 None。
    """
    try:
        original_window = driver.current_window_handle
        driver.execute_script("window.open('');")
        all_handles = driver.window_handles
        new_window_handle = [handle for handle in all_handles if handle != original_window][0]
        driver.switch_to.window(new_window_handle)
        open_url(driver, url, wait_time)
        return new_window_handle
    except Exception as e:
        print(f"为 {url} 打开新页面时出错: {e}")
        return None

def close_other_windows(driver, keep_handle):
    """
    关闭除 keep_handle 指定的窗口外的所有浏览器窗口。
    参数:
        driver: Selenium WebDriver 实例。
        keep_handle (str): 要保持打开的页面的窗口句柄。
    """
    try:
        all_handles = driver.window_handles
        if len(all_handles) > 1:
            for handle in all_handles:
                if handle != keep_handle:
                    driver.switch_to.window(handle)
                    driver.close()
            driver.switch_to.window(keep_handle) # 确保焦点在保留的窗口上
    except Exception as e:
        print(f"关闭其他窗口时出错: {e}")


def fill_input_field(driver, xpath, text_to_fill, clear_first=True):
    """
    通过 XPath 找到一个输入字段并用文本填充它。
    参数:
        driver: Selenium WebDriver 实例。
        xpath (str): 输入字段的 XPath。
        text_to_fill (str): 要输入到字段中的文本。
        clear_first (bool): 是否在发送键之前清除字段。
    返回:
        bool: 如果成功则为 True，否则为 False。
    """
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        if clear_first:
            element.clear()
        element.send_keys(text_to_fill)
        return True
    except Exception as e:
        print(f"填充输入字段 (XPath: {xpath}) 时出错，内容 '{text_to_fill}': {e}")
        return False

def select_dropdown_option_by_index(driver, xpath, index):
    """
    通过索引在下拉列表中选择一个选项。
    参数:
        driver: Selenium WebDriver 实例。
        xpath (str): select (下拉) 元素的 XPath。
        index (int): 要选择的选项的基于 0 的索引。
    返回:
        str or None: 所选选项的文本，如果失败则为 None。
    """
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        select = Select(element)
        select.select_by_index(index)
        selected_option_text = select.first_selected_option.text
        return selected_option_text
    except Exception as e:
        print(f"按索引选择下拉选项时出错 (XPath: {xpath}, 索引: {index}): {e}")
        return None

def click_element(driver, xpath):
    """
    通过 XPath 找到一个元素并点击它。
    参数:
        driver: Selenium WebDriver 实例。
        xpath (str): 要点击的元素的 XPath。
    返回:
        bool: 如果成功则为 True，否则为 False。
    """
    try:
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        element.click()
        return True
    except Exception as e:
        print(f"点击元素 (XPath: {xpath}) 时出错: {e}")
        return False

# --- 外部 API 函数 ---
def get_verification_code_from_api(email, api_url=GET_CODE_API_URL_DEFAULT, timeout=10):
    """
    调用 API (例如 Google Apps Script) 来获取电子邮件的验证码。
    参数:
        email (str): 要获取验证码的电子邮件地址。
        api_url (str): 验证码 API 的 URL。
        timeout (int): 请求超时时间（秒）。
    返回:
        dict or None: API 的 JSON 响应 (预计包含 'code')，如果失败则为 None。
    """
    if not api_url or not email:
        print("错误: get_verification_code_from_api 的 API URL 和 email 不能为空。")
        return None

    params = {'email': email}
    try:
        response = requests.get(api_url, params=params, timeout=timeout)
        response.raise_for_status()  # 对于错误的响应 (4xx 或 5xx) 抛出 HTTPError
        
        data = response.json()
        print(f"邮箱 {email} 的 API 响应: {data}")
        return data
    except requests.exceptions.Timeout:
        print(f"错误: 从 API ({api_url}) 请求 {email} 的验证码超时。")
    except requests.exceptions.HTTPError as e:
        print(f"错误: 来自 API ({api_url}) 的 HTTP 错误，邮箱 {email}: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"错误: API ({api_url}) 请求异常，邮箱 {email}: {e}")
    except json.JSONDecodeError:
        print(f"错误: 无法解码来自 API ({api_url}) 的 JSON 响应。响应文本: {response.text}")
    except Exception as e:
        print(f"获取 {email} 验证码时发生意外错误: {e}")
    return None

# --- EVM Wallet 函数 ---
def generate_evm_wallet():
    """
    生成一个新的 EVM 兼容钱包 (地址、私钥、助记词)。
    启用 HD Wallet 功能以生成助记词。

    Returns:
        dict or None: 包含 'address', 'private_key', 'mnemonic' 的字典，
                      如果发生错误则返回 None。
    """
    try:
        Account.enable_unaudited_hdwallet_features()
        acct, mnemonic = Account.create_with_mnemonic()
        private_key = acct.key.hex() # 获取十六进制私钥字符串
        wallet_info = {
            'address': acct.address,
            'private_key': private_key, # acct.key 是 bytes, private_key 是 hex string
            'mnemonic': mnemonic
        }
        print(f"EVM Wallet Generated: Address - {acct.address}")
        return wallet_info
    except Exception as e:
        print(f"Error generating EVM wallet: {e}")
        traceback.print_exc()
        return None

def get_evm_balance(wallet_address, rpc_url=DEFAULT_EVM_RPC_URL, chain_id=DEFAULT_EVM_CHAIN_ID, request_timeout=DEFAULT_EVM_REQUEST_TIMEOUT_SECONDS):
    """
    查询指定 EVM 钱包地址的余额。

    Args:
        wallet_address (str): 要查询的钱包地址。
        rpc_url (str): EVM 兼容网络的 RPC URL。
        chain_id (int, optional): 链 ID，主要用于日志。
        request_timeout (int, optional): Web3 请求的超时时间（秒）。

    Returns:
        dict: 包含 'balance_wei' (int), 'balance_eth' (str), 'error' (str or None) 的字典。
              如果成功，'error' 为 None。
    """
    result = {'balance_wei': None, 'balance_eth': None, 'error': None}

    if not wallet_address or not Web3.is_address(wallet_address):
        result['error'] = f"Invalid wallet address provided: {wallet_address}"
        print(result['error'])
        return result

    if not rpc_url:
        result['error'] = "RPC URL not provided."
        print(result['error'])
        return result
    
    w3_instance = None
    try:
        w3_instance = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': request_timeout}))
        if not w3_instance.is_connected():
            result['error'] = f"Failed to connect to RPC node: {rpc_url}"
            print(result['error'])
            return result
        
        print(f"Successfully connected to {rpc_url} (Chain ID: {chain_id if chain_id else 'Unknown'}, Timeout: {request_timeout}s)")
        
        checksum_address = Web3.to_checksum_address(wallet_address)
        balance_wei = w3_instance.eth.get_balance(checksum_address)
        balance_eth = w3_instance.from_wei(balance_wei, 'ether')
        
        result['balance_wei'] = balance_wei
        result['balance_eth'] = str(balance_eth) # 转换为字符串以保持一致性
        print(f"Address: {checksum_address}, Balance: {balance_eth} ETH ({balance_wei} Wei)")
        
    except requests.exceptions.ReadTimeout:
        error_msg = f"Timeout (> {request_timeout}s) while getting balance for {wallet_address} from {rpc_url}"
        result['error'] = error_msg
        print(error_msg)
    except Exception as e:
        error_msg = f"Error getting EVM balance for {wallet_address}: {e}"
        result['error'] = error_msg
        print(error_msg)
        traceback.print_exc(limit=2)
        
    return result


if __name__ == '__main__':
    # 示例用法 (可选, 用于直接测试库)
    print("HubStudio Automated Control Library")
    print("此文件旨在作为模块导入。")
    print("如果直接运行此文件，可以在此处添加测试代码。")

    # 示例: 测试 get_text_content
    # with open("sample_text.txt", "w", encoding='utf-8') as f: # 确保编码一致
    #     f.write("你好\n世界\n\n  测试  \n")
    # content = get_text_content("sample_text.txt")
    # print(f"文本内容: {content}") # 预期: ['你好', '世界', '测试']
    # import os
    # os.remove("sample_text.txt")

    # 示例: 测试 random_input_from_list
    # my_items = ["苹果", "香蕉", "樱桃", "枣", "接骨木莓"]
    # print(f"随机选择: {random_input_from_list(my_items, 2, 3)}")

    # 注意: HubStudio 和 Selenium 函数需要 HubStudio 客户端正在运行
    # 并且浏览器是可控的。
