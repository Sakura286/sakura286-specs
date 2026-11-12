# SPDX-FileCopyrightText: (C) 2026 Institute of Software, Chinese Academy of Sciences (ISCAS)
# SPDX-FileCopyrightText: (C) 2026 openRuyi Project Contributors
# SPDX-FileContributor: Yifan Xu <xuyifan@iscas.ac.cn>
# SPDX-FileContributor: CHEN Xuan <chenxuan@iscas.ac.cn>
#
# SPDX-License-Identifier: MulanPSL-2.0

%global srcname triton

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
Version:        3.9.0
Release:        %autorelease
Summary:        Language and compiler for custom deep-learning primitives
# Triton itself is MIT.  The statically bundled LLVM/MLIR/LLD is
# "Apache-2.0 WITH LLVM-exception OR NCSA"; nanobind is BSD-3-Clause
License:        MIT AND (Apache-2.0 WITH LLVM-exception OR NCSA) AND BSD-3-Clause
URL:            https://triton-lang.org/main/index.html
VCS:            git:https://github.com/triton-lang/triton.git
#!RemoteAsset:  sha256:78fc9ff4403a856dce609c8529b6f341a7aaf331c2582ed7167949b40f864cd5
Source0:        https://codeload.github.com/triton-lang/triton/tar.gz/refs/tags/v%{version}#/%{srcname}-%{version}.tar.gz
#!RemoteAsset:  sha256:d5e5a0b206ac7ff12b0deef16b5b3d289d9b6d151a8c4f2f35fc97588d149118
Source1:        https://codeload.github.com/RuyiAI-Stack/llvm-project/tar.gz/%{llvm_commit}#/llvm-project-%{llvm_commit}.tar.gz
#!RemoteAsset:  sha256:b59c65078650e0cac853b5df9a5a8756f701659660ebda215a6bdede79911317
Source2:        https://codeload.github.com/RuyiAI-Stack/triton-riscv/tar.gz/%{shared_commit}#/%{shared_src}.tar.gz
Source3:        test-rpm-backends.py
# Use system build tools and nanobind, without upstream wheel dependency pins.
Patch0:         2001-system-build-tools.patch
# Keep AMD and the external CPU backend, plus shared NVIDIA dialect definitions.
Patch1:         2002-amd-and-shared-backends.patch
# Resolve CPU pipeline tools from the matching Buddy RPM; add the optimizer CLI.
Patch2:         2003-shared-backend-rpm-paths.patch
BuildSystem:    pyproject

# Unpack the external backend before applying patches to both source trees.
BuildOption(prep):  -n %{srcname}-%{version} -a 2

BuildOption(install):  -l %{srcname}
BuildOption(check):  -e 'triton.instrumentation.*'
BuildOption(check):  -e 'triton.plugins.*'
BuildOption(check):  -e 'triton.runtime.interpreter'
BuildOption(check):  -e 'triton.tools.mxfp'

BuildRequires:  buddy-mlir = %{buddy_version}
BuildRequires:  buddy-mlir-llvm = %{buddy_version}
BuildRequires:  clang(major) = %{bootstrap_llvm_maj_ver}
BuildRequires:  compiler-rt(major) = %{bootstrap_llvm_maj_ver}
BuildRequires:  cmake
BuildRequires:  gcc-c++
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
BuildRequires:  python3dist(lit)
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

%description
Triton is a language and compiler for writing highly efficient custom
deep-learning primitives. It provides a Python programming interface and a
compiler stack that lowers Triton kernels through MLIR and LLVM backends for
AMD GPU execution and CPU execution through the triton_shared backend. The
CPU pipeline uses the matching Buddy tools; GPU code generation is built with
a separate private LLVM from the same source revision.

%prep -a
tar -xf %{SOURCE1}
sed -i 's|@BUDDY_LLVM_BINDIR@|%{_libdir}/buddy-mlir/llvm/bin|' \
    %{shared_src}/backend/paths.py

%generate_buildrequires
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
export TRITON_CODEGEN_BACKENDS=amd
export TRITON_PLUGIN_DIRS="$PWD/%{shared_src}"
export TRITON_BUILD_NVIDIA_GSAN_RUNTIME=OFF
export TRITON_HOME="$PWD/.build-cache"
export TRITON_OFFLINE_BUILD=1
export TRITON_APPEND_CMAKE_ARGS="-DTRITON_BUILD_TOOLS=OFF -DTRITON_SHARED_BUILD_TRITON_SAN=OFF"

%check -a
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
%license %{shared_src}/LICENSE

%changelog
%autochangelog
