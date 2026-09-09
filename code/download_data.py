# -*- coding: utf-8 -*-
"""
CMEMS 데이터 자동 다운로드 (동해 소용돌이 보고서용)

사용법:
    python download_data.py <연도>            # 1~12월 15일자 전체
    python download_data.py <연도> <월>       # 특정 월만 (예: 2026 1)

각 월 15일자 데이터 2종을 자료·연도별 폴더에 내려받는다:
  1) MSLA(SLA/지형류) : data/MSLA/<연도>/nrt_global_allsat_phy_l4_YYYYMMDD*.nc
                        (eddy_tracking.py 와 eastsea_current.py 가 같은 파일을 공유한다)
  2) OSTIA SST        : data/OSTIA/<연도>/YYYYMMDD120000-*-OSTIA-GLOB-v02.0-fv02.0.nc
                        (eastsea_sst.py, ostia_sst.py)

원본 파일(get original files) 방식을 사용하므로 변수명/격자가 기존 스크립트와 동일하다.
과거 연도는 NRT(준실시간) 대신 MY(재처리) 데이터셋에서 받으며,
파일명은 기존 스크립트의 glob 패턴에 맞게 정규화한다.

사전 준비(1회): pip install copernicusmarine && copernicusmarine login
"""
import os
import sys
import glob
import shutil
import datetime as dt

import copernicusmarine

import paths

# 저장 폴더는 자료 종류(data/<PRODUCT>/) × 연도(하위 폴더)로 나뉜다.
SLA_PRODUCT = 'MSLA'    # SLA/지형류 — eddy_tracking, eastsea_current 가 공용
SST_PRODUCT = 'OSTIA'   # OSTIA SST — eastsea_sst, ostia_sst

# ── 데이터셋 ID (변경 시 여기만 수정) ─────────────────────────────────────────
# SLA / 지형류 (DUACS L4, 0.125deg, 일별) — 기존 스크립트가 0.125° 격자 기준
SLA_NRT = 'cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D'  # SEALEVEL_GLO_PHY_L4_NRT_008_046
SLA_MY  = 'cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D'   # SEALEVEL_GLO_PHY_L4_MY_008_047
# NRT 시작일(대략값). 이 날짜 이전이면 MY 사용. 실패 시 반대쪽으로 자동 재시도하므로 정밀할 필요 없음.
SLA_NRT_START = dt.date(2022, 1, 1)

# OSTIA SST (Met Office L4)
SST_NRT = 'METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2'   # SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001
SST_REP = 'METOFFICE-GLO-SST-L4-REP-OBS-SST'      # SST_GLO_SST_L4_REP_OBSERVATIONS_010_011
SST_NRT_START = dt.date(2007, 1, 1)
# ──────────────────────────────────────────────────────────────────────────────


class AuthError(RuntimeError):
    """CMEMS 로그인 실패 — 아이디/비밀번호를 확인해야 한다."""


def _is_auth_error(exc):
    msg = str(exc).lower()
    return any(w in msg for w in
               ('credential', 'unauthor', 'invalid username', 'forgot my username'))


def _existing(pattern):
    """data/ 이하(하위 폴더 포함)에서 이미 받아둔 파일을 찾는다."""
    return paths.find_data(pattern)


def _get_original_files(dataset_id, file_filter, dest, creds=None):
    """copernicusmarine get 으로 해당 일자의 원본 파일을 받아 경로 목록을 반환.

    creds 를 주면 (username, password) 를 그 자리에서만 쓰고 자격증명 파일을
    만들지 않는다. 웹 뷰어가 사용자 계정을 넘길 때 쓰는 경로다.
    없으면 기존처럼 `copernicusmarine login` 으로 저장해 둔 자격증명을 쓴다.
    """
    extra = {}
    if creds and creds[0] and creds[1]:
        extra = {'username': creds[0], 'password': creds[1]}
    result = copernicusmarine.get(
        dataset_id=dataset_id,
        filter=file_filter,
        output_directory=dest,
        no_directories=True,
        **extra,
    )
    files = [str(f.file_path) for f in getattr(result, 'files', [])]
    return files


