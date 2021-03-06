"""invoke tasks"""

import logging
import os
import shutil

from invoke import run as irun
from invoke import task

from qwcore import echo

PROJECT_ROOT = os.getcwd()
PROJECT = os.path.basename(PROJECT_ROOT)
PACKAGE = __import__(PROJECT, fromlist=['cli', '__about__'])
PACKAGE_PATH = os.path.join(PROJECT_ROOT, PROJECT)
DOCS_PATH = os.path.join(PROJECT_ROOT, 'docs')
MODULES_PATH = os.path.join(DOCS_PATH, 'modules')
if os.path.exists("overview.rst"):
    with open("overview.rst") as fp:
        OVERVIEW = fp.read()
else:
    OVERVIEW = PACKAGE.__about__.DESCRIPTION_RST

logger = logging.getLogger(PROJECT)


__all__ = ['docs', 'install_editable', 'merge_master', 'rst_all', 'rst_api', 'rst_cli',
           'rst_docs_index', 'rst_readme', 'test']


def run(*args, **kwargs):
    """a run that logs red when it fails"""
    r = irun(*args,  warn=True, **kwargs)
    if not r.ok:
        echo.error("Command Failed")
        raise SystemExit(1)
    return r


def has_docs():
    if not os.path.exists(DOCS_PATH):
        echo.warning("No docs found")
        return False
    return True


@task
def install_editable(c):
    cmd = 'pip install -e .'
    logger.info(cmd)
    run(cmd)


@task
def rst_api(c):
    if not has_docs():
        return
    if os.path.isdir(MODULES_PATH):
        shutil.rmtree(MODULES_PATH)
    api_cmd = 'sphinx-apidoc {pkg_path} {pkg_path}/tests {pkg_path}/tasks.py -o docs/modules -e -T -f'
    run(api_cmd.format(pkg_path=PACKAGE_PATH))


@task(pre=[install_editable])
def rst_cli(c):
    """Build rst for cli docs based on console script entry points"""
    if not has_docs():
        return
    if not hasattr(PACKAGE, 'cli'):
        echo.warning("No cli package found")
        return
    rst = []
    rst.extend(['.. _%s_reference:' % PROJECT, ''])
    rst.extend(['%s cli' % PROJECT, '='*50, ''])
    rst.extend(['.. contents:: Contents', '   :local:', ''])

    for ep in PACKAGE.__about__.ENTRY_POINTS['console_scripts']:
        script, _ = ep.split('=')
        script_ep_name = '%s.commands' % script.replace('-', '.')
        cmd_eps = PACKAGE.__about__.ENTRY_POINTS[script_ep_name]
        if not cmd_eps:
            continue
        rst.extend([script, '-'*50, ''])
        r = run('%s --help' % script)
        out = ['  ' + l for l in r.stdout.splitlines()]
        rst.extend(['::', ''] + out + [''])
        for ep in cmd_eps:
            cmd, _ = ep.split('=')
            full_cmd = "%s %s" % (script, cmd)
            rst.extend([full_cmd, '-'*50, ''])
            r = run('%s --help' % full_cmd)
            out = ['  ' + l for l in r.stdout.splitlines()]
            rst.extend(['::', ''] + out + [''])

    with open(os.path.join(DOCS_PATH, 'cli.rst'), 'w') as fh:
        fh.write("\n".join(rst))


def readme(is_docs=False):
    org = PACKAGE.__about__.ORG
    name = PACKAGE.__about__.NAME
    rst = []
    rst.extend(['='*len(name), name, '='*len(name), ''])
    rst.extend([OVERVIEW, ''])
    if has_docs() and not is_docs:
        rst.extend(['`Documentation <http://%s.readthedocs.org/en/latest/>`_' % name, ''])
    rst.extend(['Status', '-'*6, ''])
    rst.extend([PACKAGE.__about__.STATUS, ''])
    if is_docs:
        rst.extend(['`github.com/{org}/{name} <https://github.com/{org}/{name}>`_'.format(org=org, name=name), ''])
    else:
        rst.extend([('.. image:: https://secure.travis-ci.org/'
                     '{org}/{name}.png?branch=develop'.format(org=org, name=name)),
                    '   :target: http://travis-ci.org/{org}/{name}'.format(org=org, name=name),
                    ''])
    return rst


@task
def rst_docs_index(c):
    if not has_docs():
        return
    rst = readme(is_docs=True)
    rst.extend(['Contents', '-'*8, ''])
    rst.extend(['.. toctree::', '  :maxdepth: 2', '', '  guide', '  reference'])
    with open(os.path.join(DOCS_PATH, 'index.rst'), 'w') as fh:
        fh.write("\n".join(rst))


@task
def rst_readme(c):
    with open(os.path.join(PROJECT_ROOT, 'readme.rst'), 'w') as fh:
        fh.write("\n".join(readme()))


@task
def merge_master(c):
    run('git checkout master')
    run('git merge --ff-only origin/master')
    run('git merge --ff-only origin/develop')
    run('git push origin master')
    run('git checkout develop')


@task
def rst_all(c):
    rst_api(c)
    rst_cli(c)
    rst_docs_index(c)
    rst_readme(c)


@task(pre=[install_editable, rst_all])
def docs(c):
    if not has_docs():
        return
    run('sphinx-build -W -b html -d docs/_build/doctree docs docs/_build/html')


@task(default=True)
def test(c):
    cmd = 'tox -e py27,flake8,py3flake8'
    logger.info(cmd)
    run(cmd)
