# 오션스코프 (OceanScope)

전 해역 해양환경 분석 도구입니다. 임의의 날짜·영역에서 소용돌이·해류·수온을 분석하고,
그중 동해 연간 분석은 「동해 소용돌이 분석보고서」(국립해양조사원, 연간) 서식 그대로 보고서로 조립합니다.
CMEMS 데이터 다운로드 → 그래프 생성 → 월별 코멘트 작성 → HWPX 보고서 조립까지 한 번에 수행합니다.

```
[CMEMS API] → code/download_data.py → data/MSLA/<연도>/*.nc   (SLA·지형류)
                                      data/OSTIA/<연도>/*.nc  (OSTIA SST)
                                    │
                     ┌──────────────┼──────────────┐
              eddy_tracking.py  eastsea_current.py  eastsea_sst.py
                     │              │               │
              소용돌이 분포도    준실시간 해류도    위성 표층 수온도
              + 개수 JSON                          + 수온 통계 JSON
                     │              │               │
        output/<자료명>/figure/  (그래프 PNG)  ·  output/<자료명>/json/  (통계)
                     └──────────────┼──────────────┘
                          code/run_pipeline.py  (월별 루프·취합)
                                    │
                    Claude Code가 그래프·통계를 보고 월별 코멘트 작성
                                    │
                          code/build_report.py
                 (template/template_2025.hwpx 치환 조립)
                                    │
             output/report/<연도> 동해 소용돌이 분석보고서.hwpx
```

## 폴더 구조

```
east-sea-eddy/   (오션스코프)
├─ code/                     파이썬 스크립트
│  ├─ paths.py               공통 경로 헬퍼 (모든 폴더 경로를 여기서 결정)
│  ├─ download_data.py  eddy_tracking.py  eastsea_current.py
│  ├─ eastsea_sst.py    ostia_sst.py
│  ├─ run_pipeline.py   build_report.py
│  └─ matlab/                원본 MATLAB 스크립트 (참고용)
├─ data/                     입력 원본 (자료 종류 × 연도)
│  ├─ MSLA/<연도>/           nrt_global_allsat_phy_l4_*.nc
│  │                         → eddy_tracking.py, eastsea_current.py 공용
│  ├─ OSTIA/<연도>/          *-UKMO-L4_GHRSST-...-OSTIA-GLOB-*.nc
│  │                         → eastsea_sst.py, ostia_sst.py
│  └─ common/                KHOA_logo2.ras 등 공용 자산
├─ output/                   산출물
│  ├─ eddy_tracking/
│  │  ├─ figure/             WA_Method_*.png
│  │  └─ json/               eddy_stats_*.json
│  ├─ eastsea_current/
│  │  └─ figure/             eastsea_current_*.png
│  ├─ eastsea_sst/
│  │  ├─ figure/             eastsea_temp_*.png
│  │  └─ json/               sst_stats_*.json
│  ├─ intermediate/          중간 산출물
│  │  ├─ summary/            summary_<연도>.json
│  │  └─ comments/           comments_<연도>.json
│  └─ report/                <연도> 동해 소용돌이 분석보고서.hwpx  ← 최종 결과물
├─ template/                 보고서 서식 템플릿
│  └─ template_2025.hwpx
├─ docs/                     문서
│  ├─ PLAN.md                자동화 계획서
│  ├─ todo.md                작업 메모
│  └─ design/                시스템 관계도 (Claude Design 캔버스 + PNG)
├─ web/                      웹 뷰어 (보고서와 별개, docs/WEB_PLAN.md 참고)
│  ├─ server/                FastAPI (app.py · jobs.py · pipeline.py)
│  ├─ static/                index.html · app.js · style.css
│  └─ cache/                 렌더된 PNG·통계 (재생성 가능)
├─ reference/                참고 자료 (파이프라인에서 사용하지 않음)
│  ├─ reports/               2025 소용돌이 보고서(.hwp), 수치예측모델 보고서
│  ├─ observation/           KHOA 해류조사·CTD 관측 자료 (.xlsx)
│  ├─ contest/               AI 공모전 서류 (.hwpx)
│  └─ WA_Method_20260818.png MATLAB 원본 출력 샘플
└─ .claude/skills/generate-eddy-report/   Claude Code 스킬
```

## 빠른 시작

Claude Code에서 한 줄이면 됩니다:

```
/generate-eddy-report 2026
```

데이터 다운로드부터 최종 HWPX 생성까지 자동으로 진행되며, 월별 요약 코멘트는 Claude가
그래프와 통계를 직접 보고 2025년 보고서 문체로 작성합니다.
과거 연도도 동일합니다: `/generate-eddy-report 2024`

## 웹 뷰어 — 원하는 날짜·영역 바로 보기

보고서와 별개로, 아무 날짜·영역이나 골라 지도 그림을 바로 보고 내려받는 도구입니다.

