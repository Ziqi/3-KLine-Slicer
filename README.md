# KLine Slicer (Transformer Data Production)

![KLine Slicer Preview](https://via.placeholder.com/800x500.png?text=KLine+Slicer+-+Geek+Dark+Theme)

---

## 🇨🇳 中文说明 (Chinese)

**KLine Slicer** 是 KLine-Kronos-Suite 中的第三个核心组件，专门负责将 5 分钟的 K 线 CSV 文件转换为深度学习模型（如 **Kronos**）可以直接消化的张量数据。它不仅是一个切片工具，更是一个数据“质检员”。

## Acknowledgements
Designed for integration with time-series forecasting foundation models like **Kronos** ([@shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos)).

### ✨ 核心功能
- **[ 数据健康体检 (Health Check) ]**：自动检测原始 5m CSV 中的空值（NaN）、零成交量、以及异常时间缺口，确保进入模型的数据 100% 纯净。
- **[ 专家对齐切片 (Expert Slicing) ]**：自动加载 `X-Matrix` 项目中的 `scaler_*.pkl` 归一化密钥，确保数据预处理逻辑与模型训练时完全一致（90日回望 + 10日预测）。
- **[ 板块全家桶并行 (Group Slicing) ]**：支持一次性勾选整个板块的股票，将它们合并并打散成一个统一的 `.npy` 训练集，极大提升模型对于板块共性的学习能力。

### 🚀 快速开始
1. **源路径挂载**：将挂载点指向程序 2 生成的 `gui_out_5m` 文件夹。
2. **专家选择**：根据你要投喂的“大脑”选择对应的专家编号（如 `expert_02_ai`）。
3. **点火生产**：点击“开始切片生产”，生成的 `.npy` 数据包将存放于 `gui_out_slices` 目录下，可直接复制到服务器进行训练。

### 📊 数据接口规范 (Data IO Specs)
- **注入流 (Input)**:
  - 数据实体: `2-KLine-Resample` 提取的 `5m.csv` 时序合集。
  - 模型预设: `X-Matrix` 模型框架依赖的独家 `scaler_*.pkl` 均值方差归一化密钥文件。
- **输出张量 (Output)**: 完全符合高维模型特征张量接口规则的 `.npy` Numpy 三维数组。
  - **数组命名规范**: `slices_[expert_id]_[生成时间戳].npy`
  - **张量维度 (Shape)**: `(样本条目数 N, 回望窗口 Lookback + 预测视野 Predict, 特征通道数 Features)`
- **工程设计哲学 (Why Tensor Slice?)**: 摒弃传统项目一边在 DataLoader 训练、一边动态切片的 CPU 密集型灾难开销。通过 Slicer 直接将数千份物理 `.csv` 并发组装成紧凑的内存块连续 Numpy 矩阵，使得核心 Transformer 网络训练流能够达到最大吞吐满载。

---

## 🇺🇸 English Documentation

**KLine Slicer** is the third core component of the KLine-Matrix-Suite. It is specialized in converting 5-minute K-Line CSV files into tensor data payloads that Deep Learning models (like **Kronos**) can directly consume.

### ✨ Core Features
- **[ Data Health Check ]**: Automatically detects NaNs, zero-volume bars, and timestamp gaps in the raw 5m CSVs, ensuring 100% data integrity for training.
- **[ Expert-Aligned Slicing ]**: Automatically loads the corresponding `scaler_*.pkl` from the `X-Matrix` project, ensuring that the normalization logic stays 100% consistent with the model's training specs (90-day lookback + 10-day prediction).
- **[ Group/Batch Production ]**: Select multiple stocks from the same sector to merge them into a single `.npy` training dataset, enhancing the model's ability to learn sector-wide temporal patterns.

---
`Author: Ziqi` | `License: MIT` | `Design Language: Cyber-Gold`
