# -*- coding: utf-8 -*-
"""
소용돌이(난수성/냉수성) 탐지 + 분포도.

SLA 등고선을 위/아래로 훑으면서 닫힌 등고선을 찾고, 크기·진폭·반경 조건을
만족하면 소용돌이로 판정한다.

    python eddy_tracking.py 20240115        보고서 스타일(로고·박스·관측점, dpi 800)

웹 뷰어는 render() 를 직접 호출한다:

    render('20240115', extent=(128, 133, 35, 39), style=mapstyle.WEB_STYLE)

분석 범위는 mapstyle.analysis_domain(extent) 이 정한다.

  · 표출 범위가 동해 기본 범위 안이면 → DOMAIN 전체를 분석하고 동해 경계
    마스킹(mask_domain 의 대각선)을 적용한다. 보고서가 쓰는 경로다.
  · 그보다 넓은 영역을 요청하면 → 요청한 영역 전체를 분석하고 동해 경계
    마스킹은 끈다. 가장자리 잘라내기(EDGE_TRIM)만 남는다.
"""
import os
import sys
import json

import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import shapely
from shapely.geometry import Point, Polygon
from netCDF4 import Dataset
from pyproj import Geod

import paths
import mapstyle

GEOD = Geod(ellps='WGS84')

AMPLITUDE_MIN = 1        # 최소 진폭 (cm)
WARM_RAD_MIN = 25        # 난수성 최소 반경 (km)
COLD_RAD_MIN = 12        # 냉수성 최소 반경 (km)
MAX_DIAMETER_KM = 250    # 이보다 큰 등고선은 소용돌이로 보지 않는다
LEVEL_STEP = 0.2         # 등고선 훑는 간격 (cm)
LEVEL_MAX = 50           # 훑는 범위 ±LEVEL_MAX (cm)

EDGE_TRIM = 0.5          # 분석창 가장자리에서 지우는 폭 (도)

# 동해 경계 — 일본 열도를 넘어 태평양으로 새는 것을 막는 대각선.
#   lat < DIAG_LAT_MAX 구간에서 (lon - lat) >= DIAG_OFFSET 이면 동해 밖이다.
# 예) 36.5°N 에서는 138.4°E 동쪽이 잘린다.
DIAG_OFFSET = 101.875
DIAG_LAT_MAX = 40.125


# ────────────────────────────── 입력 ──────────────────────────────

def load(date, domain=None):
    """SLA 원본을 분석 도메인으로 잘라 (lon_grid, lat_grid, sla) 반환.

    domain 을 생략하면 동해 기본 도메인(mapstyle.DOMAIN)을 쓴다.
    마스킹은 적용하지 않은 상태다. mask_domain() 참고.
    """
    flist = paths.find_data(f'nrt_global_allsat_phy_l4_{date}*.nc')
    if not flist:
        raise FileNotFoundError(
            f'data/ 아래에 nrt_global_allsat_phy_l4_{date}*.nc 파일이 없습니다.')

    ds = Dataset(flist[0])
    lon = ds.variables['longitude'][:]
    lat = ds.variables['latitude'][:]
    sla2 = ds.variables['sla'][:]

    lon_num, lat_num = mapstyle.domain_slices(lon, lat, domain)
    lon_grid, lat_grid = np.meshgrid(lon[lon_num], lat[lat_num])
    return lon_grid, lat_grid, sla2[0, lat_num, lon_num]


