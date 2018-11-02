from setuptools import setup, find_packages

setup(
    include_package_data=True,
    packages=find_packages('src'),
    package_dir={'': 'src'}
)
