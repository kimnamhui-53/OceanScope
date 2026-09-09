# -*- coding: utf-8 -*-
"""
프로젝트 공통 경로 헬퍼.

폴더 구조
    code/                          파이썬 스크립트 (이 파일 포함)
    code/matlab/                   원본 MATLAB 스크립트

    template/                      보고서 서식 템플릿 (template_2025.hwpx)

    data/MSLA/<연도>/              SLA·지형류 원본 (nrt_global_allsat_phy_l4_*.nc)
                                   → eddy_tracking.py, eastsea_current.py 가 공용
    data/OSTIA/<연도>/             OSTIA SST 원본 (*-OSTIA-GLOB-*.nc)
                                   → eastsea_sst.py, ostia_sst.py
    data/common/                   스크립트 공용 자산 (KHOA_logo2.ras 등)

    output/<kind>/figure/          그래프 PNG
    output/<kind>/json/            통계 JSON
        kind = eddy_tracking | eastsea_current | eastsea_sst
    output/intermediate/summary/   summary_<연도>.json   (표 1용 통계 취합)
    output/intermediate/comments/  comments_<연도>.json  (월별 코멘트)
    output/report/                 <연도> 동해 소용돌이 분석보고서.hwpx (최종 결과물)

    docs/                          계획서·메모·시스템 관계도
    reference/                     원본 보고서·관측자료 등 참고 자료 (파이프라인 미사용)

입력 파일은 find_data() 로 data/ 이하를 재귀 검색하므로, 자료를 어느 하위
폴더에 두어도 스크립트가 찾아낸다.
"""
import os
import glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(BASE, 'code')
DATA = os.path.join(BASE, 'data')
OUTPUT = os.path.join(BASE, 'output')
TEMPLATE = os.path.join(BASE, 'template')

# 입력 자료 종류 (data/ 하위 폴더명)
PRODUCTS = ('MSLA', 'OSTIA')
# 산출 자료 종류 (output/ 하위 폴더명)
KINDS = ('eddy_tracking', 'eastsea_current', 'eastsea_sst')

FIGURE = 'figure'   # 그래프 PNG
JSON = 'json'       # 통계 JSON


# ────────────────────────────── 입력 ──────────────────────────────

def data_dir(product, year):
    """입력 폴더 data/<product>/<연도>/ (없으면 생성).

    product : 'MSLA' | 'OSTIA'
    year    : 연도 (int 또는 'YYYY'/'YYYYMMDD' 문자열 — 앞 4자리를 연도로 본다)
    """
    return _mk(os.path.join(DATA, product, str(year)[:4]))


def find_data(pattern):
    """data/ 이하(연도 폴더 포함)에서 패턴에 맞는 파일 목록을 반환."""
    return sorted(set(glob.glob(os.path.join(DATA, '**', pattern), recursive=True)))


def common(name):
    """data/common/ 의 공용 자산 경로."""
    return os.path.join(DATA, 'common', name)


def template_path(name='template_2025.hwpx'):
    """보고서 서식 템플릿 경로 template/<name>."""
    return os.path.join(TEMPLATE, name)


# ────────────────────────────── 산출 ──────────────────────────────

def out_dir(kind, sub=None):
    """산출 폴더 output/<kind>/[<sub>/] (없으면 생성)."""
    parts = [OUTPUT, kind] + ([sub] if sub else [])
    return _mk(os.path.join(*parts))


def fig_dir(kind):
    """그래프 PNG 폴더 output/<kind>/figure/."""
    return out_dir(kind, FIGURE)


def json_dir(kind):
    """통계 JSON 폴더 output/<kind>/json/."""
    return out_dir(kind, JSON)


def interim_dir(name):
    """중간 산출물 폴더 output/intermediate/<name>/ (name = 'summary' | 'comments')."""
    return _mk(os.path.join(OUTPUT, 'intermediate', name))


def summary_path(year):
    """output/intermediate/summary/summary_<연도>.json"""
    return os.path.join(interim_dir('summary'), f'summary_{year}.json')


def comments_path(year):
    """output/intermediate/comments/comments_<연도>.json"""
    return os.path.join(interim_dir('comments'), f'comments_{year}.json')


def report_dir():
    """최종 보고서 폴더 output/report/."""
    return _mk(os.path.join(OUTPUT, 'report'))


def _mk(path):
    os.makedirs(path, exist_ok=True)
    return path
