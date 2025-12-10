from setuptools import find_packages
from setuptools import setup

package_name = 'dbot_teleop'

setup(
    name=package_name,
    version='2.1.5',
    packages=find_packages(exclude=[]),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
    ],
    zip_safe=True,
    maintainer='duc',
    maintainer_email='huynhduc9905@gmail.com',
    description=(
        'Teleoperation node using keyboard.'
    ),
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'teleop_keyboard = dbot_teleop.script.teleop_keyboard:main'
        ],
    },
)
