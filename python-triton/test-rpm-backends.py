# SPDX-FileCopyrightText: (C) 2026 Institute of Software, Chinese Academy of Sciences (ISCAS)
# SPDX-License-Identifier: MulanPSL-2.0
"""Exercise the installed CPU pipeline and AMD compilation without a GPU."""
from importlib.metadata import distribution
from pathlib import Path

import numpy as np
import triton
import triton.language as tl
from triton.backends import backends
from triton.backends.compiler import GPUTarget
from triton.backends.triton_shared.driver import CPUDriver
from triton.backends.triton_shared.paths import _get_llvm_bin_path
from triton.compiler import ASTSource


class Tensor:
    """Expose a NumPy allocation through Triton's public pointer protocol."""

    dtype = tl.float32

    def __init__(self, array):
        self.array = np.ascontiguousarray(array, dtype=np.float32)

    def data_ptr(self):
        return self.array.ctypes.data


@triton.jit
def vector_add(X, Y, Z, N, BLOCK: tl.constexpr):
    offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    mask = offsets < N
    tl.store(Z + offsets, tl.load(X + offsets, mask, other=0)
             + tl.load(Y + offsets, mask, other=0), mask)


@triton.jit
def matmul(A, B, C, BLOCK: tl.constexpr):
    row = tl.arange(0, BLOCK)
    col = tl.arange(0, BLOCK)
    a = tl.load(A + row[:, None] * BLOCK + col[None, :])
    b = tl.load(B + row[:, None] * BLOCK + col[None, :])
    c = tl.dot(a, b, input_precision="ieee")
    tl.store(C + row[:, None] * BLOCK + col[None, :], c)


assert triton.__version__ == "3.9.0", triton.__version__
assert distribution("triton").version == "3.9.0+git20261102.bbe38e5"
assert set(backends) == {"amd", "triton_shared"}, backends
entries = {e.name for e in distribution("triton").entry_points
           if e.group == "triton.backends"}
assert entries == {"amd", "triton_shared"}, entries
assert "buddy-mlir/llvm/bin" in _get_llvm_bin_path("opt")
assert Path(_get_llvm_bin_path("llc")).is_file()
assert CPUDriver.is_active()
triton.runtime.driver.set_active(CPUDriver())

rng = np.random.default_rng(42)
# A non-multiple of the block size also exercises masked loads and stores.
x = Tensor(rng.random(259))
y = Tensor(rng.random(259))
z = Tensor(np.zeros(259))
vector_add[(triton.cdiv(259, 64),)](x, y, z, 259, BLOCK=64)
np.testing.assert_allclose(z.array, x.array + y.array, rtol=1e-6, atol=1e-6)
print("CPU masked vector addition: passed", flush=True)

a = Tensor(rng.uniform(-1, 1, (16, 16)))
b = Tensor(rng.uniform(-1, 1, (16, 16)))
c = Tensor(np.zeros((16, 16)))
matmul[(1,)](a, b, c, BLOCK=16)
np.testing.assert_allclose(c.array, a.array @ b.array, rtol=1e-4, atol=1e-5)
print("CPU float32 matrix multiplication: passed", flush=True)

source = ASTSource(vector_add,
                   signature={"X": "*fp32", "Y": "*fp32", "Z": "*fp32", "N": "i32"},
                   constexprs={"BLOCK": 64})
kernel = triton.compile(source, target=GPUTarget("hip", "gfx90a", 64))
assert kernel.asm["hsaco"], "AMD compilation produced no code object"
print("AMD gfx90a offline compilation: passed (GPU execution not tested)", flush=True)
