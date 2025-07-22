from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    req = f.read().splitlines()

setup(
    name='Arcam ABP File operations',
    version='1.0',
    description='Arcam In-Situ Python SDK',
    author='Ted Tedford',
    author_email='Ted.Tedford@stryker.com',
    package_dir={'': 'src'},  # Add this line - tells setuptools to look in src
    packages=find_packages(where='src'),  # Modify this line
    install_requires=req,
)