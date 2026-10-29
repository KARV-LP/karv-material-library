> Atualização do contrato por face: no consumidor atual, `faceAssets` usa `artUvSet` da superfície, com UV0 como fallback. As referências históricas abaixo a UV0 como destino universal não devem substituir esse vínculo. No Maia 10 — Vinho, transferir para o UV de arte canônico por face (UV1/UV2), sem alterar o runtime. Ver `docs/maia-10-vinho-preflight.md` e `scale-masters/fabric-kv-010/face-bake.json`.

# GLB como Scale Master

## Objetivo

Usar um GLB revestido aprovado como referência oficial de escala visual, orientação e continuidade do Revestimento, sem alterar a geometria, UVs ou runtime da Poltrona KARV no configurador.

O configurador continua consumindo exatamente o contrato atual:

- Base Color por face;
- Normal OpenGL por face;
- AO por face;
- thumbnail;
- metadata do face-set.

## Entrada obrigatória por Revestimento

1. Oito Base Colors WebP:
   - `Assento.webp`
   - `ENCOSTO_FRONTAL.webp`
   - `ENCOSTO_LATERAL.webp`
   - `ENCOSTO_TRASEIRO.webp`
   - `LATERAL_EXTERNA.webp`
   - `LATERAL_INTERNA.webp`
   - `LATERAL_REAR.webp`
   - `LATERAL_TOP.webp`
2. Um `reference.glb` aprovado visualmente.

O GLB é referência técnica de calibração. Ele não substitui o `karv-chair@2`, não é carregado no configurador e não altera a geometria oficial.

## Regra de calibração

O GLB canônico do configurador usa UV0 como destino público de Revestimentos.

A auditoria do Scale Master identifica, em cada face, qual `TEXCOORD_n` o GLB de referência usa para a Base Color.

- Se a referência também usa UV0, a imagem pode seguir sem remapeamento.
- Se a referência usa UV1, UV2 ou outro canal, a Base Color deve ser bakeada desse canal para o UV0 do GLB canônico.
- Atlas, múltiplas primitives, imagens externas, `KHR_texture_transform` ou mapeamento ambíguo devem bloquear a automação na V1 em vez de inferir valores.

## Pipeline

### 1. Auditoria

```bash
node scripts/scale-master-audit.mjs reference.glb scale-master.json
```

A auditoria registra:

- SHA-256 do GLB;
- mesh oficial por face;
- canal UV de origem;
- imagem WebP embutida;
- SHA-256 da imagem;
- se a face exige bake para UV0.

### 2. Bake offline

O bake é executado fora do navegador, usando Blender em modo headless:

```bash
blender -b --python scripts/blender-scale-master-bake.py -- \
  --canonical-glb /path/to/base.glb \
  --reference-glb /path/to/reference.glb \
  --audit-json /path/to/scale-master.json \
  --output-dir /tmp/karv-scale-master
```

O processo transfere a leitura visual do GLB Scale Master para o UV0 do GLB canônico e gera uma Base Color intermediária por face.

### 3. Publicação

As imagens bakeadas passam pelo pipeline normal:

- conversão/otimização WebP;
- geração de Normal OpenGL;
- geração de AO;
- geração do thumbnail pelo Assento;
- derivação binária de `piping` a partir de `LATERAL_TOP.webp`;
- atualização do `face-set/metadata.json`;
- atualização do `public/v1/catalog.json`.

## Málaga 03 — primeiro caso

O arquivo auditado `MALAGA-03(2).glb` confirmou:

| Face | UV no Scale Master | Destino |
| --- | ---: | ---: |
| Assento | UV1 | UV0 |
| Encosto frontal | UV1 | UV0 |
| Encosto lateral | UV2 | UV0 |
| Encosto traseiro | UV2 | UV0 |
| Lateral externa | UV1 | UV0 |
| Lateral interna | UV2 | UV0 |
| Lateral traseira | UV2 | UV0 |
| Tira superior | UV2 | UV0 |

As 8 imagens embutidas no GLB são byte a byte as mesmas Base Colors fornecidas. Portanto, a diferença visual não está nos arquivos de imagem; está no canal UV usado pelo GLB de referência.

O manifesto técnico está em `scale-masters/fabric-kv-009.json`.

## Regra de falha segura

A pipeline deve falhar e exigir revisão manual quando:

- a geometria de referência não contém as 8 meshes oficiais;
- uma mesh contém mais de uma primitive;
- a Base Color não é WebP embutida;
- existe `KHR_texture_transform` na Base Color;
- o canal UV referenciado não existe;
- a associação entre face, material ou textura é ambígua.

A pipeline nunca deve modificar o GLB canônico para acomodar um Revestimento.
