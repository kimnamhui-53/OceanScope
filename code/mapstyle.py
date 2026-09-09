# -*- coding: utf-8 -*-
"""
동해 지도 그림 공통 스타일.

eddy_tracking / eastsea_current / eastsea_sst 세 스크립트가 똑같이 복사해서 쓰던
지도 축 생성·육지·해안선·격자선·지명 라벨·관측점·로고 코드를 한곳에 모은 모듈.

스타일은 두 가지다.

    REPORT_STYLE  보고서 발간용 — 로고·관측점·울릉/독도 박스 포함, dpi 800
    WEB_STYLE     웹 뷰어용     — 장식 제거(지명 라벨만 유지), dpi 100

**분석 도메인과 표출 범위(extent)는 별개다.**
분석 도메인은 analysis_domain() 이 표출 범위로부터 정한다.

  · 표출 범위가 동해 기본 범위(DEFAULT_EXTENT) 안이면  → DOMAIN 그대로.
    보고서와 동해 확대 보기가 여기에 해당하며 결과가 예전과 완전히 같다.
  · 그보다 넓은 영역을 요청하면 → 표출 범위 + ANALYSIS_MARGIN 을 분석한다.
    이때 eddy_tracking 의 동해 경계 마스킹은 꺼진다(요청한 영역을 전부 분석).

주의 — eddy_tracking.py 의 동해 경계·가장자리 마스킹은 장식이 아니라 알고리즘의
일부다(동해 밖·격자 가장자리의 가짜 소용돌이 제거). 이 모듈의 스타일 플래그로
끄고 켜는 대상이 아니라 표출 범위에 따라 자동으로 정해진다.
"""
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

import paths

# 동해 기본 분석 도메인 (lon_st, lon_ed, lat_st, lat_ed)
DOMAIN = (126, 142, 34, 50)

# 기본 표출 범위 (lon_min, lon_max, lat_min, lat_max)
DEFAULT_EXTENT = (125.9, 141.8, 33.5, 50.5)

# 동해 밖 영역을 요청했을 때 표출 범위 바깥으로 더 읽어 두는 여유(도).
# 이 여유의 바깥쪽은 가장자리 가짜 소용돌이 제거용으로 지워지므로
# (eddy_tracking.EDGE_TRIM = 0.5°) 표출 범위 자체는 온전히 분석된다.
ANALYSIS_MARGIN = 1.25

# 투영 중심 경도는 표출 범위와 무관하게 고정한다.
# Mercator 에서 central_longitude 는 x 축 평행이동일 뿐이라 그림은 달라지지 않는데,
# 값이 바뀌면 새 투영이 만들어져 cartopy 가 육지 폴리곤을 통째로 재투영한다(약 10초).
# 고정해 두면 표출 범위를 바꿔도 캐시가 재사용되어 렌더가 0.2초로 끝난다.
CENTRAL_LON = float(np.mean([DEFAULT_EXTENT[0], DEFAULT_EXTENT[1]]))

# 울릉·독도 해역 — 소용돌이 개수 집계 영역 (그리기는 region_box 스타일로 제어)
REGION_LON = [128, 133, 133, 128, 128]
REGION_LAT = [35, 35, 39, 39, 35]

# 지명 라벨: (lon, lat, 문구, 글자크기, 색)
PLACES = [
    (129.30, 42.25, 'NAJIN', 9, [1, 1, 1]),
    (128.15, 40.95, 'MUSUDAN', 9, [1, 1, 1]),
    (126.10, 39.17, 'WONSAN', 9, [1, 1, 1]),
    (127.20, 38.10, 'SOKCHO', 9, [1, 1, 1]),
    (127.60, 37.55, 'DONGHAE', 9, [1, 1, 1]),
    (128.60, 36.60, 'HUPO', 9, [1, 1, 1]),
    (128.10, 36.03, 'POHANG', 9, [1, 1, 1]),
    (128.15, 35.30, 'BUSAN', 9, [1, 1, 1]),
    (132.00, 37.50, 'DOKDO', 9, [0, 0, 0]),
    (133.00, 39.50, 'East Sea', 23, [0, 0, 0]),
]

