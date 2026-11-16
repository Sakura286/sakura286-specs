# SPDX-FileCopyrightText: (C) 2026 Institute of Software, Chinese Academy of Sciences (ISCAS)
# SPDX-FileCopyrightText: (C) 2026 openRuyi Project Contributors
# SPDX-FileContributor: CHEN Xuan <chenxuan@iscas.ac.cn>
#
# SPDX-License-Identifier: MulanPSL-2.0

%global pypi_name msgspec

Name:           python-%{pypi_name}
Version:        0.20.0
Release:        %autorelease
Summary:        Fast serialization and validation library
License:        BSD-3-Clause
URL:            https://jcristharif.com/msgspec/
#!RemoteAsset:  sha256:692349e588fde322875f8d3025ac01689fead5901e7fb18d6870a44519d62a29
Source0:        https://files.pythonhosted.org/packages/source/m/%{pypi_name}/%{pypi_name}-%{version}.tar.gz
# Check typed decoding of nested dataclasses with deferred annotations.
Source1:        test-dataclass-msgpack.py
BuildSystem:    pyproject

BuildOption(install):  %{pypi_name}

BuildRequires:  pyproject-rpm-macros
BuildRequires:  pkgconfig(python3)
BuildRequires:  python3-devel
BuildRequires:  python3dist(pip)
BuildRequires:  python3dist(setuptools)
BuildRequires:  python3dist(wheel)

Provides:       python3-%{pypi_name} = %{version}-%{release}
Provides:       python3-%{pypi_name}%{?_isa} = %{version}-%{release}
%python_provide python3-%{pypi_name}

%description
A fast serialization and validation library, with builtin support for
JSON, MessagePack, YAML, and TOML.

%generate_buildrequires
%pyproject_buildrequires

%check -a
PYTHONPATH=%{buildroot}%{python3_sitearch} %{python3} %{SOURCE1}

%files -f %{pyproject_files}
%doc README.md
%license LICENSE

%changelog
%autochangelog
