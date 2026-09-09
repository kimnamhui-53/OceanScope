
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from netCDF4 import Dataset
from scipy.io import savemat
import os
import sys
import glob

import paths

# today = sys.argv[1] if len(sys.argv) > 1 else '20251215'
today = '20260818'
yyyy = today[:4]
mm = today[4:6]
dd = today[6:8]

flist = paths.find_data(f'{today}*UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc')

if not flist:
    raise FileNotFoundError(
        f"'{data_dir}' 안에 {today}120000-UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc 파일이 없습니다."
    )

fnm = flist[0]

ds = Dataset(fnm)
lon = ds.variables['lon'][:]
lat = ds.variables['lat'][:]
mask = ds.variables['mask'][0, :, :]  # read for parity with original (unused downstream)
analysed_sst = ds.variables['analysed_sst'][0, :, :] - 273.15  # K -> degC

latnum = np.where((lat >= 34.25) & (lat <= 48.25))[0]
lonnum = np.where((lon >= 127.5) & (lon <= 142.25))[0]

lon_ = lon[lonnum]
lat_ = lat[latnum]
lon_grid, lat_grid = np.meshgrid(lon_, lat_[::-1])
sst = analysed_sst[np.ix_(latnum, lonnum)][::-1, :]

fig = plt.figure(figsize=(7.55, 8.5), facecolor='w')
ax = fig.add_axes([0.078, 0.05, 0.90, 0.90], projection=ccrs.Mercator(central_longitude=np.mean([125.9, 141.8])))
ax.set_extent([125.9, 141.8, 34.3, 48.2], crs=ccrs.PlateCarree())

pcm = ax.pcolormesh(lon_grid, lat_grid, sst, shading='gouraud', cmap='jet',
                     vmin=0, vmax=32, transform=ccrs.PlateCarree(), zorder=1)

ax.add_feature(cfeature.LAND, facecolor=[.7, .7, .7], edgecolor='none', zorder=2)
ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor=[.7, .7, .7], zorder=3)

gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, linewidth=1, color='gray', alpha=0.5, linestyle='--')
gl.top_labels = False
gl.right_labels = False
gl.xlocator = plt.FixedLocator(np.arange(0, 361, 4))
gl.ylocator = plt.FixedLocator(np.arange(-90, 91, 2))
gl.xlabel_style = {'size': 15, 'weight': 'bold'}
gl.ylabel_style = {'size': 15, 'weight': 'bold'}
ax.tick_params(direction='in')

cs = ax.contour(lon_grid, lat_grid, sst, colors='k', transform=ccrs.PlateCarree(), zorder=4)
ax.clabel(cs, fontsize=10, colors='k')

ytik = np.arange(0, 33, 2)
cbh = fig.colorbar(pcm, ax=ax, ticks=ytik)
cbh.ax.set_yticklabels([str(t) for t in ytik])

ax.set_title(f'Sea Surface Temperature ({yyyy} / {mm} / {dd})', fontsize=24, fontweight='bold', fontname='serif')

labels = [
    (126.9, 47.2, 'SST(OSTIA)', 30, [0, 0, 0]),
    (129.30, 42.25, 'NAJIN', 9, [1, 1, 1]),
    (128.15, 40.95, 'MUSUDAN', 9, [1, 1, 1]),
    (126.10, 39.17, 'WONSAN', 9, [1, 1, 1]),
    (127.20, 38.10, 'SOKCHO', 9, [1, 1, 1]),
    (127.60, 37.55, 'DONGHAE', 9, [1, 1, 1]),
    (128.60, 36.60, 'HUPO', 9, [1, 1, 1]),
    (128.10, 36.03, 'POHANG', 9, [1, 1, 1]),
    (128.15, 35.30, 'BUSAN', 9, [1, 1, 1]),
    (132, 37.5, 'DOKDO', 9, [0, 0, 0]),
    (133, 39.5, 'East Sea', 23, [0, 0, 0]),
]
for lon_t, lat_t, text, size, color in labels:
    ax.text(lon_t, lat_t, text, transform=ccrs.PlateCarree(),
            fontsize=size, fontweight='bold', fontname='serif', color=color, zorder=6)

mark_points = [
    (131.8, 37.2, '.', 11, 'r', 'r'),
    (130.89, 37.5, '.', 11, 'r', 'r'),
    (129.15, 35.2, '.', 11, 'r', 'r'),
    (129.4, 36, '.', 11, 'r', 'r'),
    (129.48, 36.7, '.', 11, 'r', 'r'),
    (129.1, 37.5, '.', 11, 'r', 'r'),
    (128.5, 38.2, '.', 11, 'r', 'r'),
    (127.35, 39.15, '.', 11, 'r', 'r'),
    (129.7, 40.9, '.', 11, 'r', 'r'),
    (130.25, 42.3, '.', 11, 'r', 'r'),
]
for lon_pt, lat_pt, marker, size, color, facecolor in mark_points:
    ax.plot(lon_pt, lat_pt, marker=marker, markersize=size, color=color, markerfacecolor=facecolor,
            transform=ccrs.PlateCarree(), zorder=7)

latlim = [35, 35, 39, 39, 35]
lonlim = [128, 133, 133, 128, 128]
ax.plot(lonlim, latlim, linewidth=2, color='r', transform=ccrs.PlateCarree(), zorder=7)

save_dir = paths.fig_dir('eastsea_sst')
os.makedirs(save_dir, exist_ok=True)
save_name = os.path.join(save_dir, f'ostia_sst_{today}.png')
plt.savefig(save_name, dpi=150, bbox_inches='tight')
plt.close()

sst_lon = lon_grid
sst_lat = lat_grid
savemat(os.path.join(paths.out_dir('eastsea_sst', 'mat'), f'sst_{today}.mat'), {'sst_lon': sst_lon, 'sst_lat': sst_lat, 'sst': sst})

print(f"Saved: {save_name}")