```bash
python -m uvicorn web.server.app:app --host 127.0.0.1 --port 8000
```

브라우저에서 `http://127.0.0.1:8000` 접속 → 날짜·영역·항목(소용돌이/해류/수온)을
고르고 **분석 실행**. 자료가 없는 날짜는 CMEMS 에서 자동으로 내려받습니다
(계정을 비워 두면 `copernicusmarine login` 으로 저장해 둔 로그인을 씁니다).

보고서와 **같은 분석 코드**를 쓰므로 숫자가 어긋나지 않습니다. 다른 것은 장식
(로고·박스·관측점 제거)과 해상도, 표출 범위뿐입니다. 설계·성능 측정·주의사항은
[docs/WEB_PLAN.md](docs/WEB_PLAN.md) 에 정리돼 있습니다.

**지정한 영역 전체가 분석됩니다.** 동해 안쪽만 고르면 예전처럼 동해 전역에서
분석하고 선택 영역을 표출·통계 범위로 쓰지만(보고서 경로 — 결과 불변), 동해
밖까지 넓히면 황해·동중국해·일본 동안까지 그 영역 전부를 분석합니다. 소용돌이
탐지는 영역이 넓을수록 오래 걸려 1,000 deg²(예: 40°×25°)까지만 허용합니다.

> CMEMS 계정을 입력받으므로 반드시 `127.0.0.1` 로만 띄우세요.
> 입력한 계정은 해당 요청에만 쓰이고 디스크·로그에 남지 않습니다.

## 사전 준비 (최초 1회)

1. **Python 패키지**

   ```bash
   pip install copernicusmarine numpy matplotlib cartopy shapely netCDF4 scipy pyproj imageio pillow
   ```