def mask_domain(lon_grid, lat_grid, sla, eastsea=True):
    """분석에서 제외할 격자를 NaN 으로 지운다 (제자리 수정).

    장식이 아니라 알고리즘의 일부다 — 가장자리를 지우지 않으면 배열 경계에서
    등고선이 인위적으로 닫히면서 가짜 소용돌이가 잡힌다.

    eastsea=True 면 여기에 더해 동해 경계(대각선) 밖을 지운다. 표출 범위가
    동해 기본 범위 안일 때만 쓰며, 예전 인덱스 기반 마스킹
    (`sla[i, i+79:130]`, `sla[:, 125:130]` …) 과 결과가 같다. 다만 이제는
    위경도로 표현되어 있으므로 격자 간격이 달라져도 그대로 성립한다.

    eastsea=False (요청 영역이 동해보다 넓을 때) 면 가장자리만 지우고
    요청한 영역 전체를 분석한다.
    """
    if eastsea:
        # 북쪽(50°N)은 원본이 자르지 않았다 — 결과를 바꾸지 않으려고 그대로 둔다
        w, e, s, _ = mapstyle.DOMAIN
        sla[lat_grid <= s + EDGE_TRIM] = np.nan
        sla[lon_grid <= w + EDGE_TRIM] = np.nan
        sla[lon_grid >= e - EDGE_TRIM] = np.nan
        sla[(lat_grid < DIAG_LAT_MAX) &
            (lon_grid - lat_grid >= DIAG_OFFSET)] = np.nan
    else:
        sla[lat_grid <= lat_grid.min() + EDGE_TRIM] = np.nan
        sla[lat_grid >= lat_grid.max() - EDGE_TRIM] = np.nan
        sla[lon_grid <= lon_grid.min() + EDGE_TRIM] = np.nan
        sla[lon_grid >= lon_grid.max() - EDGE_TRIM] = np.nan
    return sla


def cell_size(lon_grid, lat_grid, sla):
    """격자 셀의 남북(dislat)·동서(dislon) 거리(m). 반경 계산에 쓴다."""
    ny = sla.shape[0]

    dislat = np.zeros_like(sla)
    dislat[:ny - 2] = GEOD.inv(lon_grid[:ny - 2], lat_grid[:ny - 2],
                               lon_grid[2:], lat_grid[2:])[2]
    dislat[0, :] = GEOD.inv(lon_grid[0, 0], lat_grid[0, 0],
                            lon_grid[1, 0], lat_grid[1, 0])[2]
    dislat[-1, :] = dislat[0, :]

    row = GEOD.inv(lon_grid[:, 0], lat_grid[:, 0], lon_grid[:, 2], lat_grid[:, 2])[2]
    dislon = np.zeros_like(sla) + np.asarray(row)[:, None]
    return dislat, dislon


# ────────────────────────────── 탐지 ──────────────────────────────

def _max_diameter_km(x, y):
    """등고선 위 두 점 사이 최대 측지선 거리(km)."""
    n = len(x)
    d = GEOD.inv(np.repeat(x, n), np.repeat(y, n), np.tile(x, n), np.tile(y, n))[2]
    return d.max() / 1000


def _contour_segments(ax, lon_grid, lat_grid, field, level):
    """해당 레벨의 등고선 세그먼트 목록.

    레벨마다 figure 를 새로 만들면(원본 방식) 1000회 생성 비용이 붙어서
    축 하나를 재사용하고 그린 등고선만 지운다. 계산 결과는 동일하다.
    """
    cs = ax.contour(lon_grid, lat_grid, field, levels=[level, 1000])
    segs = [v for level_segments in cs.allsegs for v in level_segments]
    cs.remove()
    return segs


