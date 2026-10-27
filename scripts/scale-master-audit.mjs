import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

const OFFICIAL = [
  ['seat', 'ASSENTO'],
  ['backrest-front', 'ENCOSTO_FRONTAL'],
  ['backrest-side', 'ENCOSTO_LATERAL'],
  ['backrest-rear', 'ENCOSTO_TRASEIRO'],
  ['side-outer', 'LATERAL_EXTERNA'],
  ['side-inner', 'LATERAL_INTERNA'],
  ['side-rear', 'LATERAL_REAR'],
  ['side-top', 'LATERAL_TOP'],
];

function sha256(buf) {
  return createHash('sha256').update(buf).digest('hex');
}

function parseGlb(filePath) {
  const bytes = fs.readFileSync(filePath);
  if (bytes.length < 20 || bytes.toString('ascii', 0, 4) !== 'glTF') {
    throw new Error('reference.glb inválido');
  }
  const version = bytes.readUInt32LE(4);
  if (version !== 2) throw new Error(`GLB versão ${version} não suportada`);
  const jsonLength = bytes.readUInt32LE(12);
  const jsonType = bytes.toString('ascii', 16, 20);
  if (jsonType !== 'JSON') throw new Error('chunk JSON ausente');
  const jsonStart = 20;
  const jsonEnd = jsonStart + jsonLength;
  const gltf = JSON.parse(bytes.subarray(jsonStart, jsonEnd).toString('utf8'));
  const binHeader = jsonEnd;
  const binLength = bytes.readUInt32LE(binHeader);
  const binType = bytes.toString('ascii', binHeader + 4, binHeader + 8);
  if (binType !== 'BIN\0') throw new Error('chunk BIN ausente');
  const binStart = binHeader + 8;
  const bin = bytes.subarray(binStart, binStart + binLength);
  return { bytes, gltf, bin };
}

function embeddedImage(gltf, bin, textureIndex) {
  const texture = gltf.textures?.[textureIndex];
  if (!texture) throw new Error(`texture ${textureIndex} ausente`);
  const source =
    texture.extensions?.EXT_texture_webp?.source ??
    texture.source;
  const image = gltf.images?.[source];
  if (!image) throw new Error(`image source ${source} ausente`);
  if (image.uri) {
    throw new Error('Scale Master V1 exige imagens embutidas no GLB');
  }
  const view = gltf.bufferViews?.[image.bufferView];
  if (!view) throw new Error(`bufferView da imagem ${image.name ?? source} ausente`);
  const start = view.byteOffset ?? 0;
  const data = bin.subarray(start, start + view.byteLength);
  return {
    name: image.name ?? null,
    mime_type: image.mimeType ?? null,
    bytes: data.length,
    sha256: sha256(data),
  };
}

function main() {
  const glbPath = process.argv[2];
  if (!glbPath) {
    console.error('Uso: node scripts/scale-master-audit.mjs <reference.glb> [output.json]');
    process.exit(2);
  }
  const outputPath = process.argv[3] ?? null;
  const { bytes, gltf, bin } = parseGlb(glbPath);
  const meshes = new Map((gltf.meshes ?? []).map((mesh) => [mesh.name, mesh]));
  const faces = {};

  for (const [faceKey, meshName] of OFFICIAL) {
    const mesh = meshes.get(meshName);
    if (!mesh) throw new Error(`${faceKey}: mesh ${meshName} ausente`);
    if (!Array.isArray(mesh.primitives) || mesh.primitives.length !== 1) {
      throw new Error(`${faceKey}: Scale Master V1 exige uma primitive por mesh`);
    }
    const primitive = mesh.primitives[0];
    const material = gltf.materials?.[primitive.material];
    const base = material?.pbrMetallicRoughness?.baseColorTexture;
    if (!base || typeof base.index !== 'number') {
      throw new Error(`${faceKey}: Base Color ausente no GLB de referência`);
    }
    const transform = base.extensions?.KHR_texture_transform;
    if (transform) {
      throw new Error(`${faceKey}: KHR_texture_transform não suportado na V1; faça bake no GLB antes`);
    }
    const uvSet = base.texCoord ?? 0;
    const uvAttr = `TEXCOORD_${uvSet}`;
    if (primitive.attributes?.[uvAttr] == null) {
      throw new Error(`${faceKey}: ${uvAttr} não existe na mesh ${meshName}`);
    }
    const image = embeddedImage(gltf, bin, base.index);
    if (image.mime_type !== 'image/webp') {
      throw new Error(`${faceKey}: Scale Master V1 exige Base Color WebP embutida`);
    }
    faces[faceKey] = {
      mesh_name: meshName,
      source_uv_set: uvSet,
      source_uv_attribute: uvAttr,
      requires_uv0_bake: uvSet !== 0,
      source_image: image,
    };
  }

  const report = {
    schema: 'karv.scale-master-audit/1',
    reference_glb: {
      file: path.basename(glbPath),
      bytes: bytes.length,
      sha256: sha256(bytes),
      generator: gltf.asset?.generator ?? null,
    },
    policy: {
      target_uv_set: 0,
      runtime_geometry_unchanged: true,
      runtime_uv_unchanged: true,
      ambiguous_mapping: 'fail',
    },
    faces,
  };

  const serialized = JSON.stringify(report, null, 2) + '\n';
  if (outputPath) fs.writeFileSync(outputPath, serialized);
  else process.stdout.write(serialized);
}

main();
