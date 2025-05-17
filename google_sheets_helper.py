# google_sheets_helper.py

import time
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
import json
# import pandas as pd # 如果你计划用 pandas 处理数据，可以取消注释

load_dotenv() # 从项目根目录的 .env 文件加载环境变量

# 加载 config.json
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
config_data = {}
try:
    # 明确指定 UTF-8 编码
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f: 
        config_data = json.load(f)
except FileNotFoundError:
    print(f"警告 (google_sheets_helper.py): 库配置文件 'config.json' 未在路径 '{CONFIG_FILE_PATH}' 找到。")
except json.JSONDecodeError as e: # 注意：这里应该是 json.JSONDecodeError (如果你导入的是 import json)
    print(f"警告 (google_sheets_helper.py): 解析库配置文件 'config.json' 时发生错误: {e}。")

# --- 配置常量 (从环境变量和 config.json 读取) ---
# 从 .env 获取服务账户文件名
DEFAULT_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SHEETS_SERVICE_ACCOUNT_FILENAME', 'your_service_account_key.json') # Fallback
# 从 config.json 获取 scopes
DEFAULT_SCOPES = config_data.get('GoogleSheets', {}).get('default_scopes', ['https://www.googleapis.com/auth/spreadsheets'])

def get_sheets_service(service_account_file_path=None, scopes_list=None):
    """
    使用服务账户凭证创建并返回 Google Sheets API 服务对象。
    """
    sa_file_path = service_account_file_path if service_account_file_path is not None else DEFAULT_SERVICE_ACCOUNT_FILE
    scopes = scopes_list if scopes_list is not None else DEFAULT_SCOPES
    
    # 如果 sa_file_path 不是绝对路径，且与脚本在同一目录找不到，则尝试在项目根目录(假设脚本在子目录)
    if not os.path.isabs(sa_file_path) and not os.path.exists(sa_file_path):
        # 假设脚本在项目根目录，或者 JSON 文件与脚本在同一目录
        # 如果脚本在子目录，而 JSON 在根目录，需要调整或用户提供绝对路径
        pass # 当前 DEFAULT_SERVICE_ACCOUNT_FILE 应该就是文件名，期望在同目录

    try:
        creds = service_account.Credentials.from_service_account_file(sa_file_path, scopes=scopes)
        service = build('sheets', 'v4', credentials=creds)
        print(f"INFO: Google Sheets service initialized successfully using '{sa_file_path}'.")
        return service
    except FileNotFoundError:
        print(f"ERROR: Service account file not found at '{sa_file_path}'.")
        print("       Please ensure the GOOGLE_SHEETS_SERVICE_ACCOUNT_FILENAME in .env is correct and the file exists, or provide a full path.")
        return None
    except Exception as e:
        print(f"ERROR: Could not initialize Google Sheets service: {e}")
        traceback.print_exc()
        return None

def read_sheet_data(spreadsheet_id, range_name, service_obj=None):
    """
    从 Google Sheet 的指定范围读取数据。

    Args:
        spreadsheet_id (str): Google Sheet 的 ID。
        range_name (str): 要读取的范围，例如 'Sheet1!A1:C10' 或 'Sheet1' (读取整个表)。
        service_obj (Resource, optional): 已初始化的 Google Sheets 服务对象。
                                         如果为 None，则会尝试使用默认配置初始化一个新的。

    Returns:
        list of lists or None: 表格数据 (每行是一个列表)，如果读取失败则返回 None。
    """
    if not service_obj:
        service_obj = get_sheets_service()
        if not service_obj:
            return None # 初始化失败
    try:
        sheet_api = service_obj.spreadsheets()
        result = sheet_api.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])

        if not values:
            print(f"INFO: No data found in Google Sheet ID '{spreadsheet_id}' at range '{range_name}'. Returning empty list.")
            return [] # 返回空列表表示没有数据
        else:
            print(f"INFO: Successfully read {len(values)} rows from Google Sheet ID '{spreadsheet_id}', range '{range_name}'.")
            return values
    except Exception as e:
        print(f"ERROR: Could not read from Google Sheet ID '{spreadsheet_id}', range '{range_name}': {e}")
        traceback.print_exc()
        return None

