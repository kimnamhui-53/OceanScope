
setenv('MATLAB_USE_LOCAL_JVM','1')
opengl('save', 'software');

%% Data load
addpath(genpath('/home/kiwoong/lib/MATLAB_lib/'));
addpath(genpath('/home/kiwoong/lib/m_map/'));

%% Data load
aviso_dnpath=sprintf('/home/DATA/MSLA/2026');
flist=dir(sprintf('%s/nrt_global_allsat_phy_l4_20260818*.nc',aviso_dnpath));
FNAME=sprintf('%s/%s',aviso_dnpath,flist.name);
[P,khoa_img]=imread('KHOA_logo2.ras');
lon = ncread(FNAME,'longitude');
lat = ncread(FNAME,'latitude');
sla2= ncread(FNAME,'sla')';

lon_st = 126; lon_ed = 142; lat_st = 34; lat_ed = 50; % 126E~142E 34N~50N

lon_num = dsearchn(lon,lon_st):dsearchn(lon,lon_ed);
lat_num = dsearchn(lat,lat_st):dsearchn(lat,lat_ed);

[lon, lat] = meshgrid(lon(lon_num),lat(lat_num));

sla = sla2(lat_num,lon_num);

amplitude = 1;   % cm
warm_rad = 25;  % km
cold_rad = 12;  % km

clear lon_num lat_num sla2 time2 lon_st lon_ed lat_st lat_ed 
%%

% Nan (SouthEast of Japan)
for i = 1:50
    sla(i,i+79:129) = NaN;
end
sla(1:5,1:end) = NaN;
sla(1:129,1:5) = NaN;
sla(1:129,126:129) = NaN;

m_proj('mercator','lon',[min(min(lon)) max(max(lon))],'lat',[min(min(lat)) max(max(lat))]);

% distance between grid points (x1,y1) and (x1,y3), unit: meters
dislat(1:size(lon,1),1:size(lon,2))=m_lldist([lon(1,1) lon(3,1)],[lat(1,1) lat(3,1)])*1000;
dislat(1,:)=m_lldist([lon(1,1) lon(2,1)],[lat(1,1) lat(2,1)])*1000;
dislat(size(lon,1),:)=dislat(1,:);

% distance between (x1,y1) and (x3,y1), unit:meters
for cc=1:length(lon(:,1))
    dislon(cc,1:size(lon,2))=m_lldist([lon(cc,1) lon(cc,3)],[lat(cc,1) lat(cc,3)]).*1000;
end

clear hhh1

hhh1=sla*100; % sla : meter to centimeter

c=0; % set eddy count to zero
w=0;