2. **CMEMS 로그인** — [Copernicus Marine](https://data.marine.copernicus.eu) 무료 계정 필요

   ```bash
   copernicusmarine login
   ```

3. **템플릿** — 한글(정품)에서 `reference/reports/2025 동해 소용돌이 분석보고서.hwp`를
   **다른 이름으로 저장 → HWPX** 로 변환해 `template/template_2025.hwpx`로 배치
   (이미 배치되어 있으면 생략)

## 수동 실행

단계별로 직접 실행할 수도 있습니다:

```bash
# 1) 데이터 다운로드 + 그래프 + 통계 (연도 전체 또는 특정 월)
python code/run_pipeline.py 2026
python code/run_pipeline.py 2026 3            # 3월만
python code/run_pipeline.py 2026 --skip-download   # 데이터 보유 시

# 2) 코멘트 작성 → output/intermediate/comments/comments_2026.json (Claude 또는 수동 작성)
#    형식: {"1": "(1월) 동해에 나타난 소용돌이는 ...", ..., "12": "(12월) ..."}

# 3) 보고서 조립
python code/build_report.py 2026
python code/build_report.py 2026 --inspect    # 템플릿 구조 확인(문단/표/그림 매핑)
```

개별 그래프만 다시 그릴 때 (날짜는 `YYYYMMDD`):

```bash
python code/eddy_tracking.py 20260115
python code/eastsea_current.py 20260115
python code/eastsea_sst.py 20260115
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| `code/paths.py` | 공통 경로 헬퍼 — data/output 하위 폴더를 결정하고 입력 파일을 재귀 검색 |
| `code/mapstyle.py` | 지도 그림 공통 스타일 (보고서용/웹용) — 축·해안선·격자선·지명·로고 |
| `code/download_data.py` | CMEMS 원본 파일 다운로드 (SLA/지형류 + OSTIA SST, 매월 15일자) |
| `code/eddy_tracking.py` | W-A 알고리즘 소용돌이 탐지 → 분포도 PNG + 개수 JSON |
| `code/eastsea_current.py` | 지형류(ugos/vgos) 준실시간 해류도 PNG |
| `code/eastsea_sst.py` | OSTIA 표층 수온도 PNG + 수온 통계 JSON |
| `code/ostia_sst.py` | OSTIA SST 단독 플롯 + .mat 저장 (보조 스크립트) |
| `code/run_pipeline.py` | 월별 루프 오케스트레이터, `summary_<연도>.json` 취합 |
| `code/build_report.py` | HWPX 템플릿 치환 조립 (연도·코멘트·표1·그림 36장) |
| `code/matlab/` | 원본 MATLAB 스크립트 (참고용, 파이프라인에서 사용 안 함) |
| `template/template_2025.hwpx` | 보고서 서식 템플릿 (2025년판 변환본) |
| `.claude/skills/generate-eddy-report/` | Claude Code 스킬 (전 과정 자동화 + 코멘트 작성) |
| `web/` | 웹 뷰어 (FastAPI + 정적 HTML) — 날짜·영역별 그림 미리보기/다운로드 |
| `data/` | 다운로드된 nc 원본 (`MSLA`·`OSTIA` × 연도 폴더) |
| `output/` | 그래프 PNG, 통계 JSON, 최종 보고서 (자료별 폴더) |
| `docs/` | 계획서(`PLAN.md`)·작업 메모(`todo.md`)·시스템 관계도(`design/`) |
| `reference/` | 원본 보고서·관측 자료·공모전 서류 (읽기 전용 참고본) |

## 산출물 (output/)

그래프는 `figure/`, 통계 JSON은 `json/`으로 나뉘어 저장됩니다.

- `eddy_tracking/figure/WA_Method_<날짜>.png` — 소용돌이 분포
- `eastsea_current/figure/eastsea_current_<날짜>.png` — 준실시간 해류도
- `eastsea_sst/figure/eastsea_temp_<날짜>.png` — 위성 표층 수온
- `eddy_tracking/json/eddy_stats_<날짜>.json` — 소용돌이 개수: `warm`(동해 난수성), `cold`(동해 냉수성), `ulleung_warm`(울릉 난수성), `dokdo_cold`(독도 냉수성) + 개별 소용돌이 중심/반경
- `eastsea_sst/json/sst_stats_<날짜>.json` — 동해 전역·울릉도독도 해역 수온 min/max/mean, 수온전선 위도 추정
- `intermediate/summary/summary_<연도>.json` — 표 1용 월별 취합
- `intermediate/comments/comments_<연도>.json` — 월별 코멘트 (보고서 본문 삽입용)
- `report/<연도> 동해 소용돌이 분석보고서.hwpx` — 최종 보고서

## 알아두면 좋은 것

- **격자**: DUACS 0.125° 데이터셋을 사용합니다. `eddy_tracking.py`의 동해 경계 마스킹은
  배열 인덱스가 아니라 위경도 식으로 쓰여 있어(`mask_domain()`) 격자 간격이 달라져도
  그대로 성립합니다. 다만 탐지 문턱값(반경·진폭)은 이 격자 기준으로 맞춰져 있습니다.
- **과거 연도**: 요청 날짜가 NRT(준실시간) 범위를 벗어나면 자동으로 MY(재처리) 데이터셋으로
  전환됩니다(동일 격자·변수). 2023·2024 등 과거 보고서도 같은 명령으로 생성됩니다.
- **템플릿 구조**: 그림 36장은 일반 이미지 개체가 아니라 **표 셀 배경 채우기(borderFill)** 로
  삽입되어 있습니다. `build_report.py`가 `header.xml`의 borderFill → 셀 좌표(행=월,
  열=[소용돌이·해류·수온])를 자동 추적하므로 템플릿을 새로 만들면 `--inspect`로 매핑을 확인하세요.
- **소용돌이 개수 재현성**: CMEMS 준실시간 자료는 사후 재처리로 갱신되므로, 과거 날짜를 다시
  돌리면 발간 당시 보고서와 개수가 1~3개 차이날 수 있습니다(정상).
- **냉수성 마스킹 정정 (2026-09-07)**: 원래 코드가 냉수성만 마스킹 전 자료로 탐지해
  동해 밖(일본 동편 태평양·남해) 소용돌이가 섞여 들어왔습니다. 지금은 난수성·냉수성
  모두 마스킹된 자료로 탐지합니다. **난수성·울릉 난수성·독도 냉수성은 그대로**이고
  동해 전체 냉수성만 날짜당 0~3개 줄어듭니다. 발간된 2025년판의 동해 전체 냉수성
  수치와는 달라지며, 구 동작 결과는 `output/eddy_tracking/json_baseline_legacy/` 에
  남겨 두었습니다.
- **파일 용량**: 교체 이미지는 `build_report.py`의 `MAX_IMG_WIDTH`(기본 1400px)로 축소 후
  삽입됩니다. 최종 파일이 무거우면 1000~1200으로 낮추세요.
- **재실행 안전**: 다운로드·그래프 모두 기존 산출물이 있으면 건너뛰므로, 중단됐던 연도를
  같은 명령으로 이어서 실행하면 됩니다.
- **경로 수정**: 폴더 위치를 바꿀 일이 생기면 `code/paths.py` 한 곳만 고치면 됩니다.
  (`fig_dir()`, `json_dir()`, `summary_path()`, `comments_path()`, `report_dir()`, `template_path()`)
  입력 파일은 `find_data()`가 `data/` 이하를 재귀 검색하므로, 자료를 어느 하위 폴더에
  두어도 스크립트가 찾아냅니다.
- **입력 폴더**: 자료 종류(`MSLA`/`OSTIA`) 아래 연도별로 나뉩니다. `download_data.py`가
  연도 폴더를 자동 생성하므로 새 연도를 돌릴 때 따로 만들 필요는 없습니다.
  `eddy_tracking.py`와 `eastsea_current.py`는 같은 MSLA 원본(월 약 37MB)을 공유합니다.
