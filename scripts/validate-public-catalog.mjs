import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const catalogPath = path.join(root, 'public/v1/catalog.json');
const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));

const forbiddenKeys = new Set(['supplier', 'reference', 'cost', 'sources', 'research']);
const forbiddenText = ['wiler'];

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
  if (material.pbr_ready && (!material.assets.normal || !material.assets.ao)) {
    throw new Error(`${material.id}: pbr_ready exige normal e ao`);
  }
}

console.log(
  `Public catalog: PASS (${catalog.materials.length} materiais, sem metadata privada)`,
);