for j=50:-0.2:-50 % cold eddy
    levels=[j 1000];cf=figure('visible','off');
    [c1,~]=contour(lon,lat,hhh1,levels); % draw the contours of sea level anomalies that equal to j.
    wz=find(c1(1,:)==j); % Each j contour
    
    for k=1:length(wz)
        clear in bx by area XX YY inbndy tempe Dis
        if c1(1,wz(k)+1)==c1(1,wz(k)+c1(2,wz(k))) && c1(2,wz(k)+1)==c1(2,wz(k)+c1(2,wz(k)))&&c1(2,wz(k))~=2 % c1 = 2x4 double or lager
            % 0.5degree or lager
            if (max(c1(1,wz(k)+1:wz(k)+c1(2,wz(k))-1))-min(c1(1,wz(k)+1:wz(k)+c1(2,wz(k))-1)))>=0.5&&(max(c1(2,wz(k)+1:wz(k)+c1(2,wz(k))-1))-min(c1(2,wz(k)+1:wz(k)+c1(2,wz(k))-1)))>=0.5
                % record the lon/lat coordinates
                kmianx=(c1(1,wz(k)+1:wz(k)+c1(2,wz(k))));
                kmiany=(c1(2,wz(k)+1:wz(k)+c1(2,wz(k))));
                % calculate max distance
                for p=0:length(kmianx)-1
                    for q=1:length(kmianx)
                        Dis(p*length(kmianx)+q)=m_lldist([kmianx(p+1) kmianx(q)],[kmiany(p+1) kmiany(q)]);
                    end
                end
                    
                if max(Dis)<=250 % max distance, not longer than 200 km
                    % make boundry
                    bx=[kmianx';kmianx(1)]';
                    by=[kmiany';kmiany(1)]';
                    in=inpolygon(lon,lat,bx,by); % closed contour = 1
                        
                    centroid_lon=mean(kmianx);% longitude of eddy centroid
                    centroid_lat=mean(kmiany);% latitude of eddy centroid
                      
                    if inpolygon(centroid_lon,centroid_lat,bx,by)~=0 % check centroid in closed contour. logical = 1
                           
                        inbndy=hhh1(in); % sla in. (cm)
                        if min(inbndy)<=j % cold eddy
                            tempe=find(inbndy==min(inbndy)); 
                            if length(tempe)>1
                                tempe=floor(mean(tempe));
                            end
                            if j-inbndy(tempe)>=amplitude % amplitude 3 cm.
                                area=dislon(in).*dislat(in)/4;% area (m^2)
                                if sqrt(sum(sum(area/1000/1000))/pi)>cold_rad % radius is larger than 25 km.
                                    c=c+1; 
                                    fprintf('%d coldeddy(eddies) found.\n',c);
                                    hhh1(in)=NaN; 
                                    ColdEddy(c).center(1)=mean(kmianx);
                                    ColdEddy(c).center(2)=mean(kmiany);
                                    ColdEddy(c).amplitude(1)=j-inbndy(tempe); 
                                    ColdEddy(c).radius(1)=sqrt(sum(sum(area/1000/1000))/pi);
                                    ColdEddy(c).edge(1,1:length(bx))=bx; 
                                    ColdEddy(c).edge(2,1:length(by))=by; 
                                 end
                            end
                        end
                    end
                end
            end
        end
    end
    close(cf);close all; 
    close all hidden
end

clear hhh1
hhh1=sla*100; 
clear c1 ch1 wz
for j=-50:0.2:50 % warm eddy
    levels=[j 1000];cf=figure('visible','off');
    [c1,~]=contour(lon,lat,hhh1,levels);
    wz=find(c1(1,:)==j);
    
    for k=1:length(wz)
        
        clear in bx by area XX YY inbndy tempe Dis
        
        if c1(1,wz(k)+1)==c1(1,wz(k)+c1(2,wz(k)))&&c1(2,wz(k)+1)==c1(2,wz(k)+c1(2,wz(k)))&&c1(2,wz(k))~=2
            if (max(c1(1,wz(k)+1:wz(k)+c1(2,wz(k))-1))-min(c1(1,wz(k)+1:wz(k)+c1(2,wz(k))-1)))>=0.5&&(max(c1(2,wz(k)+1:wz(k)+c1(2,wz(k))-1))-min(c1(2,wz(k)+1:wz(k)+c1(2,wz(k))-1)))>=0.5
                   
                kmianx=(c1(1,wz(k)+1:wz(k)+c1(2,wz(k))-1));
                kmiany=(c1(2,wz(k)+1:wz(k)+c1(2,wz(k))-1));
                    
                for p=0:length(kmianx)-1
                    for q=1:length(kmianx)
                        Dis(p*length(kmianx)+q)=m_lldist([kmianx(p+1) kmianx(q)],[kmiany(p+1) kmiany(q)]);
                    end
                end
                    
                if max(Dis)<=250
                        
                    bx=[kmianx';kmianx(1)]';
                    by=[kmiany';kmiany(1)]';
                    in=inpolygon(lon,lat,bx,by);
                                        
                        
                    centroid_lon=mean(kmianx);
                    centroid_lat=mean(kmiany);
                        
                    if inpolygon(centroid_lon,centroid_lat,bx,by)~=0
                           
                        inbndy=hhh1(in);
                        if min(inbndy)>=j    % warm eddy
                            tempe=find(inbndy==max(inbndy)); 
                            if length(tempe)>1
                                tempe=floor(mean(tempe));
                            end
                            if inbndy(tempe)-j>=amplitude
                                area=dislon(in).*dislat(in)/4;
                                if sqrt(sum(sum(area/1000/1000))/pi)>warm_rad
                                    w=w+1;
                                    fprintf('%d warmeddy(eddies) found.\n',w);
                                    hhh1(in)=NaN;
                                    WarmEddy(w).center(1)=mean(kmianx);
                                    WarmEddy(w).center(2)=mean(kmiany);
                                    WarmEddy(w).amplitude(1)=inbndy(tempe)-j;
                                    WarmEddy(w).radius(1)=sqrt(sum(sum(area/1000/1000))/pi);
                                    WarmEddy(w).edge(1,1:length(bx))=bx;
                                    WarmEddy(w).edge(2,1:length(by))=by;
                                end
                            end
                        end
                    end
                end
            end
        end
    end
    close(cf);close all;
    close all hidden
end

figure('visible','off')
m_proj('mercator','lat',[33.5 50.5],'lon',[125.9 141.8]);
m_gshhs_i('patch',[.4 .4 .4], 'edgecolor','none');
m_grid('box','fancy','tickdir','in','fontsize',15,'fontweight','bold','ytick',-90:2:90,'xtick',0:4:360);
set(gcf,'color','w','position',[10 50  750 850], 'PaperPositionMode','auto');
set(gca,'position',[0.05 0.05 0.90 0.90]);

hold on;

[C,H] = m_contour(lon,lat,sla,-2:0.01:2,'linewidth',0.5,'linecolor','k');

if exist('ColdEddy','var')
    for c = 1:length(ColdEddy)
        m_plot(ColdEddy(c).edge(1,:),ColdEddy(c).edge(2,:),'color',[0.0 0.45 1],'linewidth',2);
        m_patch(ColdEddy(c).edge(1,:),ColdEddy(c).edge(2,:),[0.0 0.45 1],'facealpha',0.8);
    end
end

if exist('WarmEddy','var')
    for w = 1:length(WarmEddy)
        m_plot(WarmEddy(w).edge(1,:),WarmEddy(w).edge(2,:),'color',[1 0.25 0.0],'linewidth',2);
        m_patch(WarmEddy(w).edge(1,:),WarmEddy(w).edge(2,:),[1 0.25 0.0],'facealpha',0.8);
    end
end

title(['Warm / Cold Eddy (2026 / 08 / 18)'],'fontsize',25,'fontweight','bold', 'fontname','Times');
m_text(127.6,47.2,'SLA(CMEMS)','fontsize',30,'fontweight','bold', 'fontname','Times');
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
m_text(128.3, 46.5, 'UWE/DCE Area', 'fontsize',15, 'fontweight','bold','fontname','Times','Color','k');
m_line(127.8, 46.5, 'marker', 'square', 'markersize',15,'color','r','markerfacecolor','none');
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

axes('pos',[0.18 0.805 0.35 0.13])
imshow('./KHOA_logo2.ras')

w_c = 0;
c_c = 0;
for i = 1:length(WarmEddy)
    elon = WarmEddy(i).center(1);
    elat = WarmEddy(i).center(2);
    inside = inpolygon(elon,elat,lonlim,latlim);
    if inside
        w_c = w_c +1;
    end
end
for i = 1:length(ColdEddy)
    elon = ColdEddy(i).center(1);
    elat = ColdEddy(i).center(2);
    inside = inpolygon(elon,elat,lonlim,latlim);
    if inside
        c_c = c_c +1;
    end
end


%savef=sprintf('/home/Eddy_Tracking/figure/WA_Method_20260818.png');
%saveas(gcf,savef);

print('-dpng','-r800','/home/Eddy_Tracking/figure/WA_Method_20260818'); 

wfnm='/home/Eddy_Tracking/eddy_count/WA_Method_20260818.dat';

sdata=[w,w_c,c,c_c];
saveascii('warmeddy u_warmeddy coldeddy u_coldeddy',wfnm,'w');
saveascii(sdata,wfnm,'%u\t','%u\t','%u\t','%u\t','a');

clear all
close all
quit()
exit
