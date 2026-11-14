#!/usr/bin/env python3
"""Generate local, original primitive models; no network or mesh dependencies."""
from pathlib import Path
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[1]


def tag(parent, element_name, text=None, **attrs):
    child = E.SubElement(parent, element_name, attrs)
    if text is not None:
        child.text = str(text)
    return child


def shape(link, name, kind, size, pose, color, collision=True):
    for element in ('visual', 'collision') if collision else ('visual',):
        obj = tag(link, element, name=f'{name}_{element}')
        tag(obj, 'pose', pose)
        geom = tag(tag(obj, 'geometry'), kind)
        if kind == 'box':
            tag(geom, 'size', size)
        elif kind == 'sphere':
            tag(geom, 'radius', size)
        else:
            radius, length = size.split()
            tag(geom, 'radius', radius)
            tag(geom, 'length', length)
        if element == 'visual':
            mat = tag(obj, 'material')
            tag(mat, 'ambient', color)
            tag(mat, 'diffuse', color)


def model(parent, name, pose='0 0 0 0 0 0'):
    m = tag(parent, 'model', name=name)
    tag(m, 'static', 'true')
    tag(m, 'pose', pose)
    return tag(m, 'link', name='body')


def save(path, root):
    E.indent(root, space='  ')
    E.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def asset(name, build):
    directory = ROOT / 'models' / name
    directory.mkdir(parents=True, exist_ok=True)
    sdf = E.Element('sdf', version='1.10')
    build(model(sdf, name))
    save(directory / 'model.sdf', sdf)
    config = E.Element('model')
    tag(config, 'name', name)
    tag(config, 'version', '1.0')
    tag(config, 'sdf', 'model.sdf', version='1.10')
    tag(config, 'description', 'Original procedural static model for semantic-control simulation.')
    save(directory / 'model.config', config)


DARK = '0.025 0.03 0.04 1'
GLASS = '0.10 0.23 0.30 1'


def sedan(link):
    shape(link, 'body', 'box', '4.2 1.8 0.55', '0 0 0.65 0 0 0', '0.12 0.30 0.65 1')
    shape(link, 'cabin', 'box', '2.15 1.60 0.65', '-0.15 0 1.18 0 0 0', GLASS)
    shape(link, 'roof', 'box', '2.20 1.66 0.08', '-0.15 0 1.54 0 0 0', '0.10 0.25 0.55 1')
    for x in (-1.30, 1.30):
        for y in (-0.9, 0.9):
            shape(link, f'wheel_{x}_{y}', 'cylinder', '0.34 0.23', f'{x} {y} 0.35 1.570796 0 0', DARK)
            shape(link, f'hub_{x}_{y}', 'cylinder', '0.18 0.24', f'{x} {y} 0.35 1.570796 0 0', '0.6 0.62 0.65 1', False)
    for y in (-0.59, 0.59):
        shape(link, f'headlight_{y}', 'box', '0.04 0.38 0.20', f'2.12 {y} 0.72 0 0 0', '1 0.96 0.75 1', False)
        shape(link, f'taillight_{y}', 'box', '0.04 0.38 0.18', f'-2.12 {y} 0.72 0 0 0', '0.8 0.03 0.02 1', False)
    for y in (-0.815, 0.815):
        for x in (-1.1, -0.15, 0.8):
            shape(link, f'pillar_{x}_{y}', 'box', '0.08 0.04 0.63', f'{x} {y} 1.19 0 0 0', DARK, False)
        shape(link, f'mirror_{y}', 'box', '0.25 0.16 0.16', f'0.6 {y * 1.2} 1.12 0 0 0', DARK, False)
    shape(link, 'grille', 'box', '0.04 0.8 0.17', '2.13 0 0.52 0 0 0', DARK, False)
    shape(link, 'plate', 'box', '0.05 0.42 0.12', '-2.13 0 0.51 0 0 0', '0.95 0.95 0.95 1', False)


def person(link):
    skin = '0.65 0.43 0.30 1'
    shape(link, 'torso', 'box', '0.28 0.43 0.58', '0 0 1.12 0 0 0', '0.85 0.18 0.06 1')
    shape(link, 'neck', 'cylinder', '0.065 0.12', '0 0 1.46 0 0 0', skin)
    shape(link, 'head', 'sphere', '0.145', '0 0 1.65 0 0 0', skin)
    shape(link, 'hair', 'sphere', '0.14', '-0.025 0 1.71 0 0 0', DARK, False)
    shape(link, 'nose', 'sphere', '0.035', '0.14 0 1.65 0 0 0', skin, False)
    for y in (-0.12, 0.12):
        shape(link, f'leg_{y}', 'cylinder', '0.085 0.73', f'0 {y} 0.47 0 0 0', '0.07 0.12 0.22 1')
        shape(link, f'shoe_{y}', 'box', '0.30 0.18 0.12', f'0.06 {y} 0.07 0 0 0', DARK)
    for y in (-0.29, 0.29):
        shape(link, f'arm_{y}', 'cylinder', '0.065 0.50', f'0 {y} 1.13 0 0 0', '0.85 0.18 0.06 1')
        shape(link, f'hand_{y}', 'sphere', '0.07', f'0 {y} 0.84 0 0 0', skin)


