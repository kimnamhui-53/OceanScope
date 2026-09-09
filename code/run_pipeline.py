# -*- coding: utf-8 -*-
"""
동해 소용돌이 보고서 파이프라인 오케스트레이터

사용법:
    python run_pipeline.py <연도>              # 1~12월 전체
    python run_pipeline.py <연도> <월>         # 특정 월만
    python run_pipeline.py <연도> --skip-download   # 다운로드 생략(데이터 보유 시)

월별(15일자)로 다음을 수행한다:
  1. download_data.py 로 SLA·SST 데이터 다운로드
  2. eddy_tracking.py   → output/eddy_tracking/figure/WA_Method_YYYYMMDD.png
                          output/eddy_tracking/json/eddy_stats_YYYYMMDD.json
  3. eastsea_current.py → output/eastsea_current/figure/eastsea_current_YYYYMMDD.png
  4. eastsea_sst.py     → output/eastsea_sst/figure/eastsea_temp_YYYYMMDD.png
                          output/eastsea_sst/json/sst_stats_YYYYMMDD.json

이미 산출물이 있는 월은 건너뛰므로 중단 후 재실행해도 안전하다.
완료 후 output/intermediate/summary/summary_<연도>.json
(표 1 데이터 + 월별 수온 통계)을 생성한다.
"""
import os
import sys
import json
import subprocess

import paths

CODE = paths.CODE

# (스크립트, 산출 폴더 종류, [(하위 폴더, 산출 파일명), ...])
STEPS = [
    ('eddy_tracking.py',   'eddy_tracking',   [(paths.FIGURE, 'WA_Method_{d}.png'),
                                               (paths.JSON,   'eddy_stats_{d}.json')]),
    ('eastsea_current.py', 'eastsea_current', [(paths.FIGURE, 'eastsea_current_{d}.png')]),
    ('eastsea_sst.py',     'eastsea_sst',     [(paths.FIGURE, 'eastsea_temp_{d}.png'),
                                               (paths.JSON,   'sst_stats_{d}.json')]),
]


def expected_outputs(kind, outs, date_str):
    return [os.path.join(paths.out_dir(kind, sub), name.format(d=date_str))
            for sub, name in outs]


def outputs_exist(date_str):
    for _, kind, outs in STEPS:
        if not all(os.path.exists(p) for p in expected_outputs(kind, outs, date_str)):
            return False
    return True


def run_month(year, month, skip_download=False):
    date_str = f'{year}{month:02d}15'
    print(f'\n===== {year}년 {month}월 ({date_str}) =====')

    if outputs_exist(date_str):
        print('  산출물이 이미 모두 존재 → 건너뜀')
        return True

    if not skip_download:
        import download_data
        sla, sst = download_data.download_month(year, month)
        if not sla or not sst:
            print(f'  데이터 없음 → {month}월 건너뜀')
            return False

    for script, kind, outs in STEPS:
        expected = expected_outputs(kind, outs, date_str)
        if all(os.path.exists(p) for p in expected):
            print(f'  {script}: 산출물 존재 → 건너뜀')
            continue
        print(f'  {script} 실행 중...')
        r = subprocess.run([sys.executable, os.path.join(CODE, script), date_str],
                           capture_output=True, text=True, cwd=CODE)
        if r.returncode != 0:
            print(f'  {script} 실패:\n{r.stderr[-2000:]}')
            return False
        missing = [p for p in expected if not os.path.exists(p)]
        if missing:
            print(f'  {script}: 산출물 누락 {missing}')
            return False
    print(f'  {month}월 완료')
    return True


def build_summary(year, months_done=None):
    """표 1(월별 소용돌이 개수) + 월별 수온 통계 취합.

    이번 실행에서 처리한 월만이 아니라 디스크에 통계 JSON이 남아 있는 월을 모두
    담는다. 특정 월만 재실행해도 나머지 월이 사라지지 않는다.
    """
    summary = {'year': year, 'months': {}}
    for m in range(1, 13):
        date_str = f'{year}{m:02d}15'
        entry = {}
        eddy_p = os.path.join(paths.json_dir('eddy_tracking'), f'eddy_stats_{date_str}.json')
        sst_p = os.path.join(paths.json_dir('eastsea_sst'), f'sst_stats_{date_str}.json')
        if os.path.exists(eddy_p):
            with open(eddy_p, encoding='utf-8') as f:
                e = json.load(f)
            entry['eddy'] = {k: e[k] for k in ('warm', 'cold', 'ulleung_warm', 'dokdo_cold')}
        if os.path.exists(sst_p):
            with open(sst_p, encoding='utf-8') as f:
                entry['sst'] = json.load(f)
        if entry:
            summary['months'][str(m)] = entry

    path = paths.summary_path(year)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f'\nsummary 저장: {path}')
    return path


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    skip_download = '--skip-download' in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    year = int(args[0])
    months = [int(args[1])] if len(args) > 1 else list(range(1, 13))

    done, failed = [], []
    for m in months:
        (done if run_month(year, m, skip_download) else failed).append(m)

    build_summary(year, done)
    print(f'\n완료: {done}')
    if failed:
        print(f'실패/데이터 없음: {failed}')
