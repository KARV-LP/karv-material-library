"""Prepare lossless source copies, never runtime assets. Requires Pillow.

Usage: python scripts/prepare-maia-10-vinho.py INPUT_DIR OUTPUT_DIR
INPUT_DIR contains reference.glb and the eight original PNGs from issue #17.
"""
import copy
import hashlib
import io
import json
import pathlib
import struct
import sys

from PIL import Image

FACES = {
    'ASSENTO': ('ASSENTO.png', 'Assento.webp'),
    'ENCOSTO_FRONTAL': ('ENCOSTO FRONTAL.png', 'ENCOSTO_FRONTAL.webp'),
    'ENCOSTO_LATERAL': ('ENCOSTO LATERAL.png', 'ENCOSTO_LATERAL.webp'),
    'ENCOSTO_TRASEIRO': ('ENCOSTO TRASEITO.png', 'ENCOSTO_TRASEIRO.webp'),
    'LATERAL_EXTERNA': ('LATERAL EXTERNA.png', 'LATERAL_EXTERNA.webp'),
    'LATERAL_INTERNA': ('LATERAL INTERNA.png', 'LATERAL_INTERNA.webp'),
    'LATERAL_REAR': ('LATERAL REAR.png', 'LATERAL_REAR.webp'),
    'LATERAL_TOP': ('LATERAL SUPERIOR.png', 'LATERAL_TOP.webp'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    source, output = map(pathlib.Path, sys.argv[1:])
    output.mkdir(parents=True, exist_ok=True)
    original = (source / 'reference.glb').read_bytes()
    assert original[:4] == b'glTF' and struct.unpack_from('<I', original, 4)[0] == 2
    n = struct.unpack_from('<I', original, 12)[0]
    gltf = json.loads(original[20:20+n])
    assert original[24+n:28+n] == b'BIN\0'
    binary = bytearray(original[28+n:])
    original_structure = copy.deepcopy(gltf)
    meshes = {mesh['name']: mesh for mesh in gltf['meshes']}
    rows = []
    seen = set()
    for mesh_name, (png_name, webp_name) in FACES.items():
        mesh = meshes[mesh_name]
        assert len(mesh['primitives']) == 1
        primitive = mesh['primitives'][0]
        base = gltf['materials'][primitive['material']]['pbrMetallicRoughness']['baseColorTexture']
        assert not base.get('extensions', {}).get('KHR_texture_transform')
        texture = gltf['textures'][base['index']]
        image_index = texture['source']
        assert image_index not in seen, 'Ambiguous shared face image'
        seen.add(image_index)
        img = gltf['images'][image_index]
        assert img['mimeType'] == 'image/png' and 'uri' not in img
        view = gltf['bufferViews'][img['bufferView']]
        start = view.get('byteOffset', 0)
        png = (source / png_name).read_bytes()
        assert png == binary[start:start+view['byteLength']], png_name
        im = Image.open(io.BytesIO(png))
        rgba = im.convert('RGBA')
        target = output / webp_name
        rgba.save(target, format='WEBP', lossless=True, exact=True, method=6)
        encoded = target.read_bytes()
        decoded = Image.open(io.BytesIO(encoded)).convert('RGBA')
        assert decoded.size == rgba.size
        assert decoded.tobytes() == rgba.tobytes(), webp_name
        assert decoded.getchannel('A').tobytes() == rgba.getchannel('A').tobytes()
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(encoded)
        img['bufferView'] = len(gltf['bufferViews'])
        img['mimeType'] = 'image/webp'
        gltf['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(encoded)})
        # All references to this face image, including piping, use the same lossless copy.
        for tex in gltf['textures']:
            if tex.get('source') == image_index:
                del tex['source']
                tex.setdefault('extensions', {})['EXT_texture_webp'] = {'source': image_index}
        rows.append({'mesh_name': mesh_name, 'source_file': png_name,
                     'output_file': webp_name, 'width_px': rgba.width, 'height_px': rgba.height,
                     'source_bytes': len(png), 'output_bytes': len(encoded),
                     'source_sha256': sha(png), 'output_sha256': sha(encoded),
                     'decoded_rgba_sha256': sha(rgba.tobytes()),
                     'pixels_equal': True, 'alpha_equal': True, 'dimensions_equal': True})
    for key in ('meshes', 'nodes', 'accessors', 'materials', 'scenes'):
        assert gltf.get(key) == original_structure.get(key), key
    for key in ('extensionsUsed', 'extensionsRequired'):
        gltf.setdefault(key, [])
        if 'EXT_texture_webp' not in gltf[key]:
            gltf[key].append('EXT_texture_webp')
    gltf['buffers'][0]['byteLength'] = len(binary)
    while len(binary) % 4:
        binary.append(0)
    js = json.dumps(gltf, separators=(',', ':'), ensure_ascii=False).encode()
    js += b' ' * ((-len(js)) % 4)
    technical = (struct.pack('<4sII', b'glTF', 2, 28+len(js)+len(binary))
                 + struct.pack('<I4s', len(js), b'JSON') + js
                 + struct.pack('<I4s', len(binary), b'BIN\0') + binary)
    (output / 'reference.glb').write_bytes(technical)
    report = {'schema': 'karv.lossless-conversion/1', 'material_id_candidate': 'fabric-kv-010',
              'authorization': 'User explicitly authorized PNG to WebP lossless conversion on 2026-10-29, including a technical GLB copy.',
              'source_glb_sha256': sha(original), 'technical_glb_sha256': sha(technical),
              'geometry_uv_materials_nodes_unchanged': True, 'source_glb_preserved': True,
              'faces': rows}
    (output / 'conversion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    assert (source / 'reference.glb').read_bytes() == original
    print(f'PASS: {len(rows)} lossless copies, identical RGBA/alpha/dimensions; source GLB unchanged')


if __name__ == '__main__':
    main()
