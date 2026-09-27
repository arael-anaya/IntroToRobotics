from setuptools import setup

package_name = 'wasd_teleop'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/wasd.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Arael Anaya',
    maintainer_email='arael.a.anaya@gmail.com',
    description='Shared WASD keyboard teleop',
    license='MIT',
    entry_points={
        'console_scripts': [
            'wasd = wasd_teleop.wasd:main',
        ],
    },
)
