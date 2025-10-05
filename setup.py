"""
Setup script for gitlab-mr-review package
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
here = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'AI-powered code review for GitLab merge requests'

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    try:
        with open(os.path.join(here, filename), encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        return []

install_requires = read_requirements('requirements.txt')

setup(
    name='gitlab-mr-review',
    version='0.1.0',
    author='Napat Srithavalya',
    author_email='napat.s@devcula.com',
    description='AI-powered code review for GitLab merge requests',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.devcula.com/playground/gitlab-mr-review',
    packages=find_packages(exclude=['tests', 'tests.*', 'packages']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Quality Assurance',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.8',
    install_requires=install_requires,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'gitlab-mr-review=gitlab_mr_review.main:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
