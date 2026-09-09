# -*- coding: utf-8 -*-
"""
동해 위성 표층 수온도 (OSTIA analysed_sst).

    python eastsea_sst.py 20240115          보고서 스타일(로고·관측점, dpi 800)

웹 뷰어는 render() 를 직접 호출한다:

    render('20240115', extent=(128, 133, 35, 39), style=mapstyle.WEB_STYLE)
"""
import os
import sys
import json

import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from netCDF4 import Dataset

import paths
import mapstyle

# 보고서 코멘트용 울릉도·독도 해역 (소용돌이 집계용 REGION 과는 별개다)
UL_LON = (130.5, 132.5)
UL_LAT = (37.0, 38.0)
# 수온전선을 찾는 위도 범위
FRONT_LAT = (35, 45)


def load(date, domain=None):
    """OSTIA 원본을 분석 도메인으로 잘라 (lon_grid, lat_grid, lat_sub, sst[°C]) 반환.

    domain 을 생략하면 동해 기본 도메인(mapstyle.DOMAIN)을 쓴다.
    """
    flist = paths.find_data(
        f'{date}*UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc')
    if not flist:
        raise FileNotFoundError(
            f'data/ 아래에 {date} 자 OSTIA SST 파일이 없습니다.')

    ds = Dataset(flist[0])
    lon = ds.variables['lon'][:]
    lat = ds.variables['lat'][:]
    lon_num, lat_num = mapstyle.domain_slices(lon, lat, domain)
    lon_sub, lat_sub = lon[lon_num], lat[lat_num]
    lon_grid, lat_grid = np.meshgrid(lon_sub, lat_sub)
    sst = ds.variables['analysed_sst'][0, lat_num, lon_num] - 273.15
    return lon_grid, lat_grid, lat_sub, sst


def _eastsea_window(lon_sub, lat_sub):
    """읽어 온 배열 중 동해 도메인(mapstyle.DOMAIN)에 해당하는 (행, 열) 슬라이스.

    동해보다 넓은 영역을 요청해 배열이 커져도 보고서가 쓰는 'eastsea'·'front'
    키를 계속 동해 기준으로 남기기 위한 것이다. 동해 기본 범위에서는 배열
    전체가 잡혀 예전과 결과가 같다. 동해와 겹치지 않으면 (None, None).
    """
    w, e, s, n = mapstyle.DOMAIN
    if lon_sub[0] > e or lon_sub[-1] < w or lat_sub[0] > n or lat_sub[-1] < s:
        return None, None
    cols, rows = mapstyle.domain_slices(lon_sub, lat_sub)
    return rows, cols


def build_stats(date, lon_grid, lat_grid, lat_sub, sst, extent=None):
    """보고서 코멘트용 통계 (동해 전역 / 울릉도·독도 / 수온전선 위도).

    extent 를 기본 범위와 다르게 주면 'view' 키에 표출영역 통계를 덧붙인다.
    보고서가 쓰는 세 키는 표출 범위와 무관하게 항상 동해 전역 기준이다
    (동해 밖까지 요청해 배열이 넓어져도 마찬가지 — _eastsea_window 참고).
    """
    valid = np.ma.masked_invalid(sst)

    ul = valid[(lat_grid >= UL_LAT[0]) & (lat_grid <= UL_LAT[1]) &
               (lon_grid >= UL_LON[0]) & (lon_grid <= UL_LON[1])]

    stats = {'date': date}

    ry, rx = _eastsea_window(lon_grid[0, :], lat_sub)
    if ry is not None and valid[ry, rx].count():
        es = valid[ry, rx]
        es_lat = lat_sub[ry]

        # 수온전선 위도: 경도평균 SST 의 남북 기울기가 가장 큰 위도
        zonal_mean = np.ma.mean(es, axis=1)
        grad = np.abs(np.gradient(zonal_mean.filled(np.nan), es_lat))
        grad_in = np.where((es_lat >= FRONT_LAT[0]) & (es_lat <= FRONT_LAT[1]),
                           grad, np.nan)
        front_idx = int(np.nanargmax(grad_in))

        stats['eastsea'] = {
            'min': round(float(es.min()), 1),
            'max': round(float(es.max()), 1),
            'mean': round(float(es.mean()), 1),
        }
        stats['front'] = {
            'lat': round(float(es_lat[front_idx]), 1),
            'sst_at_front': round(float(zonal_mean[front_idx]), 1),
        }
    if ul.count():
        stats['ulleung_dokdo'] = {
            'min': round(float(ul.min()), 1),
            'max': round(float(ul.max()), 1),
            'mean': round(float(ul.mean()), 1),
        }

    if extent and tuple(extent) != mapstyle.DEFAULT_EXTENT:
        lon_min, lon_max, lat_min, lat_max = extent
        view = valid[(lon_grid >= lon_min) & (lon_grid <= lon_max) &
                     (lat_grid >= lat_min) & (lat_grid <= lat_max)]
        if view.count():
            stats['view'] = {
                'extent': list(extent),
                'min': round(float(view.min()), 1),
                'max': round(float(view.max()), 1),
                'mean': round(float(view.mean()), 1),
            }
    return stats


