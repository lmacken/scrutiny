scrutiny
========

Real-time source code auditing for Fedora

> This project is currently in the Alpha stages of development

Current Features
-----------------

* Listens to the [fedmsg](http://fedmsg.com) bus for git commits
* Downloads, extracts, and compares upstream tarballs
* Slowly scrolls code changes as they are committed

Future Features
---------------

* Automatically run linters and static analysis tools, and use git to track &
  display changes in the output
* Web interactivity, ability to +1/-1/comment/tag/flag changes, with 
  links to [datagrepper](https://apps.fedoraproject.org/datagrepper) for more details
* Statistics by project, committer, distro-wide audit coverage, etc
* A datagrepper-querying mutt-like console auditor

Running
-------

    sudo yum install fedmsg-hub colordiff GitPython
    sudo cp config.py /etc/fedmsg.d/scrutiny.py
    python setup.py egg_info
    PYTHONPATH=$(pwd) fedmsg-hub

