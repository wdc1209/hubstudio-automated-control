# google_sheets_helper.py

import time
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
# import pandas as pd # 如果你计划用 pandas 处理数据，可以取消注释

# --- 全局配置 ---
# 你的 JSON 文件名 (假设它与此脚本在同一目录)
DEFAULT_SERVICE_ACCOUNT_FILE = 'YOUR_SERVICE_ACCOUNT_JSON_FILE_NAME.json'
DEFAULT_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service(service_account_file_path=DEFAULT_SERVICE_ACCOUNT_FILE, scopes_list=DEFAULT_SCOPES):
    """
    使用服务账户凭证创建并返回 Google Sheets API 服务对象。

    Args:
        service_account_file_path (str): 服务账户JSON文件的路径。
        scopes_list (list): API 范围列表。

    Returns:
        Resource or None: Google Sheets API 服务对象，如果出错则返回 None。
    """
    try:
        creds = service_account.Credentials.from_service_account_file(service_account_file_path, scopes=scopes_list)
        service = build('sheets', 'v4', credentials=creds)
        print(f"INFO: Google Sheets service initialized successfully using '{service_account_file_path}'.")
        return service
    except FileNotFoundError:
        print(f"ERROR: Service account file not found at '{service_account_file_path}'.")
        print("       Please ensure the path is correct (e.g., file is in the same directory as the script, or provide an absolute path).")
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

# --- 模块内基础自检 (可选) ---
if __name__ == "__main__":
    print("--- Running basic self-test for google_sheets_helper.py ---")
    print(f"Attempting to use service account file: {DEFAULT_SERVICE_ACCOUNT_FILE}")
    
    # 尝试初始化服务作为基本检查
    service = get_sheets_service()
    if service:
        print("Self-test: Google Sheets service initialized successfully.")
        print("To perform read/write tests, run main_test_script.py or add specific test calls here.")
    else:
        print("Self-test: Failed to initialize Google Sheets service.")
        print("Please check the path to your service account JSON file and its permissions.")
    print("--- Self-test finished ---")