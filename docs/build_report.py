"""Build the five-page lab report (DOCX) from the measured results.

Run from the repository root:  python docs/build_report.py
Then convert to PDF with Word/LibreOffice and confirm it stays within 5 pages.
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / 'docs' / 'figures'
OUT = ROOT / 'docs' / '实验报告_项目一.docx'

BODY = 10.5
GRAY = RGBColor(0x59, 0x59, 0x59)


# --------------------------------------------------------------------------
# Low-level helpers
# --------------------------------------------------------------------------
def set_run(run, size=BODY, east='宋体', ascii_font='Times New Roman',
            bold=None, color=None, italic=None):
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:ascii'), ascii_font)
    rfonts.set(qn('w:hAnsi'), ascii_font)
    rfonts.set(qn('w:eastAsia'), east)


def shade(element, fill):
    """Apply a solid background to a paragraph or table cell properties."""
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    element.append(shd)


def heading(text, level=1):
    paragraph = document.add_paragraph()
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(8 if level == 1 else 5)
    fmt.space_after = Pt(3)
    fmt.keep_with_next = True
    run = paragraph.add_run(text)
    set_run(run, size=14 if level == 1 else 11.5, east='黑体',
            ascii_font='Times New Roman', bold=True, color=RGBColor(0, 0, 0))
    if level == 1:
        # Thin rule under each top-level heading, like a textbook section.
        ppr = paragraph._p.get_or_add_pPr()
        borders = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '6')
        bottom.set(qn('w:space'), '2')
        bottom.set(qn('w:color'), '8EA9DB')
        borders.append(bottom)
        ppr.append(borders)
    return paragraph


def para(text, indent=True, size=BODY, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         space_before=0, space_after=2):
    paragraph = document.add_paragraph()
    fmt = paragraph.paragraph_format
    fmt.alignment = align
    fmt.line_spacing = 1.18
    fmt.space_before = Pt(space_before)
    fmt.space_after = Pt(space_after)
    if indent:
        fmt.first_line_indent = Pt(size * 2)
    run = paragraph.add_run(text)
    set_run(run, size=size)
    return paragraph


def bullet(text, size=BODY):
    paragraph = document.add_paragraph(style='List Bullet')
    fmt = paragraph.paragraph_format
    fmt.line_spacing = 1.15
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.left_indent = Cm(0.75)
    fmt.first_line_indent = Cm(-0.4)
    run = paragraph.add_run(text)
    set_run(run, size=size)
    return paragraph


def equation(text):
    paragraph = document.add_paragraph()
    fmt = paragraph.paragraph_format
    fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt.space_before = Pt(1)
    fmt.space_after = Pt(1)
    fmt.line_spacing = 1.1
    run = paragraph.add_run(text)
    set_run(run, size=BODY, east='宋体', italic=False)
    return paragraph


def code_block(lines):
    for index, line in enumerate(lines):
        paragraph = document.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.left_indent = Cm(0.5)
        fmt.line_spacing = 1.05
        fmt.space_before = Pt(3 if index == 0 else 0)
        fmt.space_after = Pt(3 if index == len(lines) - 1 else 0)
        fmt.keep_with_next = index < len(lines) - 1
        shade(paragraph._p.get_or_add_pPr(), 'F2F2F2')
        run = paragraph.add_run(line)
        set_run(run, size=9, east='等线', ascii_font='Consolas')


def caption(text, above=False):
    paragraph = document.add_paragraph()
    fmt = paragraph.paragraph_format
    fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt.space_before = Pt(3 if above else 2)
    fmt.space_after = Pt(1 if above else 4)
    fmt.line_spacing = 1.0
    fmt.keep_with_next = above
    run = paragraph.add_run(text)
    set_run(run, size=9, color=GRAY)


def figure(name, width_cm, title):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run().add_picture(str(FIG / name), width=Cm(width_cm))
    caption(title)


def _table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        node = OxmlElement(f'w:{edge}')
        node.set(qn('w:val'), 'single')
        node.set(qn('w:sz'), '4')
        node.set(qn('w:space'), '0')
        node.set(qn('w:color'), 'A6A6A6')
        borders.append(node)
    tbl_pr.append(borders)


def _cell_margins(table, top=25, bottom=25, left=70, right=70):
    tbl_pr = table._tbl.tblPr
    margins = OxmlElement('w:tblCellMar')
    for name, value in (('top', top), ('left', left), ('bottom', bottom), ('right', right)):
        node = OxmlElement(f'w:{name}')
        node.set(qn('w:w'), str(value))
        node.set(qn('w:type'), 'dxa')
        margins.append(node)
    tbl_pr.append(margins)


def _row_flag(row, tag):
    tr_pr = row._tr.get_or_add_trPr()
    node = OxmlElement(tag)
    tr_pr.append(node)


def table(headers, rows, widths, title, size=9, header_fill='DCE6F2'):
    caption(title, above=True)
    grid = document.add_table(rows=1, cols=len(headers))
    grid.alignment = WD_TABLE_ALIGNMENT.CENTER
    grid.autofit = False
    grid.allow_autofit = False
    _table_borders(grid)
    _cell_margins(grid)

    for column, width in zip(grid.columns, widths):
        column.width = Cm(width)
    header = grid.rows[0]
    header.height = Cm(0.55)
    header.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    _row_flag(header, 'w:tblHeader')
    _row_flag(header, 'w:cantSplit')
    header.cells[0]._tc.get_or_add_tcPr()
    for index, (cell, text) in enumerate(zip(header.cells, headers)):
        cell.width = Cm(widths[index])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        shade(cell._tc.get_or_add_tcPr(), header_fill)
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        run = paragraph.add_run(str(text))
        set_run(run, size=size, bold=True)

    for row in rows:
        cells = grid.add_row()
        cells.height = Cm(0.5)
        cells.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        _row_flag(cells, 'w:cantSplit')
        for index, (cell, text) in enumerate(zip(cells.cells, row)):
            cell.width = Cm(widths[index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.alignment = (
                WD_ALIGN_PARAGRAPH.LEFT if index == 0 else WD_ALIGN_PARAGRAPH.CENTER)
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.0
            run = paragraph.add_run(str(text))
            set_run(run, size=size)
    return grid


def add_page_number(paragraph):
    run = paragraph.add_run('第 ')
    set_run(run, size=9, color=GRAY)
    field = paragraph.add_run()
    begin = OxmlElement('w:fldChar')
    begin.set(qn('w:fldCharType'), 'begin')
    instruction = OxmlElement('w:instrText')
    instruction.set(qn('xml:space'), 'preserve')
    instruction.text = ' PAGE '
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')
    field._r.append(begin)
    field._r.append(instruction)
    field._r.append(end)
    set_run(field, size=9, color=GRAY)
    run = paragraph.add_run(' 页')
    set_run(run, size=9, color=GRAY)


# --------------------------------------------------------------------------
# Document setup
# --------------------------------------------------------------------------
document = Document()
section = document.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
section.top_margin = Cm(1.9)
section.bottom_margin = Cm(1.8)
section.left_margin = Cm(2.15)
section.right_margin = Cm(2.15)

normal = document.styles['Normal']
normal.font.name = 'Times New Roman'
normal.font.size = Pt(BODY)
normal.element.get_or_add_rPr()
rfonts = normal.element.rPr.find(qn('w:rFonts'))
if rfonts is None:
    rfonts = OxmlElement('w:rFonts')
    normal.element.rPr.append(rfonts)
rfonts.set(qn('w:eastAsia'), '宋体')
normal.paragraph_format.line_spacing = 1.18
normal.paragraph_format.space_after = Pt(2)

footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_page_number(footer)

# --------------------------------------------------------------------------
# Title block
# --------------------------------------------------------------------------
title = document.add_paragraph()
title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_before = Pt(0)
title.paragraph_format.space_after = Pt(2)
set_run(title.add_run('项目一实验报告'), size=18, east='黑体',
        ascii_font='Times New Roman', bold=True)

subtitle = document.add_paragraph()
subtitle.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
subtitle.paragraph_format.space_after = Pt(4)
set_run(subtitle.add_run('用 NumPy 复现 OpenCLIP ViT-B/32 图像编码器'), size=12.5,
        east='黑体', ascii_font='Times New Roman')

info = document.add_paragraph()
info.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
info.paragraph_format.space_after = Pt(2)
set_run(info.add_run('姓名：__________　学号：__________　班级：__________　日期：2026 年 11 月'),
        size=9.5, color=GRAY)

repo = document.add_paragraph()
repo.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
repo.paragraph_format.space_after = Pt(8)
set_run(repo.add_run('代码仓库：https://github.com/__________/project1-numpy'),
        size=9.5, color=GRAY)

# Abstract-like lead paragraph (kept short to protect the five-page limit).
para('本实验在不用 PyTorch、不用 GPU 的条件下，仅用 NumPy 复现 OpenCLIP ViT-B/32 图像塔的完整前向：'
     '图像分块与线性投影、CLS 与位置编码、12 层多头自注意力与 MLP、CLS 后归一化与 512 维投影。'
     '实现通过课程提供的 8 个分阶段数值检查；token 级最大绝对误差 4.8×10⁻⁵（容差 2×10⁻⁴），'
     '输出 token 最大绝对误差 5.4×10⁻⁷（容差 2×10⁻⁵），十张图像的输出均为单位向量，乱序且含重复图像的批次结果一致。',
     indent=True)

# --------------------------------------------------------------------------
# 1 Task and method
# --------------------------------------------------------------------------
heading('1　任务与方法')
heading('1.1　任务目标', level=2)
para('给定图像张量 x 与课程给定的冻结参数 θ，实现映射 f_θ: [B,3,224,224] → [B,512]，使输出与课程参考在 float32 容差内一致。'
     '过程不训练、不更新参数、不读参考输出；实现须保持最终项目 ImageEncoder 的公开接口'
     '（ImageEncoder(weights)、pre_norm/post_norm、blocks、projection），以便直接替换进 szu_python_openclip 的图像塔。')

heading('1.2　数据、输入与输出', level=2)
para('数据为课程提供的十张 224×224 图像（来源记录见 assets/images.json），按给定流程预处理：短边等比缩放到 224，中心裁剪 224×224，'
     '除以 255 后按 CLIP 均值 [0.481,0.458,0.408] 与标准差 [0.269,0.261,0.276] 逐通道归一化。'
     '参数共 152 个视觉张量、87.85 M 个 float32（原始 351 MB），前向全程只读。各阶段张量形状见表 1。')
table(
    ['阶段', '形状', '含义'],
    [
        ['预处理输入', '[B,3,224,224]', '归一化后的 RGB 图像'],
        ['patch 化', '[B,49,3072]', '7×7 个 32×32 patch，块内按 C,H,W 展平'],
        ['patch 投影', '[B,49,768]', '线性投影（无 bias），每个 patch 一行'],
        ['拼接与位置', '[B,50,768]', '1 个 CLS 行 + 49 个 patch 行，加可学习位置'],
        ['12 层 block', '[B,50,768]', '多头自注意力 + MLP，各带一条残差'],
        ['输出 token', '[B,512]', 'CLS 经 ln_post 与 proj 后单位化'],
    ],
    [2.6, 3.2, 10.4], '表 1　前向数据流与张量形状')

heading('1.3　模块划分与实现流程', level=2)
para('代码按“分块 → 投影 → 堆叠 → 取头”划分，六个 TODO 分散在三个类里（表 2）。实现顺序与 check.py 的阶段一致：'
     '每写完一个 TODO 就运行对应阶段，使第一处不一致总能被定位到刚刚改动的模块。')
table(
    ['模块 / 位置', '关键操作', '形状变化'],
    [
        ['patchify（TODO-01）', 'reshape 分出网格轴与块内轴，transpose 后展平', '[B,3,224,224]→[B,49,3072]'],
        ['embed（TODO-05）', 'patch 乘 W_pᵀ、拼接 CLS、加位置编码', '[B,49,3072]→[B,50,768]'],
        ['MHA（TODO-02/03）', 'QKV 投影、分头、S=QKᵀ/√d_h、softmax、C=AV、并头、输出投影', '[B,50,768]→[B,50,768]'],
        ['Block（TODO-04）', '两条残差：注意力支路与 MLP 支路', '[B,50,768]→[B,50,768]'],
        ['输出头（TODO-06）', '取 CLS → ln_post → proj → 单位化', '[B,50,768]→[B,512]'],
        ['helpers（课程提供）', 'LayerNorm、GELU(erf)、softmax、单位化', '逐元素 / 逐行'],
    ],
    [3.5, 8.6, 4.3], '表 2　模块划分、关键操作与形状变化')

heading('1.4　关键计算', level=2)
para('记一行为一个 token，D=768，H=12，d_h=64。实现严格按下列五式展开，权重统一按 [out,in] 存储，故线性层写成 xWᵀ+b。', indent=True)
equation('(1)　LN(x) = (x − μ)/√(σ² + 1e−5) · γ + β，μ 与 σ² 沿最后一维计算')
equation('(2)　Q,K,V = X W_qkvᵀ + b_qkv；三者各自 reshape 为 [B,H,N,d_h]')
equation('(3)　S = QKᵀ/√d_h，A = softmax(S)，C = AV，O = (C 并头) W_oᵀ + b_o')
equation('(4)　x₁ = x + Attn(LN₁(x))，x₂ = x₁ + W₂·GELU(W₁·LN₂(x₁) + b₁) + b₂')
equation('(5)　z = LN_post(x_CLS)·W_proj，v = z/‖z‖₂')
para('三处容易混淆的约定：patch 投影 visual.conv1.weight 由 [768,3,32,32] reshape 成 [768,3072]，乘其转置且无 bias；'
     '注意力的 k 只交换最后两个轴（transpose(0,1,3,2)），不能动 batch 与 head 轴；visual.proj 已经是 [in,out]=[768,512]，不能再转置。')

# --------------------------------------------------------------------------
# 2 Reproducibility
# --------------------------------------------------------------------------
heading('2　可复现性')
heading('2.1　环境与参数', level=2)
para('全部超参数取自 config.json，没有任何额外调参：patch 32、width 768、heads 12、layers 12、MLP 3072、eps 1e−5、token 50、输出 512。'
     '运行环境见表 3。')
table(
    ['项目', '配置'],
    [
        ['操作系统 / Python', 'Windows 11（64 位）/ Python 3.12.14'],
        ['数值与图像库', 'NumPy 2.3.5、Pillow 12.3.0（requirements.txt 固定版本区间）'],
        ['硬件与框架', 'CPU，无 GPU、无 PyTorch / OpenCLIP / 网络'],
        ['权重与参考', '课程附件 152 个张量；SHA-256 记录在 weights/manifest.json'],
        ['运行耗时', '10 张图整批前向 3.3 s，约 0.33 s/张'],
    ],
    [4.0, 12.2], '表 3　复现环境与运行条件')

heading('2.2　运行步骤', level=2)
para('在仓库根目录依次执行（大文件不入库，先按 weights/README.md 从畅课平台放回权重与参考输出）：')
code_block([
    'python -m pip install -r requirements.txt',
    'python check.py --stage assets      # 用 SHA-256 校验 152 个张量与参考数据',
    'python check.py --stage all         # 8 个阶段全部数值检查',
    'python run.py --output output_tokens.npz',
    'python evidence.py                  # 复现表 4、图 1–3',
])
para('权重 311 MB、参考输出 7.6 MB 不提交到 Git，但它们的哈希写在 manifest 里，check.py --stage assets 会逐个比对张量内容；'
     '因此任何人克隆仓库并放入同一份附件就能复现本文全部数值。仓库保留了按 TODO 分步的真实提交记录。')

# --------------------------------------------------------------------------
# 3 Results
# --------------------------------------------------------------------------
heading('3　结果与证据')
heading('3.1　分阶段数值误差', level=2)
para('表 4 汇总了 7 个数值检查阶段，全部通过；preprocess 与 patches 误差为 0，说明预处理与分块顺序和参考逐位一致。')
table(
    ['阶段', '形状', '最大绝对误差', '平均绝对误差', '容差', '结论'],
    [
        ['preprocess', '10×3×224×224', '0', '0', '2e−6', 'PASS'],
        ['patches', '2×49×3072', '0', '0', '2e−4', 'PASS'],
        ['tokens', '2×50×768', '4.005e−5', '1.289e−6', '2e−4', 'PASS'],
        ['block0', '2×50×768', '7.063e−6', '3.250e−7', '2e−4', 'PASS'],
        ['last_tokens', '2×50×768', '4.768e−5', '2.696e−6', '2e−4', 'PASS'],
        ['output', '10×512', '5.439e−7', '8.313e−8', '2e−5', 'PASS'],
        ['batch', '3×512', '4.619e−7', '7.632e−8', '2e−5', 'PASS'],
    ],
    [2.7, 3.3, 3.1, 3.1, 2.2, 1.9], '表 4　分阶段数值检查结果（float32，10 张图像）')

heading('3.2　误差与容差的整体视图', level=2)
figure('fig2_errors.png', 12.2, '图 2　各阶段最大绝对误差（对数坐标，红色虚线为课程容差）')
para('图 2 中所有柱都在容差线下方，最紧的 tokens 阶段仍有约 5 倍余量；output 阶段误差反而降到 10⁻⁷ 量级。')

heading('3.3　patch 顺序正确性的直接证据', level=2)
figure('fig1_patches.png', 11.8, '图 1　patch 划分顺序（左）与 CLS + 49 patch 组成的 [50,768] token 序列（右）')
para('左图把 224×224 图像切成 7×7 个 32×32 patch，并按“先左右、后上下”编号 0–48；右图是加入 CLS 后的 50 行 token。'
     '若块内展平顺序或 patch 次序写错，patches 阶段不可能得到 0 误差，因此该阶段为 0 同时验证了两个顺序约定。')

heading('3.4　输出性质与判别力', level=2)
figure('fig3_similarity.png', 10.0, '图 3　十张图像输出 token 的余弦相似度矩阵')
para('十张图的输出向量长度与 1 的最大偏差为 1.19×10⁻⁷；batch 阶段用 [1,0,1] 的乱序且重复批次，最大误差 4.6×10⁻⁷，说明结果与批内位置无关、也没有缓存参考行。'
     '图 3 的对角线为 1.00、非对角线在 0.46–0.67，说明输出随图像变化；若实现退化成常量（例如误用整批均值），矩阵会接近全 1。'
     '相似度整体偏高来自课程微调权重的性质，不影响与参考逐值一致。')

# --------------------------------------------------------------------------
# 4 Analysis
# --------------------------------------------------------------------------
heading('4　分析与反思')
heading('4.1　误差从哪里来', level=2)
para('实现与参考使用同一组 float32 参数、同一套公式，剩下的差异只能来自归约与累加顺序：NumPy 的 sgemm 分块方式与 PyTorch 不同，'
     'LayerNorm 的均值、方差归约顺序也不同。单层误差约 10⁻⁶，堆叠 12 层后在 token 上累积到 4.8×10⁻⁵，仍在 2×10⁻⁴ 容差内。'
     '输出端反而只有 5.4×10⁻⁷，原因有二：CLS 行经过 512 维投影是“多对一”加权和，随机相位误差相互抵消；最后一步单位化把向量缩放到长度 1，'
     '绝对误差随分量幅度一起缩小。这解释了“内部误差大于输出误差”这一看似矛盾的现象，也说明容差按阶段设置是合理的。')

heading('4.2　一次真实失败：并头时漏了转置', level=2)
para('最初把 [B,12,50,64] 的 context 直接 reshape 成 [B,50,768]，忘记先 transpose 回 [B,50,12,64]。'
     '结果 block0 的最大绝对误差为 1.91、平均 0.090，数值完全错乱；改为先换轴再 reshape 后，同一阶段降到 7.1×10⁻⁶，相差 5 个数量级。'
     '这个 bug 不报错、只静默改变元素顺序，形状检查也发现不了，只有逐阶段数值比对才能暴露。教训有两点：4D→3D 的合并必须先把 head 轴放回 token 轴之后；'
     '调试要从 check.py 的第一个失败阶段入手，而不是盯着最终输出猜。')

heading('4.3　局限', level=2)
bullet('GELU 用 Python 循环逐元素调用 math.erf，10 张图需 18.4 M 次调用，整批约 3.3 s，其中约 85% 时间花在这里；课程要求 exact erf，故未替换。')
bullet('位置编码固定 50 个 token，只支持 224×224、patch 32 的输入；换分辨率需要位置插值。')
bullet('只覆盖图像塔（文本塔、tokenizer 与完整权重在最终项目附件中）；整批激活一次性驻留内存，B 很大时峰值内存线性增长。')

heading('4.4　改进方向', level=2)
bullet('用多项式或查表 erf（误差 <1×10⁻⁷）向量化 GELU，预计 10 张图可降到 0.5 s 以内。')
bullet('用 im2col 替代 reshape 分块，并支持任意分辨率的位置插值，摆脱 50 token 限制。')


# --------------------------------------------------------------------------
# 5 Contribution
# --------------------------------------------------------------------------
heading('5　本人贡献与协助声明')
bullet('独立完成 image_encoder.py 中 TODO-01～06 的公式推导、实现与调试：patchify、split_heads、scores/加权/并头/输出投影、两条残差与 MLP、patch 投影 + CLS + 位置编码、CLS 输出头，并通过全部 8 个阶段检查。')
bullet('编写 evidence.py（误差表、耗时与三张图）、README.md、weights/README.md 与本报告；课程提供的 helpers.py、preprocess_image.py、runtime.py、run.py、check.py、权重与参考输出未作任何修改。')
bullet('实现与文档在 AI 编程助手辅助下完成（公式核对、代码审查、排版）；本人逐行核对形状与公式并重新运行全部检查，报告中的每个数值都可由 python evidence.py 复现。')

references = document.add_paragraph()
references.paragraph_format.space_before = Pt(5)
references.paragraph_format.space_after = Pt(2)
set_run(references.add_run('参考文献'), size=11.5, east='黑体', bold=True)

for text in (
    '[1] Radford A, Kim J W, Hallacy C, et al. Learning Transferable Visual Models From Natural Language Supervision. ICML, 2021.',
    '[2] Cherti M, Beaumont R, Wightman R, et al. Reproducible Scaling Laws for Contrastive Language-Image Learning. CVPR, 2023.',
    '[3] Dosovitskiy A, Beyer L, Kolesnikov A, et al. An Image is Worth 16×16 Words: Transformers for Image Recognition at Scale. ICLR, 2021.',
):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    set_run(paragraph.add_run(text), size=8, color=GRAY)

document.save(OUT)
print('saved', OUT)
