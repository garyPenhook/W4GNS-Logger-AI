"""Setup script for building Cython extensions."""

import os
import sys
from pathlib import Path

from setuptools import Extension, setup

# Check if Cython is available
try:
    from Cython.Build import cythonize

    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False
    print("Cython not found. Building from C sources if available.", file=sys.stderr)

# Define extension modules
ext_modules = []

if USE_CYTHON:
    # ADIF parsing extension (highest priority)
    ext_modules.append(
        Extension(
            "w4gns_logger_ai.c_extensions.c_adif_parser",
            sources=["w4gns_logger_ai/c_extensions/c_adif_parser.pyx"],
            language="c",
            extra_compile_args=["-O3", "-march=native"] if os.name != "nt" else ["/O2"],
        )
    )

    # Awards computation extension
    ext_modules.append(
        Extension(
            "w4gns_logger_ai.c_extensions.c_awards",
            sources=["w4gns_logger_ai/c_extensions/c_awards.pyx"],
            language="c",
            extra_compile_args=["-O3", "-march=native"] if os.name != "nt" else ["/O2"],
        )
    )

    # ADIF export extension
    ext_modules.append(
        Extension(
            "w4gns_logger_ai.c_extensions.c_adif_export",
            sources=["w4gns_logger_ai/c_extensions/c_adif_export.pyx"],
            language="c",
            extra_compile_args=["-O3", "-march=native"] if os.name != "nt" else ["/O2"],
        )
    )

    # Cythonize with compiler directives for optimization
    ext_modules = cythonize(
        ext_modules,
        compiler_directives={
            "language_level": "3",
            "embedsignature": True,
            "boundscheck": False,  # Disable bounds checking for speed
            "wraparound": False,  # Disable negative indexing for speed
            "cdivision": True,  # Use C division (no zero check)
            "initializedcheck": False,  # Disable memoryview initialization check
        },
    )
else:
    # Try to build from pre-generated C sources
    c_sources = [
        "w4gns_logger_ai/c_extensions/c_adif_parser.c",
        "w4gns_logger_ai/c_extensions/c_awards.c",
        "w4gns_logger_ai/c_extensions/c_adif_export.c",
    ]

    for c_source in c_sources:
        if Path(c_source).exists():
            module_name = c_source.replace("/", ".").replace(".c", "")
            ext_modules.append(
                Extension(
                    module_name,
                    sources=[c_source],
                    language="c",
                    extra_compile_args=["-O3", "-march=native"]
                    if os.name != "nt"
                    else ["/O2"],
                )
            )

# Build configuration
setup(
    ext_modules=ext_modules,
    # Allow build to succeed even if C extensions fail
    # (pure Python fallback will be used)
    zip_safe=False,
)
