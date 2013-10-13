from setuptools import setup

setup(
    name='scrutiny',
    version='0.0.1',
    description='',
    author='Luke Macken',
    author_email='lmacken@redhat.com',
    url='https://github.com/lmacken/scrutiny',
    install_requires=["fedmsg"],
    packages=[],
    entry_points="""
    [moksha.consumer]
    scm_consumer = scrutiny.scm_consumer:SCMConsumer
    """,
)
