import time
import threading
import pandas as pd
# import pyodbc
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import configparser

import utils as ut

DB_ENGINE = None


def fetch_battle_log(beg_time, end_time):
    def get_db_engine():
        global DB_ENGINE
        if DB_ENGINE is None:
            dbc = ut.st_secrets('DB_CONNECT').strip('\'"')
            DB_ENGINE = create_engine(dbc)
        return DB_ENGINE
    # query = "SELECT * FROM your_table_name WHERE your_time_column BETWEEN %s AND %s"
    b_time = beg_time.strftime("%Y-%m-%d %H:%M:%S")
    e_time = end_time.strftime("%Y-%m-%d %H:%M:%S")

    query = f"""
SELECT [LogDate],[WorldID],[Reason],[UserID],[UserLevel],[CharLevel]
    ,[P0],[P1],[P2],[P3],[P4],[P5],[P6],[P7],[P8],[P9],[P10]
    ,[P11],[P12],[P13],[P14],[P15],[P16],[P17],[P18],[P19],[P20]
    ,[P21],[P22],[P23],[P24],[P25],[P26],[P27],[P28],[P29],[P30]
FROM [DWMART_GWF].[dbo].[T_DM_Battle]
WHERE [LogDate] BETWEEN '{b_time}' AND '{e_time}'
"""
    # print(f"fetching data from {b_time} to {e_time}")
    # print(query)
    df = pd.read_sql_query(query, get_db_engine())

    if not df.empty:
        csv_file_name = f"fromdb/bl-{beg_time.strftime('%Y%m%dT%H%M%S')}.csv"
        print(f"working folder: {ut.get_project_path()}")
        # print(ut.get_work_file(csv_file_name))
        df.to_csv(ut.get_work_path(csv_file_name), index=False, header=False, encoding='utf-8')
        print(f"{csv_file_name} is saved.")


def setup_schedule():
    beg_time = datetime.strptime(config.get('DEFAULT', 'BEG_TIME'), "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(config.get('DEFAULT', 'END_TIME'), "%Y-%m-%d %H:%M:%S")
    interval_min = config.getint('DEFAULT', 'INTERVAL_MIN')
    sleeping_sec = config.getint('DEFAULT', 'SLEEPING_SEC')

    current_time = beg_time
    while current_time < end_time and not ut.QUIT_THREAD:
        # print(f"fetching data from {current_time} to {current_time + timedelta(seconds=interval_sec-1)}")
        fetch_battle_log(current_time, current_time + timedelta(seconds=interval_min*60-1))
        current_time += timedelta(minutes=interval_min)
        time.sleep(sleeping_sec)

    if ut.QUIT_THREAD:
        print("Data scrapping is terminated by user.")
    else:
        print("Data scrapping is completed.")


if __name__ == '__main__':
    # 설정 파일 읽기
    config = configparser.ConfigParser()
    config.read(ut.get_work_path('main-bl.ini'))

    with ut.dont_disturb():
        t = threading.Thread(target=ut.check_keyboard_input)
        t.daemon = True
        t.start()
        start_time = time.time()  # 함수 시작 시간 기록
        try:
            setup_schedule()
        except Exception as e:
            print(f"Error occurred: {e}")

        elapsed_time = time.time() - start_time  # 실행 시간 계산
    print(f"Elapsed time: {elapsed_time:.2f} sec")
