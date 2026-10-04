"""Export MicroAST to one ONNX graph: (content, style, alpha) -> stylized image in [0, 1].

Runs while the Docker image builds. The build fails if ONNX and PyTorch disagree.
"""
import json
import os
import sys
import time

sys.path.insert(0, "/opt/MicroAST")

import numpy as np
import onnx
import onnxruntime as ort
import torch
from PIL import Image

import net_microAST as net

SRC = "/opt/MicroAST"
RAW = "/tmp/raw.onnx"
OUT = "/site/microast.onnx"


def adain(content, style, eps=1e-5):
    """Same maths as MicroAST's function.py, without the view/expand calls that export
    as chains of shape operations. Those run on the CPU in the browser and stall the GPU."""
    def stats(x):
        return x.mean((2, 3), keepdim=True), (x.var((2, 3), keepdim=True) + eps).sqrt()
    (cm, cs), (sm, ss) = stats(content), stats(style)
    return (content - cm) / cs * ss + sm


class MicroAST(torch.nn.Module):
    def __init__(self, parts):
        super().__init__()
        self.content_encoder, self.style_encoder, self.modulator, self.decoder = parts

    def forward(self, content, style, alpha):
        s = self.style_encoder(style)
        w, b = self.modulator(s)
        out = self.decoder(self.content_encoder(content), s, w, b, 1.0).clamp(0, 1)
        # MicroAST's own alpha only works at 0 and 1: the released weights blow up in between
        # (output range reaches 11 at alpha 0.5). Strength is a blend with the photo instead.
        return alpha * out + (1 - alpha) * content


def load(path, long_side):
    img = Image.open(path).convert("RGB")
    k = long_side / max(img.size)
    # The network halves the size twice, so both sides must be multiples of 4.
    img = img.resize([round(d * k / 4) * 4 for d in img.size])
    return img, np.asarray(img, np.float32).transpose(2, 0, 1)[None] / 255


def run(sess, content, style, alpha=1.0):
    return sess.run(None, {"content": content, "style": style, "alpha": np.array(alpha, np.float32)})[0]


parts = [net.Encoder(), net.Encoder(), net.Modulator(), net.Decoder()]
for name, part in zip(("content_encoder", "style_encoder", "modulator", "decoder"), parts):
    part.load_state_dict(torch.load(f"{SRC}/models/{name}_iter_160000.pth.tar", map_location="cpu"))
    part.eval()

# Reference output from the authors' own inference class, before anything is changed.
content_img, content = load(f"{SRC}/inputs/content/1.jpg", 1024)
style_img, style = load(f"{SRC}/inputs/style/1.jpg", 512)
check_c, check_s = torch.rand(1, 3, 320, 416), torch.rand(1, 3, 256, 200)
with torch.no_grad():
    reference = net.TestNet(*parts)(check_c, check_s, 1.0).clamp(0, 1).numpy()

net.featMod = adain
torch.onnx.export(
    MicroAST(parts),
    (torch.rand(1, 3, 256, 256), torch.rand(1, 3, 192, 224), torch.tensor(1.0)),
    RAW,
    input_names=["content", "style", "alpha"],
    output_names=["output"],
    dynamic_axes={"content": {2: "h", 3: "w"}, "style": {2: "sh", 3: "sw"}, "output": {2: "h", 3: "w"}},
    opset_version=17,
    dynamo=False,
)

# Fold the constant shape arithmetic the exporter emits around every reflection pad.
fold = ort.SessionOptions()
fold.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
fold.optimized_model_filepath = OUT
sess = ort.InferenceSession(RAW, fold)

# Check: sizes other than the ones traced, at full and partial strength.
max_diff = 0.0
for alpha in (1.0, 0.3):
    want = alpha * reference + (1 - alpha) * check_c.numpy()
    got = run(sess, check_c.numpy(), check_s.numpy(), alpha)
    assert got.shape == want.shape, (got.shape, want.shape)
    max_diff = max(max_diff, float(np.abs(got - want).max()))
assert max_diff < 1e-3, f"ONNX and PyTorch outputs differ by {max_diff}"
assert 0.01 < reference.std(), "reference output is flat, so the check above proves nothing"

# Sample images for the bench page, and one stylized result to look at.
os.makedirs("/site/samples", exist_ok=True)
content_img.save("/site/samples/content.jpg", quality=90)
style_img.save("/site/samples/style.jpg", quality=90)
out = run(sess, content, style)[0].transpose(1, 2, 0)
Image.fromarray((out * 255).round().astype(np.uint8)).save("/site/samples/result.jpg", quality=90)

# One CPU core, as a first number for the server fallback (spec section 10).
opts = ort.SessionOptions()
opts.intra_op_num_threads = 1
one_core = ort.InferenceSession(OUT, opts)
cpu_seconds = {}
for side in (512, 1024):
    _, x = load(f"{SRC}/inputs/content/1.jpg", side)
    run(one_core, x, style)
    tic = time.perf_counter()
    run(one_core, x, style)
    cpu_seconds[side] = round(time.perf_counter() - tic, 2)

report = {
    "onnx_bytes": os.path.getsize(OUT),
    "onnx_nodes": len(onnx.load(OUT).graph.node),
    "parameters": sum(p.numel() for part in parts for p in part.parameters()),
    "max_diff_vs_pytorch": max_diff,
    "one_cpu_core_seconds": cpu_seconds,
}
json.dump(report, open("/site/export_report.json", "w"), indent=2)
print(json.dumps(report, indent=2))
