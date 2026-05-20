# Screener: Self-supervised Pathology Segmentation in Medical CT Images

## Metadata
- **Title**: Screener: Self-supervised Pathology Segmentation in Medical CT Images
- **Authors**: Mikhail Goncharov*, Eugenia Soboleva*, Mariia Donskova, Daniil Ignatyev, Mikhail Belyaev, Ivan Oseledets, Marina Munkhoeva, Maxim Panov (*equal contribution)
- **arXiv ID**: 2502.08321 (v2)
- **Categories**: cs.CV
- **Date**: 2025-09-18 (v2); originally 2025-02-12
- **Venue**: ICLR 2026
- **GitHub**: https://github.com/mishgon/screener
- **Project page**: https://openreview.net/forum?id=fNyfV5otuV (OpenReview)

## Section anchors
- `§1 — UVAS framing: pathology = statistical anomaly; rarity assumption motivates density-based UVAS`
- `§2.1 — density-based UVAS background (descriptor + density model + conditioning)`
- `§2.2 — dense joint embedding SSL background (DenseInfoNCE, DenseVICReg)`
- `§3.1 — descriptor model: 3D UNet trained via dense SSL at full resolution`
- `§3.2 — masking-invariant condition model (key innovation)`
- `§3.3 — density model q_θ(y|c) as Gaussian or Glow flow; anomaly score = −log q`
- `§3.4 — distill the modular pipeline into a single UNet for fine-tuning`
- `§4.1 — unsupervised UVAS results (Table 1)`
- `§4.2 — fine-tuning results (Table 2)`
- `§4.3 — condition × density ablation (Table 3)`
- `§6 — limitations (rarity assumption, CT-only validation, scaling laws open)`
- `App. A — Dice underestimation: true positives counted as false positives`
- `App. B — DenseInfoNCE and DenseVICReg objectives`
- `App. D — Gaussian and Glow density model architectures`
- `App. F — CLAHE preprocessing is load-bearing; condition model gets mask as input channel`
- `App. G — domain-shift robustness study (low-dose, contrast)`
- `App. H — why reconstruction-based UVAS fails: overfits to anomalies after a few epochs`

## Named components & terminology
- `descriptor model f_{θ^desc}` — 3D UNet, full-resolution feature maps
- `descriptor y[p] ∈ R^d` — per-voxel embedding from the descriptor model (d=32 in DenseVICReg)
- `condition model g_{θ^cond}` — 3D UNet with identical architecture/training as descriptor + random masking augmentation
- `condition c[p] ∈ R^{d_cond}` — per-voxel context embedding (masking-invariant)
- `density model q_{θ^dens}(y | c)` — Gaussian (μ(c), Σ(c)) or Glow normalizing flow
- `anomaly score score(p) = −log q_{θ^dens}(y[p] | c[p])` — per-voxel prediction error
- `distilled UNet h_φ` — regression UNet trained to predict score maps via MSE; used as SSL pretraining for fine-tuning

## Loss function (verbatim)
The training objective for the density model is conditional negative log-likelihood:

$$\min_{\theta^{\text{dens}}} \; \frac{1}{m \cdot |P|} \sum_{i=1}^{m} \sum_{p \in P} -\log q_{\theta^{\text{dens}}}\bigl(\mathbf{y}_i[p] \,\big|\, \mathbf{c}_i[p]\bigr)$$

where $(\mathbf{y}_i, \mathbf{c}_i)$ are descriptor/condition feature maps for the $i$-th crop in a batch of $m$, $P$ is the spatial grid, and $\text{sg}[\cdot]$ is implicit on $\mathbf{y}$, $\mathbf{c}$ (the descriptor and condition models are frozen during density training).

At inference, the anomaly score at position $p$ is:

$$\text{score}(p) \;=\; -\log q_{\theta^{\text{dens}}}\bigl(\mathbf{y}[p] \,\big|\, \mathbf{c}[p]\bigr)$$

## Key equations (additional)
- **DenseInfoNCE objective** (App. B, used for descriptor pretraining):
  $$\min_{\theta} \; \sum_{i=1}^{N} \sum_{k \in \{1,2\}} -\log \frac{\exp\!\bigl(\langle z_i^{(1)}, z_i^{(2)} \rangle / \tau\bigr)}{\exp\!\bigl(\langle z_i^{(1)}, z_i^{(2)} \rangle / \tau\bigr) + \sum_{j \ne i}\sum_{l \in \{1,2\}} \exp\!\bigl(\langle z_i^{(k)}, z_j^{(l)} \rangle / \tau\bigr)}$$
  where $z_i^{(k)}$ is the descriptor at the $i$-th positive position from view $k$.

- **Distillation loss** (§3.4):
  $$\mathcal{L}_{\text{distill}} \;=\; \mathbb{E}_{x} \,\Bigl\|\, h_\phi(x) \;-\; \bigl(-\log q_{\theta^{\text{dens}}}\bigl(f_{\theta^{\text{desc}}}(x) \,\big|\, g_{\theta^{\text{cond}}}(x)\bigr)\bigr) \,\Bigr\|_2^2$$

## Benchmarks (headline)
- **LIDC unsup AUROC**: 0.96 (Screener) vs 0.87 next-best (Patched Diffusion). Table 1.
- **MIDRC unsup AUROC**: 0.87 (Screener) vs 0.79 (MOOD-Top1). Table 1.
- **KiTS unsup AUROC**: 0.90 (Screener) vs 0.82 (DRAEM). Table 1.
- **LiTS unsup AUROC**: 0.93 (Screener) vs 0.83 (DRAEM). Table 1.
- **LIDC fine-tune Dice (25 cases, 3-fold CV)**: 0.31 (Screener) vs 0.21 (nnUNet random-init), +49% (p<0.01). Table 2.
- **Scale**: 30,000+ unlabeled CT volumes for training (NLST + AMOS + AbdomenAtlas, App. E). 1,820 evaluation scans across LIDC + MIDRC + KiTS + LiTS.
- **Compute**: 3 days each on a single H100 for descriptor, condition, and density. 5–10 sec/volume inference (App. F).

