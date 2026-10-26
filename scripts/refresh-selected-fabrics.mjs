import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import sharp from 'sharp';

const ROOT = process.cwd();
const ASSETS = path.join(ROOT, 'public/v1/assets');
const CATALOG = path.join(ROOT, 'public/v1/catalog.json');
const FABRIC_ID = 'fabric-kv-005';

const SOURCES = {
  'Assento.webp': '1uQHHQ39fX0TuqSaJdZessbsx_VtY47jy',
  'ENCOSTO_FRONTAL.webp': '1-P5cH8DmmoU6AljJA6n3rvm0YOTZ-L_m',
  'ENCOSTO_LATERAL.webp': '1RlYLBAFgd7sDRBwM7_Si-5qeGO7oNz9n',
  'ENCOSTO_TRASEIRO.webp': '1ZPHBlvNIF66TMOi1xMnopJ7uL3Xo16jR',
  'LATERAL_EXTERNA.webp': '1M7iw3XQUNabSFmes1adLVxNNuSCRjG7-',
  'LATERAL_INTERNA.webp': '1G36w7m8Uwytwsg83fgbJyuyzwz0RnlZt',
  'LATERAL_REAR.webp': '16r_RaDNkUEWKGMdafiOZ4YyyDy5XCVIE',
  'LATERAL_TOP.webp': '1YS1EjvOY73p4ou78Br7Vg53GIx_MklOg',
};

const FACES = [
  ['Assento.webp', 'seat', ['seat']],
  ['ENCOSTO_FRONTAL.webp', 'backrest-front', ['backrest-front']],
  ['ENCOSTO_LATERAL.webp', 'backrest-side', ['backrest-side']],
  ['ENCOSTO_TRASEIRO.webp', 'backrest-rear', ['backrest-rear']],
  ['LATERAL_EXTERNA.webp', 'side-outer', ['side-outer']],
  ['LATERAL_INTERNA.webp', 'side-inner', ['side-inner']],
  ['LATERAL_REAR.webp', 'side-rear', ['side-rear']],
  ['LATERAL_TOP.webp', 'side-top', ['side-top']],
];

const MAX_EDGE = 2048;
const WEBP_QUALITY = 90;
const NORMAL_STRENGTH = 2.25;
const AO_STRENGTH = 0.65;

function sha256(buf) {
  return createHash('sha256').update(buf).digest('hex');
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

async function downloadDrive(fileId) {
  const url = `https://drive.usercontent.google.com/download?id=${encodeURIComponent(fileId)}&export=download&confirm=t`;
  const res = await fetch(url, { redirect: 'follow' });
  if (!res.ok) throw new Error(`Drive download failed ${fileId}: HTTP ${res.status}`);
  const type = res.headers.get('content-type') || '';
  const buf = Buffer.from(await res.arrayBuffer());
  if (type.includes('text/html') || buf.subarray(0, 32).toString('utf8').includes('<!DOCTYPE')) {
    throw new Error(`Drive returned HTML instead of image for ${fileId}`);
  }
  return buf;
}

async function optimizedWebp(input) {
  const img = sharp(input, { failOn: 'error' });
  const meta = await img.metadata();
  const longest = Math.max(meta.width || 0, meta.height || 0);
  let pipeline = img;
  if (longest > MAX_EDGE) {
    pipeline = pipeline.resize({
      width: meta.width >= meta.height ? MAX_EDGE : undefined,
      height: meta.height > meta.width ? MAX_EDGE : undefined,
      fit: 'inside',
      withoutEnlargement: true,
    });
  }
  return pipeline.webp({ quality: WEBP_QUALITY, alphaQuality: 100, smartSubsample: false }).toBuffer();
}

function luminance(raw, channels, pixel) {
  const i = pixel * channels;
  return raw[i] * 0.2126 + raw[i + 1] * 0.7152 + raw[i + 2] * 0.0722;
}

function sample(raw, width, height, channels, x, y) {
  const cx = Math.max(0, Math.min(width - 1, x));
  const cy = Math.max(0, Math.min(height - 1, y));
  return luminance(raw, channels, cy * width + cx) / 255;
}

function generateMaps(raw, width, height, channels) {
  const normal = Buffer.alloc(width * height * 4);
  const ao = Buffer.alloc(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const px = y * width + x;
      const left = sample(raw, width, height, channels, x - 1, y);
      const right = sample(raw, width, height, channels, x + 1, y);
      const top = sample(raw, width, height, channels, x, y - 1);
      const bottom = sample(raw, width, height, channels, x, y + 1);
      const dx = (right - left) * NORMAL_STRENGTH;
      const dy = (bottom - top) * NORMAL_STRENGTH;
      const inv = 1 / Math.hypot(dx, dy, 1);
      const o = px * 4;
      normal[o] = Math.round((-dx * inv * 0.5 + 0.5) * 255);
      normal[o + 1] = Math.round((-dy * inv * 0.5 + 0.5) * 255);
      normal[o + 2] = Math.round((inv * 0.5 + 0.5) * 255);
      normal[o + 3] = channels === 4 ? raw[px * channels + 3] : 255;

      const center = sample(raw, width, height, channels, x, y);
      const neighbors = (left + right + top + bottom) / 4;
      const occ = Math.max(0, neighbors - center);
      const value = Math.round(Math.max(0, Math.min(1, 1 - occ * AO_STRENGTH)) * 255);
      ao[o] = ao[o + 1] = ao[o + 2] = value;
      ao[o + 3] = channels === 4 ? raw[px * channels + 3] : 255;
    }
  }
  return { normal, ao };
}

