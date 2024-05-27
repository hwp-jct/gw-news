import os
from tqdm import tqdm
import pandas as pd
import utils as ut


# ----------------------------------------------

def get_battle_log_headers(is_full_log:bool, dynamic_headers = None):
    if is_full_log:
        header = ['LogDate', 'LogDate_Svr', 'WorldID', 'CountryID', 'Command', 'Reason', 'SN', 'UserID', 'UserName', 'UserLevel', 'CharLevel']
    else:
        header = ['LogDate', 'WorldID', 'Reason', 'UserID', 'UserLevel', 'CharLevel']

    if dynamic_headers:
        header += dynamic_headers
    else:
        header += [f'P{i}' for i in range(31)]  # add 'P0' to 'P30' to the header

    if is_full_log:
        header += ['C0', 'C1', 'RegDate']  # add 'C0', 'C1', 'RegDate' to the header
    return header


# ----------------------------------------------

def load_battle_desc():
    df_battle_desc = pd.read_excel(ut.get_work_path("fromdb/GW_게임로그정의서.xlsx"), sheet_name='Battle', skiprows=4, usecols="C:AI")
    df_battle_desc.set_index("Reason", inplace=True)
    return df_battle_desc


# ----------------------------------------------

def load_all_user_names():
    df = ut.pd_read_csv(ut.get_work_path("fromdb/uid.csv"), header=None)
    header = ["ServerID", "UserID", "LordName"]
    df.columns = header

    duplicated_ids = df[df["UserID"].duplicated(keep=False)]
    if not duplicated_ids.empty:
        ut.print_log("Warning! UserIDs that are not unique:")
        ut.print_log(f"{duplicated_ids}")

    # df['LordName'] = df['LordName'].astype(str).str.strip('"')
    df['LordName'] = df['LordName'].apply(ut.fix4_xl_str)

    # dic_user_names = pd.Series(df[["ServerID", "LordName"]].valuesvalues, index=df.UserID).to_dict()
    df = df.drop_duplicates(subset='UserID', keep='first')
    dic_user_names = df.set_index('UserID')[['ServerID', 'LordName']].to_dict('index')
    return dic_user_names


# ----------------------------------------------

def load_all_guild_names():
    # ! AI는 GuildID 10만번 이하. 또는 [GuildMsg]==AI Guild
    df = ut.pd_read_csv(ut.get_work_path("fromdb/gid.csv"), header=None)
    header = ["ServerID", "GuildID", "GuildName"]
    df.columns = header

    # df['GuildName'] = df['GuildName'].astype(str).str.strip('"')
    df['GuildName'] = df['GuildName'].apply(ut.fix4_xl_str)

    df['SvrGuildID'] = df['ServerID'].astype(str) + '_' + df['GuildID'].astype(str)
    duplicated_ids = df[df["SvrGuildID"].duplicated(keep=False)]
    if not duplicated_ids.empty:
        ut.print_log(f"Warning! SvrGuildID that are not unique:")
        ut.print_log(f"{duplicated_ids}")
    dic_guild_names = pd.Series(df.GuildName.values, index=df.SvrGuildID).to_dict()
    return dic_guild_names


# ----------------------------------------------

def merge_battle_logs():
    db_folder = ut.get_work_path('fromdb')
    csv_files = [f for f in os.listdir(db_folder) if f.startswith('bl-') and f.endswith('.csv')]
    df_list = []
    for i, file in tqdm(enumerate(csv_files), total=len(csv_files)):
        df_list.append(ut.pd_read_csv(os.path.join(db_folder, file), header=None))
    merged_df = pd.concat(df_list, ignore_index=True)
    return merged_df


# ----------------------------------------------

def merge_name_for_battle_log_header(merged_df, is_full_log):
    # merged_df의 컬럼수가 37개인지 45개인지 확인
    is_full_log = len(merged_df.columns) == 45
    if not is_full_log and len(merged_df.columns) != 37:
        raise ValueError(f"Unexpected number of columns: {len(merged_df.columns)}")

    # 생략된 컬럼명 목록
    # [LogDate_Svr], [CountryID], [Command], [SN], [UserName], [C0], [C1], [RegDate]
    
    merged_df.columns = get_battle_log_headers(is_full_log)
    # ut.df_write_csv(merged_df, ut.get_work_path('result/merged.csv', encoding='utf-8')


# ----------------------------------------------

