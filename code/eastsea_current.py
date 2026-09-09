# -*- coding: utf-8 -*-
"""
동해 준실시간 표층 해류도 (지형류 ugos/vgos).

    python eastsea_current.py 20240115      보고서 스타일(로고·관측점, dpi 800)

웹 뷰어는 render() 를 직접 호출한다:

    render('20240115', extent=(128, 133, 35, 39), style=mapstyle.WEB_STYLE)

자료는 eddy_tracking.py 와 같은 MSLA 원본을 공유한다.
"""
import os
import sys
import json

import numpy as np
import cartopy.crs as ccrs
from netCDF4 import Dataset

import paths
import mapstyle

# 화살표 간격 — 기본 표출 범위에서 2가 되도록 폭에 비례시킨다
SKIP_REF_DEG = 8.0


def load(date, domain=None):
    """지형류 원본을 분석 도메인으로 잘라 (lon_grid, lat_grid, u, v) 반환.

    domain 을 생략하면 동해 기본 도메인(mapstyle.DOMAIN)을 쓴다.
    """
    flist = paths.find_data(f'nrt_global_allsat_phy_l4_{date}*.nc')
    if not flist:
        raise FileNotFoundError(
            f'data/ 아래에 nrt_global_allsat_phy_l4_{date}*.nc 파일이 없습니다.')

    ds = Dataset(flist[0])
    lon = ds.variables['longitude'][:]
    lat = ds.variables['latitude'][:]
    lon_num, lat_num = mapstyle.domain_slices(lon, lat, domain)
    lon_grid, lat_grid = np.meshgrid(lon[lon_num], lat[lat_num])
    u = ds.variables['ugos'][0, lat_num, lon_num]
    v = ds.variables['vgos'][0, lat_num, lon_num]
    return lon_grid, lat_grid, u, v


def arrow_skip(extent):
    """표출 폭에 맞춘 화살표 간격. 기본 범위에서는 원본과 같은 2가 나온다."""
    return max(1, int(round((extent[1] - extent[0]) / SKIP_REF_DEG)))


def view_slices(lon_grid, lat_grid, extent, margin=0.5):
    """표출 범위(+여유) 안의 격자만 골라내는 슬라이스.

    화면 밖 화살표까지 그리면 영역을 좁혔을 때 렌더가 크게 느려진다.
    기본 표출 범위에서는 도메인 전체가 잡혀 원본과 결과가 같다.
    """
    lon_min, lon_max, lat_min, lat_max = extent
    rows = np.flatnonzero((lat_grid[:, 0] >= lat_min - margin) &
                          (lat_grid[:, 0] <= lat_max + margin))
    cols = np.flatnonzero((lon_grid[0, :] >= lon_min - margin) &
                          (lon_grid[0, :] <= lon_max + margin))
    if len(rows) == 0 or len(cols) == 0:
        return slice(None), slice(None)
    return slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1)


def build_stats(date, lon_grid, lat_grid, u, v, extent):
    """표출 영역 안의 유속 통계 (m/s)."""
    lon_min, lon_max, lat_min, lat_max = extent
    sel = ((lon_grid >= lon_min) & (lon_grid <= lon_max) &
           (lat_grid >= lat_min) & (lat_grid <= lat_max))
    speed = np.ma.masked_invalid(np.ma.sqrt(u ** 2 + v ** 2))[sel]
    if speed.count() == 0:
        return {'date': date, 'speed': None}
    return {
        'date': date,
        'extent': list(extent),
        'speed': {
            'max': round(float(speed.max()), 2),
            'mean': round(float(speed.mean()), 2),
        },
    }


def render(date, extent=None, style=None, out_path=None, json_path=None, quiet=False):
    """해류도 PNG 를 만든다. 반환: {'png':…, 'stats':…}"""
    style = mapstyle.resolve(style)
    extent = tuple(extent) if extent else mapstyle.DEFAULT_EXTENT

    lon_grid, lat_grid, u, v = load(date, mapstyle.analysis_domain(extent))
    stats = build_stats(date, lon_grid, lat_grid, u, v, extent)

    skip = arrow_skip(extent)
    ry, rx = view_slices(lon_grid, lat_grid, extent)
    fig, ax = mapstyle.make_map(extent)
    q = ax.quiver(lon_grid[ry, rx][::skip, ::skip], lat_grid[ry, rx][::skip, ::skip],
                  u[ry, rx][::skip, ::skip], v[ry, rx][::skip, ::skip],
                  transform=ccrs.PlateCarree(), scale=8, width=0.0025,
                  color='lightgreen', alpha=0.85)
    ax.quiverkey(q, 0.18, 0.92, 0.5, '0.5 m/s', labelpos='E',
                 coordinates='axes', color='lightgreen')

    ax.set_title(f'Eastsea Surface Current({date[:4]} / {date[4:6]} / {date[6:8]})',
                 fontsize=20, fontweight='bold', fontname='serif', y=mapstyle.TITLE_Y)
    mapstyle.decorate(fig, ax, style, extent=extent, source='SLA(CMEMS)', source_size=20)
    if style.get('region_box'):
        # 보고서 원본에 있던 축척 문구 (quiverkey 와 별개로 찍히던 것)
        ax.text(128.3, 46.3, '→ 1m/s', transform=ccrs.PlateCarree(), fontsize=20,
                fontweight='bold', fontname='serif', color=[0, 0, 0], zorder=6)

    png = out_path or os.path.join(paths.fig_dir('eastsea_current'),
                                   f'eastsea_current_{date}.png')
    mapstyle.save(fig, png, style)

    if json_path:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    if not quiet:
        print(f'{os.path.basename(png)} saved.')
    return {'png': png, 'json': json_path, 'stats': stats}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    render(sys.argv[1], style=mapstyle.REPORT_STYLE)
