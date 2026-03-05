import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'helmoro_motor_driver'

setup(
    name=package_name,
    version='2.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='Muhammed',
    maintainer_email='muhammed@todo.com',
    description='Motor driver for HelMoRo: BTS7960B H-Bridge + Pico 2W controller',
    license='BSD',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'motor_driver_node = helmoro_motor_driver.motor_driver_node:main',
        ],
    },
)
