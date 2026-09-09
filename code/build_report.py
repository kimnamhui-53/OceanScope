# -*- coding: utf-8 -*-
"""
HWPX 템플릿 기반 보고서 조립

사용법:
    python build_report.py <연도>                 # 보고서 생성
    python build_report.py <연도> --inspect       # 템플릿 구조 확인(문단/표/이미지 순서 덤프)

입력:
    template/template_2025.hwpx   : 2025 보고서를 한글에서 .hwpx로 저장한 템플릿 (1회 준비)
    output/intermediate/summary/summary_<연도>.json   : run_pipeline.py 산출 (표 1 데이터)
    output/intermediate/comments/comments_<연도>.json : 월별 코멘트 {"1": "…", …, "12": "…"}
    output/eddy_tracking/figure/WA_Method_YYYYMM15.png
    output/eastsea_current/figure/eastsea_current_YYYYMM15.png
    output/eastsea_sst/figure/eastsea_temp_YYYYMM15.png        (합계 36장)

출력:
    output/report/<연도> 동해 소용돌이 분석보고서.hwpx

작업 내용:
  1. 표지/분석날짜 표의 2025 연도 문자열 → <연도> 치환
  2. 월별 코멘트 문단 "(N월) …" 교체
  3. 표 1(소용돌이 개수) 12행 × 4열 숫자 교체
  4. 그림 36장: BinData 바이너리를 새 PNG로 교체 (문서 등장 순서 기준 매핑)

HWPX는 ZIP(+XML)이므로 zipfile + 정규식/문자열 치환으로 처리한다(서식 XML은 건드리지 않음).
"""
import os
import io
import re
import sys
import json
import zipfile
import shutil

import paths

BASE = paths.BASE
TEMPLATE = paths.template_path()
TEMPLATE_YEAR = '2025'

# 이미지 임베드 시 최대 픽셀 폭 (dpi=800 원본은 너무 커서 파일이 비대해짐)
MAX_IMG_WIDTH = 1400

# 분기 그림표 안에서 이미지의 등장 순서 가정: 월(행) × [소용돌이, 해류, 수온](열)
# --inspect 결과가 다르면 이 순서만 수정하면 된다.
IMG_TYPES = ['WA_Method', 'eastsea_current', 'eastsea_temp']

T_RE = re.compile(r'<hp:t>([^<]*)</hp:t>')
# 그림 36장은 표 셀 배경(borderFill)의 <hc:img binaryItemIDRef="imageN"/> 로 들어가 있다.
BORDERFILL_RE = re.compile(r'<hh:borderFill id="(\d+)".*?</hh:borderFill>', re.S)
HC_IMG_RE = re.compile(r'binaryItemIDRef="(image\d+)"')


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def write_zip(path, items):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        # mimetype은 무압축 저장이 관례
        if 'mimetype' in items:
            z.writestr('mimetype', items['mimetype'], zipfile.ZIP_STORED)
        for n, b in items.items():
            if n != 'mimetype':
                z.writestr(n, b)


def section_names(items):
    return sorted(n for n in items if re.match(r'Contents/section\d+\.xml', n))


def para_texts(xml):
    """<hp:p> 단위로 (문단전체매치, 이어붙인 텍스트) 목록."""
    out = []
    for m in re.finditer(r'<hp:p [^>]*>.*?</hp:p>', xml, re.S):
        text = ''.join(T_RE.findall(m.group(0)))
        out.append((m, text))
    return out


# ──────────────────────────── inspect ────────────────────────────

def inspect(items):
    print('=== 파일 목록 ===')
    for n in sorted(items):
        if n.startswith('BinData/'):
            print(f'  {n}  ({len(items[n])} bytes)')
    for sec in section_names(items):
        xml = items[sec].decode('utf-8')
        print(f'\n=== {sec}: 문단 텍스트 ===')
        for i, (m, text) in enumerate(para_texts(xml)):
            t = text.strip()
            if t:
                print(f'  [{i}] {t[:80]}')
    mapping = image_cell_map(items)
    print(f'\n=== 그림 셀 매핑 ({len(mapping)}개, 월×열[0=소용돌이,1=해류,2=수온]) ===')
    for (mth, col) in sorted(mapping):
        print(f'  {mth:2d}월 col{col} -> {mapping[(mth, col)]}')


# ──────────────────────── 텍스트/코멘트 치환 ─────────────────────

