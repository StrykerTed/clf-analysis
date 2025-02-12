from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    req = f.read().splitlines()

setup(
    name='insitu-python-sdk',
    version='1.0',
    description='Arcam In-Situ Python SDK',
    author='Arcam EBM',
    author_email='viktor.kaernstrand@ge.com',
    packages=find_packages(),  # Automatically find all packages
    install_requires=req,
)
