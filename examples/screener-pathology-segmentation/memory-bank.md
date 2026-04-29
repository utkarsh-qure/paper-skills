# Paper Memory Bank
Last updated: 2026-04-29

### [goncharov2026screener] Screener: Self-supervised Pathology Segmentation in Medical CT Images
- **Authors**: Mikhail Goncharov, Eugenia Soboleva, Mariia Donskova, Daniil Ignatyev, Mikhail Belyaev, Ivan Oseledets, Marina Munkhoeva, Maxim Panov
- **Venue**: ICLR 2026 Poster (v2, Sep 2025; v1 Feb 2025)
- **URL**: https://arxiv.org/abs/2502.08321
- **OpenReview**: https://openreview.net/forum?id=fNyfV5otuV
- **GitHub**: https://github.com/mishgon/screener
- **Citations**: (new)
- **Status**: analyzed
- **Tier**: 0 (focal paper)
- **Topics**: unsupervised visual anomaly segmentation, dense self-supervised learning, conditional density estimation, medical CT, pretraining
- **Abstract**: Frames pathology detection as UVAS over 3D CT volumes; replaces ImageNet/STU-Net descriptors with dense-SSL UNet features and replaces sin-cos/APE conditions with masking-invariant dense embeddings. SOTA on 4 large CT datasets unsupervised; +49% Dice over nnUNet at fine-tuning.
- **Notes**: Main paper. Two key innovations: (1) dense SSL descriptor (DenseInfoNCE / DenseVICReg) + (2) masking-invariant condition. The masking-invariance is what enables Gaussian density to match normalizing flow (Tab. 3). CLAHE preprocessing is load-bearing (App. F). Supervised STU-Net features actively HARMFUL (Tab. 4). Reconstruction-based methods get worse with training (App. H). Code: condition_model.py concatenates the binary mask as an extra input channel, so the masking-invariance is engineered (not just emergent). DenseVICReg uses i_weight=v_weight=25, c_weight=1, and an 8192-D MLP projector with GroupNorm + SiLU.
---

### [cflow] CFLow-AD
- **Authors**: Denis Gudovskiy, Shun Ishizaka, Kazuki Kozuka
- **Venue**: WACV 2022
- **URL**: https://arxiv.org/abs/2107.12571
- **Citations**: ~700
- **Status**: discovered
- **Tier**: 1
- **Topics**: density-based UVAS, conditional normalizing flows
- **Abstract**: Real-time UVAS via conditional normalizing flows on ImageNet feature maps; conditioned on sin-cos positional encodings.
- **Notes**: The framework Screener inherits and improves. Sets the convention of conditional density modeling for pixel-level UVAS.
---

### [msflow] MSFlow
- **Authors**: Yixuan Zhou, Xing Xu, Jingkuan Song, Fumin Shen, Heng Tao Shen
- **Venue**: TNNLS 2024
- **URL**: https://arxiv.org/abs/2308.15300
- **Citations**: ~150
- **Status**: discovered
- **Tier**: 1
- **Topics**: density-based UVAS, multi-scale flows
- **Notes**: Multi-scale flow-based UVAS, top-5 on MVTec-AD. Tab. 1 baseline (AUROC 0.71/0.67/0.63/0.63 on CT — fails because of ImageNet features).
---

### [voco] VoCo
- **Authors**: Linshan Wu, Jiaxin Zhuang, Hao Chen
- **Venue**: CVPR 2024
- **URL**: https://arxiv.org/abs/2402.17300
- **Citations**: ~120
- **Status**: discovered
- **Tier**: 1
- **Topics**: 3D medical SSL, contrastive learning
- **Notes**: Strongest competitor at fine-tuning time (Tab. 2). Volume contrast — predicts which sub-volume a region belongs to.
---

### [densecl] DenseCL
- **Authors**: Xinlong Wang, Rufeng Zhang, Chunhua Shen, Tao Kong, Lei Li
- **Venue**: CVPR 2021
- **URL**: https://arxiv.org/abs/2011.09157
- **Citations**: ~700
- **Status**: discovered
- **Tier**: 1
- **Topics**: dense contrastive SSL
- **Notes**: Original dense contrastive SSL — pixel-level positive pairs. Foundational for Screener's descriptor model.
---

### [vicregl] VICRegL
- **Authors**: Adrien Bardes, Jean Ponce, Yann LeCun
- **Venue**: NeurIPS 2022
- **URL**: https://arxiv.org/abs/2210.01571
- **Citations**: ~500
- **Status**: discovered
- **Tier**: 1
- **Topics**: dense SSL, VICReg local
- **Notes**: Local VICReg formulation that DenseVICReg in Screener adapts to 3D voxel pairs.
---

