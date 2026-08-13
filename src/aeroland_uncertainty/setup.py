from setuptools import find_packages, setup

package_name = 'aeroland_uncertainty'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='shivali',
    maintainer_email='shivali.shrivastavaa@gmail.com',
    description='Landing uncertainty estimation for AeroLand.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            (
                "landing_confidence = "
                "aeroland_uncertainty.landing_confidence:main"
            ),
        ],
    },
)
