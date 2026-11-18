# 项目一：用 NumPy 复现 OpenCLIP ViT-B/32 图像编码器

本项目在**纯 NumPy**（无 PyTorch、无 GPU、无网络）环境下实现 OpenCLIP
ViT-B/32 的图像塔前向计算：输入一批预处理后的图像，输出每条图像对应的
512 维单位向量。模型参数全部由课程提供且保持冻结，本仓库只做前向推导，
不涉及训练。

全部 8 个检查阶段通过（`python check.py --stage all`），与独立 FP32 参考的
最大绝对误差如下（容差 2e-4 / 2e-5）：

| stage | shape | max abs error | atol | 结果 |
| --- | --- | --- | --- | --- |
| preprocess | 10×3×224×224 | 0 | 2e-6 | PASS |
| patches | 2×49×3072 | 0 | 2e-4 | PASS |
| tokens | 2×50×768 | 4.005e-05 | 2e-4 | PASS |
| block0 | 2×50×768 | 7.063e-06 | 2e-4 | PASS |
| last_tokens | 2×50×768 | 4.768e-05 | 2e-4 | PASS |
| output | 10×512 | 5.439e-07 | 2e-5 | PASS |
| batch | 3×512 | 4.619e-07 | 2e-5 | PASS |

十张图像输出向量的长度与 1 的最大偏差为 `1.19e-07`；打乱顺序并重复一张图
组成的新批次与逐张推理结果一致（`batch` 阶段）。

## 1. 代码结构与职责

| 文件 | 职责 |
| --- | --- |
| `image_encoder.py` | **本人实现**：`MultiHeadAttention`、`TransformerBlock`、`ImageEncoder`，六个 TODO 全部在此完成 |
| `helpers.py` | 课程提供：LayerNorm、GELU(erf)、softmax、单位化，不改动 |
| `preprocess_image.py` | 课程提供：短边双三次缩放、中心裁剪、CLIP 均值方差归一化 |
| `runtime.py` | 课程提供：按脚本所在目录加载权重与图像，路径与当前工作目录无关 |
| `run.py` | 课程提供：命令行入口，`--images` 指定图片，`--output` 保存 `.npz` |
| `check.py` | 课程提供：8 个分阶段数值检查，逐级定位第一处不一致 |
| `evidence.py` | 本人新增：复现报告中的误差表、耗时与三张图（`docs/figures/`） |
| `transformer_steps.py` | 课程提供：3 token / 4 特征的单头教学小例子 |
| `config.json`、`weights/manifest.json` | 课程提供：结构与 152 个张量的指纹 |
| `assets/` | 十张图像、`images.json` 来源信息、参考输出（不入库） |
| `weights/` | 视觉权重（不入库，获取方法见 `weights/README.md`） |
| `docs/` | 实验报告（DOCX/PDF）、三张结果图、`results.csv`、报告构建脚本 |
| `practice/`、`lecture-demos/` | 课程练习 PDF 与课堂示例，原样保留 |

数据流（以 B 张图为例）：

```
[B,3,224,224] --patchify--> [B,49,3072] --W_p^T--> [B,49,768]
      --拼接 CLS、加位置编码--> [B,50,768] --ln_pre--> 12 × TransformerBlock
      --取 CLS、ln_post、proj--> [B,512] --单位化--> [B,512]
```

## 2. 环境与依赖

- Python ≥ 3.9（实测 3.12 / 3.13）
- NumPy（实测 2.3.5）、Pillow（实测 12.3.0）
- `imageio` 只有课堂示例 `lecture-demos/02_imageio_images.py` 需要

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` 只列出三个直接依赖，版本上界按课程附件给出：
`numpy>=1.24,<3`、`Pillow>=9.2,<13`、`imageio>=2.31,<3`。

## 3. 数据与权重的获取

`weights/image_encoder.npz`（326 MB）与 `assets/reference_outputs.npz`
（7.6 MB）体积大且属于课程评测数据，**没有提交到仓库**：

1. 从畅课平台下载项目一附件并解压；
2. 把 `weights/image_encoder.npz`、`assets/reference_outputs.npz` 放回对应目录；
3. 运行 `python check.py --stage assets`，用 manifest 中的 SHA-256 校验。

细节见 [`weights/README.md`](weights/README.md)。

## 4. 运行步骤

以下命令都在仓库根目录执行：

```bash
# 1) 校验资源（152 个张量 + 10 组图像/参考）
python check.py --stage assets

# 2) 按实现顺序分阶段检查，先看最前面的失败项
python check.py --stage preprocess
python check.py --stage patches
python check.py --stage tokens
python check.py --stage block0
python check.py --stage last_tokens
python check.py --stage output
python check.py --stage batch

# 3) 一次跑完全部阶段
python check.py --stage all

# 4) 对十张图生成输出 token
python run.py --output output_tokens.npz

