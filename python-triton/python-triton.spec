# SPDX-FileCopyrightText: (C) 2026 Institute of Software, Chinese Academy of Sciences (ISCAS)
# SPDX-FileCopyrightText: (C) 2026 openRuyi Project Contributors
# SPDX-FileContributor: Yifan Xu <xuyifan@iscas.ac.cn>
# SPDX-FileContributor: CHEN Xuan <chenxuan@iscas.ac.cn>
#
# SPDX-License-Identifier: MulanPSL-2.0

%global srcname triton
# The triton-riscv compatibility baseline is a post-3.9.0 upstream snapshot.
%global commit bbe38e5742621fa0e46435133f79a6aff2ffaf7d
%global snapshot_suffix +git20261112.bbe38e5

# Match the LLVM gitlink of the Buddy snapshot, including the RuyiAI fork.
%global llvm_commit f346011a7ac59144fe085e0bc029cb24835f7a69
%global shared_commit 9ded1d4c19462dd13a9addef5551a4d09e7e3e97
%global shared_src triton-riscv-%{shared_commit}
%global buddy_version 0.1.4~git20261112.72dcb5d

%global bootstrap_llvm_maj_ver 22
%global bootstrap_llvm_bindir %{_libdir}/llvm%{bootstrap_llvm_maj_ver}/bin

# Build the bundled LLVM and the Triton extension with clang
%global toolchain clang
%global _lto_cflags %{nil}
%define _find_debuginfo_dwz_opts %{nil}

Name:           python-%{srcname}
Version:        3.9.0%{snapshot_suffix}
Release:        %autorelease
Summary:        Language and compiler for custom deep-learning primitives
# Triton itself is MIT.  The statically bundled LLVM/MLIR/LLD is
# "Apache-2.0 WITH LLVM-exception OR NCSA"; nanobind is BSD-3-Clause
License:        MIT AND (Apache-2.0 WITH LLVM-exception OR NCSA) AND BSD-3-Clause
URL:            https://triton-lang.org/main/index.html
VCS:            git:https://github.com/triton-lang/triton.git
#!RemoteAsset:  sha256:b42983a22beaf0043ec01e0d38529193d6653cc3147ea9dac2c729ee98a0129e
Source0:        https://codeload.github.com/triton-lang/triton/tar.gz/%{commit}#/%{srcname}-%{commit}.tar.gz
#!RemoteAsset:  sha256:d5e5a0b206ac7ff12b0deef16b5b3d289d9b6d151a8c4f2f35fc97588d149118
Source1:        https://codeload.github.com/RuyiAI-Stack/llvm-project/tar.gz/%{llvm_commit}#/llvm-project-%{llvm_commit}.tar.gz
#!RemoteAsset:  sha256:b59c65078650e0cac853b5df9a5a8756f701659660ebda215a6bdede79911317
Source2:        https://codeload.github.com/RuyiAI-Stack/triton-riscv/tar.gz/%{shared_commit}#/%{shared_src}.tar.gz
Source3:        test-rpm-backends.py
BuildSystem:    pyproject

# Unpack the external backend before applying patches to both source trees.
BuildOption(prep):  -n %{srcname}-%{commit} -a 2

BuildOption(install):  -l %{srcname}
BuildOption(check):  -e 'triton.instrumentation.*'
BuildOption(check):  -e 'triton.plugins.*'
BuildOption(check):  -e 'triton.runtime.interpreter'
BuildOption(check):  -e 'triton.tools.mxfp'
# Optional NVIDIA GSan helpers require PyTorch and disabled native bindings.
BuildOption(check):  -e 'triton.experimental.gsan*'
BuildOption(check):  -e 'triton.tools.gsan'

BuildRequires:  buddy-mlir = %{buddy_version}
BuildRequires:  buddy-mlir-llvm = %{buddy_version}
BuildRequires:  clang(major) = %{bootstrap_llvm_maj_ver}
BuildRequires:  compiler-rt(major) = %{bootstrap_llvm_maj_ver}
BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  git
BuildRequires:  libstdc++-devel
BuildRequires:  lld(major) = %{bootstrap_llvm_maj_ver}
BuildRequires:  ninja
BuildRequires:  nlohmann-json
BuildRequires:  pkgconfig(libffi)
BuildRequires:  pkgconfig(libxml-2.0)
BuildRequires:  pkgconfig(libzstd)
BuildRequires:  pkgconfig(python3)
BuildRequires:  pkgconfig(zlib)
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3dist(build)
BuildRequires:  python3dist(installer)
BuildRequires:  python3dist(nanobind) >= 2.10.2
BuildRequires:  python3dist(numpy)
BuildRequires:  python3dist(setuptools)
BuildRequires:  python3dist(wheel)

