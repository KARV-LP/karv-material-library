import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const catalogPath = path.join(root, 'public/v1/catalog.json');
const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));

const forbiddenKeys = new Set(['supplier', 'reference', 'cost', 'sources', 'research']);
const forbiddenText = ['wiler'];
const PBR_TEXTURE_BUDGET_BYTES = 3.5 * 1024 * 1024;

function assertNoPrivateData(value, trail = 'catalog') {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => assertNoPrivateData(entry, `${trail}[${index}]`));
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    if (forbiddenKeys.has(key)) throw new Error(`${trail}: chave privada no contrato público: ${key}`);
    assertNoPrivateData(child, `${trail}.${key}`);
  }
}

function sha256(filePath) {
  return createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function assertIntegrity(material, assetKey, assetUrl) {
  const expected = material.asset_integrity?.[assetKey];
  if (!expected) throw new Error(`${material.id}: integridade ausente para ${assetKey}`);
  const assetPath = path.resolve(path.dirname(catalogPath), assetUrl);
  const stat = fs.statSync(assetPath);
  if (stat.size !== expected.bytes) {
    throw new Error(`${material.id}: tamanho divergente para ${assetKey}`);
  }
  if (sha256(assetPath) !== expected.sha256) {
    throw new Error(`${material.id}: SHA-256 divergente para ${assetKey}`);
  }
  if (expected.width_px < 1 || expected.height_px < 1) {
    throw new Error(`${material.id}: dimensões inválidas para ${assetKey}`);
  }
  return stat.size;
}

assertNoPrivateData(catalog);
const serialized = JSON.stringify(catalog).toLowerCase();
for (const term of forbiddenText) {
  if (serialized.includes(term)) throw new Error(`Contrato público contém termo privado: ${term}`);
}

if (catalog.schema !== 'karv.public-material-catalog/1') {
  throw new Error('schema público inesperado');
}
if (
  !Array.isArray(catalog.channels) ||
  !catalog.channels.includes('fabric') ||
  !catalog.channels.includes('karv_design')
) {
  throw new Error('canais públicos incompletos');
}
if (!Array.isArray(catalog.materials) || catalog.materials.length === 0) {
  throw new Error('catálogo público sem materiais');
}

const allowedChannels = new Set(['fabric', 'karv_design']);
const allowedKeys = new Set([
  'id',
  'channel',
  'name',
  'collection',
  'color',
  'material_type',
  'technologies',
  'functional',
  'appearance',
  'physical_reference_cm',
  'assets',
  'asset_integrity',
  'pbr',
  'published',
  'ready_for_configurator',
  'pbr_ready',
  'compatibility',
]);
const ids = new Set();

for (const material of catalog.materials) {
  for (const key of Object.keys(material)) {
    if (!allowedKeys.has(key)) {
      throw new Error(`${material.id ?? 'material'}: campo público não permitido: ${key}`);
    }
  }
  if (!/^((fabric|design)-kv-[0-9]{3,})$/.test(material.id)) {
    throw new Error(`id público inválido: ${material.id}`);
  }
  if (ids.has(material.id)) throw new Error(`id público duplicado: ${material.id}`);
  ids.add(material.id);
  if (!allowedChannels.has(material.channel)) throw new Error(`${material.id}: channel inválido`);
  if (material.published !== true || material.ready_for_configurator !== true) {
    throw new Error(
      `${material.id}: somente materiais publicados e habilitados podem entrar no contrato público`,
    );
  }
  if (
    !material.compatibility?.geometry_ids?.includes('karv-chair') ||
    material.compatibility.min_geometry_version > 2
  ) {
    throw new Error(`${material.id}: incompatível com karv-chair@2`);
  }
  if (!material.color?.family || !material.material_type || !material.name) {
    throw new Error(`${material.id}: metadata pública insuficiente para Cor → Material → Tecido`);
  }

  for (const [assetName, assetUrl] of Object.entries(material.assets ?? {})) {
    if (assetUrl == null) continue;
    if (
      typeof assetUrl !== 'string' ||
      !assetUrl.startsWith(`./assets/${material.id}/`) ||
      assetUrl.includes('..') ||
      /^https?:/i.test(assetUrl)
    ) {
      throw new Error(`${material.id}: asset público inválido em ${assetName}`);
    }
    const assetPath = path.resolve(path.dirname(catalogPath), assetUrl);
    if (!fs.existsSync(assetPath)) throw new Error(`${material.id}: asset ausente: ${assetUrl}`);
  }

  if (!material.assets?.preview || !material.assets?.base_color) {
    throw new Error(`${material.id}: preview/base_color obrigatórios`);
  }

  if (material.pbr_ready) {
    if (!material.assets.normal || !material.assets.ao) {
      throw new Error(`${material.id}: pbr_ready exige normal e ao`);
    }
    const pbr = material.pbr;
    if (
      pbr?.status !== 'production' ||
      pbr.metalness !== 0 ||
      pbr.normal_convention !== 'opengl' ||
      typeof pbr.roughness_factor !== 'number' ||
      pbr.roughness_factor < 0 ||
      pbr.roughness_factor > 1 ||
      typeof pbr.normal_strength !== 'number' ||
      pbr.normal_strength < 0 ||
      pbr.normal_strength > 2 ||
      typeof pbr.ao_strength !== 'number' ||
      pbr.ao_strength < 0 ||
      pbr.ao_strength > 1
    ) {
      throw new Error(`${material.id}: parâmetros PBR de produção inválidos`);
    }

    const pbrBytes =
      assertIntegrity(material, 'base_color', material.assets.base_color) +
      assertIntegrity(material, 'normal', material.assets.normal) +
      assertIntegrity(material, 'ao', material.assets.ao);
    if (pbrBytes > PBR_TEXTURE_BUDGET_BYTES) {
      throw new Error(
        `${material.id}: PBR web excede budget (${pbrBytes} > ${PBR_TEXTURE_BUDGET_BYTES})`,
      );
    }
  }
}

console.log(
  `Public catalog: PASS (${catalog.materials.length} materiais, sem metadata privada; PBR <= ${PBR_TEXTURE_BUDGET_BYTES} B/material)`,
);
