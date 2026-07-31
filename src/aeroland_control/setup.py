from setuptools import find_packages, setup

package_name = "aeroland_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Shivali Shrivastava",
    maintainer_email="shivali.shrivastavaa@gmail.com",
    description="PX4 flight-control nodes for the AeroLand platform.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            (
                "offboard_controller = "
                "aeroland_control.offboard_controller:main"
            ),
        ],
    },
)