# 관측점(빨간 점): (lon, lat)
STATIONS = [
    (131.80, 37.20), (130.89, 37.50), (129.15, 35.20), (129.40, 36.00),
    (129.48, 36.70), (129.10, 37.50), (128.50, 38.20), (127.35, 39.15),
    (129.70, 40.90), (130.25, 42.30),
]

# 자료 출처 문구를 보고서에서 찍던 위치·크기
SOURCE_POS = (127.6, 47.2)

# 기본 표출 범위에서의 figure 크기 — 다른 범위는 auto_figsize() 가 여기서 유도한다
BASE_FIGSIZE = (8.5, 9.5)

# 제목 위치를 축 상단(1.0)에 고정한다 — set_title(..., y=TITLE_Y) 로 쓴다.
# 값을 주지 않으면 matplotlib 이 제목을 눈금 라벨 위로 자동으로 밀어 올리는데,
# 그 계산이 cartopy 0.25 의 격자선 라벨(gridlines(draw_labels=True))과 맞지 않아
# matplotlib 3.11 에서 제목 좌표가 nan 이 된다. 그러면 제목이 아예 안 그려지고
# 축의 tight bbox 까지 nan 이 되어, save() 의 bbox_inches='tight' 가 지도를 버리고
# 컬러바만 잘라 낸다(수온도가 컬러바 조각으로 나오던 원인).
# 자동 계산이 꺼져도 기본 표출 범위에서 제목은 원래 자리 그대로다(그림 불변).
TITLE_Y = 1.0

REPORT_STYLE = dict(logo=True,  stations=True,  region_box=True,  places=True, dpi=800)
WEB_STYLE    = dict(logo=False, stations=False, region_box=False, places=True, dpi=100)


def resolve(style=None, **override):
    """스타일 dict 를 확정한다. style 미지정 시 WEB_STYLE 기준."""
    s = dict(WEB_STYLE if style is None else style)
    s.update({k: v for k, v in override.items() if v is not None})
    return s


def dsearchn(array, value):
    """value 에 가장 가까운 원소의 인덱스 (세 스크립트에 중복돼 있던 헬퍼)."""
    return int(np.abs(array - value).argmin())


def is_eastsea_view(extent=None):
    """표출 범위가 동해 기본 범위(DEFAULT_EXTENT) 안에 들어오는가.

    True 면 예전과 똑같이 DOMAIN 을 분석하고 동해 경계 마스킹을 적용한다.
    """
    if extent is None:
        return True
    lon_min, lon_max, lat_min, lat_max = extent
    w, e, s, n = DEFAULT_EXTENT
    eps = 1e-9
    return (lon_min >= w - eps and lon_max <= e + eps and
            lat_min >= s - eps and lat_max <= n + eps)


def analysis_domain(extent=None, margin=ANALYSIS_MARGIN):
    """표출 범위에 맞는 분석 도메인 (lon_st, lon_ed, lat_st, lat_ed).

    동해 기본 범위 안이면 DOMAIN 을 그대로 쓴다(보고서·동해 확대 결과 불변).
    더 넓은 영역을 요청하면 그 영역 전체 + margin 을 분석 대상으로 삼는다.
    """
    if is_eastsea_view(extent):
        return DOMAIN
    lon_min, lon_max, lat_min, lat_max = extent
    return (max(lon_min - margin, -180.0), min(lon_max + margin, 180.0),
            max(lat_min - margin, -90.0), min(lat_max + margin, 90.0))


def domain_slices(lon, lat, domain=None):
    """분석 도메인에 해당하는 (lon_slice, lat_slice) 를 돌려준다.

    domain 을 생략하면 동해 기본 도메인(DOMAIN)을 쓴다.
    """
    lon_st, lon_ed, lat_st, lat_ed = domain if domain else DOMAIN
    return (slice(dsearchn(lon, lon_st), dsearchn(lon, lon_ed) + 1),
            slice(dsearchn(lat, lat_st), dsearchn(lat, lat_ed) + 1))


def _tick_step(span, base_span, base_step):
    """격자선 간격. 기본 표출 범위에서는 정확히 base_step 이 나온다."""
    target = base_span / base_step
    for s in (0.25, 0.5, 1, 2, 4, 5, 10):
        if span / s <= target + 1e-9:
            return s
    return 10


