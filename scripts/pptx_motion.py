#!/usr/bin/env python3
"""Inspect PPTX content and apply native transitions and click-to-appear steps.

Requires lxml, available in the Codex bundled presentation Python runtime.
Works on a new output copy. Checks package structure, not application playback.
"""
import argparse
import json
import posixpath
from pathlib import Path
from urllib.parse import unquote
from zipfile import ZipFile

from lxml import etree as E

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MC = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
NS = {'p': P, 'a': A, 'mc': MC}


def parse(data):
    return E.fromstring(data, E.XMLParser(resolve_entities=False, no_network=True))


def el(parent, tag, **attrs):
    return E.SubElement(parent, '{' + P + '}' + tag,
                        **{key: str(value) for key, value in attrs.items()})


def slide_parts(z):
    root = parse(z.read('ppt/presentation.xml'))
    rels = parse(z.read('ppt/_rels/presentation.xml.rels'))
    mapping = {r.get('Id'): r for r in rels}
    result = []
    for item in root.findall('p:sldIdLst/p:sldId', NS):
        rel = mapping[item.get('{' + R + '}id')]
        if rel.get('TargetMode') == 'External':
            raise ValueError('External slide relationship is unsupported')
        target = unquote(rel.get('Target'))
        part = posixpath.normpath(target.lstrip('/') if target.startswith('/')
                                 else posixpath.join('ppt', target))
        if part.startswith('../') or part not in z.namelist():
            raise ValueError('Unresolvable slide relationship: ' + target)
        result.append(part)
    return result


def objects(root):
    result = []
    for node in root.findall('.//p:cNvPr', NS):
        parent = node.getparent().getparent()
        if parent.tag == '{' + P + '}spTree':
            continue
        result.append({'id': node.get('id'), 'name': node.get('name'),
                       'type': E.QName(parent).localname})
    return result


def inspect(path):
    rows = []
    with ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        for index, part in enumerate(slide_parts(z), 1):
            root = parse(z.read(part))
            transitions = root.findall('.//p:transition', NS)
            rows.append({
                'slide': index, 'part': part,
                'text_chars': sum(len(n.text or '') for n in root.findall('.//a:t', NS)),
                'text_shapes': len(root.findall('.//p:sp/p:txBody', NS)),
                'pictures': len(root.findall('.//p:pic', NS)),
                'transitions': [[E.QName(c).localname for c in t] for t in transitions],
                'has_timing': bool(root.findall('.//p:timing', NS)),
                'click_effects': len(root.xpath('.//p:cTn[@nodeType="clickEffect"]', namespaces=NS)),
                'targets': root.xpath('.//p:timing//p:spTgt/@spid', namespaces=NS),
                'objects': objects(root),
            })
    return {'slides': rows, 'playback_verified': False}


def insert_ordered(root, child, before):
    index = next((i for i, c in enumerate(root)
                  if c.tag in {'{' + P + '}' + name for name in before}), len(root))
    root.insert(index, child)


def transition(root, spec):
    if root.xpath('./mc:AlternateContent//p:transition', namespaces=NS):
        raise ValueError('Existing alternate-content transition: use a native application')
    effect = spec.get('effect', 'fade')
    speed = spec.get('speed', 'med')
    if effect not in {'fade', 'push', 'wipe', 'cut'} or speed not in {'slow', 'med', 'fast'}:
        raise ValueError('Unsupported transition effect or speed')
    for old in root.findall('p:transition', NS):
        root.remove(old)
    node = E.Element('{' + P + '}transition', spd=speed, advClick='1')
    attrs = {}
    if effect in {'push', 'wipe'}:
        direction = spec.get('direction', 'l')
        if direction not in {'l', 'r', 'u', 'd'}:
            raise ValueError('Invalid direction')
        attrs['dir'] = direction
    el(node, effect, **attrs)
    insert_ordered(root, node, ['timing', 'extLst'])


def resolve_steps(root, steps):
    found = objects(root)
    resolved, used = [], set()
    if not isinstance(steps, list) or not steps:
        raise ValueError('reveals must contain at least one click step')
    for step in steps:
        if not isinstance(step, list) or not step:
            raise ValueError('Each click step must contain object names or id:N selectors')
        ids = []
        for selector in step:
            if not isinstance(selector, str):
                raise ValueError('Object selectors must be strings')
            matches = [o for o in found if (o['id'] == selector[3:] if selector.startswith('id:')
                                           else o['name'] == selector)]
            if len(matches) != 1:
                raise ValueError('Missing or ambiguous object: ' + selector)
            sid = matches[0]['id']
            if sid in used:
                raise ValueError('An object cannot appear in multiple reveal steps: ' + selector)
            used.add(sid)
            ids.append(sid)
        resolved.append(ids)
    # Animating a group and one of its descendants is ambiguous.
    for group in root.findall('.//p:grpSp', NS):
        ids = set(group.xpath('.//p:cNvPr/@id', namespaces=NS))
        own = group.find('p:nvGrpSpPr/p:cNvPr', NS)
        if own is not None and own.get('id') in used and len(ids & used) > 1:
            raise ValueError('Choose a group or its children, not both')
    return resolved