def _analyze_30004_admiral_battle_power(group, writer):

    # adf = group.copy()
    adf = group
    adf['공격자 전투력 감소'] = adf['p18: 공격자전투력'] - adf['p19: 공격자전투후 전투력']
    adf['방어자 전투력 감소'] = adf['p20: 방어자전투력'] - adf['p21: 방어자 전투후 전투력']
    adf['총 전투력 감소 합산'] = adf['공격자 전투력 감소'] + adf['방어자 전투력 감소']
    top_attackers = adf[adf['방어자 전투력 감소'] > 0].sort_values(by=['방어자 전투력 감소'], ascending=False)
    top_defenders = adf[adf['공격자 전투력 감소'] > 0].sort_values(by=['공격자 전투력 감소'], ascending=False)
    total_consume = adf[adf['총 전투력 감소 합산'] > 0].sort_values(by=['총 전투력 감소 합산'], ascending=False)

    columns_to_keep = ['UserLevel', 'CharLevel', 'p1: 공격자 승패여부(1:승리,0패배)', 'p2: 공격자기지레벨', 'p3: 공격자연합ID',
                       'p4: 방어자기지레벨', 'p5: 방어자연합ID', 'p18: 공격자전투력', 'p19: 공격자전투후 전투력',
                       'p20: 방어자전투력', 'p21: 방어자 전투후 전투력', 'p26: 공격자UID', 'p27: 방어자UID',
                       '공격자 전투력 감소', '방어자 전투력 감소', '총 전투력 감소 합산']
    top_attackers = top_attackers[columns_to_keep]
    top_defenders = top_defenders[columns_to_keep]
    total_consume = total_consume[columns_to_keep]

    top_a50 = top_attackers.head(50)
    top_d50 = top_defenders.head(50)
    top_c10 = total_consume.head(10)

    enc_type = os.getenv("ENC_TYPE", 'utf-8')

    top_a50.to_excel(writer, sheet_name="방어자_전투력_감소_Top50", index=False)
    ut.df_write_csv(top_a50, ut.get_work_path('result/방어자_전투력_감소_Top50.csv'), encoding=enc_type)
    top_d50.to_excel(writer, sheet_name="공격자_전투력_감소_Top50", index=False)
    ut.df_write_csv(top_d50, ut.get_work_path('result/공격자_전투력_감소_Top50.csv'), encoding=enc_type)
    top_c10.to_excel(writer, sheet_name="총_전투력_감소_합산_Top10", index=False)
    ut.df_write_csv(top_c10, ut.get_work_path('result/총_전투력_감소_합산_Top10.csv'), encoding=enc_type)


# ----------------------------------------------

def _analyze_30004_admiral_battle_count(group, writer):

    adf = group.copy()
    adf[['p26: 공격자UID', 'p27: 방어자UID']] = adf[['p26: 공격자UID', 'p27: 방어자UID']].astype(str)
    ad_pair = adf.groupby(['WorldID', 'p26: 공격자UID', 'p27: 방어자UID']).size().reset_index(name='공격자의 공격 빈도수')
    ad_pair.columns = ['WorldID', 'p26: 공격자UID', 'p27: 방어자UID', '공격자의 공격 빈도수']
    
    def get_reverse_attack_frequency(row):
        reverse_rows = ad_pair[
            (ad_pair['p26: 공격자UID'] == row['p27: 방어자UID']) & (ad_pair['p27: 방어자UID'] == row['p26: 공격자UID'])]
        return reverse_rows['공격자의 공격 빈도수'].values[0] if len(reverse_rows) > 0 else 0
    ad_pair["방어자의 역공 빈도수"] = ad_pair.apply(get_reverse_attack_frequency, axis=1)
    ad_pair["제독간 전투 빈도수"] = ad_pair['공격자의 공격 빈도수'] + ad_pair['방어자의 역공 빈도수']

    enc_type = os.getenv("ENC_TYPE", 'utf-8')

    # (p26, p27) 쌍이 (p27, p26) 반대 쌍과 같은 중복 데이터 제거
    ad_pair = ad_pair[ad_pair['p26: 공격자UID'] < ad_pair['p27: 방어자UID']]

    # 역공 빈도가 0이 아닌 전투 빈도수 상위 10개를 엑셀로 저장
    top_ads = ad_pair[ad_pair['방어자의 역공 빈도수'] > 0].sort_values(by='제독간 전투 빈도수', ascending=False).head(10)
    top_ads.to_excel(writer, sheet_name='제독간_전투_공방_빈도_순위_Top10', index=False)
    ut.df_write_csv(top_ads, ut.get_work_path('result/제독간_전투_공방_빈도_순위_Top10.csv'), encoding=enc_type)

    # 역공 빈도가 0포함 전투 빈도수 상위 100개를 엑셀로 저장
    top_ads = ad_pair.sort_values(by='제독간 전투 빈도수', ascending=False).head(100)
    top_ads.to_excel(writer, sheet_name='제독간_전투_빈도_순위_Top100', index=False)
    ut.df_write_csv(top_ads, ut.get_work_path('result/제독간_전투_빈도_순위_Top100.csv'), encoding=enc_type)


# ----------------------------------------------