def _ticks(vmin, vmax, step, lo, hi):
    """표출 범위(+한 칸 여유) 안의 격자선 위치.

    전 지구 범위로 격자선을 만들면 화면 밖 선까지 cartopy 가 경계와 교차 계산을
    해서 좁은 영역일수록 느려진다. 그려지는 선은 어차피 같다.
    """
    start = np.floor((vmin - step) / step) * step
    stop = np.ceil((vmax + step) / step) * step
    return np.arange(max(start, lo), min(stop, hi) + step / 2, step)


def _merc_aspect(extent):
    """Mercator 로 그렸을 때의 가로/세로 비."""
    def y(deg):
        deg = float(np.clip(deg, -84, 84))
        return np.degrees(np.log(np.tan(np.pi / 4 + np.radians(deg) / 2)))

    lon_min, lon_max, lat_min, lat_max = extent
    return (lon_max - lon_min) / (y(lat_max) - y(lat_min))


def auto_figsize(extent):
    """표출 범위 종횡비에 맞춘 figure 크기.

    기본 표출 범위에서는 정확히 BASE_FIGSIZE 가 나온다(보고서 그림 불변).
    가로로 넓은 영역을 요청하면 그림도 가로로 넓어진다 — 크기를 고정해 두면
    지도가 납작한 띠로 눌리면서 제목·컬러바가 지도와 겹친다.
    """
    w, h = BASE_FIGSIZE
    ratio = (w / h) * (_merc_aspect(extent) / _merc_aspect(DEFAULT_EXTENT))
    ratio = float(np.clip(ratio, 0.4, 2.5))
    area = w * h
    return (np.sqrt(area * ratio), np.sqrt(area / ratio))


def make_map(extent=None, figsize=None):
    """지도 축을 만들어 (fig, ax) 반환. 육지·해안선·격자선까지 그린다.

    figsize 를 생략하면 표출 범위 종횡비에 맞춰 자동으로 정한다.
    """
    extent = tuple(extent) if extent else DEFAULT_EXTENT
    lon_min, lon_max, lat_min, lat_max = extent

    fig = plt.figure(figsize=figsize or auto_figsize(extent), facecolor='w')
    ax = fig.add_axes([0.05, 0.05, 0.90, 0.90],
                      projection=ccrs.Mercator(central_longitude=CENTRAL_LON))
    ax.set_extent(list(extent), crs=ccrs.PlateCarree())

    ax.add_feature(cfeature.LAND, facecolor=[.4, .4, .4], edgecolor='none', zorder=1)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor='k', zorder=2)

    d = DEFAULT_EXTENT
    xstep = _tick_step(lon_max - lon_min, d[1] - d[0], 4)
    ystep = _tick_step(lat_max - lat_min, d[3] - d[2], 2)

    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                      linewidth=1, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.xlocator = plt.FixedLocator(_ticks(lon_min, lon_max, xstep, 0, 360))
    gl.ylocator = plt.FixedLocator(_ticks(lat_min, lat_max, ystep, -90, 90))
    gl.xlabel_style = {'size': 15, 'weight': 'bold'}
    gl.ylabel_style = {'size': 15, 'weight': 'bold'}
    ax.tick_params(direction='in')
    return fig, ax


def _visible(extent, lon, lat):
    lon_min, lon_max, lat_min, lat_max = extent
    return lon_min <= lon <= lon_max and lat_min <= lat <= lat_max


def add_places(ax, extent=None):
    """지명 라벨. 표출 범위 밖 라벨은 그리지 않는다.

    라벨은 좌표에서 오른쪽으로 뻗으므로, 글자가 오른쪽 테두리를 넘어가는
    라벨도 뺀다. 넓은 영역(서해·남해·전 해역)에서 큰 'East Sea' 글자가
    지도 밖 여백으로 삐져나오는 것을 막는다. 기본 표출 범위에서는 모든
    라벨이 그대로 남아 보고서 그림은 달라지지 않는다.
    """
    extent = tuple(extent) if extent else DEFAULT_EXTENT
    lon_min, lon_max = extent[0], extent[1]
    ax_width_in = ax.figure.get_size_inches()[0] * ax.get_position().width
    for lon, lat, text, size, color in PLACES:
        if not _visible(extent, lon, lat):
            continue
        # Mercator 의 x 는 경도에 비례하므로 글자 폭을 도(°) 로 환산할 수 있다.
        # 0.6 은 굵은 serif 글자의 대략적인 폭/크기 비.
        width_deg = (0.6 * size / 72 * len(text)) / ax_width_in * (lon_max - lon_min)
        if lon + width_deg > lon_max:
            continue
        ax.text(lon, lat, text, transform=ccrs.PlateCarree(), fontsize=size,
                fontweight='bold', fontname='serif', color=color, zorder=6)