def _sweep(lon_grid, lat_grid, field, dislat, dislon, warm, quiet):
    """등고선을 훑어 소용돌이를 찾는다. warm=True 면 난수성, False 면 냉수성.

    field 는 cm 단위 SLA (sla * 100). 제자리에서 수정되므로 호출자가 사본을 준다.
    """
    rad_min = WARM_RAD_MIN if warm else COLD_RAD_MIN
    levels = (np.arange(-LEVEL_MAX, LEVEL_MAX + LEVEL_STEP, LEVEL_STEP) if warm
              else np.arange(LEVEL_MAX, -LEVEL_MAX - LEVEL_STEP, -LEVEL_STEP))

    found = []
    fig, ax = plt.subplots(figsize=(8, 6))
    try:
        for level in levels:
            for v in _contour_segments(ax, lon_grid, lat_grid, field, level):
                if len(v) < 4:
                    continue
                x, y = v[:, 0], v[:, 1]

                # 닫힌 등고선만
                if not (np.isclose(x[0], x[-1]) and np.isclose(y[0], y[-1])):
                    continue
                # 너무 작은 것 제외
                if (x.max() - x.min()) < 0.5 or (y.max() - y.min()) < 0.5:
                    continue
                # 너무 큰 것 제외
                if _max_diameter_km(x, y) > MAX_DIAMETER_KM:
                    continue

                polygon = Polygon(zip(x, y))
                in_mask = shapely.contains_xy(polygon, lon_grid, lat_grid)

                if not polygon.contains(Point(np.mean(x), np.mean(y))):
                    continue

                inbndy = field[in_mask]
                if len(inbndy) == 0:
                    continue
                if warm:
                    if np.min(inbndy) < level:
                        continue
                    amplitude = inbndy[np.argmax(inbndy)] - level
                else:
                    if np.min(inbndy) > level:
                        continue
                    amplitude = level - inbndy[np.argmin(inbndy)]
                if amplitude < AMPLITUDE_MIN:
                    continue

                area = dislon[in_mask] * dislat[in_mask] / 4      # m^2
                radius_km = np.sqrt(np.sum(area) / 1e6 / np.pi)
                if radius_km <= rad_min:
                    continue

                field[in_mask] = np.nan
                found.append({
                    'center': [float(np.mean(x)), float(np.mean(y))],
                    'amplitude': float(amplitude),
                    'radius': float(radius_km),
                    'edge': np.array([x, y]),
                })
                if not quiet:
                    print(f"{len(found)} {'warm' if warm else 'cold'}eddy(eddies) found.")
    finally:
        plt.close(fig)
    return found


def detect(lon_grid, lat_grid, sla, quiet=False, eastsea=True):
    """소용돌이 탐지. 반환: (난수성 목록, 냉수성 목록).

    각 항목은 {'center', 'amplitude'(cm), 'radius'(km), 'edge'} 형태.
    작도 없이 숫자만 필요하면 이 함수만 쓰면 된다.
    인자로 준 sla 는 제자리에서 마스킹된다(작도도 마스킹된 자료로 해야 한다).
    eastsea=False 면 동해 경계 마스킹 없이 준 자료 전체를 탐지한다.

    ── 원본 대비 수정 사항 (2026-09-07) ──────────────────────────────────
    원본 스크립트는 `hhh1 = sla * 100` 을 마스킹 코드보다 **먼저** 실행해서
    냉수성만 마스킹 안 된 자료로 탐지하고 있었다. 그 탓에 동해 밖(일본 동편
    태평양, 남해 등)의 소용돌이가 냉수성에 섞여 들어왔다.
    예) 2026-09-01 의 141.5°E / 36.5°N — 36.5°N 에서는 138.4°E 동쪽이
        마스킹 대상이므로 원래 잡히면 안 되는 것이었다.

    지금은 난수성·냉수성 모두 마스킹된 자료로 탐지한다. 영향 범위(15일치 실측):
      · 난수성, 울릉 난수성, 독도 냉수성 — 변화 없음
      · 동해 전체 냉수성 — 날짜당 0~3개 감소 (동해 밖 오탐지만 빠진다)
    발간된 2025년판 보고서의 '동해 전체 냉수성' 수치와는 달라진다.
    """
    mask_domain(lon_grid, lat_grid, sla, eastsea=eastsea)
    dislat, dislon = cell_size(lon_grid, lat_grid, sla)
    # _sweep 은 받은 배열을 제자리에서 수정하므로 각각 새로 만들어 넘긴다
    cold = _sweep(lon_grid, lat_grid, sla * 100, dislat, dislon, warm=False, quiet=quiet)
    warm = _sweep(lon_grid, lat_grid, sla * 100, dislat, dislon, warm=True, quiet=quiet)
    return warm, cold


# ────────────────────────────── 통계 ──────────────────────────────

def _count_in(eddies, poly):
    return sum(1 for e in eddies if poly.contains(Point(e['center'])))


