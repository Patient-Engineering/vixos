try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="vixos",
    version="0.0.0",
    description="VixOS is a secure app launcher, inspired by QubesOS and jollheef/appvm.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Patient Engineering",
    author_email="msm@tailcall.net",
    packages=["vixos"],
    entry_points={
        "console_scripts": [
            "vixos = vixos.__main__:main",
        ],
    },
    license="GPLv3",
    include_package_data=True,
    install_requires=open("requirements.txt").read().splitlines(),
    url="https://github.com/Patient-Engineering/vixos",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.7'
)