def add_stations(ax, extent=None):
    """관측점(빨간 점). 보고서 전용."""
    extent = tuple(extent) if extent else DEFAULT_EXTENT
    for lon, lat in STATIONS:
        if not _visible(extent, lon, lat):
            continue
        ax.plot(lon, lat, marker='.', markersize=11, color='r', markerfacecolor='r',
                transform=ccrs.PlateCarree(), zorder=8)


def add_region_box(ax, label=None):
    """울릉·독도 해역 빨간 사각형 + 범례 표식. 보고서 전용."""
    ax.plot(REGION_LON, REGION_LAT, linewidth=2, color='r',
            transform=ccrs.PlateCarree(), zorder=8)
    if label:
        ax.plot(127.8, 46.5, marker='s', markersize=15, color='r', markerfacecolor='none',
                transform=ccrs.PlateCarree(), zorder=8)
        ax.text(128.3, 46.3, label, transform=ccrs.PlateCarree(), fontsize=15,
                fontweight='bold', fontname='serif', color=[1, 1, 1], zorder=6)


def add_source(ax, text, size, style):
    """자료 출처 문구.

    보고서는 기존과 같은 지도 좌표 위치에, 웹은 영역을 좁혀도 안 잘리도록
    축 좌상단에 고정해서 찍는다.
    """
    if style.get('logo'):   # 보고서 스타일
        ax.text(SOURCE_POS[0], SOURCE_POS[1], text, transform=ccrs.PlateCarree(),
                fontsize=size, fontweight='bold', fontname='serif', color=[0, 0, 0], zorder=6)
    else:
        ax.text(0.02, 0.98, text, transform=ax.transAxes, fontsize=13,
                fontweight='bold', fontname='serif', color=[0, 0, 0],
                va='top', ha='left', zorder=6)


def add_logo(fig):
    """KHOA 로고. 보고서 전용."""
    import imageio.v2 as imageio
    logo = imageio.imread(paths.common('KHOA_logo2.ras'))
    ab = AnnotationBbox(OffsetImage(logo, zoom=0.1), (0.35, 0.90),
                        xycoords='figure fraction', frameon=False)
    fig.add_artist(ab)


def decorate(fig, ax, style, extent=None, source=None, source_size=20, box_label=None):
    """스타일에 따라 라벨·관측점·박스·로고를 한 번에 얹는다."""
    if source:
        add_source(ax, source, source_size, style)
    if style.get('places'):
        add_places(ax, extent)
    if style.get('stations'):
        add_stations(ax, extent)
    if style.get('region_box'):
        add_region_box(ax, box_label)
    if style.get('logo'):
        add_logo(fig)


_warmed = False


def warmup():
    """cartopy 육지 폴리곤 재투영 캐시를 미리 채운다.

    한 프로세스에서 육지가 많이 걸리는 영역을 처음 그릴 때 폴리곤 재투영에
    10초 남짓이 든다(그 뒤로는 0.2초). 웹 서버는 기동할 때 한 번 불러 두면
    첫 요청이 느려지지 않는다.
    """
    global _warmed
    if _warmed:
        return
    import io
    fig, _ = make_map((128, 133, 35, 39))   # 한반도·일본 해안선이 걸리는 영역
    fig.savefig(io.BytesIO(), format='png', dpi=50)
    plt.close(fig)
    _warmed = True


def save(fig, path, style):
    """dpi 를 스타일에서 가져와 저장하고 figure 를 닫는다."""
    fig.savefig(path, dpi=style.get('dpi', 100), bbox_inches='tight')
    plt.close(fig)
    return path