async function assetInfo(filePath, uri, expectedFormat) {
  const bytes = fs.readFileSync(filePath);
  const meta = await sharp(bytes).metadata();
  if (meta.format !== expectedFormat || !meta.width || !meta.height) throw new Error(`Invalid asset ${uri}`);
  return {
    uri,
    media_type: `image/${expectedFormat}`,
    sha256: sha256(bytes),
    width_px: meta.width,
    height_px: meta.height,
    bytes: bytes.byteLength,
  };
}

async function main() {
  const fabricRoot = path.join(ASSETS, FABRIC_ID);
  const faceRoot = path.join(fabricRoot, 'face-set');
  fs.rmSync(fabricRoot, { recursive: true, force: true });
  ensureDir(faceRoot);

  const optimized = {};
  for (const [name, id] of Object.entries(SOURCES)) {
    const raw = await downloadDrive(id);
    optimized[name] = await optimizedWebp(raw);
  }

  const faces = {};
  for (const [sourceName, key, surfaceIds] of FACES) {
    const source = optimized[sourceName];
    const dir = path.join(faceRoot, key);
    ensureDir(dir);
    const basePath = path.join(dir, 'base-color.webp');
    fs.writeFileSync(basePath, source);

    const decoded = await sharp(source).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    const maps = generateMaps(decoded.data, decoded.info.width, decoded.info.height, decoded.info.channels);

    const normalPath = path.join(dir, 'normal.png');
    const aoPath = path.join(dir, 'ao.webp');
    await sharp(maps.normal, { raw: { width: decoded.info.width, height: decoded.info.height, channels: 4 } })
      .png({ compressionLevel: 9, adaptiveFiltering: false }).toFile(normalPath);
    await sharp(maps.ao, { raw: { width: decoded.info.width, height: decoded.info.height, channels: 4 } })
      .webp({ quality: 90, alphaQuality: 100, smartSubsample: false }).toFile(aoPath);

    faces[key] = {
      source_filename: sourceName,
      surface_ids: surfaceIds,
      base_color: await assetInfo(basePath, `./${key}/base-color.webp`, 'webp'),
      normal: await assetInfo(normalPath, `./${key}/normal.png`, 'png'),
      ambient_occlusion: await assetInfo(aoPath, `./${key}/ao.webp`, 'webp'),
    };
  }

  const top = faces['side-top'];
  const pipingDir = path.join(faceRoot, 'piping');
  ensureDir(pipingDir);
  for (const filename of ['base-color.webp', 'normal.png', 'ao.webp']) {
    fs.copyFileSync(path.join(faceRoot, 'side-top', filename), path.join(pipingDir, filename));
  }
  faces.piping = {
    source_filename: 'LATERAL_TOP.webp',
    derivation: 'byte-copy-from-side-top',
    surface_ids: ['piping-seat', 'piping-backrest'],
    base_color: { ...top.base_color, uri: './piping/base-color.webp' },
    normal: { ...top.normal, uri: './piping/normal.png' },
    ambient_occlusion: { ...top.ambient_occlusion, uri: './piping/ao.webp' },
  };

  const thumbPath = path.join(faceRoot, 'thumbnail.webp');
  await sharp(optimized['Assento.webp'])
    .resize(512, 512, { fit: 'contain', position: 'centre', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .webp({ quality: 88, alphaQuality: 100, smartSubsample: false }).toFile(thumbPath);
  const thumbnail = await assetInfo(thumbPath, './thumbnail.webp', 'webp');

  const metadata = {
    schema: 'karv.fabric-face-set/1',
    fabric_id: FABRIC_ID,
    face_count: 9,
    map_count: 27,
    thumbnail: { source_face: 'seat', ...thumbnail },
    generation: {
      source_optimization: { max_edge_px: MAX_EDGE, format: 'webp', quality: WEBP_QUALITY },
      normal_convention: 'opengl',
      normal_strength: NORMAL_STRENGTH,
      ao_strength: AO_STRENGTH,
    },
    faces,
  };
  fs.writeFileSync(path.join(faceRoot, 'metadata.json'), JSON.stringify(metadata, null, 2) + '\n');

  fs.copyFileSync(thumbPath, path.join(fabricRoot, 'preview.webp'));
  fs.copyFileSync(path.join(faceRoot, 'seat', 'base-color.webp'), path.join(fabricRoot, 'base-color.webp'));
  fs.copyFileSync(path.join(faceRoot, 'seat', 'normal.png'), path.join(fabricRoot, 'normal.png'));
  fs.copyFileSync(path.join(faceRoot, 'seat', 'ao.webp'), path.join(fabricRoot, 'ao.webp'));

  const catalog = JSON.parse(fs.readFileSync(CATALOG, 'utf8'));
  catalog.materials = catalog.materials.filter((m) => ['fabric-kv-002', 'fabric-kv-004'].includes(m.id));

  const rootBase = await assetInfo(path.join(fabricRoot, 'base-color.webp'), './assets/fabric-kv-005/base-color.webp', 'webp');
  const rootNormal = await assetInfo(path.join(fabricRoot, 'normal.png'), './assets/fabric-kv-005/normal.png', 'png');
  const rootAo = await assetInfo(path.join(fabricRoot, 'ao.webp'), './assets/fabric-kv-005/ao.webp', 'webp');

  catalog.materials.push({
    id: FABRIC_ID,
    channel: 'fabric',
    name: 'Trieste 37 Linho Cinza Médio',
    collection: 'Trieste',
    color: { name: 'Cinza Médio', family: 'cinza' },
    material_type: 'tecido com aparência de linho',
    technologies: [],
    functional: {
      pet_friendly: null,
      water_repellency: null,
      easy_clean: null,
      indoor_use: true,
      outdoor_use: null,
    },
    appearance: {
      texture: 'trama de linho aparente',
      touch: null,
      sheen: 'baixo',
      visual_character: ['neutro', 'texturizado', 'contemporâneo', 'cinza'],
    },
    physical_reference_cm: { width: 120, height: 60 },
    assets: {
      preview: './assets/fabric-kv-005/preview.webp',
      base_color: './assets/fabric-kv-005/base-color.webp',
      normal: './assets/fabric-kv-005/normal.png',
      ao: './assets/fabric-kv-005/ao.webp',
    },
    face_set: './assets/fabric-kv-005/face-set/metadata.json',
    asset_integrity: {
      base_color: {
        sha256: rootBase.sha256,
        width_px: rootBase.width_px,
        height_px: rootBase.height_px,
        bytes: rootBase.bytes,
      },
      normal: {
        sha256: rootNormal.sha256,
        width_px: rootNormal.width_px,
        height_px: rootNormal.height_px,
        bytes: rootNormal.bytes,
      },
      ao: {
        sha256: rootAo.sha256,
        width_px: rootAo.width_px,
        height_px: rootAo.height_px,
        bytes: rootAo.bytes,
      },
    },
    pbr: {
      status: 'production',
      roughness_factor: 0.88,
      metalness: 0,
      normal_convention: 'opengl',
      normal_strength: 1,
      ao_strength: 1,
    },
    published: true,
    ready_for_configurator: true,
    pbr_ready: true,
    compatibility: { geometry_ids: ['karv-chair'], min_geometry_version: 2 },
  });

  fs.rmSync(path.join(ASSETS, 'fabric-kv-001'), { recursive: true, force: true });
  fs.rmSync(path.join(ASSETS, 'fabric-kv-003'), { recursive: true, force: true });
  fs.writeFileSync(CATALOG, JSON.stringify(catalog, null, 2) + '\n');
}

await main();