def tree(link):
    shape(link, 'trunk', 'cylinder', '0.21 2.8', '0 0 1.4 0 0 0', '0.28 0.14 0.06 1')
    for i, (x, y, z, r) in enumerate(((0, 0, 3.6, 1.25), (-0.6, 0.2, 3.0, 0.95), (0.6, -0.3, 3.1, 1.0), (0, 0.3, 4.3, 0.85))):
        shape(link, f'crown_{i}', 'sphere', str(r), f'{x} {y} {z} 0 0 0', '0.12 0.36 0.08 1')


def main():
    for name, builder in (('demo_sedan', sedan), ('demo_person', person), ('demo_tree', tree)):
        asset(name, builder)
    sdf = E.Element('sdf', version='1.10')
    # Keep the existing world name so ros_gz_bridge.yaml also works with arena.sdf.
    world = tag(sdf, 'world', name='e2es_indoor')
    for system in ('Physics', 'UserCommands', 'SceneBroadcaster', 'Sensors'):
        filename = {'SceneBroadcaster': 'scene-broadcaster', 'UserCommands': 'user-commands'}.get(system, system.lower())
        plugin = tag(world, 'plugin', name=f'gz::sim::systems::{system}', filename=f'gz-sim-{filename}-system')
        if system == 'Sensors':
            tag(plugin, 'render_engine', 'ogre2')
    physics = tag(world, 'physics', name='physics', type='ignored')
    tag(physics, 'max_step_size', '0.001')
    tag(physics, 'real_time_factor', '1')
    tag(world, 'gravity', '0 0 -9.8')
    scene = tag(world, 'scene')
    tag(scene, 'ambient', '0.65 0.65 0.65 1')
    tag(scene, 'background', '0.65 0.80 0.94 1')
    tag(scene, 'shadows', 'true')
    sun = tag(world, 'light', name='sun', type='directional')
    tag(sun, 'pose', '0 0 15 0 0 0')
    tag(sun, 'diffuse', '0.9 0.9 0.85 1')
    tag(sun, 'specular', '0.2 0.2 0.2 1')
    tag(sun, 'direction', '-0.4 0.2 -0.9')
    tag(sun, 'cast_shadows', 'true')
    ground = model(world, 'park_ground')
    shape(ground, 'grass', 'box', '36 28 0.2', '0 0 -0.10 0 0 0', '0.28 0.43 0.18 1')
    road = model(world, 'road_and_parking')
    shape(road, 'road', 'box', '30 6 0.04', '0 0 0.02 0 0 0', '0.16 0.17 0.18 1')
    shape(road, 'parking', 'box', '18 6 0.04', '3 -6 0.02 0 0 0', '0.22 0.23 0.24 1')
    shape(road, 'sidewalk', 'box', '30 2.5 0.16', '0 4.25 0.08 0 0 0', '0.67 0.65 0.60 1')
    for x in range(-13, 15, 4):
        shape(road, f'lane_{x}', 'box', '1.8 0.12 0.01', f'{x} 0 0.045 0 0 0', '0.95 0.85 0.25 1', False)
    for x in range(-6, 14, 3):
        shape(road, f'bay_{x}', 'box', '0.10 5.5 0.01', f'{x} -6 0.045 0 0 0', '0.95 0.95 0.95 1', False)
    for y in (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5):
        shape(road, f'crossing_{y}', 'box', '2 0.5 0.01', f'0 {y} 0.05 0 0 0', '0.95 0.95 0.9 1', False)
    pad = model(world, 'takeoff_pad')
    shape(pad, 'base', 'box', '2 2 0.02', '-11 1.5 0.05 0 0 0', '0.12 0.35 0.65 1')
    for y in (1.05, 1.95):
        shape(pad, f'H_leg_{y}', 'box', '1.1 0.13 0.01', f'-11 {y} 0.065 0 0 0', '1 1 1 1', False)
    shape(pad, 'H_bar', 'box', '0.13 0.9 0.01', '-11 1.5 0.065 0 0 0', '1 1 1 1', False)
    placements = {
        'demo_sedan': [('car_road', '7 1.5 0.04 0 0 0'), ('car_park_1', '1.5 -6 0.04 0 0 1.570796'), ('car_park_2', '7.5 -6 0.04 0 0 1.570796')],
        'demo_person': [('person_crossing', '0 1.5 0.055 0 0 3.141593'), ('person_sidewalk', '-5 4.2 0.16 0 0 -1.570796'), ('person_parking', '4.5 -4 0.04 0 0 1.570796')],
        'demo_tree': [(f'tree_{i}', f'{x} {y} 0 0 0 0') for i, (x, y) in enumerate(((-10, 8), (-3, 8), (5, 8), (12, 8), (-10, -7)), 1)],
    }
    for asset_name, instances in placements.items():
        for name, pose in instances:
            inc = tag(world, 'include')
            tag(inc, 'uri', f'model://{asset_name}')
            tag(inc, 'name', name)
            tag(inc, 'pose', pose)
    save(ROOT / 'worlds' / 'semantic_outdoor.sdf', sdf)


if __name__ == '__main__':
    main()