def reveals(root, steps):
    if root.findall('.//p:timing', NS):
        raise ValueError('Existing timing would be overwritten; edit it in the native application')
    steps = resolve_steps(root, steps)
    node = E.Element('{' + P + '}timing')
    counter = iter(range(1, 1000000))

    def time(parent, **attrs):
        return el(parent, 'cTn', id=next(counter), **attrs)

    def start(parent, delay):
        el(el(parent, 'stCondLst'), 'cond', delay=delay)

    top = time(el(el(node, 'tnLst'), 'par'), dur='indefinite', restart='never', nodeType='tmRoot')
    seq = el(el(top, 'childTnLst'), 'seq', concurrent='1', nextAc='seek')
    main = time(seq, dur='indefinite', nodeType='mainSeq')
    children = el(main, 'childTnLst')
    for ids in steps:
        click = time(el(children, 'par'), fill='hold')
        start(click, 'indefinite')
        group = time(el(el(click, 'childTnLst'), 'par'), fill='hold')
        start(group, '0')
        effects = el(group, 'childTnLst')
        for offset, sid in enumerate(ids):
            effect = time(el(effects, 'par'), presetID='1', presetClass='entr',
                          presetSubtype='0', fill='hold',
                          nodeType='clickEffect' if offset == 0 else 'withEffect')
            start(effect, '0')
            action = el(el(effect, 'childTnLst'), 'set')
            behavior = el(action, 'cBhvr')
            behavior_time = time(behavior, dur='1', fill='hold')
            start(behavior_time, '0')
            el(el(behavior, 'tgtEl'), 'spTgt', spid=sid)
            el(el(behavior, 'attrNameLst'), 'attrName').text = 'style.visibility'
            el(el(action, 'to'), 'strVal', val='visible')
    for name, event in [('prevCondLst', 'onPrev'), ('nextCondLst', 'onNext')]:
        cond = el(el(seq, name), 'cond', evt=event, delay='0')
        el(el(cond, 'tgtEl'), 'sldTgt')
    insert_ordered(root, node, ['extLst'])


def apply(source, output, plan):
    source, output = Path(source), Path(output)
    if output.exists() or source.resolve() == output.resolve():
        raise ValueError('Use a new output filename; source is never overwritten')
    if set(plan) - {'transitions', 'reveals'}:
        raise ValueError('Unknown plan key')
    changes = {}
    with ZipFile(source) as z:
        parts = slide_parts(z)
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError('Duplicate ZIP entries')
        for section in ('transitions', 'reveals'):
            for page in plan.get(section, {}):
                if not str(page).isdigit() or not 1 <= int(page) <= len(parts):
                    raise ValueError('Invalid slide number: ' + str(page))
        for index, part in enumerate(parts, 1):
            page = str(index)
            if page not in plan.get('transitions', {}) and page not in plan.get('reveals', {}):
                continue
            root = parse(z.read(part))
            if page in plan.get('transitions', {}):
                transition(root, plan['transitions'][page])
            if page in plan.get('reveals', {}):
                reveals(root, plan['reveals'][page])
            changes[part] = E.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as stream, ZipFile(stream, 'w') as dest:
            dest.comment = z.comment
            for item in z.infolist():
                dest.writestr(item, changes.get(item.filename, z.read(item.filename)))
    report = inspect(output)
    for page, steps in plan.get('reveals', {}).items():
        row = report['slides'][int(page) - 1]
        if row['click_effects'] != len(steps):
            raise ValueError('Written animation step count does not match plan')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inspect', 'apply'])
    parser.add_argument('input')
    parser.add_argument('--output')
    parser.add_argument('--plan')
    parser.add_argument('--require-images', action='store_true')
    parser.add_argument('--require-reveals', action='store_true')
    parser.add_argument('--require-transitions', action='store_true')
    args = parser.parse_args()
    if args.action == 'apply':
        if not args.plan or not args.output:
            parser.error('apply requires --plan and --output')
        report = apply(args.input, args.output, json.loads(Path(args.plan).read_text(encoding='utf-8')))
    else:
        report = inspect(args.input)
    rows = report['slides']
    errors = []
    if args.require_images and not any(r['pictures'] for r in rows):
        errors.append('No embedded picture objects; image generation provenance still needs manual review')
    if args.require_reveals and not any(r['click_effects'] for r in rows):
        errors.append('No click-to-reveal animations')
    if args.require_transitions and (len(rows) < 2 or any(not r['transitions'] for r in rows[1:])):
        errors.append('Missing transitions on non-cover slides, or deck has fewer than two slides')
    report['errors'] = errors
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