def _analyze_30004_alliance_battle(group, writer):
    adf = group.copy()
    adf[['p3: 공격자연합ID', 'p5: 방어자연합ID']] = adf[['p3: 공격자연합ID', 'p5: 방어자연합ID']].astype(str)
    # adf[['p3: 공격자연합ID', 'p5: 방어자연합ID']] = np.sort(adf[['p3: 공격자연합ID', 'p5: 방어자연합ID']].values, axis=1)
    ad_pair = adf.groupby(['WorldID', 'p3: 공격자연합ID', 'p5: 방어자연합ID']).size().reset_index(name='공격 연합의 공격 빈도수')
    ad_pair.columns = ['WorldID', 'p3: 공격자연합ID', 'p5: 방어자연합ID', '공격 연합의 공격 빈도수']

    def get_reverse_attack_frequency(row):
        reverse_rows = ad_pair[
            (ad_pair['p3: 공격자연합ID'] == row['p5: 방어자연합ID']) & (ad_pair['p5: 방어자연합ID'] == row['p3: 공격자연합ID'])]
        return reverse_rows['공격 연합의 공격 빈도수'].values[0] if len(reverse_rows) > 0 else 0
    ad_pair["방어 연합의 역공 빈도수"] = ad_pair.apply(get_reverse_attack_frequency, axis=1)
    ad_pair["연합간 전투 빈도수"] = ad_pair['공격 연합의 공격 빈도수'] + ad_pair['방어 연합의 역공 빈도수']

    enc_type = os.getenv("ENC_TYPE", 'utf-8')

    # 연합간 전투 빈도 순위 상위 100개를 엑셀로 저장
    adc_100 = ad_pair.sort_values(by='연합간 전투 빈도수', ascending=False).head(100)
    adc_100.to_excel(writer, sheet_name="연합간_전투_빈도_순위_Top100", index=False)
    ut.df_write_csv(adc_100, ut.get_work_path('result/연합간_전투_빈도_순위_Top100.csv'), encoding=enc_type)

    # 역공 빈도가 0이 아닌 전투 빈도수를 엑셀로 저장
    top_ads = ad_pair[ad_pair['방어 연합의 역공 빈도수'] > 0].sort_values(by='연합간 전투 빈도수', ascending=False)
    # (p3, p5) 쌍이 (p5, p3) 반대 쌍과 같은 중복 데이터 제거
    # ad_pair = ad_pair[ad_pair['p3: 공격자연합ID'] < ad_pair['p5: 방어자연합ID']]

    top_ads.to_excel(writer, sheet_name='연합간_전투_공방_빈도_순위', index=False)
    ut.df_write_csv(top_ads, ut.get_work_path('result/연합간_전투_공방_빈도_순위.csv'), encoding=enc_type)

    def normalize_pair(attacker, defender):
        return tuple(sorted([attacker, defender]))

    filtered_data = top_ads.copy()
    filtered_data['pair'] = filtered_data.apply(lambda row: normalize_pair(row['p3: 공격자연합ID'], row['p5: 방어자연합ID']), axis=1)

    final_data = filtered_data.groupby('pair').agg(
        alliance1=('p3: 공격자연합ID', lambda x: x.iloc[0] if x.iloc[0] < x.iloc[1] else x.iloc[1]),
        alliance2=('p5: 방어자연합ID', lambda x: x.iloc[0] if x.iloc[0] > x.iloc[1] else x.iloc[1]),
        alliance1_attack_count=('공격 연합의 공격 빈도수', 'first'),
        alliance2_attack_count=('방어 연합의 역공 빈도수', 'first'),
        total_battles=('공격 연합의 공격 빈도수', 'sum')
    ).reset_index(drop=True)
    final_data.sort_values(by='total_battles', ascending=False)
    final_data.to_excel(writer, sheet_name='연합간_전투_공방_순위', index=False)
    ut.df_write_csv(final_data, ut.get_work_path('result/연합간_전투_공방_순위.csv'), encoding=enc_type)
    ut.df_write_csv(final_data, ut.get_work_path('result/context_1.csv'), encoding=enc_type)

    # 공방 순위에 포함되는 전투 로그를 엑셀로 저장
    top_ad_logs = pd.DataFrame()
    for _, row in top_ads.iterrows():
        temp_df = adf[
            ((adf['p3: 공격자연합ID'] == row['p3: 공격자연합ID']) & (adf['p5: 방어자연합ID'] == row['p5: 방어자연합ID'])) |
            ((adf['p3: 공격자연합ID'] == row['p5: 방어자연합ID']) & (adf['p5: 방어자연합ID'] == row['p3: 공격자연합ID']))
        ]
        top_ad_logs = pd.concat([top_ad_logs, temp_df])
    drop_list = ['Reason', 'WorldID', 'UserID', 'p0: BattleID', 'p25: 워크ID']
    top_ad_logs.drop(columns=drop_list, inplace=True)

    brief_name = "연합간 전투 로그"
    top_ad_logs.to_excel(writer, sheet_name='연합간_전투_로그', index=False)
    ut.df_write_csv(top_ad_logs, ut.get_work_path('result/연합간_전투_로그.csv'), encoding=enc_type)
    ut.df_write_csv(top_ad_logs, ut.get_work_path('result/context_2.csv'), encoding=enc_type)


