import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import sharp from 'sharp';

const ROOT = process.cwd();
const ASSETS = path.join(ROOT, 'public/v1/assets');
const CATALOG = path.join(ROOT, 'public/v1/catalog.json');
const FABRIC_ID = 'fabric-kv-009';

const SOURCES = {
  'Assento.webp': '1iTDcHcW6pHRWS7MoJ-8tLh4Quxew5It6',
  'ENCOSTO_FRONTAL.webp': '10cgfJzW3LgrXeNK7zrweErkoRguygfaa',
  'ENCOSTO_LATERAL.webp': '1S3pKoWbrlq2Ok51k7-MollCai4y5oI9R',
  'ENCOSTO_TRASEIRO.webp': '1kXzsCP_ewJ68LTJWf6E2l5V0mY8zYNfM',
  'LATERAL_EXTERNA.webp': '1YBUJQwMgK7SBMvVRKQlw9qCqIIItV8jo',
  'LATERAL_INTERNA.webp': '1w4Q2LiP_ehQaiJZUsUySksZ6YeEIvpbK',
  'LATERAL_REAR.webp': '1GNn85vChEt8pvrV07AE3xG9KukOo0bmM',
  'LATERAL_TOP.webp': '1QI6BKiuBfpEJIxYIiMV1lTgR_ViVHhyd',
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

const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');
const ensureDir = (dir) => fs.mkdirSync(dir, { recursive: true });

async function downloadDrive(id) {
  const url = `https://drive.usercontent.google.com/download?id=${encodeURIComponent(id)}&export=download&confirm=t`;
  const res = await fetch(url, { redirect: 'follow' });
  if (!res.ok) throw new Error(`Drive download failed ${id}: HTTP ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  const type = res.headers.get('content-type') || '';
  if (type.includes('text/html') || buf.subarray(0, 32).toString('utf8').includes('<!DOCTYPE')) {
    throw new Error(`Drive returned HTML for ${id}`);
  }
  return buf;
}

async function optimizeWebp(input) {
  const meta = await sharp(input, { failOn: 'error' }).metadata();
  let img = sharp(input, { failOn: 'error' });
  if (Math.max(meta.width || 0, meta.height || 0) > MAX_EDGE) {
    img = img.resize({
      width: meta.width >= meta.height ? MAX_EDGE : undefined,
      height: meta.height > meta.width ? MAX_EDGE : undefined,
      fit: 'inside',
      withoutEnlargement: true,
    });
  }
  return img.webp({ quality: WEBP_QUALITY, alphaQuality: 100, smartSubsample: false }).toBuffer();
}

function luminance(raw, channels, p) {
  const i = p * channels;
  return raw[i] * 0.2126 + raw[i + 1] * 0.7152 + raw[i + 2] * 0.0722;
}
function sample(raw, w, h, c, x, y) {
  const cx = Math.max(0, Math.min(w - 1, x));
  const cy = Math.max(0, Math.min(h - 1, y));
  return luminance(raw, c, cy * w + cx) / 255;
}
function maps(raw, w, h, c) {
  const normal = Buffer.alloc(w * h * 4);
  const ao = Buffer.alloc(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      const l = sample(raw, w, h, c, x - 1, y);
      const r = sample(raw, w, h, c, x + 1, y);
      const t = sample(raw, w, h, c, x, y - 1);
      const b = sample(raw, w, h, c, x, y + 1);
      const dx = (r - l) * NORMAL_STRENGTH;
      const dy = (b - t) * NORMAL_STRENGTH;
      const inv = 1 / Math.hypot(dx, dy, 1);
      const o = p * 4;
      normal[o] = Math.round((-dx * inv * 0.5 + 0.5) * 255);
      normal[o + 1] = Math.round((-dy * inv * 0.5 + 0.5) * 255);
      normal[o + 2] = Math.round((inv * 0.5 + 0.5) * 255);
      normal[o + 3] = c === 4 ? raw[p * c + 3] : 255;

      const center = sample(raw, w, h, c, x, y);
      const neighbors = (l + r + t + b) / 4;
      const value = Math.round(Math.max(0, Math.min(1, 1 - Math.max(0, neighbors - center) * AO_STRENGTH)) * 255);
      ao[o] = ao[o + 1] = ao[o + 2] = value;
      ao[o + 3] = c === 4 ? raw[p * c + 3] : 255;
    }
  }
  return { normal, ao };
}

async function assetInfo(filePath, uri, expected) {
  const bytes = fs.readFileSync(filePath);
  const m = await sharp(bytes).metadata();
  if (m.format !== expected || !m.width || !m.height) throw new Error(`Invalid asset ${uri}`);
  return { uri, media_type: `image/${expected}`, sha256: sha256(bytes), width_px: m.width, height_px: m.height, bytes: bytes.length };
}

async function main() {
  const root = path.join(ASSETS, FABRIC_ID);
  const faceRoot = path.join(root, 'face-set');
  fs.rmSync(root, { recursive: true, force: true });
  ensureDir(faceRoot);

  const source = {};
  for (const [name, id] of Object.entries(SOURCES)) source[name] = await optimizeWebp(await downloadDrive(id));

  const faces = {};
  for (const [sourceName, key, surfaceIds] of FACES) {
    const dir = path.join(faceRoot, key);
    ensureDir(dir);
    const base = path.join(dir, 'base-color.webp');
    fs.writeFileSync(base, source[sourceName]);
    const decoded = await sharp(source[sourceName]).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    const out = maps(decoded.data, decoded.info.width, decoded.info.height, decoded.info.channels);
    const normal = path.join(dir, 'normal.png');
    const ao = path.join(dir, 'ao.webp');
    await sharp(out.normal, { raw: { width: decoded.info.width, height: decoded.info.height, channels: 4 } }).png({ compressionLevel: 9, adaptiveFiltering: false }).toFile(normal);
    await sharp(out.ao, { raw: { width: decoded.info.width, height: decoded.info.height, channels: 4 } }).webp({ quality: 90, alphaQuality: 100, smartSubsample: false }).toFile(ao);
    faces[key] = {
      source_filename: sourceName,
      surface_ids: surfaceIds,
      base_color: await assetInfo(base, `./${key}/base-color.webp`, 'webp'),
      normal: await assetInfo(normal, `./${key}/normal.png`, 'png'),
      ambient_occlusion: await assetInfo(ao, `./${key}/ao.webp`, 'webp'),
    };
  }

  const pipingDir = path.join(faceRoot, 'piping');
  ensureDir(pipingDir);
  for (const f of ['base-color.webp', 'normal.png', 'ao.webp']) fs.copyFileSync(path.join(faceRoot, 'side-top', f), path.join(pipingDir, f));
  faces.piping = {
    source_filename: 'LATERAL_TOP.webp',
    derivation: 'byte-copy-from-side-top',
    surface_ids: ['piping-seat', 'piping-backrest'],
    base_color: { ...faces['side-top'].base_color, uri: './piping/base-color.webp' },
    normal: { ...faces['side-top'].normal, uri: './piping/normal.png' },
    ambient_occlusion: { ...faces['side-top'].ambient_occlusion, uri: './piping/ao.webp' },
  };

  const thumb = path.join(faceRoot, 'thumbnail.webp');
  await sharp(source['Assento.webp']).resize(512, 512, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } }).webp({ quality: 88, alphaQuality: 100, smartSubsample: false }).toFile(thumb);
  const thumbnail = await assetInfo(thumb, './thumbnail.webp', 'webp');

  fs.writeFileSync(path.join(faceRoot, 'metadata.json'), JSON.stringify({
    schema: 'karv.fabric-face-set/1',
    fabric_id: FABRIC_ID,
    face_count: 9,
    map_count: 27,
    thumbnail: { source_face: 'seat', ...thumbnail },
    generation: { source_optimization: { max_edge_px: MAX_EDGE, format: 'webp', quality: WEBP_QUALITY }, normal_convention: 'opengl', normal_strength: NORMAL_STRENGTH, ao_strength: AO_STRENGTH },
    faces,
  }, null, 2) + '\n');

  fs.copyFileSync(thumb, path.join(root, 'preview.webp'));
  fs.copyFileSync(path.join(faceRoot, 'seat', 'base-color.webp'), path.join(root, 'base-color.webp'));
  fs.copyFileSync(path.join(faceRoot, 'seat', 'normal.png'), path.join(root, 'normal.png'));
  fs.copyFileSync(path.join(faceRoot, 'seat', 'ao.webp'), path.join(root, 'ao.webp'));

  const rootBase = await assetInfo(path.join(root, 'base-color.webp'), './assets/fabric-kv-009/base-color.webp', 'webp');
  const rootNormal = await assetInfo(path.join(root, 'normal.png'), './assets/fabric-kv-009/normal.png', 'png');
  const rootAo = await assetInfo(path.join(root, 'ao.webp'), './assets/fabric-kv-009/ao.webp', 'webp');

  const catalog = JSON.parse(fs.readFileSync(CATALOG, 'utf8'));
  catalog.materials = catalog.materials.filter((m) => m.id !== FABRIC_ID);
  catalog.materials.push({
    id: FABRIC_ID,
    channel: 'fabric',
    name: 'Málaga 03',
    collection: 'Málaga',
    color: { name: '03', family: 'neutro' },
    material_type: 'tecido texturizado',
    technologies: [],
    functional: { pet_friendly: null, water_repellency: null, easy_clean: null, indoor_use: true, outdoor_use: null },
    appearance: { texture: 'trama texturizada', touch: null, sheen: 'baixo', visual_character: ['neutro', 'texturizado', 'sofisticado', 'contemporâneo'] },
    physical_reference_cm: { width: 120, height: 60 },
    assets: { preview: './assets/fabric-kv-009/preview.webp', base_color: './assets/fabric-kv-009/base-color.webp', normal: './assets/fabric-kv-009/normal.png', ao: './assets/fabric-kv-009/ao.webp' },
    face_set: './assets/fabric-kv-009/face-set/metadata.json',
    asset_integrity: {
      base_color: { sha256: rootBase.sha256, width_px: rootBase.width_px, height_px: rootBase.height_px, bytes: rootBase.bytes },
      normal: { sha256: rootNormal.sha256, width_px: rootNormal.width_px, height_px: rootNormal.height_px, bytes: rootNormal.bytes },
      ao: { sha256: rootAo.sha256, width_px: rootAo.width_px, height_px: rootAo.height_px, bytes: rootAo.bytes },
    },
    pbr: { status: 'production', roughness_factor: 0.88, metalness: 0, normal_convention: 'opengl', normal_strength: 1, ao_strength: 1 },
    published: true,
    ready_for_configurator: true,
    pbr_ready: true,
    compatibility: { geometry_ids: ['karv-chair'], min_geometry_version: 2 },
  });

  fs.writeFileSync(CATALOG, JSON.stringify(catalog, null, 2) + '\n');
}

await main();
