from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    req = f.read().splitlines()

setup(
    name='insitu-python-sdk',
    version='1.0',
    description='Arcam In-Situ Python SDK',
    author='Arcam EBM',
    author_email='viktor.kaernstrand@ge.com',
    package_dir={'': 'src'},  # Add this line - tells setuptools to look in src
    packages=find_packages(where='src'),  # Modify this line
    install_requires=req,
)