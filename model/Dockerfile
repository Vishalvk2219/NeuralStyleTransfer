# Model work for M0: exports MicroAST to ONNX, serves a browser test page, runs quality comparisons.
#   docker build -t nst-bench model
#   docker run --rm -p 8000:8000 nst-bench                                   then open http://localhost:8000
#   docker run --rm --gpus all -v "<repo>:/work" nst-bench python /work/model/compare.py <run-name>
FROM python:3.12-slim

# About 2.5 GB of downloads. The cache mount and resume flag let a dropped connection continue.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -U pip \
 && pip install --retries 10 --resume-retries 10 torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121 \
 && pip install --retries 10 onnx onnxruntime pillow
# Pinned to the CUDA 12.1 build: this laptop's NVIDIA driver (536.52, July 2023) supports CUDA 12.2 at most.
# Newer builds report the GPU as available and then fail with "device busy or unavailable".
# After a driver update, drop the pins and the index URL to get the current PyTorch.

# VGG19 is the loss network for the optimisation method in compare.py.
RUN python -c "import torchvision.models as m; m.vgg19(weights=m.VGG19_Weights.IMAGENET1K_V1)"

# Pinned third-party inputs: MicroAST code and weights (MIT), ONNX Runtime Web.
ADD https://github.com/EndyWon/MicroAST.git#5a6c9050d8c408191cb9db12c697f3e4c7ebe137 /opt/MicroAST

# Candidate models for compare.py. Their weights are large and live in model/weights/ (see CLAUDE.md).
RUN pip install --no-cache-dir einops
ADD https://github.com/Chernobyllight/SaMam.git#b0911ac655c208e8bcedff8d5a5c4e335c0f6577 /opt/SaMam
# NNST (MIT) matches features of VGG16.
RUN pip install --no-cache-dir imageio \
 && python -c "import torchvision.models as m; m.vgg16(weights=m.VGG16_Weights.IMAGENET1K_V1)"
ADD https://github.com/nkolkin13/NeuralNeighborStyleTransfer.git#290976abad7f7a2465900b0567584a3e9a682a4a /opt/NNST
# DeepLabV3 finds animals for regions.py (the MediaPipe parts model only knows people).
RUN python -c "from torchvision.models.segmentation import *; deeplabv3_mobilenet_v3_large(weights=DeepLabV3_MobileNet_V3_Large_Weights.COCO_WITH_VOC_LABELS_V1)"
# SaMam's compiled GPU kernel. Without it SaMam falls back to a pure-PyTorch scan that takes 10 to 50 s
# per image and overflows a 6 GB GPU; with it, 0.44 s and 0.3 GB. The wheel must match Python, PyTorch
# and CUDA: this one is cp312, torch 2.5, cu12.
RUN pip install --no-cache-dir "https://github.com/state-spaces/mamba/releases/download/v2.3.0/mamba_ssm-2.3.0+cu12torch2.5cxx11abiFALSE-cp312-cp312-linux_x86_64.whl"
ADD https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-1.30.0.tgz /tmp/ort.tgz

WORKDIR /site
RUN tar -xzf /tmp/ort.tgz -C /tmp \
 && mkdir ort \
 && cp /tmp/package/dist/ort.webgpu.min.mjs /tmp/package/dist/ort-wasm-simd-threaded*.mjs /tmp/package/dist/ort-wasm-simd-threaded*.wasm ort/ \
 && rm -rf /tmp/ort.tgz /tmp/package

COPY export_onnx.py /app/
RUN python /app/export_onnx.py

COPY serve.py /app/
COPY bench.html index.html

EXPOSE 8000
CMD ["python", "/app/serve.py"]
