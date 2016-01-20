#!/usr/bin/env python

import os
import sys
import time
import json
import logging
import requests

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

        builds = [('running', build) for build in project['branches']['master']['running_builds']] +\
            [('recent', build) for build in project['branches']['master']['recent_builds'][:1]]

        for i, (build_type, recent_build) in enumerate(builds):
            git_commit_url = GIT_API_COMMIT.format(
                repo=project['reponame'],
                hashtag=recent_build['vcs_revision']
            )

            git_response = git_request(git_commit_url)
            data.append({
                'circle': str(recent_build['build_num']) + " " + str(recent_build['outcome'][:4]),
                'github': '{email} - {message}'.format(
                    email=git_response['author']['email'],
                    message=git_response['message']
                ) if git_response is not None else "N/A",
                'type': build_type
            })

        print("{col}{name}{nc}:\n{data}".format(
            col=RED,
            name=project['reponame'],
            nc=NC,
            data='\n'.join([
                "\t{github}\n\t{circle} - {build_type}".format(
                    github=entry['github'].replace("\n", "\n\t"),
                    circle=entry['circle'].replace("\n", "\n\t"),
                    build_type=entry['type']
                ) for entry in data
            ])
        ))

except:
    logging.exception("Failed querying status")
