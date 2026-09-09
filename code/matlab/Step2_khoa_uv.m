clc; clear; close all;

addpath(genpath('/home/kiwoong/lib/MATLAB_lib/'));
addpath(genpath('/home/kiwoong/lib/m_map/'));
addpath(genpath('/home/EASTSEA/code/'));

%%
year=2025; 
month=12; 
day=15;

%%
aviso_dnpath=sprintf('/home/DATA/MSLA/2025');
flist=dir(sprintf('%s/nrt_global_allsat_phy_l4_%04u%02u%02u*.nc',aviso_dnpath,year,month,day));
FNAME=sprintf('%s/%s',aviso_dnpath,flist.name);
[P,khoa_img]=imread('./code/KHOA_logo2.ras');
lon = ncread(FNAME,'longitude');
lat = ncread(FNAME,'latitude');
sla2= ncread(FNAME,'sla')';
sla = sla2 .* 100; % cm


latnum=find(lat >= 34.25 &  lat <= 48.25);
lonnum=find(lon >= 127.5 &  lon <= 142.25);

load 'Interp_JES_MSSH_Ver3.mat'

%[lon_ add .edit]
lon_=lon(lonnum); lat_=lat(latnum);
[h.lon2,h.lat2]=meshgrid(lon_,flipud(lat_));
h.mssh=flipud(h.mssh);
Grid_0002=flipud(sla(latnum,lonnum));
mssh=h.mssh; % unit = cm 


h.lon2 = double(h.lon2);
h.lat2 = double(h.lat2);

sss = griddata(h.lon2,h.lat2,Grid_0002,h.lon,h.lat,'linear');

h.madt=sss+mssh;




% h.madt=Grid_0002+mssh;



ssh=h.madt./100; % cm => m
[u,v]=geo_current_20180227_sol(h.lon,h.lat,ssh); 

mask=zeros(size(u));
mask(~isnan(u) & ~isnan(v))=1; % sea=1, land=0

figure('visible','on')
m_proj('mercator','lat',[33.5 49.5],'lon',[125.9 141.8]);
m_gshhs_i('patch',[.7 .7 .7], 'edgecolor','none');
m_grid('box','fancy','tickdir','in','fontsize',15,'fontweight','bold','ytick',-90:2:90,'xtick',0:4:360);
set(gcf,'color','w','position',[10 50  750 850], 'PaperPositionMode','auto');
set(gca,'position',[0.05 0.05 0.90 0.90]);
hold on;
m_quiver(h.lon,h.lat,u,v,2,'g','maxheadsize',1); hold on;
m_quiver(127.1,46.5,0.3,0,2,'k','linewidth',3,'maxheadsize',1);
title(['East Sea surface currents',sprintf(' (%04u / %02u / %02u)',year,month,day)],'fontsize',25,'fontweight','bold', 'fontname','Times');
m_text(128.0,46.5,'1 m/s','fontsize',15,'fontweight','bold','fontname','Times','color',[0,0,0]);
m_text(127.1,47.2,'SLA(CMEMS)','fontsize',20,'fontweight','bold', 'fontname','Times');
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
axes('pos',[0.18 0.805 0.35 0.13])
imshow('./code/KHOA_logo2.ras')

savef=sprintf('/home/EASTSEA/figure/khoa_uv/plot_uv_%04u%02u%02u.png',year,month,day);
saveas(gcf,savef);

uv_lon = h.lon; uv_lat = h.lat;
save(sprintf('./output/uv_%04u%02u%02u.mat',year,month,day),'uv_lon','uv_lat','u','v');