def build_stats(date, warm, cold, extent=None, domain=None):
    """보고서 표1용 개수 + 웹 통계 패널용 표출영역 개수.

    'warm'/'cold' 는 분석 도메인 전체 개수다. 동해 기본 범위에서는 예전처럼
    동해 전체를 뜻하고('scope' = '동해'), 더 넓은 영역을 요청하면 그 영역
    전체를 뜻한다('scope' = '분석영역'). 표출영역만 센 값은 'view' 에 있다.
    """
    region = Polygon(zip(mapstyle.REGION_LON, mapstyle.REGION_LAT))
    eastsea = mapstyle.is_eastsea_view(extent)
    stats = {
        'date': date,
        'domain': list(domain if domain else mapstyle.analysis_domain(extent)),
        'scope': '동해' if eastsea else '분석영역',
        'warm': len(warm),                       # 난수성 소용돌이(분석 도메인)
        'cold': len(cold),                       # 냉수성 소용돌이(분석 도메인)
        'ulleung_warm': _count_in(warm, region),  # 울릉 난수성
        'dokdo_cold': _count_in(cold, region),    # 독도 냉수성
        'warm_eddies': [{'center': e['center'], 'amplitude': e['amplitude'],
                         'radius_km': e['radius']} for e in warm],
        'cold_eddies': [{'center': e['center'], 'amplitude': e['amplitude'],
                         'radius_km': e['radius']} for e in cold],
    }
    if extent and tuple(extent) != mapstyle.DEFAULT_EXTENT:
        lon_min, lon_max, lat_min, lat_max = extent
        view = Polygon([(lon_min, lat_min), (lon_max, lat_min),
                        (lon_max, lat_max), (lon_min, lat_max)])
        stats['view'] = {
            'extent': list(extent),
            'warm': _count_in(warm, view),
            'cold': _count_in(cold, view),
        }
    return stats


# ────────────────────────────── 작도 ──────────────────────────────

def render(date, extent=None, style=None, out_path=None, json_path=None, quiet=False):
    """소용돌이 분포도 PNG + 통계를 만든다. 반환: {'png':…, 'json':…, 'stats':…}"""
    style = mapstyle.resolve(style)
    extent = tuple(extent) if extent else mapstyle.DEFAULT_EXTENT

    domain = mapstyle.analysis_domain(extent)
    eastsea = mapstyle.is_eastsea_view(extent)

    lon_grid, lat_grid, sla = load(date, domain)
    warm, cold = detect(lon_grid, lat_grid, sla, quiet=quiet, eastsea=eastsea)
    stats = build_stats(date, warm, cold, extent, domain)

    fig, ax = mapstyle.make_map(extent)
    ax.contour(lon_grid, lat_grid, sla, levels=np.arange(-2, 2.01, 0.01),
               colors='k', linewidths=0.5, transform=ccrs.PlateCarree(), zorder=3)
    for eddies, color in ((cold, [0.0, 0.45, 1]), (warm, [1, 0.45, 0.0])):
        for eddy in eddies:
            ex, ey = eddy['edge']
            ax.fill(ex, ey, color=color, alpha=0.8, transform=ccrs.PlateCarree(), zorder=4)
            ax.plot(ex, ey, color=color, linewidth=2, transform=ccrs.PlateCarree(), zorder=5)

    ax.set_title(f'Warm / Cold Eddy ({date[:4]} / {date[4:6]} / {date[6:8]})',
                 fontsize=25, fontweight='bold', fontname='serif', y=mapstyle.TITLE_Y)
    mapstyle.decorate(fig, ax, style, extent=extent,
                      source='SLA(CMEMS)', source_size=30, box_label='UWE/DCE Area')

    png = out_path or os.path.join(paths.fig_dir('eddy_tracking'), f'WA_Method_{date}.png')
    mapstyle.save(fig, png, style)

    jpath = json_path or os.path.join(paths.json_dir('eddy_tracking'), f'eddy_stats_{date}.json')
    with open(jpath, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    if not quiet:
        print(f'Warm eddies in area: {stats["ulleung_warm"]}, '
              f'Cold eddies in area: {stats["dokdo_cold"]}')
        print(f'eddy_stats_{date}.json saved.')
    return {'png': png, 'json': jpath, 'stats': stats}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    render(sys.argv[1], style=mapstyle.REPORT_STYLE)
