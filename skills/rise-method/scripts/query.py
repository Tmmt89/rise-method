#!/usr/bin/env python3
"""Read selected RiseAcademy specification records without copying the corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
CATALOGS = {
    'profiles': ('profiles.json', 'profiles'),
    'contexts': ('profiles.json', 'context_overlays'),
    'frameworks': ('frameworks.json', 'frameworks'),
    'activities': ('activities.json', 'activities'),
    'rules': ('core-rules.json', 'rules'),
    'checks': ('quality-rubric.json', 'checks'),
    'platform': ('platform-requirements.json', 'requirements'),
}
DOCUMENTS = {
    'blueprint': 'methodology/blueprint-contract.ru.md',
    'decisions': 'methodology/decisions.ru.md',
    'glossary': 'GLOSSARY.md',
    'platform': 'methodology/platform-fit.ru.md',
    'workflow': 'methodology/README.ru.md',
    'scenarios': 'methodology/review-scenarios.ru.md',
    'framework-selection': 'methodology/framework-selection.ru.md',
}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def bounded_ids(values, limit=8):
    if len(values) > limit:
        raise ValueError(f'Request at most {limit} IDs per call; load the selected branch in smaller groups.')
    if len(set(values)) != len(values):
        raise ValueError('Duplicate IDs in request.')
    return values


class Specification:
    def __init__(self, workspace, platform_repo):
        self.root = Path(workspace).expanduser().resolve()
        self.platform_repo = Path(platform_repo).expanduser().resolve() if platform_repo else None
        self.base = self.root / 'methodology'
        self.cache = {}
        if not (self.base / 'core-rules.json').is_file():
            raise ValueError(f'Methodology workspace unavailable: {self.root}; expected methodology/core-rules.json.')

    def load(self, filename):
        if filename not in self.cache:
            self.cache[filename] = read_json(self.base / filename)
        return self.cache[filename]

    def origin(self, filename):
        return {'path': str(self.base / filename), 'sha256': sha256(self.base / filename)}

    def registry(self):
        result = {}
        for filename, key in CATALOGS.values():
            for item in self.load(filename)[key]:
                if item['id'] in result:
                    raise ValueError(f'Duplicate canonical ID: {item["id"]}')
                result[item['id']] = (filename, item)
        return result

    def get(self, ids):
        registry = self.registry()
        missing = [identifier for identifier in bounded_ids(ids) if identifier not in registry]
        if missing:
            raise ValueError('Unknown canonical IDs: ' + ', '.join(missing))
        return [dict(id=identifier, catalog=self.origin(registry[identifier][0]), record=registry[identifier][1])
                for identifier in ids]

    def catalog(self, category):
        filename, key = CATALOGS[category]
        result = []
        for item in self.load(filename)[key]:
            row = {'id': item['id'], 'name': item.get('name', item.get('title', item.get('requirement')))}
            for field in ('gate', 'severity', 'applies_when', 'scopes', 'scope', 'domains'):
                if field in item:
                    row[field] = item[field]
            result.append(row)
        return {'catalog': self.origin(filename), 'items': result}

    def selector(self, category):
        filename = CATALOGS[category][0]
        data = self.load(filename)
        value = data['shared'] if category == 'profiles' else data['selector']
        return {'catalog': self.origin(filename), 'selector': value}

    def bindings(self, ids):
        data = self.load('platform-bindings.json')
        registry = {item['activity_id']: item for item in data['bindings']}
        missing = [identifier for identifier in bounded_ids(ids) if identifier not in registry]
        if missing:
            raise ValueError('No platform bindings for: ' + ', '.join(missing))
        checks = {}
        for key, filename in [('activities', 'activities.json'), ('platform_requirements', 'platform-requirements.json')]:
            expected = data.get('reference_sha256', {}).get(key)
            checks[key] = 'unchanged' if expected == sha256(self.base / filename) else 'changed_or_untracked'
        return {'catalog': self.origin('platform-bindings.json'), 'reference_freshness': checks,
                'mapping_status': data['mapping_status'],
                'global_requirements': data['global_requirements'],
                'conditional_requirements': data['conditional_requirements'],
                'format_definitions': data['format_definitions'],
                'bindings': [registry[identifier] for identifier in ids]}

    def source(self, ids):
        index = {item['id']: item for item in read_json(self.root / 'research/rule-index.json')}
        missing = [identifier for identifier in bounded_ids(ids, 3) if identifier not in index]
        if missing:
            raise ValueError('Unknown source card IDs: ' + ', '.join(missing))
        result = []
        for identifier in ids:
            item = index[identifier]
            path = self.root / item['notes_file']
            lines = path.read_text(encoding='utf-8').splitlines()
            start = item['line'] - 1
            if start < 0 or start >= len(lines) or identifier not in lines[start]:
                raise ValueError(f'Stale source locator: {identifier} at {path}:{item["line"]}.')
            heading = re.match(r'^(#{1,6})\s', lines[start])
            end = start + 1
            if heading:
                level = len(heading[1])
                end = len(lines)
                for cursor in range(start + 1, len(lines)):
                    next_heading = re.match(r'^(#{1,6})\s', lines[cursor])
                    if next_heading and len(next_heading[1]) <= level:
                        end = cursor
                        break
            result.append({'id': identifier, 'notes_file': str(path), 'line': start + 1,
                           'last_line': end, 'note_sha256': sha256(path),
                           'note_context': '\n'.join(lines[:min(start, 14)]),
                           'card_text': '\n'.join(lines[start:end]).rstrip(),
                           'verification_scope': 'Reads the source card; original media have not been reverified by this command.'})
        return result

    def platform_check(self, ids):
        data = self.load('platform-requirements.json')
        records = {item['id']: item for item in data['requirements']}
        missing = [identifier for identifier in bounded_ids(ids) if identifier not in records]
        if missing:
            raise ValueError('Unknown platform requirements: ' + ', '.join(missing))
        if self.platform_repo is None:
            return {'repository': None, 'verification_status': 'not_configured', 'runtime_verified': False,
                    'all_selected_evidence_unchanged': False, 'requirements': ids, 'files': [],
                    'meaning': 'The bundle contains a recorded capability specification, not platform source code. Set --platform-repo or RISE_MATERIALS_PLATFORM_REPO for fresh local-file verification; otherwise keep runtime/current-code claims unverified.'}
        snapshot = data['source_snapshot']
        original_root = Path(snapshot['repository'])
        files = {}
        for identifier in ids:
            for evidence in records[identifier]['evidence']:
                original_path = Path(evidence['path'])
                try:
                    path = self.platform_repo / original_path.relative_to(original_root)
                except ValueError as error:
                    raise ValueError(f'Evidence lies outside recorded platform repository: {original_path}') from error
                key = str(path)
                if key not in files:
                    expected = snapshot['file_sha256'].get(str(original_path))
                    actual = sha256(path) if path.is_file() else None
                    status = 'missing' if actual is None else 'untracked' if expected is None else 'unchanged' if actual == expected else 'changed'
                    files[key] = {'path': key, 'status': status, 'expected_sha256': expected,
                                  'actual_sha256': actual, 'requirements': [], 'recorded_lines': []}
                files[key]['requirements'].append(identifier)
                files[key]['recorded_lines'].append(evidence['line'])
        return {'repository': str(self.platform_repo), 'recorded_head': snapshot['head'],
                'basis': snapshot['read_basis'], 'runtime_verified': False,
                'all_selected_evidence_unchanged': all(item['status'] == 'unchanged' for item in files.values()),
                'files': list(files.values()),
                'meaning': 'Unchanged confirms the recorded local-file basis only. Changed/missing evidence needs targeted review; none of these statuses proves production behavior.'}

    def status(self):
        last_validation = self.base / 'validation.json'
        report = read_json(last_validation) if last_validation.is_file() else {}
        return {'skill_name': 'rise-method', 'supported_clients': ['codex', 'claude-code'],
                'methodology_version': self.load('core-rules.json')['version'],
                'methodology_status': self.load('core-rules.json')['status'],
                'catalog_counts': {key: len(self.load(filename)[array]) for key, (filename, array) in CATALOGS.items()},
                'documents': {key: str(self.root / path) for key, path in DOCUMENTS.items()},
                'recorded_validation': {'path': str(last_validation), 'checked_at_utc': report.get('checked_at_utc'),
                                        'passed_at_that_time': report.get('passed'), 'fresh_validation_performed': False},
                'platform_repository': str(self.platform_repo) if self.platform_repo else None,
                'platform_runtime_verified_by_this_command': False,
                'bundle_manifest': str(self.root / 'bundle-manifest.json') if (self.root / 'bundle-manifest.json').is_file() else None,
                'note': 'Uses the selected local workspace or the bundled methodological snapshot. Original textbooks, recordings and platform source code are not part of the public bundle.'}


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument('--workspace', help='Canonical Teaching skills workspace; overrides env/config.')
    root.add_argument('--platform-repo', help='Speaking_livekit checkout; overrides env/config.')
    commands = root.add_subparsers(dest='command', required=True)
    commands.add_parser('status')
    commands.add_parser('catalog').add_argument('category', choices=list(CATALOGS))
    commands.add_parser('selector').add_argument('category', choices=['profiles', 'frameworks', 'activities'])
    for name in ['get', 'bindings', 'source', 'platform-check']:
        commands.add_parser(name).add_argument('ids', nargs='+')
    commands.add_parser('checks').add_argument('--gate', required=True, choices=['authoring', 'runtime', 'post_pilot'])
    commands.add_parser('text').add_argument('document', choices=list(DOCUMENTS))
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        config = read_json(SKILL_DIR / 'references/workspace.json')
        workspace = args.workspace or os.environ.get('RISE_METHOD_WORKSPACE') or os.environ.get('RISE_MATERIALS_WORKSPACE') or config.get('methodology_workspace') or SKILL_DIR / 'references/basis'
        platform_repo = args.platform_repo or os.environ.get('RISE_METHOD_PLATFORM_REPO') or os.environ.get('RISE_MATERIALS_PLATFORM_REPO') or config.get('platform_repository')
        spec = Specification(workspace, platform_repo)
        if args.command == 'status':
            data = spec.status()
        elif args.command == 'catalog':
            data = spec.catalog(args.category)
        elif args.command == 'selector':
            data = spec.selector(args.category)
        elif args.command == 'get':
            data = spec.get(args.ids)
        elif args.command == 'bindings':
            data = spec.bindings(args.ids)
        elif args.command == 'source':
            data = spec.source(args.ids)
        elif args.command == 'platform-check':
            data = spec.platform_check(args.ids)
        elif args.command == 'checks':
            data = spec.catalog('checks')
            data['items'] = [row for row in data['items'] if row['gate'] == args.gate]
        else:
            path = spec.root / DOCUMENTS[args.document]
            data = {'path': str(path), 'sha256': sha256(path), 'text': path.read_text(encoding='utf-8')}
        print(json.dumps({'workspace': str(spec.root), 'data': data}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
