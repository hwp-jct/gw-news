import os
import csv
import time
import json
import threading
import configparser

import boto3
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from collections import OrderedDict
from tqdm import tqdm
from stqdm import stqdm

import utils as ut
import game_log_analyzer as gla

# --------------------------------------

DB_ENGINE = None
prog_bar = stqdm  # use tqdm console mode. see __main__


# ----------------- DB -----------------

# def fetch_battle_log_from_db(beg_time, end_time):
#     def get_db_engine():
#         global DB_ENGINE
#         if DB_ENGINE is None:
#             dbc = ut.st_secrets('DB_CONNECT').strip('\'"')
#             DB_ENGINE = create_engine(dbc)
#         return DB_ENGINE

#     # query = "SELECT * FROM your_table_name WHERE your_time_column BETWEEN %s AND %s"
#     b_time = beg_time.strftime("%Y-%m-%d %H:%M:%S")
#     e_time = end_time.strftime("%Y-%m-%d %H:%M:%S")

#     query = f"""
# SELECT [LogDate],[WorldID],[Reason],[UserID],[UserLevel],[CharLevel]
#     ,[P0],[P1],[P2],[P3],[P4],[P5],[P6],[P7],[P8],[P9],[P10]
#     ,[P11],[P12],[P13],[P14],[P15],[P16],[P17],[P18],[P19],[P20]
#     ,[P21],[P22],[P23],[P24],[P25],[P26],[P27],[P28],[P29],[P30]
# FROM [DWMART_GWF].[dbo].[T_DM_Battle]
# WHERE [LogDate] BETWEEN '{b_time}' AND '{e_time}'
# """
#     # print(f"fetching data from {b_time} to {e_time}")
#     # print(query)
#     df = pd.read_sql_query(query, get_db_engine())

#     if not df.empty:
#         csv_file_name = f"fromdb/bl-{beg_time.strftime('%Y%m%dT%H%M%S')}.csv"
#         print(f"working folder: {ut.get_project_path()}")
#         # print(ut.get_work_file(csv_file_name))
#         ut.df_write_csv(df, ut.get_work_path(csv_file_name), encoding='utf-8')
#         print(f"{csv_file_name} is saved.")


# def fetch_battle_log_fromdb_schedule():
#     config = configparser.ConfigParser()
#     config.read(ut.get_work_path('main-bl.ini'))
#     beg_time = datetime.strptime(config.get('DEFAULT', 'BEG_TIME'), "%Y-%m-%d %H:%M:%S")
#     end_time = datetime.strptime(config.get('DEFAULT', 'END_TIME'), "%Y-%m-%d %H:%M:%S")
#     interval_min = config.getint('DEFAULT', 'INTERVAL_MIN')
#     sleeping_sec = config.getint('DEFAULT', 'SLEEPING_SEC')

#     current_time = beg_time
#     while current_time < end_time and not ut.QUIT_THREAD:
#         # print(f"fetching data from {current_time} to {current_time + timedelta(seconds=interval_sec-1)}")
#         fetch_battle_log_from_db(current_time, current_time + timedelta(seconds=interval_min * 60 - 1))
#         current_time += timedelta(minutes=interval_min)
#         time.sleep(sleeping_sec)

#     if ut.QUIT_THREAD:
#         print("Data scrapping is terminated by user.")
#     else:
#         print("Data scrapping is completed.")


# ----------------- AWS S3 -----------------

def _s3_file_download(date: datetime, server_id):
    bucket_name = 'gw-server-log'
    sub_path = f'collect/{server_id}'
    file_name = f'Game_{date:%Y-%m-%d}.gz'
    # s3_obj_name = f'{date:%Y/%m/%d}/{server_id}/dblog/Game_{date:%Y-%m-%d_%H-%M}.gz'
    s3_obj_name = f'{date:%Y/%m/%d}/{server_id}/dblog/Game_{date:%Y-%m-%d}_00:00.gz'
    if ut.f_exists(file_name, sub_path):
        print(f'{server_id}/{file_name} already exists.')
        return
    try:
        s3r = boto3.resource('s3')
        s3fo = s3r.Object(bucket_name, s3_obj_name)
        file_size = s3fo.content_length
        s3_client = boto3.client('s3')
        # print(f'USE_STREAMLIT: {os.getenv("USE_STREAMLIT", "True")}')
        if os.getenv("USE_STREAMLIT", "True") == "True":
            # print(f"Downloading with stqdm!")
            with st.spinner(f'Downloading {s3_obj_name}'):
                with ut.fs_open(file_name, sub_path, 'wb') as z_file:
                    s3_client.download_fileobj(bucket_name, s3_obj_name, z_file)
        else:
            # print(f"Downloading with tqdm!")
            with prog_bar(
                    total=file_size,
                    desc=f's3://{bucket_name}/{s3_obj_name}',
                    unit='B',
                    unit_scale=True) as pbar:
                with ut.fs_open(file_name, sub_path, 'wb') as z_file:
                    s3_client.download_fileobj(bucket_name, s3_obj_name, z_file, Callback=pbar.update)
        print(f'{server_id}/{file_name} complete!')
    except Exception as e_s3:
        print(f"Error occurred: {e_s3}")


