import os
from tqdm import tqdm
import pandas as pd
import utils as ut


# ----------------------------------------------

def get_battle_log_headers(is_full_log:bool, readerble_p = None):
    if is_full_log:
        header = ['LogDate', 'LogDate_Svr', 'WorldID', 'CountryID', 'Command', 'Reason', 'SN', 'UserID', 'UserName', 'UserLevel', 'CharLevel']
    else:
        header = ['LogDate', 'WorldID', 'Reason', 'UserID', 'UserLevel', 'CharLevel']

    if readerble_p:
        header += readerble_p
    else:
        header += [f'p{i}' for i in range(31)]  # add 'P0' to 'P30' to the header

    if is_full_log:
        header += ['c0', 'c1', 'RegDate']  # add 'C0', 'C1', 'RegDate' to the header
    return header


# ----------------------------------------------

def load_battle_log_desc():
    df_battle_desc = pd.read_excel(ut.get_work_path("GW_게임로그정의서.xlsx"), sheet_name='Battle', skiprows=4, usecols="C:AI")
    df_battle_desc.set_index("Reason", inplace=True)
    return df_battle_desc


# ----------------------------------------------

def load_users_mas_info():
    df = ut.pd_read_csv(ut.get_work_path("mom.csv"))
    drop_list = ['Guild_WL_TYpe', 'LastKWGuild', 'Carrier_Move_Type']
    df.drop(columns=drop_list, inplace=True)
    df['LordName'] = df['LordName'].apply(ut.fix4_xl_str)
    # UserID로 LoardName을 찾기 위해 UserID를 key로 하는 dict 생성
    return df


# ----------------------------------------------

def load_guild_info():
    df = pd.DataFrame(columns=['ServerID', 'GuildID', 'GuildName'])
    df['GuildName'] = df['GuildName'].apply(ut.fix4_xl_str)
    return df


# ----------------------------------------------

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


# ----------------------------------------------

def _load_raw_log(svr_id, reason, log_desc, dic_users, dic_guild):
    try:
        df = ut.pd_read_csv(ut.get_work_path(f'collect/{svr_id}/{reason}.csv'), header=None)
    except FileNotFoundError:
        df = pd.DataFrame()
        print(f"File not found: {ut.get_work_path(f'collect/{svr_id}/{reason}.csv')}")
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()
    return df


# ----------------------------------------------

def _organize_header(df, log_desc, reason):
    header = log_desc.loc[reason]
    readable_p = []
    drop_list = []
    for i in range(31):
        key_str = f'p{i}'
        hdr_str = header[key_str]
        if pd.isna(hdr_str):
            drop_list.append(key_str)
            readable_p.append(key_str)
        else:
            readable_p.append(f'p{i}: ' + str(hdr_str))

    if len(df) > 0:
        df.columns = get_battle_log_headers(False, readable_p)
        df.drop(columns=drop_list, inplace=True)
    return df


# ----------------------------------------------

def _organize_id_to_name(df_org, dic_users, dic_guild):
    uid_cols = []
    gid_cols = []
    base_kind = {1:'Base Operation', 2:'Missile Base 2', 3:'Missile Base1', 4:'Multipurpose Base 1', 5:'Multipurpose Base 2', 6:'Control Base 1', 7:'Control Base 2'}
    for col in df_org.columns:
        if '연합ID' in col:
            df_org[col.replace('연합ID', '연합명')] = df_org[col].apply(lambda x: dic_guild.get(x, str(x)))
            gid_cols.append(col)
        if 'UID' in col:
            df_org[col.replace('UID', '제독명')] = df_org[col].apply(lambda x: dic_users.get(x, str(x)))
            uid_cols.append(col)
        if '건물Kind' in col:
            df_org[col] = df_org[col].apply(lambda x: base_kind.get(x, str(x)))
    return df_org, uid_cols, gid_cols

# ----------------------------------------------

def _filter_ww_participants(df, dic_users, dic_guild, svr_id, reason, uid_cols, gid_cols):
    # !--- WW 참여자만 추출
    unknown_users = df[~df[uid_cols].isin(dic_users.keys()).all(axis=1)]
    if not unknown_users.empty:
        unknown_users.to_csv(ut.get_work_path(f'collect/{svr_id}/{reason}-unknown-users.csv'), index=False, encoding='utf-8-sig')
    df = df[df[uid_cols].isin(dic_users.keys()).all(axis=1)]

    # !--- WW 참여 연합만 추출
    # not ready yet
    # unknown_guilds = df[~df[gid_cols].isin(dic_guild.keys()).all(axis=1)]
    # if not unknown_guilds.empty:
    #     unknown_guilds.to_csv(ut.get_work_path(f'collect/{svr_id}/{reason}_unknown_guilds.csv'), index=False, encoding='utf-8-sig')
    # df = df[df[gid_cols].isin(dic_guild.keys()).all(axis=1)]

    return df


