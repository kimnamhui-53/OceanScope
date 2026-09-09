# -*- coding: utf-8 -*-
"""
웹 요청 한 건을 처리하는 실제 작업 — 자료 확보 → 레이어별 PNG 렌더 → 캐시.

렌더 자체는 code/ 의 render() 함수를 그대로 호출한다. 보고서와 웹이 같은
분석 코드를 쓰므로 숫자가 어긋나지 않는다. 다른 것은 스타일(장식 제거)과
dpi, 그리고 표출 범위(extent)뿐이다.

분석 범위는 extent 를 따라간다(mapstyle.analysis_domain). 동해 기본 범위
안이면 예전과 같은 동해 도메인, 그보다 넓게 요청하면 요청한 영역 전체다.

산출물은 web/cache/<날짜>/<레이어>_<설정해시>.png 로 남는다. 같은 조건으로
다시 요청하면 다시 그리지 않는다. 원본 nc 는 data/ 아래 보고서와 같은 자리에
받아 두므로 두 번 내려받지 않는다.
"""
import hashlib
import json
import os
import sys
import datetime as dt

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = os.path.join(BASE, 'code')
CACHE = os.path.join(BASE, 'web', 'cache')
if CODE not in sys.path:
    sys.path.insert(0, CODE)

import matplotlib                                   # noqa: E402
matplotlib.use('Agg')

import paths                                        # noqa: E402,F401
import mapstyle                                     # noqa: E402
import eddy_tracking                                # noqa: E402
import eastsea_current                              # noqa: E402
import eastsea_sst                                  # noqa: E402
import download_data                                # noqa: E402

# 레이어 이름 → (모듈, 표시명, 필요한 원본)
LAYERS = {
    'eddy':    (eddy_tracking,   '소용돌이', 'sla'),
    'current': (eastsea_current, '해류',     'sla'),
    'sst':     (eastsea_sst,     '수온',     'sst'),
}

DPI_PRESETS = {'preview': 100, 'high': 300}

# 분석·작도 코드가 바뀌어 결과가 달라지면 이 값을 올린다.
# 캐시 키에 들어가므로 옛 그림이 그대로 나오는 일을 막는다.
#   1 → 2 : 냉수성도 마스킹된 자료로 탐지 (동해 밖 오탐지 제거, 2026-09-07)
#   2 → 3 : 동해보다 넓은 영역을 요청하면 그 영역 전체를 분석 (2026-09-07)
#   3 → 4 : 지도 밖으로 삐져나가는 지명 라벨 제외 (2026-09-07)
ALGO_VERSION = 4


def cache_dir(date):
    d = os.path.join(CACHE, date)
    os.makedirs(d, exist_ok=True)
    return d


def _key(extent, dpi):
    raw = json.dumps({'extent': list(extent), 'dpi': dpi, 'algo': ALGO_VERSION},
                     sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:10]


def have_local(date, need):
    """이미 받아둔 원본이 있는지 확인한다."""
    if need == 'sla':
        return bool(paths.find_data(f'nrt_global_allsat_phy_l4_{date}*.nc'))
    return bool(paths.find_data(
        f'{date}*UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc'))


def stored_login():
    """이 PC 에 `copernicusmarine login` 으로 저장해 둔 자격증명이 있는지."""
    return os.path.exists(os.path.expanduser(
        '~/.copernicusmarine/.copernicusmarine-credentials'))


def ensure_data(date, needs, creds, report):
    """필요한 원본이 없으면 CMEMS 에서 받아온다.

    creds 는 (id, pw) 이며 이 호출 안에서만 쓰이고 저장되지 않는다.
    비워 두면 이 PC 에 저장된 로그인(copernicusmarine login)을 쓴다.
    """
    missing = [n for n in needs if not have_local(date, n)]
    if not missing:
        report('자료 확인 완료 (이미 보유)', 0.15)
        return

    typed = bool(creds and creds[0] and creds[1])
    if not typed and not stored_login():
        kinds = ', '.join('해면고도·해류' if m == 'sla' else '수온' for m in missing)
        raise RuntimeError(
            f'{date} 자료({kinds})가 없습니다. CMEMS 계정을 입력하면 자동으로 내려받습니다.')

    report('CMEMS 에서 자료 내려받는 중…', 0.05)
    d = dt.date(int(date[:4]), int(date[4:6]), int(date[6:8]))
    try:
        sla, sst = download_data.download_date(d, creds if typed else None)
    except download_data.AuthError as e:
        if typed:
            raise RuntimeError(str(e)) from e
        raise RuntimeError('저장된 CMEMS 로그인이 만료된 것 같습니다. '
                           '계정을 직접 입력해 주세요.') from e

    if 'sla' in missing and not sla:
        raise RuntimeError(f'{date} 해면고도(SLA) 자료를 받지 못했습니다. '
                           '날짜가 너무 최근이거나 계정 권한을 확인하세요.')
    if 'sst' in missing and not sst:
        raise RuntimeError(f'{date} 수온(OSTIA) 자료를 받지 못했습니다. '
                           '날짜가 너무 최근이거나 계정 권한을 확인하세요.')
    report('자료 내려받기 완료', 0.15)


def run(job):
    """작업 하나를 처리하고 결과 목록을 돌려준다."""
    spec = job.spec
    date = spec['date']
    extent = tuple(spec['extent'])
    layers = [l for l in spec['layers'] if l in LAYERS]
    dpi = DPI_PRESETS.get(spec.get('quality', 'preview'), 100)
    creds = (spec.get('username'), spec.get('password'))

    if not layers:
        raise RuntimeError('표출할 항목을 하나 이상 선택하세요.')

    needs = {LAYERS[l][2] for l in layers}
    ensure_data(date, needs, creds, job.report)

    style = mapstyle.resolve(mapstyle.WEB_STYLE, dpi=dpi)
    key = _key(extent, dpi)
    out = cache_dir(date)

    results = []
    for i, name in enumerate(layers):
        mod, label, _ = LAYERS[name]
        job.report(f'{label} 그리는 중…', 0.2 + 0.75 * i / len(layers))

        png = os.path.join(out, f'{name}_{key}.png')
        meta = os.path.join(out, f'{name}_{key}.json')

        if os.path.exists(png) and os.path.exists(meta):
            with open(meta, encoding='utf-8') as f:
                stats = json.load(f)
        else:
            res = mod.render(date, extent=extent, style=style,
                             out_path=png, json_path=meta, quiet=True)
            stats = res['stats']

        results.append({
            'layer': name,
            'label': label,
            'url': f'/api/image/{date}/{name}_{key}.png',
            'download_url': f'/api/download/{date}/{name}_{key}.png',
            'filename': _filename(name, date, extent, dpi),
            'size': os.path.getsize(png),
            'stats': stats,
        })
    return results


def _filename(layer, date, extent, dpi):
    """다운로드할 때 보이는 파일 이름."""
    tag = 'eastsea' if tuple(extent) == mapstyle.DEFAULT_EXTENT else (
        f'{extent[0]:g}-{extent[1]:g}E_{extent[2]:g}-{extent[3]:g}N')
    return f'{layer}_{date}_{tag}_{dpi}dpi.png'
