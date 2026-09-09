clear all; close all; clc;

addpath(genpath('/home/kiwoong/lib/MATLAB_lib/'));
addpath(genpath('/home/kiwoong/lib/m_map/'));
addpath(genpath('/home/EASTSEA/code'));
fpath='/home/DATA/OSTIA/2025';
%
year = 2025; 
month = 12; 
day = 15;
%
fnm=sprintf('%s/%4u%02u%02u120000-UKMO-L4_GHRSST-SSTfnd-OSTIA-GLOB-v02.0-fv02.0.nc',fpath,year,month,day);
       
lon=ncread(fnm,'lon');
lat=ncread(fnm,'lat');
mask=ncread(fnm,'mask')';        
analysed_sst=ncread(fnm,'analysed_sst')'-273.15;

latnum=find(lat >= 34.25 &  lat <= 48.25);
lonnum=find(lon >= 127.5 &  lon <= 142.25);

%[lon_ add .edit]
lon_=lon(lonnum); lat_=lat(latnum);
[lon,lat]=meshgrid(lon_,flipud(lat_));
sst=flipud(analysed_sst(latnum,lonnum));
        
figure('visible','on')
m_proj('mercator','lat',[34.3 48.2],'lon',[125.9 141.8]);
caxis([0 32]); hold on;
m_pcolor(lon,lat,sst); shading interp;
m_gshhs_i('color',[.7 .7 .7]);
m_gshhs_i('patch',[.7 .7 .7], 'edgecolor','none');
m_grid('box','fancy','tickdir','in','fontsize',15,'fontweight','bold','ytick',-90:2:90,'xtick',0:4:360);
% % set(gcf,'color','w','position',[10 50 900 850], 'PaperPositionMode','auto');
%%
% set(gcf,'color','w','position',[10 50 800 850], 'PaperPositionMode','auto');
% set(gca,'position',[0.065 0.05 0.93 0.90]);
%%
set(gcf,'color','w','position',[10 50 755 850], 'PaperPositionMode','auto');
set(gca,'position',[0.078 0.05 0.90 0.90]);



[C,H] = m_contour(lon,lat,sst,'k');
clabel(C,H,'fontsize',10,'color','k');
ytik = [0:2:32];
cbh = colorbar;
set(cbh,'YTick',ytik);
set(cbh,'YTicklabel',num2str(ytik'));
colormap('jet');
title(['Sea Surface Temperature',sprintf(' (%04u / %02u / %02u)',year,month,day)],'fontsize',24,'fontweight','bold', 'fontname','Times');
m_text(126.9,47.2,'SST(OSTIA)','fontsize',30,'fontweight','bold', 'fontname','Times');
m_text(129.30,42.25,'NAJIN','fontsize',9,'fontweight','bold','fontname','Times','color',[1,1,1]);
m_text(128.15,40.95,'MUSUDAN','fontsize',9,'fontweight','bold','fontname','Times','color',[1,1,1]);
m_text(126.10,39.17,'WONSAN','fontsize',9,'fontweight','bold','fontname','Times','color',[1,1,1]);
m_text(127.20,38.10,'SOKCHO','fontsize',9,'fontweight','bold','fontname','Times','color',[1,1,1]);
m_text(127.60,37.55,'DONGHAE','fontsize',9,'fontweight','bold','fontname','Times','color',[1,1,1]);
m_text(128.60,36.60,'HUPO','fontsize',9,'fontweight','bold','fontname','Times','color',[1,1,1]);
m_text(128.10,36.03,'POHANG','fontsize',9,'fontweight','bold','fontname','Times','color',[1,1,1]);
m_text(128.15,35.30,'BUSAN','fontsize',9,'fontweight','bold','fontname','Times','color',[1,1,1]);
m_text(132,37.5,'DOKDO','fontsize',9,'fontweight','bold','fontname','Times','color',[0,0,0]);
m_text(133,39.5,'East Sea','fontsize',23,'fontweight','bold','fontname','Times','color',[0,0,0]);
m_line(131.8,37.2,'marker','.','markersize',11,'color','r');
m_line(130.89,37.5,'marker','.','markersize',11,'color','r');
m_line(129.15,35.2,'marker','.','markersize',11,'color','r');
m_line(129.4,36,'marker','.','markersize',11,'color','r');
m_line(129.48,36.7,'marker','.','markersize',11,'color','r');
m_line(129.1,37.5,'marker','.','markersize',11,'color','r');
m_line(128.5,38.2,'marker','.','markersize',11,'color','r');
m_line(127.35,39.15,'marker','.','markersize',11,'color','r');
m_line(129.7,40.9,'marker','.','markersize',11,'color','r');
m_line(130.25,42.3,'marker','.','markersize',11,'color','r');
latlim=[35 35 39 39 35]; 
lonlim=[128 133 133 128 128];
m_line(lonlim, latlim, 'linewi',2, 'color','r');

savef=sprintf('/home/EASTSEA/figure/ostia_sst/ostia_sst_%04u%02u%02u.png',year,month,day);
saveas(gcf,savef);
sst_lon = lon; sst_lat = lat;
save(sprintf('./output/sst_%04u%02u%02u.mat',year,month,day), 'sst_lon','sst_lat','sst');      
        

