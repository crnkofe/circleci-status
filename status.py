#!/usr/bin/env python
"""CircleCI Status.

Usage:
  status.py [-b=<BRANCH>] [-p=<PROJECTS>] [-l=<LAST> ]
  status.py (-h | --help)
  status.py --version

Options:
  -h --help                Show this screen.
  -b --branch=<BRANCH>     Branch to use(master by default)
  -p --projects=<PROJECTS> Comma separated list of repository names
  -l --last=<BUILDS>       How many builds to show.
"""

import os
import sys
import time
import json
import logging
import requests
from docopt import docopt


logging.basicConfig(level=logging.WARNING)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

RED='\033[0;31m'
NC='\033[0m' # No Color

MAX_RETRIES = 3

GIT_TOKEN =  os.environ['GIT_TOKEN']
GIT_API = 'https://api.github.com'
GIT_OWNER = os.environ['GIT_OWNER']
GIT_API_COMMIT = GIT_API + '/repos/' + GIT_OWNER + '/{repo}/git/commits/{hashtag}'

CIRCLECI_TOKEN = os.environ['CIRCLECI_TOKEN']
CIRCLECI_PROJECTS_API = "https://circleci.com/api/v1/projects?circle-token={token}"

if not __name__ == '__main__':
    logging.error('Script must be run and not imported')
    sys.exit(1)

arguments = docopt(__doc__, version='CircleCI Status')
branch = arguments.get('--branch', 'master') or 'master'
projects = arguments.get('--projects')
if projects is not None:
    projects = set(projects.split(','))
count_builds = int(arguments.get('--last') or 1)

def git_request(api, token=None):
    success = False
    retries = 0
    r = None
    while not success and retries < MAX_RETRIES:
        try:
            r = requests.get(
                api,
                headers={
                    'content-type':'application/json',
                    'Authorization': 'token {}'.format(token or GIT_TOKEN),
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            success = True
        except:
            logging.warning('Failed querying Git API')
        time.sleep(1)
        retries += 1
    try:
        return r.json() if r is not None else None
    except:
        return None


try:
    r = requests.get(
        CIRCLECI_PROJECTS_API.format(token = CIRCLECI_TOKEN),
        headers={
            'content-type':'application/json',
            'Accept': 'application/json'
        }
    )
    blob = r.json()  # str(r.content).replace("'", "")[1:]

    # blob = json.loads(content)
    if not r.status_code == 200:
        logging.error("Failed fetching status from CircleCI")
        sys.exit(1)

    for project in blob:
        data = []

        if projects is not None:
            if project['reponame'] not in projects:
                continue

        valid_branch = project['branches'][branch] if branch in project['branches'] else None

        if valid_branch is not None:
            builds = [('running', build) for build in valid_branch['running_builds']] +\
                [('recent', build) for build in valid_branch['recent_builds'][:count_builds]]
        else:
            builds = []

        for i, (build_type, recent_build) in enumerate(builds):
            git_commit_url = GIT_API_COMMIT.format(
                repo=project['reponame'],
                hashtag=recent_build['vcs_revision']
            )

            git_response = git_request(git_commit_url)
            outcome = (recent_build['outcome'] or '')[:4] if 'outcome' in recent_build else ''
            if outcome != "":
                outcome = " " + outcome
            data.append({
                'circle': str(recent_build['build_num']) + outcome,
                'github': '{email} - {message}'.format(
                    email=git_response['author']['email'],
                    message=git_response['message']
                ) if git_response is not None else "N/A",
                'type': build_type
            })
            if i >= count_builds:
                break

        if len(data) == 0:
            data = " N/A"
        else:
            data = "\n" + '\n'.join([
                "\t{github}\n\t{circle} - {build_type}".format(
                    github=entry['github'].replace("\n", "\n\t").strip(),
                    circle=entry['circle'].replace("\n", "\n\t"),
                    build_type=entry['type']
                ) for entry in data
            ])

        print("{col}{name}{nc}:{data}".format(
            col=RED,
            name=project['reponame'],
            nc=NC,
            data=data
        ))

except:
    logging.exception("Failed querying status")
