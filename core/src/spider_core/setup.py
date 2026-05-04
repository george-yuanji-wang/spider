from setuptools import find_packages, setup

package_name = 'spider_core'

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
    maintainer='spider',
    maintainer_email='spider@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            # ── Existing nodes ──────────────────────────────────
            'camera       = spider_core.camera:main',
            'motor        = spider_core.motor:main',
            'keyboard     = spider_core.keyboard:main',
            'ball_track   = spider_core.ball_track:main',
            'ball_display = spider_core.ball_display:main',

            # ── New nodes ────────────────────────────────────────
            'camera_node     = spider_core.camera_node:main',
            'ball_track_node = spider_core.ball_track_node:main',
            'path_plan_node  = spider_core.path_plan_node:main',
            'motor_node      = spider_core.motor_node:main',
            'bridge_node     = spider_core.bridge_node:main',
            'stream_node     = spider_core.stream_node:main',
        ],
    },
)