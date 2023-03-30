from setuptools import find_packages, setup
import os
path = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(path, "README.md"), "r", encoding="utf-8") as f:
    long_description = f.read()
    setup(name='nonebot_plugin_xdu_support',  # 包名
          version='0.5.1',  # 版本号
          description='A plugin based on nonebot2, which is support XDU services.',
          long_description=long_description,
          long_description_content_type="text/markdown",
          author='longchengguxiao',
          author_email='1298919732@qq.com',
          url='http://lcgx.xdu.org.cn/',
          include_package_data=True,
          install_requires=[
              "nonebot2>=2.0.0a16",
              "nonebot-adapter-onebot>=2.0.0b1",
              "nonebot-plugin-apscheduler>=0.2.0",
              "requests",
              "libxduauth>=1.7.4",
              "pytz",
              "lxml",
              "pyDes",
              "httpx",
              "numpy",
              "jionlp",
              "pycryptodome",
              "python-dateutil",
              "setuptools",
              "jieba"
          ],
          license='AGPL-3.0 License',
          packages=find_packages(),
          platforms=["all"],
          classifiers=['Intended Audience :: Developers',
                       'Operating System :: OS Independent',
                       'Natural Language :: Chinese (Simplified)',
                       'Programming Language :: Python',
                       'Programming Language :: Python :: 3.8',
                       'Programming Language :: Python :: 3.9',
                       'Topic :: Software Development :: Libraries'
                       ],
          )
