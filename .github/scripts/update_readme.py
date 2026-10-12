import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

mode = sys.argv[1]
event_name = os.environ['GITHUB_EVENT_NAME']
event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
path = Path('README.md')
text = path.read_text(encoding='utf-8-sig')
lines = text.splitlines()
sha = os.environ['GITHUB_SHA']

if mode == 'ci':
    branch = os.environ['GITHUB_REF_NAME']
    if event_name == 'pull_request':
        branch = event['pull_request']['head']['ref']
    elif event_name == 'push':
        repo = os.environ['GITHUB_REPOSITORY']
        api = os.environ.get('GITHUB_API_URL', 'https://api.github.com')
        request = Request(f'{api}/repos/{repo}/commits/{sha}/pulls')
        request.add_header('Authorization', 'Bearer ' + os.environ['GH_TOKEN'])
        request.add_header('Accept', 'application/vnd.github+json')
        with urlopen(request, timeout=30) as response:
            pulls = json.load(response)
        for pr in pulls:
            if (pr.get('merged_at') and pr['base']['ref'] == 'develop'
                    and pr.get('merge_commit_sha') == sha):
                branch = pr['head']['ref']
                break
    line = f'Añadida feature: {branch}'
    if line not in lines:
        lines.append(line)
    print(line)
elif mode == 'cd':
    message = (event.get('head_commit') or {}).get('message', '')
    if event_name == 'push' and message.startswith('[bootstrap-ci-cd]'):
        print('Preparacion inicial: se conserva AppVersion-0.')
        sys.exit(0)
    versions = [(i, re.fullmatch(r'AppVersion-(\d+)', line.strip()))
                for i, line in enumerate(lines)]
    versions = [(i, match) for i, match in versions if match]
    if len(versions) != 1:
        raise SystemExit('README debe tener una sola linea AppVersion-N.')
    marker = f'Version origen: {sha}'
    if event_name != 'pull_request' and marker in lines:
        print('Este commit ya fue versionado; no se incrementa otra vez.')
        sys.exit(0)
    index, match = versions[0]
    version = int(match.group(1)) + 1
    lines[index] = f'AppVersion-{version}'
    lines = [line for line in lines
             if not line.startswith(('Actualizada UTC: ', 'Version origen: '))]
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    lines.extend([f'Actualizada UTC: {stamp}', marker])
    print(f'AppVersion-{version} | {stamp}')
else:
    raise SystemExit('Modo esperado: ci o cd')

path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
if event_name == 'pull_request':
    print('Vista previa del PR; no se publica un commit en la rama destino.')