### [vader] VADER (Pinheiro et al. 2020)
- **Authors**: Pedro O. Pinheiro, Amjad Almahairi, Ryan Benmalek, Florian Golemo, Aaron C. Courville
- **Venue**: NeurIPS 2020
- **URL**: https://arxiv.org/abs/2011.05499
- **Status**: discovered
- **Tier**: 1
- **Topics**: dense SSL
- **Notes**: Original unsupervised learning of dense visual representations; cited as foundational dense SSL alongside DenseCL.
---

### [pdm] Patched Diffusion Model
- **Authors**: Finn Behrendt, Debayan Bhattacharya, Julia Krüger, Roland Opfer, Alexander Schlaefer
- **Venue**: MIDL 2024
- **URL**: https://arxiv.org/abs/2303.03758
- **Status**: discovered
- **Tier**: 1
- **Topics**: medical UVAS, diffusion models
- **Notes**: Strongest reconstruction-based medical UVAS baseline. App. H of Screener shows it overfits to anomalies after ~7 epochs (Fig. 8).
---

### [moodtop1] MOOD-Top1
- **Authors**: Sergio Naval Marimont, Giacomo Tarroni
- **Venue**: arXiv, 2023
- **URL**: https://arxiv.org/abs/2308.01412
- **Status**: discovered
- **Tier**: 1
- **Topics**: medical UVAS, synthetic anomalies
- **Notes**: Top-1 of MOOD challenge. Synthetics-based; Tab. 1 baseline at 0.79/0.79/0.77/0.80 AUROC.
---

### [draem] DRAEM
- **Authors**: Vitjan Zavrtanik, Matej Kristan, Danijel Skočaj
- **Venue**: ICCV 2021
- **URL**: https://arxiv.org/abs/2108.07610
- **Status**: discovered
- **Tier**: 1
- **Topics**: synthetics-based UVAS
- **Notes**: Synthesizes anomalies and trains a discriminative network to segment them. Tab. 1 baseline.
---

### [vox2vec] vox2vec
- **Authors**: Mikhail Goncharov, Vera Soboleva, Anvar Kurmukov, Maxim Pisov, Mikhail Belyaev
- **Venue**: MICCAI 2023
- **URL**: https://arxiv.org/abs/2305.15087
- **Status**: discovered
- **Tier**: 1
- **Topics**: 3D voxel SSL, medical
- **Notes**: Same authors' prior work — voxel-level contrastive framework. Predecessor to Screener's descriptor model.
---

### [ape] APE (Anatomical Positional Embeddings)
- **Authors**: Mikhail Goncharov, Valentin Samokhin, Eugenia Soboleva, Roman Sokolov, Boris Shirokikh, Mikhail Belyaev, Anvar Kurmukov, Ivan Oseledets
- **Venue**: arXiv, 2024
- **URL**: https://arxiv.org/abs/2409.10291
- **Status**: discovered
- **Tier**: 1
- **Topics**: anatomical embeddings, retrieval
- **Notes**: Same authors' prior work. Originally for retrieval. Used as a baseline condition in Screener's Tab. 3 — beaten by the new masking-invariant approach.
---

### [pinaya2022] Anomaly Diffusion (Pinaya et al. 2022)
- **Authors**: Walter HL Pinaya, Mark S Graham, Robert Gray, et al.
- **Venue**: MICCAI 2022
- **URL**: https://arxiv.org/abs/2206.03461
- **Status**: discovered
- **Tier**: 1
- **Topics**: medical UVAS, diffusion models
- **Notes**: Diffusion-based brain MRI anomaly detection (Pinaya 2022a). Cited but not in main tables.
---

### [vicreg] VICReg
- **Authors**: Adrien Bardes, Jean Ponce, Yann LeCun
- **Venue**: ICLR 2022 (v1: 2021)
- **URL**: https://arxiv.org/abs/2105.04906
- **Citations**: ~1500
- **Status**: discovered
- **Tier**: 2
- **Topics**: SSL, non-contrastive
- **Notes**: Variance-invariance-covariance regularization. Underlies DenseVICReg.
---

### [simclr_screener] SimCLR
- **Authors**: Ting Chen, Simon Kornblith, Mohammad Norouzi, Geoffrey Hinton
- **Venue**: ICML 2020
- **URL**: https://arxiv.org/abs/2002.05709
- **Status**: discovered
- **Tier**: 2
- **Topics**: contrastive SSL
- **Notes**: Underlies DenseInfoNCE objective.
---

### [stunet] STU-Net
- **Authors**: Ziyan Huang, Haoyu Wang, Zhongying Deng, Jin Ye, Yanzhou Su, Hui Sun, Junjun He, Yun Gu, Lixu Gu, Shaoting Zhang, et al.
- **Venue**: arXiv, 2023
- **URL**: https://arxiv.org/abs/2304.06716
- **Status**: discovered
- **Tier**: 2
- **Topics**: supervised medical pretraining
- **Notes**: Supervised pretrained on anatomical structures. Tab. 4 shows it gets WORSE AUROC (0.52 LIDC) than ImageNet ResNet50 (0.70) — a striking failure mode.
---

