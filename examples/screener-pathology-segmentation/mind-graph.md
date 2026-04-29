# Mind Graph
Last updated: 2026-04-29

### Density-Based Unsupervised Visual Anomaly Segmentation (UVAS)
- **Description**: Methods that learn the marginal or conditional density of feature embeddings under the assumption that anomalies fall in low-density regions. The framework Screener inhabits and improves.
- **Related topics**: [Dense Self-Supervised Learning], [Medical UVAS], [Normalizing Flows]
- **Key papers**:
  - [goncharov2026screener] Screener (focal) — replaces ImageNet descriptors + sin-cos conditions with dense-SSL features + masking-invariant conditions
  - [cflow] CFLow-AD (WACV 2022) — direct predecessor; conditional normalizing flow with sin-cos conditioning
  - [msflow] MSFlow (TNNLS 2024) — multi-scale flow-based UVAS, top of MVTec-AD
- **Other relevant papers**:
  - [fastflow] FastFlow (2021) — earlier 2D normalizing-flow UVAS
  - [patchcore] PatchCore (CVPR 2022) — non-parametric memory-bank density approach
  - [glow] Glow (NeurIPS 2018) — the normalizing-flow architecture used for $q(y|c)$

---

### Dense Self-Supervised Learning (Voxel/Pixel-Level)
- **Description**: SSL objectives that produce embeddings at every pixel/voxel, with positive pairs defined as the same spatial location across augmented crops.
- **Related topics**: [Density-Based UVAS], [3D Medical SSL]
- **Key papers**:
  - [densecl] DenseCL (CVPR 2021) — original dense contrastive
  - [vader] VADER / Pinheiro 2020 (NeurIPS 2020) — original unsupervised dense visual representations
  - [vicregl] VICRegL (NeurIPS 2022) — local VICReg formulation
  - [goncharov2026screener] Screener — adapts these to 3D medical CT (DenseInfoNCE / DenseVICReg) + adds masking augmentation for the condition model
- **Other relevant papers**:
  - [vox2vec] vox2vec (MICCAI 2023) — same authors' 3D voxel SSL
  - [vicreg] VICReg (ICLR 2022) — global formulation that DenseVICReg localizes
  - [simclr_screener] SimCLR (ICML 2020) — contrastive SSL underlying DenseInfoNCE

---

### Medical UVAS (Reconstruction / Synthetics / Density)
- **Description**: Unsupervised pathology detection in 3D medical imaging. Three competing paradigms.
- **Related topics**: [Density-Based UVAS], [3D Medical SSL]
- **Key papers**:
  - [goncharov2026screener] Screener — first density-based medical UVAS method to dominate all three paradigms
  - [pdm] Patched Diffusion Model (MIDL 2024) — strongest reconstruction-based baseline; overfits at >7 epochs (App. H)
  - [moodtop1] MOOD-Top1 (2023) — top synthetics-based method
  - [fanogan] f-AnoGAN (MIA 2019) — foundational GAN-based medical UVAS
- **Other relevant papers**:
  - [autoencoder_uvas] Baur 2021 — comparative autoencoder UVAS
  - [draem] DRAEM (ICCV 2021) — synthetics-based, originally for industrial
  - [pinaya2022] Pinaya 2022 — diffusion-based brain MRI UVAS

---

### 3D Medical Self-Supervised Pretraining
- **Description**: Methods that pretrain encoders on unlabeled 3D medical data, used as initialization for downstream supervised fine-tuning. Screener's distilled model competes here.
- **Related topics**: [Dense SSL], [Medical UVAS]
- **Key papers**:
  - [voco] VoCo (CVPR 2024) — strongest competitor in Tab. 2; volume contrast
  - [goncharov2026screener] Screener (distilled) — UVAS-derived pretraining, +49% Dice on LIDC fine-tuning
  - [modelgenesis] Model Genesis (MIA 2021) — reconstruction-based pretext tasks
  - [swinunetr] SwinUNETR (CVPR 2022) — Swin transformer + masked image modeling
  - [dae] DAE (2023) — disruptive autoencoders
- **Other relevant papers**:
  - [vox2vec] vox2vec (MICCAI 2023) — voxel-level contrastive
  - [stunet] STU-Net (2023) — supervised pretraining baseline (fails at UVAS!)

---

### Conditioning for Density-Based Anomaly Detection
- **Description**: How to inject contextual information into the conditional density $q(y|c)$ so anomalies are defined relative to context, not in absolute embedding space.
- **Related topics**: [Density-Based UVAS]
- **Key papers**:
  - [goncharov2026screener] Screener — proposes <em>masking-invariant</em> learned conditions; simplifies $q(y|c)$ enough that a Gaussian matches a normalizing flow
  - [ape] APE (2024) — same authors' anatomical positional embeddings; baseline condition (Tab. 3, AUROC 0.88/0.80/0.78/0.86 with Gaussian)
- **Other relevant papers**:
  - [cflow] CFLow-AD — sin-cos positional encodings as conditions

---

### Datasets (Training & Evaluation)
- **Description**: Large-scale CT corpora used in Screener.
- **Training (unlabeled, no class info needed)**:
  - [nlst] NLST — 25,652 lung-screening CTs
  - [amos] AMOS — 2,123 abdominal CTs
  - [abdomenatlas] AbdomenAtlas-8K — 4,607 abdominal CTs (subset)
- **Evaluation (labeled, single-pathology each)**:
  - [lidc] LIDC-IDRI — 1,017 lung-cancer scans
  - [midrc] MIDRC-RICORD-1a — 115 pneumonia scans
  - [kits] KiTS — 298 kidney-tumor scans
  - [lits] LiTS — 117 liver-tumor scans
- **Reference benchmarks**:
  - [mvtec] MVTec-AD — natural-image UVAS, where MSFlow / PatchCore / FastFlow won
  - [mood] MOOD — medical OoD challenge

---

### Foundations & Tools
- **Description**: Building blocks the method depends on.
- **Architectures**:
  - [nnunet] nnUNet — supervised baseline + UNet design language
  - [glow] Glow — normalizing-flow blocks (act-norm, invertible 1×1 conv, affine coupling)
- **Optimization & preprocessing**:
  - [adamw] AdamW (ICLR 2019) — optimizer
  - [clahe] CLAHE (CVGIP 1987) — load-bearing preprocessing step (App. F)

---