def write_sheet_data(data_to_write, spreadsheet_id, start_cell_range, service_obj=None,
                       value_input_option='USER_ENTERED', clear_before_write=False,
                       sheet_name_for_clearing=None):
    """
    将数据写入 Google Sheet 的指定起始单元格。

    Args:
        data_to_write (list of lists): 要写入的数据。例如 [[row1_colA, row1_colB], ...]。
        spreadsheet_id (str): Google Sheet 的 ID。
        start_cell_range (str): 要开始写入的单元格和工作表名，例如 'Sheet1!A1'。
        service_obj (Resource, optional): 已初始化的 Google Sheets 服务对象。
        value_input_option (str, optional): 'USER_ENTERED' 或 'RAW'.
        clear_before_write (bool, optional): 是否在写入前清除目标范围。
        sheet_name_for_clearing (str, optional): 如果 clear_before_write 为 True，则需提供工作表名。

    Returns:
        dict or None: API 响应，如果成功，通常包含更新的单元格数量等信息。
                      如果写入失败则返回 None。
    """
    if not service_obj:
        service_obj = get_sheets_service()
        if not service_obj:
            return None

    if not isinstance(data_to_write, list) or (data_to_write and not isinstance(data_to_write[0], list)):
        print("ERROR: data_to_write must be a list of lists (e.g., [[val1, val2], [val3, val4]]).")
        return None
    
    # 预处理数据，确保所有 None 值转换为空字符串，避免 API 错误
    processed_data = []
    for row in data_to_write:
        processed_data.append(["" if cell is None else cell for cell in row])

    body = {'values': processed_data}

    try:
        sheet_api = service_obj.spreadsheets()
        if clear_before_write:
            if not sheet_name_for_clearing:
                print("ERROR: 'sheet_name_for_clearing' must be provided when 'clear_before_write' is True.")
                return None
            
            actual_start_cell_for_clear = "A1" # 默认从A1开始清除，如果无法解析
            try:
                # 尝试从 start_cell_range 中解析出单元格起始点，用于构建清除范围
                # 例如 'SheetName!C5' -> cell_start_for_clear = 'C5'
                # 注意：这里我们用 sheet_name_for_clearing 作为清除时的表名
                _sheet_part, cell_start_for_clear = start_cell_range.split('!', 1)
                actual_start_cell_for_clear = cell_start_for_clear
            except ValueError:
                print(f"WARNING: Could not parse cell from start_cell_range ('{start_cell_range}') for precise clear start. "
                      f"Will clear from A1 of sheet '{sheet_name_for_clearing}'.")


            # 估算清除范围
            num_rows_to_clear = max(1000, len(data_to_write) + 200) # 清除足够多的行，至少1000行
            num_cols_to_write = 0
            if data_to_write and data_to_write[0]:
                num_cols_to_write = len(data_to_write[0])
            
            end_col_letter = 'Z' # 默认清除到 Z 列
            if 0 < num_cols_to_write <= 26:
                end_col_letter = chr(ord('A') + num_cols_to_write - 1)
            elif num_cols_to_write > 26:
                # 对于超过26列的简单处理，可以固定一个更大的列，例如 'AZ'
                # 精确计算会更复杂，这里为了通用性，使用 'ZZ' 作为较大范围的上限
                end_col_letter = 'ZZ' 
            
            range_to_clear_str = f"{sheet_name_for_clearing}!{actual_start_cell_for_clear}:{end_col_letter}{num_rows_to_clear}"
            print(f"INFO: Clearing range '{range_to_clear_str}' before writing...")
            clear_body = {} # 空 body 表示清除内容
            sheet_api.values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_to_clear_str,
                body=clear_body
            ).execute()
            print(f"INFO: Range '{range_to_clear_str}' cleared.")

        result = sheet_api.values().update(
            spreadsheetId=spreadsheet_id,
            range=start_cell_range, # API 会自动扩展范围以适应数据
            valueInputOption=value_input_option,
            body=body
        ).execute()
        updated_cells = result.get('updatedCells', 0)
        print(f"INFO: Successfully wrote {updated_cells} cells to Google Sheet ID '{spreadsheet_id}' starting at '{start_cell_range}'.")
        return result
    except Exception as e:
        print(f"ERROR: Could not write to Google Sheet ID '{spreadsheet_id}' at '{start_cell_range}': {e}")
        traceback.print_exc()
        return None

