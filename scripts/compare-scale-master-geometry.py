"""Blender pre-bake coverage gate. Does not modify or export geometry.

blender -b --python scripts/compare-scale-master-geometry.py -- canonical.glb reference.glb output.json
Bounding-box/triangle-count equality is a necessary coverage check, not a complete UV or visual approval.
"""
import hashlib
import json
import pathlib
import sys

import bpy

FACES = ['ASSENTO', 'ENCOSTO_FRONTAL', 'ENCOSTO_LATERAL', 'ENCOSTO_TRASEIRO',
         'LATERAL_EXTERNA', 'LATERAL_INTERNA', 'LATERAL_REAR', 'LATERAL_TOP']


def inspect(filename):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(filename.resolve()))
    current = {}
    for name in FACES:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH':
            raise RuntimeError(f'Official mesh missing: {name}')
        coords = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        obj.data.calc_loop_triangles()
        current[name] = {
            'vertices': len(obj.data.vertices),
            'triangles': len(obj.data.loop_triangles),
            'world_min': [min(c[i] for c in coords) for i in range(3)],
            'world_max': [max(c[i] for c in coords) for i in range(3)],
        }
    return current


def main():
    canonical_path, reference_path, output = map(pathlib.Path, sys.argv[sys.argv.index('--') + 1:])
    canonical = inspect(canonical_path)
    reference = inspect(reference_path)
    tolerance = 0.0001
    mismatches = []
    for name in FACES:
        c, r = canonical[name], reference[name]
        bounds_equal = all(abs(c[k][i] - r[k][i]) <= tolerance
                           for k in ('world_min', 'world_max') for i in range(3))
        if c['triangles'] != r['triangles'] or not bounds_equal:
            mismatches.append(name)
    report = {
        'schema': 'karv.scale-master-geometry-preflight/1',
        'blender_version': bpy.app.version_string,
        'canonical_sha256': hashlib.sha256(canonical_path.read_bytes()).hexdigest(),
        'reference_sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        'bounds_tolerance_m': tolerance,
        'canonical': canonical, 'reference': reference,
        'mismatched_faces': mismatches,
        'status': 'blocked_geometry_coverage' if mismatches else 'coverage_check_passed',
        'note': 'Coverage check only; passing does not approve geometry correspondence, UVs or appearance.',
    }
    output.write_text(json.dumps(report, indent=2) + '\n')
    if mismatches:
        raise RuntimeError('Bake blocked: geometry coverage differs: ' + ', '.join(mismatches))


if __name__ == '__main__':
    main()