# ----------------------------------------------

def analyze_battle_logs_by_reason(merged_df, is_full_log):
    # split by reason
    reasons = merged_df['Reason'].unique()
    merged_df = {reason: merged_df[merged_df['Reason'] == reason] for reason in reasons}

    # sort dfs_reason by reason
    merged_df = dict(sorted(merged_df.items(), key=lambda x: x[0]))

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    with pd.ExcelWriter(ut.get_work_path('result/result-30004.xlsx'), engine='xlsxwriter') as writer:
        dic_guild = load_all_guild_names()
        dic_users = load_all_user_names()
        tab_descr = load_battle_desc()

        tab_descr.to_excel(writer, sheet_name="배틀로그 형식 정의서", index=False)

        # for reason, group in tqdm(merged_df.items()):
        for reason, group in merged_df.items():
            # ! check only 30004
            if reason == 30004:
                group = change_header_readable(is_full_log, tab_descr, reason, group)
                chage_id_to_name(dic_guild, dic_users, reason, group)
                group.to_excel(writer, sheet_name=f'{reason}', index=False)
                analyze_30004(writer, group)
                
                break


def analyze_30004(writer, group):
    _analyze_30004_admiral_battle_power(group, writer)
    _analyze_30004_admiral_battle_count(group, writer)
    _analyze_30004_alliance_battle(group, writer)


def chage_id_to_name(dic_guild, dic_users, reason, group):
    group['UserName'] = group['UserID'].apply(lambda x: dic_users.get(x, {'LordName': x})['LordName'])
    group['UserName'] = group['UserName'].astype(str)
    for col in group.columns:
        if '연합ID' in col:
            sgid = group['WorldID'].astype(str) + '_' + group[col].astype(str)
            group[col] = sgid.map(dic_guild).apply(lambda x: f'{x}' if pd.notnull(x) else x)
        if 'UID' in col:
            group[col] = group[col].apply(lambda x: dic_users.get(x, {'LordName': x})['LordName'])
            group[col] = group[col].astype(str)

    reason_csv = ut.get_work_path(f'result/{reason}.csv')
    enc_type = os.getenv("ENC_TYPE", 'utf-8')
    ut.df_write_csv(group, reason_csv, encoding=enc_type)


def change_header_readable(is_full_log, tab_descr, reason, group):
    header = tab_descr.loc[reason]
    dynamic_headers = [f'p{i}' for i in range(31)]
    drop_list = [] if len(group.columns) != 45 else ['LogDate_Svr', 'CountryID', 'Command', 'SN', 'C0', 'C1', 'RegDate']
    for i in range(31):
        key_str = f'p{i}'
        hdr_str = header[key_str]
        if pd.isna(hdr_str):
            drop_list.append(key_str)
        else:
            dynamic_headers[i] = f'p{i}: ' + str(hdr_str)
    group.columns = get_battle_log_headers(is_full_log, dynamic_headers)
    group = group.copy()
    group.drop(columns=drop_list, inplace=True)
    return group


# ----------------------------------------------

if __name__ == '__main__':
    # cwd = os.path.dirname(os.path.abspath(__file__))
    # os.chdir(cwd)
    # print(f">>> Current working directory: {cwd}")

    print("Start analyzing battle logs...")
    print("Merging battle logs...")
    merged_df = merge_battle_logs()

    merged_file = ut.get_work_path("fromdb/merged.csv")
    ut.df_write_csv(merged_file, header=False, encoding='utf-8-sig')
    # merged_df = ut.pd_read_csv(merged_file, header=None)
    print(f"SAVED {merged_file}")

    # merged_df의 컬럼수가 37개인지 45개인지 확인
    is_full_log = len(merged_df.columns) == 45
    if not is_full_log and len(merged_df.columns) != 37:
        raise ValueError(f"Unexpected number of columns: {len(merged_df.columns)}")
    # 생략된 컬럼명 목록
    # [LogDate_Svr], [CountryID], [Command], [SN], [UserName], [C0], [C1], [RegDate]
    merge_name_for_battle_log_header(merged_df, is_full_log)
    print("Analyzing 30004 battle issues...")
    analyze_battle_logs_by_reason(merged_df, is_full_log)
    print("SAVED fromdb/result-30004.xlsx")


