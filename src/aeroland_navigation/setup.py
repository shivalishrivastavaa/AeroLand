from setuptools import find_packages, setup

package_name = "aeroland_navigation"

setup(
    name=package_name,
    version="0.0.0",
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
    maintainer="shivali",
    maintainer_email="shivali@todo.todo",
    description="Autonomous navigation nodes for the AeroLand platform.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "turtle_patrol = aeroland_navigation.turtle_patrol:main",
        ],
    },
)