# 权重与参考数据说明

本目录中的 `image_encoder.npz`（约 326 MB）**不纳入 Git 版本库**，
`assets/reference_outputs.npz`（约 7.6 MB）同样不纳入，原因有两点：

1. 体积过大，不适合放进代码仓库；
2. 它们是课程提供的评测基准数据，应由课程平台统一分发。

## 获取方法

1. 登录畅课平台，下载项目一的原始附件（`project1-学生版.zip`）；
2. 解压后，把 `weights/image_encoder.npz`、`weights/manifest.json` 与
   `assets/reference_outputs.npz`、`assets/manifest.json` 放回本仓库的对应目录；
3. 运行 `python check.py --stage assets` 校验文件完整性。

`check.py --stage assets` 会做三件事：

- 用 `weights/manifest.json` 中的 SHA-256 校验权重文件；
- 逐个校验 152 个视觉张量的名称、形状、dtype 与内容哈希；
- 校验十张图像的哈希和参考输出的哈希。

校验通过时会输出：

```
assets       PASS: 152 matching visual tensors and ten image/reference pairs
```

只要文件不是课程发布的那一份，这一步就会失败，因此不需要把大文件提交到
GitHub 也能证明复现用的是同一套参数。