def append_rows_to_sheet(data_to_append, spreadsheet_id, sheet_name, service_obj=None,
                         value_input_option='USER_ENTERED'):
    """
    将数据追加到 Google Sheet 指定工作表的末尾。

    Args:
        data_to_append (list of lists): 要追加的数据行。例如 [[row1_colA, row1_colB], ...]。
        spreadsheet_id (str): Google Sheet 的 ID。
        sheet_name (str): 要追加数据的工作表名称，例如 'Sheet1'。
        service_obj (Resource, optional): 已初始化的 Google Sheets 服务对象。
        value_input_option (str, optional): 'USER_ENTERED' 或 'RAW'.

    Returns:
        dict or None: API 响应，如果成功，通常包含更新的范围等信息。
                      如果追加失败则返回 None。
    """
    if not service_obj:
        service_obj = get_sheets_service()
        if not service_obj:
            return None

    if not isinstance(data_to_append, list) or \
       (data_to_append and not isinstance(data_to_append[0], list)):
        print("ERROR: data_to_append must be a list of lists for appending.")
        return None

    # 预处理数据，确保所有 None 值转换为空字符串
    processed_data = []
    for row in data_to_append:
        processed_data.append(["" if cell is None else cell for cell in row])

    body = {'values': processed_data}
    # 要追加到的范围，使用工作表名即可，API会自动找到第一个空行
    range_to_append = f"{sheet_name}!A1" # 指定A1只是为了API知道在哪个表，实际会追加

    try:
        sheet_api = service_obj.spreadsheets()
        result = sheet_api.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_to_append, # API 会找到此工作表中的第一个空行开始追加
            valueInputOption=value_input_option,
            insertDataOption='INSERT_ROWS', # 确保是插入新行而不是覆盖
            body=body
        ).execute()
        
        updated_range = result.get('updates', {}).get('updatedRange', 'N/A')
        print(f"INFO: Successfully appended {len(processed_data)} rows to Google Sheet ID '{spreadsheet_id}', "
              f"Sheet '{sheet_name}'. Updated range: {updated_range}")
        return result
    except Exception as e:
        print(f"ERROR: Could not append to Google Sheet ID '{spreadsheet_id}', Sheet '{sheet_name}': {e}")
        traceback.print_exc()
        return None

def ensure_sheet_headers(spreadsheet_id, sheet_name, expected_headers, service_obj=None):
    """确保工作表有正确的表头，如果没有或不匹配则写入。"""
    if not service_obj:
        service_obj = get_sheets_service()
        if not service_obj: return False
    
    try:
        current_headers_raw = read_sheet_data(spreadsheet_id, f"{sheet_name}!A1:{chr(ord('A') + len(expected_headers) - 1)}1", service_obj=service_obj)
        needs_write = True
        if current_headers_raw and current_headers_raw[0]:
            current_headers = [str(h).strip() for h in current_headers_raw[0]]
            if current_headers == expected_headers:
                needs_write = False
                print(f"INFO: 表 '{sheet_name}' 表头已正确存在。")
        
        if needs_write:
            print(f"INFO: 表 '{sheet_name}' 表头不匹配或不存在。将写入新表头。")
            # 确保写入时不会因为 clear_before_write 清除我们刚检查的表头（如果表头是唯一数据）
            # 或者，如果表是空的，write_sheet_data 从A1写就行
            # 如果表非空但表头不对，覆盖A1开始的区域
            write_sheet_data([expected_headers], spreadsheet_id, f"{sheet_name}!A1", service_obj=service_obj, clear_before_write=False) # 通常写表头不需要清除
            print(f"INFO: 表头已写入 '{sheet_name}'。")
        return True
    except Exception as e:
        print(f"ERROR: 检查或写入表 '{sheet_name}' 表头时出错: {e}")
        return False

# --- 模块内基础自检 (可选) ---
if __name__ == "__main__":
    print("--- Running basic self-test for google_sheets_helper.py ---")
    # 使用从 .env 和 config.json 加载的默认值
    print(f"Attempting to use service account file (from .env or default): {DEFAULT_SERVICE_ACCOUNT_FILE}")
    
    service = get_sheets_service() # 调用时不传参数，测试默认加载
    if service:
        print("Self-test: Google Sheets service initialized successfully.")
    else:
        print("Self-test: Failed to initialize Google Sheets service.")
    print("--- Self-test finished ---")