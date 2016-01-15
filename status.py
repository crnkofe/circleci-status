#!/usr/bin/env python

import os
import sys
import json
import logging
import requests

logging.basicConfig(level=logging.INFO)

CIRCLECI_TOKEN = os.environ['CIRCLECI_TOKEN']
CIRCLECI_PROJECTS_API = "https://circleci.com/api/v1/projects?circle-token={token}"

if not __name__ == '__main__':
    logging.error('Script must be run and not imported')
    sys.exit(1)


try:
    r = requests.get(
        CIRCLECI_PROJECTS_API.format(token = CIRCLECI_TOKEN),
        headers={
            'content-type':'application/json',
            'Accept': 'application/json'
        }
    )
    content = str(r.content).replace("'", "")[1:]

    blob = json.loads(content)
    if not r.status_code == 200:
        logging.error("Failed fetching status from CircleCI")
        sys.exit(1)

    for project in blob:
        data = []
        for i, recent_build in enumerate(project['branches']['master']['recent_builds']):
            data.append(str(recent_build['build_num']) + " " + str(recent_build['outcome'][:4]))
            if i >= 2:
                break

        print("{name: <15}: {data}".format(
            name=project['reponame'],
            data=' :: '.join(data)
        ))

except:
    logging.exception("Failed querying status")