# ----------------------------------------------

def _analyze_ww_30004(df_org, svr_id):
    # !--- 전투력 감소 분석
    df_org['제독1_공격전투력소모'] = df_org['p18: 공격자전투력'] - df_org['p19: 공격자전투후 전투력']
    df_org['제독2_방어전투력소모'] = df_org['p20: 방어자전투력'] - df_org['p21: 방어자 전투후 전투력']
    df_org['제독1_공격총전투력소모'] = df_org['제독1_공격전투력소모'] + df_org['제독2_방어전투력소모']

    # !--- 전투 통계 분석
    df = df_org[[
        'p26: 공격자UID', 'p26: 공격자제독명', 'p27: 방어자UID', 'p27: 방어자제독명',
        'p1: 공격자 승패여부(1:승리,0패배)', '제독1_공격전투력소모', '제독2_방어전투력소모', '제독1_공격총전투력소모']]
    df.columns = ['제독1_UID', '제독1_이름', '제독2_UID', '제독2_이름', '승리', '제독1_공격전투력소모', '제독2_방어전투력소모', '제독1_공격총전투력소모']
    # print(df.head(5))
    grouped = df.groupby(['제독1_UID', '제독1_이름', '제독2_UID', '제독2_이름'])
    ad_pair = grouped.agg(제독1_공격횟수=pd.NamedAgg(column='승리', aggfunc='size'),
                          제독1_승리횟수=pd.NamedAgg(column='승리', aggfunc=lambda x: (x == 1).sum()),
                          제독1_공격전투력소모=pd.NamedAgg(column='제독1_공격전투력소모', aggfunc='sum'),
                          제독2_방어전투력소모=pd.NamedAgg(column='제독2_방어전투력소모', aggfunc='sum'),
                          제독1_공격총전투력소모=pd.NamedAgg(column='제독1_공격총전투력소모', aggfunc='sum'),
                          ).reset_index()

    # 공격/방어 반대 쌍 추출
    ad_rvrs = ad_pair[ad_pair['제독1_UID'] > ad_pair['제독2_UID']]
    # 공격/방어 반대 쌍 중복 데이터 제거
    ad_pair = ad_pair[ad_pair['제독1_UID'] < ad_pair['제독2_UID']]

    def _reverse_op_(row, column_name):
        reverse_condition = (ad_rvrs['제독1_UID'] == row['제독2_UID']) & (ad_rvrs['제독2_UID'] == row['제독1_UID'])
        # filtered_data = ad_rvrs[reverse_condition][column_name]
        filtered_data = ad_rvrs.loc[reverse_condition, column_name]
        return filtered_data.values[0] if len(filtered_data) > 0 else 0

    ad_pair['제독2_공격횟수'] = ad_pair.apply(lambda row: _reverse_op_(row, '제독1_공격횟수'), axis=1)
    ad_pair['제독2_승리횟수'] = ad_pair.apply(lambda row: _reverse_op_(row, '제독1_승리횟수'), axis=1)
    # ad_pair['제독2_공격횟수'] = ad_pair.apply(lambda row: len(df[(df['제독1_UID'] == row['제독2_UID']) & (df['제독2_UID'] == row['제독1_UID'])]), axis=1)
    # ad_pair['제독2_승리횟수'] = ad_pair.apply(lambda row: len(df[(df['제독1_UID'] == row['제독2_UID']) & (df['제독2_UID'] == row['제독1_UID']) & (df['승리'] == 1)]), axis=1)

    ad_pair['제독2_공격전투력소모'] = ad_pair.apply(lambda row: _reverse_op_(row, '제독1_공격전투력소모'), axis=1)
    ad_pair['제독1_방어전투력소모'] = ad_pair.apply(lambda row: _reverse_op_(row, '제독2_방어전투력소모'), axis=1)
    ad_pair['제독2_공격총전투력소모'] = ad_pair.apply(lambda row: _reverse_op_(row, '제독1_공격총전투력소모'), axis=1)
    ad_pair['총전투횟수'] = ad_pair['제독1_공격횟수'] + ad_pair['제독2_공격횟수']
    ad_pair['총전투력소모'] = ad_pair['제독1_공격총전투력소모'] + ad_pair['제독2_공격총전투력소모'] + ad_pair['제독1_방어전투력소모'] + ad_pair['제독2_방어전투력소모']
    ad_pair = ad_pair.sort_values(by='총전투횟수', ascending=False)
    ad_pair.drop(columns=['제독1_UID', '제독2_UID'], inplace=True)

    ad_pair.drop(columns=['제독1_공격전투력소모', '제독2_방어전투력소모', '제독1_공격총전투력소모', '제독2_공격전투력소모', '제독1_방어전투력소모', '제독2_공격총전투력소모'], inplace=True)
    # ad_pair = ad_pair[(ad_pair['제독1_공격횟수'] > 0) & (ad_pair['제독2_공격횟수'] > 0)]
    ad_pair = ad_pair.head(50)
    ad_pair.to_csv(ut.get_work_path(f'collect/{svr_id}/C{svr_id}_30004.csv'), index=False, encoding='utf-8')
    # print(ad_pair.head(5))
    print(f'Complete {svr_id}/30004')