### [nnunet] nnUNet
- **Authors**: Fabian Isensee, Paul F Jaeger, Simon AA Kohl, Jens Petersen, Klaus H Maier-Hein
- **Venue**: Nature Methods 2021
- **URL**: https://arxiv.org/abs/1809.10486
- **Citations**: ~7000
- **Status**: discovered
- **Tier**: 2
- **Topics**: supervised medical segmentation
- **Notes**: The supervised baseline in Tab. 2 (random init: 0.21/0.61/0.41/0.45 Dice).
---

### [modelgenesis] Model Genesis
- **Authors**: Zongwei Zhou, Vatsal Sodha, Jiaxuan Pang, Michael B Gotway, Jianming Liang
- **Venue**: Medical Image Analysis 2021
- **URL**: https://arxiv.org/abs/2004.07882
- **Status**: discovered
- **Tier**: 2
- **Topics**: 3D medical SSL
- **Notes**: Foundational 3D medical SSL via reconstruction-based pretext tasks. Tab. 2 baseline (mostly underperforms nnUNet from scratch).
---

### [swinunetr] SwinUNETR
- **Authors**: Yucheng Tang, Dong Yang, Wenqi Li, Holger R Roth, Bennett Landman, Daguang Xu, Vishwesh Nath, Ali Hatamizadeh
- **Venue**: CVPR 2022
- **URL**: https://arxiv.org/abs/2111.14791
- **Status**: discovered
- **Tier**: 2
- **Topics**: 3D medical SSL, Swin transformer
- **Notes**: Swin-transformer 3D medical SSL with masked-image and contrastive losses. Tab. 2 baseline (drops 24-53% from random init).
---

### [dae] DAE (Disruptive Autoencoders)
- **Authors**: Jeya Maria Jose Valanarasu, Yucheng Tang, Dong Yang, Ziyue Xu, Can Zhao, Wenqi Li, Vishal M Patel, Bennett Landman, Daguang Xu, Yufan He, et al.
- **Venue**: arXiv, 2023
- **URL**: https://arxiv.org/abs/2307.16896
- **Status**: discovered
- **Tier**: 2
- **Topics**: 3D medical SSL, masked image modeling
- **Notes**: Local masking + low-level perturbations + reconstruction. Tab. 2 baseline (drops 13-38% from random init).
---

### [fanogan] f-AnoGAN
- **Authors**: Thomas Schlegl, Philipp Seeböck, Sebastian M Waldstein, Georg Langs, Ursula Schmidt-Erfurth
- **Venue**: Medical Image Analysis 2019
- **URL**: https://arxiv.org/abs/1807.02011
- **Status**: discovered
- **Tier**: 2
- **Topics**: medical UVAS, GAN
- **Notes**: Foundational GAN-based medical UVAS. Tab. 1 baseline.
---

### [autoencoder_uvas] Autoencoder UVAS (Baur et al. 2021)
- **Authors**: Christoph Baur, Stefan Denner, Benedikt Wiestler, Nassir Navab, Shadi Albarqouni
- **Venue**: Medical Image Analysis 2021
- **URL**: https://www.sciencedirect.com/science/article/pii/S1361841520303145
- **Status**: discovered
- **Tier**: 2
- **Topics**: medical UVAS, autoencoders
- **Notes**: Comparative study of autoencoders for brain MR UVAS. Tab. 1 baseline.
---

### [patchcore] PatchCore
- **Authors**: Karsten Roth, Latha Pemula, Joaquin Zepeda, Bernhard Schölkopf, Thomas Brox, Peter Gehler
- **Venue**: CVPR 2022
- **URL**: https://arxiv.org/abs/2106.08265
- **Status**: discovered
- **Tier**: 2
- **Topics**: density-based UVAS, memory bank
- **Notes**: Non-parametric memory-bank-based UVAS. Cited in §5 as alternative density approach.
---

### [fastflow] FastFlow
- **Authors**: Jiawei Yu, Ye Zheng, Xiang Wang, Wei Li, Yushuang Wu, Rui Zhao, Liwei Wu
- **Venue**: arXiv, 2021
- **URL**: https://arxiv.org/abs/2111.07677
- **Status**: discovered
- **Tier**: 2
- **Topics**: density-based UVAS, normalizing flows
- **Notes**: 2D normalizing flows for UVAS. Predecessor to MSFlow.
---

### [glow] Glow
- **Authors**: Diederik P Kingma, Prafulla Dhariwal
- **Venue**: NeurIPS 2018
- **URL**: https://arxiv.org/abs/1807.03039
- **Status**: discovered
- **Tier**: 2
- **Topics**: normalizing flows
- **Notes**: Glow architecture (act-norm, invertible 1×1 conv, affine coupling) used by Screener's normalizing-flow density model (App. D).
---

