import re
import shutil
import subprocess

from pathlib import Path

import requests
import yaml

INDEX_URL = 'https://raw.githubusercontent.com/Azure/awesome-azd/main/website/static/templates.json'

LOCAL_DIR = Path(__file__).resolve().parent
CATALOG_INFO = LOCAL_DIR / 'catalog-info.yaml'

def azure_yaml_path(source: str) -> str:
    branch = 'main'

    # TODO this is garbage
    if source.endswith('ASA-Samples-Web-Application'):
        branch = 'quickstart'
    if source.endswith('simple-flask-azd') or source.endswith('simple-streamlit-azd'):
        branch = 'master'

    path = source.replace('https://github.com/', 'https://raw.githubusercontent.com/')

    return f'{path}/{branch}/azure.yaml'


def normalize_entity_name(name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '-', name.strip().lower())

    # invalid to end with _
    while clean.endswith('_'):
        clean = clean[:-1]

    # cleans up format for groups like 'my group (Reader)'
    clean = clean.replace('__', '_')

    if len(clean) > 63:
        clean = clean[:63]

    return clean

print('Fetching templates...')
templates = requests.get(INDEX_URL).json()

print()

pairs = []

for template in templates:
    print(f'Fetching azure.yaml for {template["title"]}...')
    azure_text = requests.get(azure_yaml_path(template['source'])).text
    # azure = yaml.safe_load(azure_text)
    # template['azure'] = yaml.safe_load(azure)
    pairs.append((template, yaml.safe_load(azure_text)))

entities = []

# add a service group entity
entities.append({
    'apiVersion': 'backstage.io/v1alpha1',
    'kind': 'Group',
    'metadata': {
        'name': 'awesome-azd',
    },
    'spec': {
        'type': 'product-area',
        'children': []
    }
})

# add a service user account
entities.append({
    'apiVersion': 'backstage.io/v1alpha1',
    'kind': 'User',
    'metadata': {
        'name': 'awesome-azd',
    },
    'spec': {
        'memberOf': [ 'awesome-azd' ]
    }
})

print()

for template, azure in pairs:

    print(f'Processing {template["title"]}...')

    component = {
        'apiVersion': 'backstage.io/v1alpha1',
        'kind': 'Component',
        'metadata': {
            'name': azure['name'],
            'namespace': 'awesome-azd',
            'title': template['title'],
            'description': template['description'],
            'annotations': {
                'github.com/project-slug': template['source'].removeprefix('https://github.com/'),
                'awesome.azd/template': azure['metadata']['template'],
                'awesome.azd/author': template['author'],
            },
            'tags': template['tags'],
            'links': [
                {
                    'url': template['website'],
                    'title': 'Website',
                    'icon': 'help',
                },
                {
                    'url': template['source'],
                    'title': 'Source',
                    'icon': 'github',
                },
                {
                    'url': f'https://github.com/Azure/awesome-azd/website/static/{template["preview"].removeprefix("./")}',
                    'title': 'Preview',
                    'icon': 'docs',
                }
            ],
        },
        'spec': {
            'type': 'website',
            'lifecycle': 'experimental',
            'owner': 'awesome-azd',
            'azure': azure
        }
    }

    entities.append(component)


# get the full path to the git executable
git = shutil.which('git')

print(f'  Ensuring: {CATALOG_INFO}')
if not CATALOG_INFO.exists():
    # if the catalog-info.yaml file doesn't exist, create it
    CATALOG_INFO.touch()
    # run the git command to add the catalog-info.yaml file
    subprocess.run([git, 'add', CATALOG_INFO])

with open (CATALOG_INFO, 'w') as f:
    yaml.safe_dump_all(entities, f, default_flow_style=False, sort_keys=False)