# ----------------------------------------------

def _analyze_ww_30005(df_org, svr_id):
    # !--- 전투력 감소 분석
    df_org['연합1_집결공격전투력소모'] = df_org['p20: 공격자전투력'] - df_org['p21: 공격자전투후 전투력']
    df_org['연합2_집결방어전투력소모'] = df_org['p22: 방어자전투력'] - df_org['p23: 방어자 전투후 전투력']
    df_org['연합1_집결총전투력소모'] = df_org['연합1_집결공격전투력소모'] + df_org['연합2_집결방어전투력소모']

    df = df_org[[
        'p3: 공격자연합ID', 'p3: 공격자연합명', 'p6: 방어자연합ID', 'p6: 방어자연합명',
        'p28: 공격자UID', 'p28: 공격자제독명', 'p29: 방어자UID', 'p29: 방어자제독명',
        'p1: 공격자 승패여부(1:승리,0패배)', 'p4: 공격유저수', 'p7: 방어유저수',
        '연합1_집결공격전투력소모', '연합2_집결방어전투력소모', '연합1_집결총전투력소모']]
    df.columns = [
        '연합1_UID', '연합1_이름', '연합2_UID', '연합2_이름',
        '공격자UID', '공격자이름', '방어자UID', '방어자이름',
        '승리', '연합1_집결참여', '연합2_방어참여',
        '연합1_집결공격전투력소모', '연합2_집결방어전투력소모', '연합1_집결총전투력소모']
    
    grouped = df.groupby(['연합1_UID', '연합1_이름', '연합2_UID', '연합2_이름'])
    ad_pair = grouped.agg(연합1_공격횟수=pd.NamedAgg(column='승리', aggfunc='size'),
                          연합1_승리횟수=pd.NamedAgg(column='승리', aggfunc=lambda x: (x == 1).sum()),
                          연합1_집결공격전투력소모=pd.NamedAgg(column='연합1_집결공격전투력소모', aggfunc='sum'),
                          연합2_집결방어전투력소모=pd.NamedAgg(column='연합2_집결방어전투력소모', aggfunc='sum'),
                          연합1_집결총전투력소모=pd.NamedAgg(column='연합1_집결총전투력소모', aggfunc='sum'),
                          ).reset_index()

    # 원정 서버에서 길드 ID가 바꾸어져 있을 수 있으므로, 서버별로 다른 길드 ID를 가질 수 있음
    # 공격/방어 반대 쌍 추출
    ad_rvrs = ad_pair[ad_pair['연합1_UID'] > ad_pair['연합2_UID']]
    # 공격/방어 반대 쌍 중복 데이터 제거
    ad_pair = ad_pair[ad_pair['연합1_UID'] < ad_pair['연합2_UID']]

    def _reverse_op_(row, column_name):
        reverse_condition = (ad_rvrs['연합1_UID'] == row['연합2_UID']) & (ad_rvrs['연합2_UID'] == row['연합1_UID'])
        # filtered_data = ad_rvrs[reverse_condition][column_name]
        filtered_data = ad_rvrs.loc[reverse_condition, column_name]
        return filtered_data.values[0] if len(filtered_data) > 0 else 0

    ad_pair['연합2_공격횟수'] = ad_pair.apply(lambda row: _reverse_op_(row, '연합1_공격횟수'), axis=1)
    ad_pair['연합2_승리횟수'] = ad_pair.apply(lambda row: _reverse_op_(row, '연합1_승리횟수'), axis=1)

    ad_pair['연합2_집결공격전투력소모'] = ad_pair.apply(lambda row: _reverse_op_(row, '연합1_집결공격전투력소모'), axis=1)
    ad_pair['연합1_집결방어전투력소모'] = ad_pair.apply(lambda row: _reverse_op_(row, '연합2_집결방어전투력소모'), axis=1)
    ad_pair['연합2_집결총전투력소모'] = ad_pair.apply(lambda row: _reverse_op_(row, '연합1_집결총전투력소모'), axis=1)
    ad_pair['총전투횟수'] = ad_pair['연합1_공격횟수'] + ad_pair['연합2_공격횟수']
    ad_pair['총전투력소모'] = ad_pair['연합1_집결총전투력소모'] + ad_pair['연합2_집결총전투력소모'] + ad_pair['연합1_집결방어전투력소모'] + ad_pair['연합2_집결방어전투력소모']
    ad_pair = ad_pair.sort_values(by='총전투횟수', ascending=False)
    ad_pair.drop(columns=['연합1_UID', '연합2_UID', '연합1_이름', '연합2_이름'], inplace=True)

    ad_pair.to_csv(ut.get_work_path(f'collect/{svr_id}/C{svr_id}_30005.csv'), index=False, encoding='utf-8')
    # print(ad_pair.head(5))
    print(f'Complete {svr_id}/30005')