def replace_years(xml, year):
    """2025.MM.15. / 2025. 12. 등 연도 문자열을 대상 연도로 치환 (hp:t 내부만)."""
    def fix(m):
        t = m.group(1)
        t = t.replace(f'{TEMPLATE_YEAR}.', f'{year}.')
        return f'<hp:t>{t}</hp:t>'
    return T_RE.sub(fix, xml)


def replace_comment(xml, month, new_text):
    """'(N월)'로 시작하는 코멘트 문단을 찾아 텍스트 전체를 교체.

    marker 앞의 원문 접두사('   - ' 등)는 보존하고, 문단 안의 첫 <hp:t>에
    접두사+새 텍스트를 넣은 뒤 나머지 <hp:t>는 비운다(서식 유지).
    같은 (N월) 문단이 다른 곳에 없다는 전제(2025 본문 기준 각 1회).
    new_text는 '(N월) ...'로 시작해야 한다.
    """
    marker = f'({month}월)'
    replaced = [0]

    def para_sub(m):
        para = m.group(0)
        text = ''.join(T_RE.findall(para))
        pos = text.find(marker)
        # 코멘트 문단은 "- (N월) ..." 형태 — 문단 앞부분에 marker가 있어야 함
        if replaced[0] or pos < 0 or pos > 12:
            return para
        replaced[0] += 1
        prefix = text[:pos]
        first = [True]

        def t_sub(tm):
            if first[0]:
                first[0] = False
                return f'<hp:t>{escape(prefix + new_text)}</hp:t>'
            return '<hp:t></hp:t>'
        return T_RE.sub(t_sub, para)

    new_xml = re.sub(r'<hp:p [^>]*>.*?</hp:p>', para_sub, xml, flags=re.S)
    return new_xml, replaced[0]


def escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ─────────────────────────── 표 1 치환 ───────────────────────────

def replace_table1(xml, summary):
    """표 1: 행 머리가 'N월'인 표 행의 숫자 4개를 새 값으로 교체."""
    months_data = summary['months']
    count = [0]

    def tr_sub(m):
        tr = m.group(0)
        cells = re.findall(r'<hp:tc.*?</hp:tc>', tr, re.S)
        if not cells:
            return tr
        head = ''.join(T_RE.findall(cells[0])).strip()
        mm = re.fullmatch(r'(\d{1,2})월', head)
        if not mm:
            return tr
        mkey = str(int(mm.group(1)))
        if mkey not in months_data or 'eddy' not in months_data[mkey]:
            return tr
        e = months_data[mkey]['eddy']
        vals = [e['warm'], e['cold'], e['ulleung_warm'], e['dokdo_cold']]
        new_tr = tr
        for cell, val in zip(cells[1:5], vals):
            done = [False]

            def t_sub(tm):
                if done[0]:
                    return '<hp:t></hp:t>'
                done[0] = True
                return f'<hp:t>{val}</hp:t>'
            new_cell = T_RE.sub(t_sub, cell)
            new_tr = new_tr.replace(cell, new_cell, 1)
        count[0] += 1
        return new_tr

    new_xml = re.sub(r'<hp:tr>.*?</hp:tr>', tr_sub, xml, flags=re.S)
    return new_xml, count[0]


# ─────────────────────────── 이미지 교체 ─────────────────────────

