# -*- coding: utf-8 -*-
"""
오션스코프 — 해양환경 뷰어 FastAPI 서버.

    python -m uvicorn web.server.app:app --host 127.0.0.1 --port 8000

CMEMS 계정을 받으므로 반드시 127.0.0.1 로만 띄운다. 계정은 요청 본문으로만
받아 작업이 끝나면 메모리에서 지우고, 디스크에 쓰거나 로그로 남기지 않는다.
"""
import io
import os
import re
import zipfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import jobs, pipeline

BASE = pipeline.BASE
STATIC = os.path.join(BASE, 'web', 'static')

DATE_RE = re.compile(r'^\d{8}$')
NAME_RE = re.compile(r'^[a-z]+_[0-9a-f]{10}\.png$')

@asynccontextmanager
async def lifespan(_app):
    # 첫 요청이 cartopy 육지 폴리곤 재투영 때문에 10초쯤 느려지는 걸 막는다
    import mapstyle
    mapstyle.warmup()
    yield


app = FastAPI(title='오션스코프 해양환경 뷰어', lifespan=lifespan)


# 소용돌이 탐지는 격자 수에 민감해서(등고선 500단계 × 후보마다 격자 전체 판정)
# 영역을 무한정 넓히면 한 건에 수 분씩 걸린다. 동해 기본 범위가 270 deg² 이고
# 1,500 deg² 에서 2분을 넘기므로 그 아래에서 끊는다. 수온·해류는 제한 없다.
MAX_EDDY_AREA = 1000     # deg²


class RenderRequest(BaseModel):
    date: str = Field(..., description='YYYYMMDD')
    north: float = 50.5
    south: float = 33.5
    west: float = 125.9
    east: float = 141.8
    layers: list[str] = ['eddy', 'current', 'sst']
    quality: str = 'preview'
    username: str | None = None
    password: str | None = None


@app.post('/api/render')
def render(req: RenderRequest):
    if not DATE_RE.match(req.date):
        raise HTTPException(400, '날짜는 YYYYMMDD 형식이어야 합니다.')
    if req.south >= req.north or req.west >= req.east:
        raise HTTPException(400, '영역이 올바르지 않습니다 (남<북, 서<동).')
    if not (-90 <= req.south and req.north <= 90):
        raise HTTPException(400, '위도는 -90 ~ 90 사이여야 합니다.')
    if not (-180 <= req.west and req.east <= 180):
        raise HTTPException(400, '경도는 -180 ~ 180 사이여야 합니다 (날짜변경선은 넘을 수 없습니다).')
    if not req.layers:
        raise HTTPException(400, '표출할 항목을 하나 이상 선택하세요.')

    area = (req.east - req.west) * (req.north - req.south)
    if 'eddy' in req.layers and area > MAX_EDDY_AREA:
        raise HTTPException(
            400, f'소용돌이 분석 영역이 너무 넓습니다 ({area:.0f} deg²). '
                 f'{MAX_EDDY_AREA} deg² 이하로 좁히거나 소용돌이 항목을 빼고 실행하세요.')

    job = jobs.submit({
        'date': req.date,
        'extent': (req.west, req.east, req.south, req.north),
        'layers': req.layers,
        'quality': req.quality,
        'username': req.username,
        'password': req.password,
    }, pipeline.run)
    return {'job_id': job.id, 'queued': jobs.pending()}


@app.get('/api/jobs/{job_id}')
def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, '작업을 찾을 수 없습니다 (서버가 재시작됐을 수 있습니다).')
    return job.to_dict()


def _cached(date: str, name: str):
    if not DATE_RE.match(date) or not NAME_RE.match(name):
        raise HTTPException(400, '잘못된 경로입니다.')
    path = os.path.join(pipeline.CACHE, date, name)
    if not os.path.exists(path):
        raise HTTPException(404, '이미지를 찾을 수 없습니다.')
    return path


@app.get('/api/image/{date}/{name}')
def image(date: str, name: str):
    return FileResponse(_cached(date, name), media_type='image/png')


@app.get('/api/download/{date}/{name}')
def download(date: str, name: str, filename: str | None = None):
    return FileResponse(_cached(date, name), media_type='image/png',
                        filename=filename or name)


@app.get('/api/download/{date}.zip')
def download_zip(date: str, names: str = Query(..., description='쉼표로 구분한 파일명')):
    entries = [n.strip() for n in names.split(',') if n.strip()]
    if not entries:
        raise HTTPException(400, '내려받을 파일이 없습니다.')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in entries:
            path = _cached(date, n)
            z.write(path, arcname=f'{n.split("_")[0]}_{date}.png')
    buf.seek(0)
    return StreamingResponse(
        buf, media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="eastsea_{date}.zip"'})


@app.get('/api/health')
def health():
    return {'ok': True, 'queued': jobs.pending()}


app.mount('/', StaticFiles(directory=STATIC, html=True), name='static')