### [lidc] LIDC-IDRI Dataset
- **Authors**: Samuel G Armato III et al.
- **Venue**: Medical Physics 2011
- **URL**: https://www.thecancerimagingarchive.net/collection/lidc-idri/
- **Status**: discovered
- **Tier**: 3
- **Topics**: lung CT, dataset
- **Notes**: Lung Image Database Consortium; 1017 CT scans with lung nodule annotations. Eval dataset.
---

### [kits] KiTS19
- **Authors**: Nicholas Heller et al.
- **Venue**: arXiv, 2019
- **URL**: https://arxiv.org/abs/1904.00445
- **Status**: discovered
- **Tier**: 3
- **Topics**: kidney CT, dataset
- **Notes**: 300 kidney tumor CT cases. Eval dataset.
---

### [lits] LiTS
- **Authors**: Patrick Bilic et al.
- **Venue**: Medical Image Analysis 2023
- **URL**: https://arxiv.org/abs/1901.04056
- **Status**: discovered
- **Tier**: 3
- **Topics**: liver CT, dataset
- **Notes**: Liver Tumor Segmentation Benchmark. Eval dataset.
---

### [midrc] MIDRC-RICORD
- **Authors**: Emily Tsai et al.
- **Venue**: TCIA 2020
- **URL**: https://www.cancerimagingarchive.net/collection/midrc-ricord-1a/
- **Status**: discovered
- **Tier**: 3
- **Topics**: COVID-19 chest CT, dataset
- **Notes**: 115 COVID+ chest CT scans. Eval dataset.
---

### [nlst] NLST
- **Authors**: National Lung Screening Trial Research Team
- **Venue**: Radiology 2011
- **URL**: https://pubmed.ncbi.nlm.nih.gov/21045183/
- **Status**: discovered
- **Tier**: 3
- **Topics**: lung CT screening, dataset
- **Notes**: 25,652 lung-cancer-screening CT volumes. Largest training source.
---

### [amos] AMOS
- **Authors**: Yuanfeng Ji et al.
- **Venue**: NeurIPS 2022
- **URL**: https://arxiv.org/abs/2206.08023
- **Status**: discovered
- **Tier**: 3
- **Topics**: abdominal multi-organ, dataset
- **Notes**: 2,123 abdominal CT scans. Training set.
---

### [abdomenatlas] AbdomenAtlas-8K
- **Authors**: Chongyu Qu, Tiezheng Zhang, Hualin Qiao, Yucheng Tang, Alan L Yuille, Zongwei Zhou, et al.
- **Venue**: NeurIPS 2024
- **URL**: https://arxiv.org/abs/2407.16697
- **Status**: discovered
- **Tier**: 3
- **Topics**: abdominal CT, dataset
- **Notes**: 8,000 CT volumes annotated for multi-organ segmentation. Training set (4,607 volumes used).
---

### [mvtec] MVTec-AD
- **Authors**: Paul Bergmann, Kilian Batzner, Michael Fauser, David Sattlegger, Carsten Steger
- **Venue**: IJCV 2021
- **URL**: https://www.mvtec.com/company/research/datasets/mvtec-ad
- **Status**: discovered
- **Tier**: 3
- **Topics**: industrial anomaly detection benchmark
- **Notes**: Standard natural-image UVAS benchmark. Cited in §2.1 / §5 as the benchmark MSFlow / FastFlow / PatchCore were optimized for.
---

### [mood] MOOD challenge
- **Authors**: David Zimmerer, Jens Petersen, Gregor Köhler, et al.
- **Venue**: MICCAI 2022
- **URL**: https://www.synapse.org/#!Synapse:syn21343101
- **Status**: discovered
- **Tier**: 3
- **Topics**: medical OoD challenge
- **Notes**: Medical out-of-distribution analysis challenge; MOOD-Top1 was developed for this.
---

### [adamw] AdamW
- **Authors**: Ilya Loshchilov, Frank Hutter
- **Venue**: ICLR 2019
- **URL**: https://arxiv.org/abs/1711.05101
- **Status**: discovered
- **Tier**: 3
- **Topics**: optimization
- **Notes**: Optimizer used for all Screener training stages.
---

### [clahe] CLAHE
- **Authors**: Stephen M Pizer et al.
- **Venue**: CVGIP 1987
- **URL**: https://www.sciencedirect.com/science/article/abs/pii/S0734189X8780186X
- **Status**: discovered
- **Tier**: 3
- **Topics**: image preprocessing
- **Notes**: Contrast-limited adaptive histogram equalization. App. F flags it as load-bearing — color jitter would erase pathology signal without it.
---