## Ablations (with table attribution)
- **Remove dense SSL features → use ImageNet ResNet50** as descriptor: AUROC drops to **0.70 / 0.66 / 0.64 / 0.64** (LIDC / MIDRC / KiTS / LiTS). Table 4.
- **Remove dense SSL → use STU-Net (supervised medical pretrain)**: AUROC drops to **0.52 / 0.44 / 0.52 / 0.64** — worse than ImageNet. Supervised features become organ-shape detectors, losing pathology discrimination. Table 4.
- **Remove masking-invariant condition → use sin-cos PE** with diagonal Gaussian density: AUROC drops to **0.88 / 0.80 / 0.78 / 0.86**. Table 3.
- **With masking-invariant condition + diagonal Gaussian** density: AUROC = **0.96 / 0.84 / 0.87 / 0.90** — competitive with Glow normalizing flow (0.96 / 0.87 / 0.90 / 0.93) using a much simpler density model. Table 3.

## Nuances
- **Dice scores are systematically under-estimated, not the model's fault.** Test datasets only label the headline pathology per dataset (lung cancer / pneumonia / kidney tumor / liver tumor), but Screener detects *everything* statistically rare. App. A explicitly demonstrates a pneumothorax that Screener correctly detects being counted as a false positive against the incomplete mask. The honest metric is voxel-level AUROC sampled over labeled-pathology voxels and out-of-mask normal voxels — that's why the paper headlines AUROC. (§4.1, App. A)
- **Supervised medical pretraining is *actively harmful* for this task.** STU-Net (supervised on anatomical-structure segmentation) gets AUROC 0.52 / 0.44 / 0.52 / 0.64 — *below* ImageNet ResNet50 (0.70 / 0.66 / 0.64 / 0.64) on the same density-based pipeline (Table 4). The supervised features collapse to organ shapes, losing the discriminative pathology signal that dense-SSL features preserve.
- **The masking-invariance trick is a model-simplicity win, not just an accuracy win.** Table 3: with a fixed DenseVICReg descriptor, sin-cos / APE conditioning *requires* a Glow normalizing flow to hit AUROC 0.96 / 0.89 / 0.90 / 0.94. With masking-invariant conditions, a diagonal Gaussian density gets to 0.96 / 0.84 / 0.87 / 0.90 — competitive with the NF, with one MLP for $\mu(c)$ and $\Sigma(c)$ instead of an invertible network with act-norms, 1×1 convs, and affine couplings. (Table 3, App. D)
- **CLAHE preprocessing is load-bearing, and the condition model's auxiliary input is the mask itself.** App. F: without CLAHE, "*the quality of our method degrades largely*" because color jitter erases the pathology signal. The condition model concatenates the binary mask as a second input channel (`in_channels + 1` in `condition_model.py`), telling the network exactly what's been hidden — the masking-invariance is engineered, not just emergent.

## Lede + prereqs material

### Lede (1–2 paragraphs)
Screener reframes pathology detection in 3D CT: instead of training supervised models on the few annotated classes (which only ever find what someone labeled), treat every pathology as a statistical anomaly relative to healthy tissue. The work sits in the **density-based unsupervised visual anomaly segmentation (UVAS)** framework, where one model learns voxel-level features ("descriptors") and a second learns their density; voxels in low-density regions are flagged as anomalous. Prior work used ImageNet-pretrained CNNs as descriptors — these fail on CT due to domain shift, and *supervised* medical encoders fail even worse, because their features collapse to organ shapes.

Screener's two contributions are: (1) replace the generic descriptor with a 3D UNet trained from scratch via dense self-supervised learning (DenseInfoNCE / DenseVICReg) at full resolution on 30,000+ unlabeled CT volumes, and (2) replace hand-crafted conditioning variables (sin-cos positional encodings) with **learned masking-invariant conditions** — features that capture global anatomy and patient context but stay ignorant of local pathology by construction. The masking trick simplifies the conditional density enough that a diagonal Gaussian matches a Glow normalizing flow. Final touch: distill the modular three-model pipeline into a single regression UNet, which doubles as state-of-the-art self-supervised pretraining for downstream fine-tuning (+49% Dice gain over nnUNet on LIDC with 25 cases).

### Prerequisites (4)
- **Unsupervised visual anomaly segmentation (UVAS)** — a framework for detecting anomalous regions in images without per-pixel labels by modeling the distribution of "normal" patterns. Four families: synthetic-based, reconstruction-based, density-based (Screener's family), and student-teacher.
- **Dense self-supervised learning** — pretraining objectives that produce per-pixel/per-voxel embeddings rather than a global image vector. Positive pairs are formed at the pixel level: same anatomical position, different augmentations. DenseCL (Wang 2021) and VICRegL (Bardes 2022) are the closest references.
- **Conditional density estimation in UVAS** — modeling $q(y | c)$ rather than $q(y)$ directly. Conditioning on positional/anatomical context lets the model account for "expected" appearance per region (e.g., a calcification is normal in lung but abnormal in breast). The challenge is that the condition must not leak the pathology signal it's trying to detect.
- **Normalizing flows (Glow)** — invertible neural networks that learn exact density via change-of-variables (act-norm + invertible 1×1 conv + affine coupling). Used here as the baseline density model that masking-invariance lets a simple diagonal Gaussian replace.
