from setuptools import find_packages, setup


package_name = 'aeroland_perception'


setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        (
            'share/' + package_name,
            ['package.xml'],
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='shivali',
    maintainer_email='shivali.shrivastavaa@gmail.com',
    description=(
        'ROS 2 perception nodes for ArUco-based precision landing.'
    ),
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'aruco_detector = aeroland_perception.aruco_detector:main',
        ],
    },
)