# CPU JIT compiles its launcher against Python headers with g++.
Requires:       buddy-mlir%{?_isa} = %{buddy_version}
Requires:       buddy-mlir-llvm%{?_isa} = %{buddy_version}
Requires:       gcc-c++
Requires:       pkgconfig(python3)
Provides:       python3-%{srcname} = %{version}-%{release}
Provides:       python3-%{srcname}%{?_isa} = %{version}-%{release}
%python_provide python3-%{srcname}

%patchlist
# Use system build tools and nanobind, without upstream wheel dependency pins.
2001-system-build-tools.patch
# Keep AMD and the external CPU backend, plus shared NVIDIA dialect definitions.
2002-amd-and-shared-backends.patch
# Resolve CPU pipeline tools from the matching Buddy RPM; add the optimizer CLI.
2003-shared-backend-rpm-paths.patch
# Adapt both loop annotation builders to the fixed Buddy LLVM API.
2004-buddy-llvm-loop-annotations.patch
# Update AMD relaxed loads and ROCDL target selection for the same LLVM.
2005-buddy-llvm-amd-lowering.patch
# Keep pass gating and optimization pipelines compatible with Buddy LLVM.
2006-buddy-llvm-pass-management.patch

%description
Triton is a language and compiler for writing highly efficient custom
deep-learning primitives. It provides a Python programming interface and a
compiler stack that lowers Triton kernels through MLIR and LLVM backends for
AMD GPU execution and CPU execution through the triton_shared backend. The
CPU pipeline uses the matching Buddy tools; GPU code generation is built with
a separate private LLVM from the same source revision.

%prep -a
tar -xf %{SOURCE1}
cp %{shared_src}/LICENSE LICENSE.triton-shared
# nanobind-static is compiled into libtriton from the system build dependency.
cp %{_datadir}/licenses/python-nanobind/LICENSE LICENSE.nanobind
sed -i 's|@BUDDY_LLVM_BINDIR@|%{_libdir}/buddy-mlir/llvm/bin|' \
    %{shared_src}/backend/paths.py

%generate_buildrequires
export TRITON_WHEEL_VERSION_SUFFIX="%{snapshot_suffix}"
export TRITON_CODEGEN_BACKENDS=amd
export TRITON_PLUGIN_DIRS="$PWD/%{shared_src}"
export TRITON_BUILD_PROTON=OFF
%pyproject_buildrequires

%build -p
export PATH="%{bootstrap_llvm_bindir}:${PATH}"
export CC="%{bootstrap_llvm_bindir}/clang"
export CXX="%{bootstrap_llvm_bindir}/clang++"

llvm_src="$(pwd)/llvm-project-%{llvm_commit}"
llvm_install="$(pwd)/llvm-install"

mem_gb=$(awk '/MemTotal/ {print int($2/1024/1024)}' /proc/meminfo)
compile_jobs=$(nproc)
mem_jobs=$(( 1 + mem_gb / 2 ))
[ "$mem_jobs" -lt "$compile_jobs" ] && compile_jobs=$mem_jobs
[ "$compile_jobs" -lt 1 ] && compile_jobs=1
link_jobs=$(( 1 + mem_gb / 16 ))
[ "$link_jobs" -lt 1 ] && link_jobs=1

llvm_targets="X86;RISCV;AMDGPU;NVPTX"