def _normalize(files, target_name, dest):
    """받은 파일명을 기존 스크립트의 glob 패턴에 맞게 통일. 중복 파일은 제거."""
    if not files:
        return None
    src = files[0]
    dst = os.path.join(dest, target_name)
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.move(src, dst)
    for extra in files[1:]:
        if os.path.abspath(extra) != os.path.abspath(dst) and os.path.exists(extra):
            os.remove(extra)
    return dst


def download_sla(date, creds=None):
    """SLA/지형류 원본 파일 다운로드. 반환: 파일 경로 또는 None."""
    date_str = date.strftime('%Y%m%d')
    target = f'nrt_global_allsat_phy_l4_{date_str}_dl.nc'

    hit = _existing(f'nrt_global_allsat_phy_l4_{date_str}*.nc')
    if hit:
        print(f'  [SLA ] {date_str} 이미 존재: {os.path.basename(hit[0])}')
        return hit[0]

    dest = paths.data_dir(SLA_PRODUCT, date.year)
    primary, fallback = (SLA_NRT, SLA_MY) if date >= SLA_NRT_START else (SLA_MY, SLA_NRT)
    for ds_id in (primary, fallback):
        try:
            # NRT: nrt_global_allsat_phy_l4_YYYYMMDD_처리일.nc / MY: dt_global_allsat_phy_l4_YYYYMMDD_처리일.nc
            files = _get_original_files(ds_id, f'*l4_{date_str}_*', dest, creds)
        except Exception as e:
            if _is_auth_error(e):
                raise AuthError('CMEMS 계정을 확인하세요 (아이디 또는 비밀번호가 틀렸습니다).') from e
            print(f'  [SLA ] {date_str} {ds_id} 실패: {e}')
            files = []
        if files:
            path = _normalize(files, target, dest)
            print(f'  [SLA ] {date_str} 다운로드 완료 ({ds_id})')
            return path
    print(f'  [SLA ] {date_str} 다운로드 실패 (NRT/MY 모두)')
    return None


def download_sst(date, creds=None):
    """OSTIA SST 원본 파일 다운로드. 반환: 파일 경로 또는 None."""
    date_str = date.strftime('%Y%m%d')
    target = f'{date_str}120000-UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc'

    hit = _existing(f'{date_str}*UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc')
    if hit:
        print(f'  [SST ] {date_str} 이미 존재: {os.path.basename(hit[0])}')
        return hit[0]

    dest = paths.data_dir(SST_PRODUCT, date.year)
    primary, fallback = (SST_NRT, SST_REP) if date >= SST_NRT_START else (SST_REP, SST_NRT)
    for ds_id in (primary, fallback):
        try:
            # 파일명: YYYYMMDD120000-UKMO-L4_GHRSST-...nc
            files = _get_original_files(ds_id, f'*{date_str}120000*', dest, creds)
        except Exception as e:
            if _is_auth_error(e):
                raise AuthError('CMEMS 계정을 확인하세요 (아이디 또는 비밀번호가 틀렸습니다).') from e
            print(f'  [SST ] {date_str} {ds_id} 실패: {e}')
            files = []
        if files:
            path = _normalize(files, target, dest)
            print(f'  [SST ] {date_str} 다운로드 완료 ({ds_id})')
            return path
    print(f'  [SST ] {date_str} 다운로드 실패 (NRT/REP 모두)')
    return None


def download_month(year, month, creds=None):
    """해당 연·월 15일자 데이터 2종 다운로드. 반환: (sla_path, sst_path)"""
    return download_date(dt.date(year, month, 15), creds)


def download_date(date, creds=None):
    """임의 날짜의 데이터 2종 다운로드. 반환: (sla_path, sst_path)

    보고서는 매월 15일자만 쓰지만 웹 뷰어는 아무 날짜나 요청할 수 있다.
    """
    print(f'[{date}] 다운로드 시작')
    return download_sla(date, creds), download_sst(date, creds)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    year = int(sys.argv[1])
    months = [int(sys.argv[2])] if len(sys.argv) > 2 else list(range(1, 13))

    failed = []
    for m in months:
        sla, sst = download_month(year, m)
        if not sla or not sst:
            failed.append(m)
    if failed:
        print(f'\n실패한 월: {failed}')
        sys.exit(2)
    print('\n모든 다운로드 완료')