# ----------------------------------------------

def _analyze_ww_30027(df_org, svr_id):
    drop_list = [
        'WorldID', 'UserID', 'UserLevel', 'CharLevel', 'Reason',
        'p0: BattleID', 'p3: 공격자기지레벨', 'p4: 공격자원본연합ID', 'p5: 공격유저수',
        'p6: 방어자기지레벨', 'p7: 방어자원본연합ID', 'p8: 방어유저수',
        'p9: 공격자전투기수', 'p10: 공격자생존전투기수', 'p11: 방어자전투기수', 'p12: 방어자생존전투기수',
        'p13: 공격자총기갑부대', 'p14: 공격자생존기갑부대', 'p15: 방어자총기갑부대', 'p16: 방어자생존기갑부대',
        'p17: 공격자함선수', 'p18: 공격자생존함선수', 'p19: 방어자함선수', 'p20: 방어자생존함선수',
        'p21: 공격자전투력', 'p22: 공격자전투후 전투력', 'p23: 방어자전투력', 'p24: 방어자 전투후 전투력',
        'p25: 공격자항모KIND', 'p26: 워크ID', 'p27: 공격자UID', 'p28: 방어자UID']
    df_org.drop(columns=drop_list, inplace=True)
    df_org.set_index('LogDate', inplace=True)
    df_org.to_csv(ut.get_work_path(f'collect/{svr_id}/C{svr_id}_30027.csv'), index=True, encoding='utf-8')
    print(f'Complete {svr_id}/30027')


# ==============================================

def analyze_ww_logs(server_ids):
    mas_df = load_users_mas_info()
    dic_users = pd.Series(mas_df.LordName.values, index=mas_df.UserID).to_dict()
    dic_guild = load_guild_info()
    log_desc = load_battle_log_desc()

    ww_reasons = [30004, 30005, 30027]
    analyze_ww = {
        30004: _analyze_ww_30004,
        30005: _analyze_ww_30005,
        30027: _analyze_ww_30027
    }

    for svr_id in server_ids:
        for reason in ww_reasons:
            df = _load_raw_log(svr_id, reason, log_desc, dic_users, dic_guild)
            df = _organize_header(df, log_desc, reason)
            df, uid_cols, gid_cols = _organize_id_to_name(df, dic_users, dic_guild)
            df.to_csv(ut.get_work_path(f'collect/{svr_id}/{reason}-readable.csv'), index=True, encoding='utf-8-sig')
            df = _filter_ww_participants(df, dic_users, dic_guild, svr_id, reason, uid_cols, gid_cols)
            analyze_ww[reason](df, svr_id)


if __name__ == '__main__':
    server_ids = [1133, 2092]
    analyze_ww_logs(server_ids)
    print("Complete!")