def _s3_decompress_log(file_name: str, server_id):
    sub_path = f'collect/{server_id}'
    if ut.f_exists(file_name, sub_path):
        print(f'{server_id}/{file_name} already exists.')
        return
    with ut.z_open(f'{file_name}.gz', sub_path, 'rb') as z_file:
        # progress_bar 진행율을 z_file의 크기로 설정
        z_file.seek(0, 2)
        z_file_size = z_file.tell()
        buffer_size = 65536
        chunks = int(z_file_size / buffer_size + 1)
        z_file.seek(0)
        with ut.fs_open(file_name, sub_path, 'wb') as uz_file:
            pbar = prog_bar(iter(lambda: z_file.read(buffer_size), b""), desc=f'un_zip: {file_name}.gz', total=chunks)
            for chunk in pbar:
                uz_file.write(chunk)
        print(f'{server_id}/{file_name} complete!')


def _s3_extract_log_by_reason(file_name: str, server_id, beg_time, end_time, mode):
    keys = gla.get_battle_log_headers(False)
    key_idx = keys.index('LogDate')
    keys[key_idx] = 'Time'
    # print(f'keys: {keys}')
    # beg_time = start_date.replace(hour=10, minute=0, second=0, microsecond=0)
    # end_time = beg_time + timedelta(days=1)
    sub_path = f'collect/{server_id}'
    with ut.fs_open(file_name, sub_path, 'r') as f:
        try:
            with (ut.fs_open(f'30004.csv', sub_path, mode) as wf30004,
                  ut.fs_open(f'30005.csv', sub_path, mode) as wf30005,
                  ut.fs_open(f'30027.csv', sub_path, mode) as wf30027):
                csv30004 = csv.DictWriter(wf30004, fieldnames=keys, lineterminator='\n')
                csv30005 = csv.DictWriter(wf30005, fieldnames=keys, lineterminator='\n')
                csv30027 = csv.DictWriter(wf30027, fieldnames=keys, lineterminator='\n')
                cnt_line = sum(1 for _ in f)
                print(f"total lines: {cnt_line}")
                f.seek(0)
                # ignore_keys = {'Level', 'LogType', 'LogDate_Svr', 'Command', 'SN', 'MSG'}
                pbar = prog_bar(f, desc=f'xtract: {file_name}', total=cnt_line)
                writerow = {30004: csv30004.writerow, 30005: csv30005.writerow, 30027: csv30027.writerow}
                dbg_write_once = {30004:True, 30005:True, 30027:True }
                for line in pbar:
                    data = json.loads(line)
                    log_time = datetime.strptime(data['Time'], "%Y-%m-%d %H:%M:%S.%f")
                    reason = data['Reason']
                    if reason not in [30004, 30005, 30027]:
                        continue
                    # is_valid_time = beg_time <= log_time <= end_time
                    # if not is_valid_time:
                    #     continue
                    if beg_time > log_time:
                        continue
                    if log_time > end_time:
                        break
                    ordered_data = OrderedDict((k, data.get(k, None)) for k in keys)
                    # ordered_data = OrderedDict((k, data.get(k, None)) for k in keys if k not in ignore_keys)
                    # filtered_data = {k: data.get(k, None) for k in keys if k not in ignore_keys}
                    # ordered_data = OrderedDict(filtered_data)
                    if dbg_write_once[reason]:
                        # print(f"write header: {reason}\n{ordered_data}")
                        dbg_write_once[reason] = False
                    writerow[reason](ordered_data)
            print(f'{server_id}/{file_name} extract 30004, 30005, 30027 csv file "{mode}" mode complete!')
        except Exception as e_extract:
            print(f"Error occurred: {e_extract}")


def s3_fetch_game_log_process(srv_ids, beg_time, end_time):
    print('Fetch From S3...')
    for srv_id in srv_ids:
        for date in pd.date_range(beg_time.date(), end_time.date()):
            _s3_file_download(date.date(), srv_id)
    print('Unzip Downloaded GZ...')
    for srv_id in srv_ids:
        for date in pd.date_range(beg_time.date(), end_time.date()):
            file_name = f'Game_{date:%Y-%m-%d}'
            _s3_decompress_log(file_name, srv_id)
    print(f'Extracting World War Stats {beg_time} to {end_time}...')
    for srv_id in srv_ids:
        for date in pd.date_range(beg_time.date(), end_time.date()):
            is_start_date = date.date() == beg_time.date()
            file_name = f'Game_{date:%Y-%m-%d}'
            _s3_extract_log_by_reason(file_name, srv_id, beg_time, end_time, 'w' if is_start_date else 'a')


if __name__ == '__main__':
    os.environ["USE_STREAMLIT"] = "False"
    prog_bar = tqdm
    # 설정 파일 읽기
    # config = configparser.ConfigParser()
    # config.read(ut.get_work_path('main-bl.ini'))

    server_ids = ['1133', '2092']
    # server_ids = ['1029']
    # server_ids = ['2092']
    # ut.clear_work_folder('collect')

    with ut.dont_disturb():
        t = threading.Thread(target=ut.check_keyboard_input)
        t.daemon = True
        t.start()
        check_start_time = time.time()  # 함수 시작 시간 기록
        try:
            # fetch_battle_log_fromdb_schedule()
            s3_fetch_game_log_process(server_ids, datetime(2024, 6, 1, 10), datetime(2024, 6, 2, 10))
        except Exception as e:
            print(f"Error occurred: {e}")

        elapsed_time = time.time() - check_start_time  # 실행 시간 계산
    print(f"Elapsed time: {elapsed_time:.2f} sec")
    print('All done.')