def shrink_png(png_bytes, max_width=MAX_IMG_WIDTH):
    from PIL import Image
    img = Image.open(io.BytesIO(png_bytes))
    if img.width > max_width:
        h = round(img.height * max_width / img.width)
        img = img.resize((max_width, h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def binname_for_ref(items, ref):
    """binaryItemIDRef → BinData/ 실제 파일명 (content.hpf manifest에서 탐색)."""
    hpf = items.get('Contents/content.hpf', b'').decode('utf-8', errors='ignore')
    m = re.search(rf'id="{re.escape(ref)}"[^>]*href="([^"]+)"', hpf)
    if m:
        return m.group(1)
    # manifest에 없으면 관례적 이름 시도
    for n in items:
        if n.startswith('BinData/') and ref in n:
            return n
    return None


def image_cell_map(items):
    """분기 그림표의 (월, 열) → binaryItemIDRef 매핑 산출.

    - header.xml: borderFill id → imageN (이미지 배경 채우기가 있는 것만)
    - section*.xml: 그림표(이미지 borderFill을 참조하는 셀 9개짜리 표)를 문서
      순서대로 찾음 → 표 순서 = 1~4분기, rowAddr = 분기 내 월(0~2), colAddr = 유형
    반환: {(month, col): image_ref}
    """
    hdr = items['Contents/header.xml'].decode('utf-8')
    fill_to_img = {}
    for m in BORDERFILL_RE.finditer(hdr):
        img = HC_IMG_RE.search(m.group(0))
        if img:
            fill_to_img[m.group(1)] = img.group(1)

    mapping = {}
    quarter = 0
    for sec in section_names(items):
        xml = items[sec].decode('utf-8')
        for tm in re.finditer(r'<hp:tbl .*?</hp:tbl>', xml, re.S):
            cells = []
            for cm in re.finditer(
                    r'<hp:tc [^>]*borderFillIDRef="(\d+)"[^>]*>.*?'
                    r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"', tm.group(0), re.S):
                bf, col, row = cm.group(1), int(cm.group(2)), int(cm.group(3))
                if bf in fill_to_img:
                    cells.append((row, col, fill_to_img[bf]))
            if len(cells) == 9:  # 분기 그림표 (3개월 × 3유형)
                quarter += 1
                for row, col, img in cells:
                    month = (quarter - 1) * 3 + row + 1
                    mapping[(month, col)] = img
    return mapping


def replace_images(items, year):
    """분기 그림표 36장의 BinData 바이너리를 새 PNG로 교체."""
    mapping = image_cell_map(items)
    # (산출 폴더 종류, 파일명 형식) — IMG_TYPES 와 같은 순서
    col_files = [
        ('eddy_tracking',   'WA_Method_{d}.png'),
        ('eastsea_current', 'eastsea_current_{d}.png'),
        ('eastsea_sst',     'eastsea_temp_{d}.png'),
    ]

    swapped, missing = 0, []
    for mth in range(1, 13):
        d = f'{year}{mth:02d}15'
        for col, (kind, tpl) in enumerate(col_files):
            png_name = tpl.format(d=d)
            ref = mapping.get((mth, col))
            if ref is None:
                missing.append(f'{png_name} (셀 매핑 없음)')
                continue
            src = os.path.join(paths.fig_dir(kind), png_name)
            if not os.path.exists(src):
                missing.append(png_name)
                continue
            binname = binname_for_ref(items, ref)
            if not binname or binname not in items:
                missing.append(f'{png_name} (BinData 미확인: {ref})')
                continue
            with open(src, 'rb') as f:
                items[binname] = shrink_png(f.read())
            swapped += 1
    return swapped, missing


# ─────────────────────────────── main ───────────────────────────────

def build(year):
    if not os.path.exists(TEMPLATE):
        sys.exit(f'템플릿이 없습니다: {TEMPLATE}\n'
                 '한글(정품)에서 2025 보고서를 [다른 이름으로 저장 → HWPX]로 변환해 배치하세요.')
    items = read_zip(TEMPLATE)

    summary_p = paths.summary_path(year)
    comments_p = paths.comments_path(year)
    summary = json.load(open(summary_p, encoding='utf-8')) if os.path.exists(summary_p) else None
    comments = json.load(open(comments_p, encoding='utf-8')) if os.path.exists(comments_p) else {}

    report = {'year_swap': 0, 'comments': [], 'table_rows': 0, 'images': 0, 'img_missing': []}

    for sec in section_names(items):
        xml = items[sec].decode('utf-8')
        before = xml
        xml = replace_years(xml, str(year))
        if xml != before:
            report['year_swap'] += 1
        for mth in range(1, 13):
            if str(mth) in comments:
                xml, n = replace_comment(xml, mth, comments[str(mth)])
                if n:
                    report['comments'].append(mth)
        if summary:
            xml, rows = replace_table1(xml, summary)
            report['table_rows'] += rows
        items[sec] = xml.encode('utf-8')

    swapped, missing = replace_images(items, year)
    report['images'] = swapped
    report['img_missing'] = missing

    out_path = os.path.join(paths.report_dir(), f'{year} 동해 소용돌이 분석보고서.hwpx')
    write_zip(out_path, items)

    print(f'생성 완료: {out_path}')
    print(f'  연도 치환된 섹션 수 : {report["year_swap"]}')
    print(f'  코멘트 교체 월      : {sorted(set(report["comments"]))}')
    print(f'  표 1 교체 행 수     : {report["table_rows"]}')
    print(f'  이미지 교체         : {report["images"]}/36')
    if missing:
        print(f'  누락 이미지         : {missing}')
    return out_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    year = int(sys.argv[1])
    if '--inspect' in sys.argv:
        inspect(read_zip(TEMPLATE))
    else:
        build(year)
