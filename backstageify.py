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

    while clean.endswith('_'):
        clean = clean[:-1]

    clean = clean.replace('__', '_')

    if len(clean) > 63:
        clean = clean[:63]

    return clean

def clean_tag(tag: str) -> str:
    clean = re.sub(r'[^a-z0-9\-\.]', '-', tag.strip().lower())

    if len(clean) > 63:
        clean = clean[:63]

    return clean


print('Fetching templates...')

azd_templates = requests.get(INDEX_URL).json()

print()

pairs = []

for azd in azd_templates:
    print(f'Fetching azure.yaml for {azd["title"]}...')
    azure_text = requests.get(azure_yaml_path(azd['source'])).text
    # azure = yaml.safe_load(azure_text)
    # template['azure'] = yaml.safe_load(azure)
    pairs.append((azd, yaml.safe_load(azure_text)))

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

for azd, azure in pairs:

    print(f'Processing {azd["title"]}...')

    component = {
        'apiVersion': 'backstage.io/v1alpha1',
        'kind': 'Component',
        'metadata': {
            'name': azure['name'],
            'namespace': 'awesome-azd',
            'title': azd['title'],
            'description': azd['description'],
            'annotations': {
                'github.com/project-slug': azd['source'].removeprefix('https://github.com/'),
                'awesome.azd/template': azure['metadata']['template'],
                'awesome.azd/author': azd['author'],
            },
            'tags': [ clean_tag(tag) for tag in azd['tags'] ],
            'links': [
                {
                    'url': azd['website'],
                    'title': 'Website',
                    'icon': 'help',
                },
                {
                    'url': azd['source'],
                    'title': 'Source',
                    'icon': 'github',
                },
                {
                    'url': f'https://github.com/Azure/awesome-azd/website/static/{azd["preview"].removeprefix("./")}',
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

    # entities.append(component)

    template = {
        'apiVersion': 'scaffolder.backstage.io/v1beta3',
        'kind': 'Template',
        'metadata': {
            'name': azure['name'],
            'namespace': 'awesome-azd',
            'title': azd['title'],
            'description': azd['description'],
            'annotations': {
                'github.com/project-slug': azd['source'].removeprefix('https://github.com/'),
                'awesome.azd/template': azure['metadata']['template'],
                'awesome.azd/author': azd['author'],
            },
            'tags': [ clean_tag(tag) for tag in azd['tags'] ],
            'links': [
                {
                    'url': azd['website'],
                    'title': 'Website',
                    'icon': 'help',
                },
                {
                    'url': azd['source'],
                    'title': 'Source',
                    'icon': 'github',
                },
                {
                    'url': f'https://github.com/Azure/awesome-azd/website/static/{azd["preview"].removeprefix("./")}',
                    'title': 'Preview',
                    'icon': 'docs',
                }
            ],
        },
        'spec': {
            'type': 'website',
            # 'lifecycle': 'experimental',
            'owner': 'awesome-azd',
            'parameters': [
                {
                    'title': 'Create new Application',
                    'type': 'object',
                    'required': [ 'name', 'subscriptionId', 'location' ],
                    'properties': {
                        'name': {
                            'title': 'Application Name',
                            'type': 'string',
                            'description': 'The name of the application to create.',
                        },
                        'subscriptionId': {
                            'title': 'Subscription ID',
                            'type': 'string',
                            'description': 'The Azure Subscription ID to use.',
                        },
                        'location': {
                            'title': 'Location',
                            'type': 'string',
                            'description': 'The Azure Region to use.',
                        },
                    }
                }
            ],
            'steps': [
                {
                    'id': 'log',
                    'name': 'Log',
                    'action': 'debug:log',
                    'input': {
                        'message': 'Creating Azure Application...',
                        'listWorkspace': True,
                    },
                }
            ],
            'azure': azure
        }
    }

    entities.append(template)




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