# 5) 对自己的图片生成输出 token（按输入顺序保存 id）
python run.py --images path/to/a.jpg path/to/b.png --output my_tokens.npz

# 6) 复现报告图表与指标
python evidence.py
```

预期输出（节选）：

```
assets       PASS: 152 matching visual tensors and ten image/reference pairs
preprocess   PASS shape=(10, 3, 224, 224) max_abs=0.000e+00 ...
patches      PASS shape=(2, 49, 3072) max_abs=0.000e+00 ...
tokens       PASS shape=(2, 50, 768) max_abs=4.005e-05 ...
block0       PASS shape=(2, 50, 768) max_abs=7.063e-06 ...
last_tokens  PASS shape=(2, 50, 768) max_abs=4.768e-05 ...
output       PASS shape=(10, 512) max_abs=5.439e-07 ...
batch        PASS shape=(3, 512) max_abs=4.619e-07 ...
Requested numerical checks passed. The reference file is never an encoder input.
```

## 5. 实现说明（六个 TODO）

| 编号 | 位置 | 做法 |
| --- | --- | --- |
| TODO-01 | `patchify` | `[B,3,224,224]` → `[B,3,7,32,7,32]` → 转置为 `[B,7,7,3,32,32]` → `reshape(B,49,3072)`；先左右后上下，块内按 C,H,W 展平 |
| TODO-02 | `split_heads` | `reshape(B,N,H,64)` 后 `transpose(0,2,1,3)`，得到 `[B,12,N,64]`，token 顺序不变 |
| TODO-03 | `MultiHeadAttention.__call__` | `S = QKᵀ/√64`（只交换 k 的最后两轴）→ 已提供的 softmax → `C = AV` → 先转回 `[B,N,768]` 再乘 `W_oᵀ+b_o` |
| TODO-04 | `TransformerBlock.__call__` | `x1 = x + Attn(LN1(x))`；`u = LN2(x1)`；`x2 = x1 + GELU(uW1ᵀ+b1)W2ᵀ+b2` |
| TODO-05 | `embed` | `patches @ W_pᵀ`（无 bias）→ 与 CLS 在第 1 轴拼接 → `+ positional_embedding`（按 B 广播） |
| TODO-06 | `__call__` | 取 `tokens[:,0]` → `ln_post`（补一个长度 1 的 token 轴）→ `@ proj`（`[768,512]` 已是 `[in,out]`）→ `unit_vector` |

三条与仓库默认直觉不同的约定：

1. 注意力/MLP 的线性权重存成 `[out,in]`，所以统一写 `x @ W.T + b`；
2. patch 投影 `visual.conv1.weight` 存成 `[768,3,32,32]`，初始化时已经
   `reshape(768,3072)`，计算时同样乘转置，且**没有 bias**；
3. `visual.proj` 是 `[768,512]`，已经是 `[in,out]`，**不要转置**。

## 6. 数值结果与图表

`docs/results.csv` 是 `evidence.py` 生成的完整误差表；三张图在
`docs/figures/`：

- `fig1_patches.png`：7×7 patch 编号与 `[50,768]` token 序列；
- `fig2_errors.png`：各阶段最大绝对误差与容差线（对数坐标）；
- `fig3_similarity.png`：十张图输出向量的余弦相似度矩阵（0.46–0.67）。

耗时（CPU，10 张图，实测）：预处理 0.03 s，patch 投影 0.02 s，12 个
Transformer block 约 3.2–3.5 s，整批前向约 3.3 s（约 0.33 s/张）。主要
开销是 `helpers.GELU` 的逐元素 `math.erf` 循环（每批 18.4 M 次调用）。

## 7. 已知限制

- 位置编码固定 50 个 token，因此只接受 224×224、patch 32 的输入；
- 仅包含图像塔，不含最终项目的文本塔；
- GELU 用 Python 循环实现（课程要求“exact”），未做向量化加速；
- 参考输出只用于比对，编码器本身从不读取 `reference_outputs.npz`。

## 8. 提交与版本记录

仓库保留了分步提交记录：先导入课程起始代码，再按实现顺序（patchify →
patch 投影与 CLS → 多头注意力 → 残差块 → 输出头）逐个提交，最后补充
README、`evidence.py`、图表与报告。完整命令：

```bash
git log --oneline --stat
```

推送到 GitHub（公开仓库，或把助教/老师加为 collaborator）：

```bash
git remote add origin https://github.com/<your-name>/<repo>.git
git branch -M main
git push -u origin main
```

## 9. 学术诚信

课程提供了 `helpers.py`、`preprocess_image.py`、`runtime.py`、`run.py`、
`check.py`、权重与参考输出；本人完成 `image_encoder.py` 的六个 TODO、
`evidence.py`、本 README 与实验报告。实现与调试过程中使用了 AI 编程助手
进行公式核对、代码审查与文字整理，所有数值均由本仓库脚本重新跑出。
报告第 5 节对此有更详细的说明。