def _color_range(lon_grid, lat_grid, sst, extent):
    """표출 영역 안의 값으로 색 범위를 잡는다.

    기본 범위에서는 배열 전체 min/max 가 되어 matplotlib 자동 스케일과 같다.
    영역을 좁혔을 때 색 대비가 죽지 않게 하려는 것.
    """
    lon_min, lon_max, lat_min, lat_max = extent
    sel = np.ma.masked_invalid(sst)[(lon_grid >= lon_min) & (lon_grid <= lon_max) &
                                    (lat_grid >= lat_min) & (lat_grid <= lat_max)]
    if sel.count() == 0:
        return None, None
    return float(sel.min()), float(sel.max())


def render(date, extent=None, style=None, out_path=None, json_path=None, quiet=False):
    """표층 수온도 PNG + 통계를 만든다. 반환: {'png':…, 'json':…, 'stats':…}"""
    style = mapstyle.resolve(style)
    extent = tuple(extent) if extent else mapstyle.DEFAULT_EXTENT

    lon_grid, lat_grid, lat_sub, sst = load(date, mapstyle.analysis_domain(extent))
    stats = build_stats(date, lon_grid, lat_grid, lat_sub, sst, extent)
    vmin, vmax = _color_range(lon_grid, lat_grid, sst, extent)

    fig, ax = mapstyle.make_map(extent)
    pcm = ax.pcolormesh(lon_grid, lat_grid, sst, transform=ccrs.PlateCarree(),
                        shading='auto', cmap='RdYlBu_r', vmin=vmin, vmax=vmax)
    plt.colorbar(pcm, ax=ax, orientation='vertical', label='SST (°C)',
                 shrink=0.7, pad=0.05)

    cs = ax.contour(lon_grid, lat_grid, sst, levels=np.arange(0, 30, 2),
                    colors='k', linewidths=0.5, transform=ccrs.PlateCarree(), zorder=3)
    ax.clabel(cs, inline=True, fontsize=9, fmt='%d', colors='k')

    ax.set_title(f'Eastsea Surface Temperature ({date[:4]} / {date[4:6]} / {date[6:8]})',
                 fontsize=20, fontweight='bold', fontname='serif', y=mapstyle.TITLE_Y)
    mapstyle.decorate(fig, ax, style, extent=extent, source='SST(OSTIA)', source_size=25)

    png = out_path or os.path.join(paths.fig_dir('eastsea_sst'), f'eastsea_temp_{date}.png')
    mapstyle.save(fig, png, style)

    jpath = json_path or os.path.join(paths.json_dir('eastsea_sst'), f'sst_stats_{date}.json')
    with open(jpath, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    if not quiet:
        print(f'sst_stats_{date}.json saved.')
    return {'png': png, 'json': jpath, 'stats': stats}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    render(sys.argv[1], style=mapstyle.REPORT_STYLE)