cmake -S "$llvm_src/llvm" -B "$llvm_src/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$llvm_install" \
    -DCMAKE_C_COMPILER="$CC" \
    -DCMAKE_CXX_COMPILER="$CXX" \
    -DLLVM_USE_LINKER=lld \
    -DLLVM_ENABLE_PROJECTS="mlir;lld" \
    -DLLVM_TARGETS_TO_BUILD="$llvm_targets" \
    -DLLVM_ENABLE_ASSERTIONS=OFF \
    -DBUILD_SHARED_LIBS=OFF \
    -DLLVM_BUILD_LLVM_DYLIB=OFF \
    -DLLVM_INSTALL_UTILS=ON \
    -DLLVM_ENABLE_ZSTD=ON \
    -DLLVM_INCLUDE_BENCHMARKS=OFF \
    -DLLVM_INCLUDE_EXAMPLES=OFF \
    -DLLVM_INCLUDE_TESTS=OFF \
    -DLLVM_PARALLEL_COMPILE_JOBS=$compile_jobs \
    -DLLVM_PARALLEL_LINK_JOBS=$link_jobs
cmake --build "$llvm_src/build" --target install -- -j$compile_jobs

# The AMD backend has a separate codegen library in Triton 3.9. Build it
# against the same source-built LLVM rather than fetching an upstream binary.
cmake -S third_party/amd/backend/codegen -B amd-codegen-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER="$CC" \
    -DCMAKE_CXX_COMPILER="$CXX" \
    -DLLVM_DIR="$llvm_install/lib/cmake/llvm" \
    -DTRITON_AMD_LLVM_REVISION=%{llvm_commit}
cmake --build amd-codegen-build --target triton_amd_codegen -- -j$compile_jobs
install -Dpm0755 amd-codegen-build/libtriton_amd_codegen.so \
    third_party/amd/backend/lib/libtriton_amd_codegen.so
export TRITON_AMD_CODEGEN_PATH="$PWD/third_party/amd/backend/lib/libtriton_amd_codegen.so"

export LLVM_SYSPATH="$llvm_install"
export PATH="$llvm_install/bin:$PATH"
export JSON_SYSPATH="%{_prefix}"
export MAX_JOBS=$compile_jobs
export TRITON_PARALLEL_LINK_JOBS=$link_jobs
export TRITON_BUILD_WITH_CLANG_LLD=ON
export TRITON_BUILD_PROTON=OFF
export TRITON_WHEEL_VERSION_SUFFIX="%{snapshot_suffix}"
export TRITON_CODEGEN_BACKENDS=amd
export TRITON_PLUGIN_DIRS="$PWD/%{shared_src}"
export TRITON_BUILD_NVIDIA_GSAN_RUNTIME=OFF
export TRITON_HOME="$PWD/.build-cache"
export TRITON_OFFLINE_BUILD=1
export TRITON_APPEND_CMAKE_ARGS="-DTRITON_BUILD_TOOLS=OFF -DTRITON_SHARED_BUILD_TRITON_SAN=OFF -DLLVM_EXTERNAL_LIT=$llvm_src/llvm/utils/lit/lit.py"

%check -a
# Use lit from the pinned LLVM source; openRuyi has no standalone lit RPM.
triton_cmake_dir=$(%{python3} -c 'from python.build_helpers import get_cmake_dir; print(get_cmake_dir())')
PATH="$PWD/llvm-install/bin:$PATH" %{python3} \
    llvm-project-%{llvm_commit}/llvm/utils/lit/lit.py -sv \
    --filter='Conversion/TritonToLinalg/' \
    "$triton_cmake_dir/third_party/triton_shared/test"

# Use installed files and normal RPM tool lookup; do not mask path problems
# with the build-time LLVM_SYSPATH or backend/tool environment overrides.
export TRITON_CACHE_DIR="$PWD/.check-cache"
export TRITON_DEFAULT_BACKEND=triton_shared
unset LLVM_SYSPATH LLVM_BINARY_DIR BUDDY_MLIR_BINARY_DIR TRITON_SHARED_OPT_PATH
PYTHONPATH=%{buildroot}%{python3_sitearch} %{python3} %{SOURCE3}
PYTHONPATH=%{buildroot}%{python3_sitearch} %{buildroot}%{_bindir}/triton-shared-opt --help > /dev/null

%files -f %{pyproject_files}
%{_bindir}/triton-shared-opt
%doc README.md
%license LICENSE
%license llvm-project-%{llvm_commit}/llvm/LICENSE.TXT
%license LICENSE.triton-shared
%license LICENSE.nanobind

%changelog
%autochangelog
