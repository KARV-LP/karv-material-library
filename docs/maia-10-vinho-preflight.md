# Maia 10 — Vinho: conferência de entrada (issue #17)

Status: **conversão lossless autorizada e concluída; auditoria de texturas PASS; bake bloqueado por cobertura geométrica incompleta**.

Este documento registra a preparação da inclusão. O Revestimento ainda não foi adicionado ao catálogo e não está disponível no configurador.

## Entrada verificada em 29/10/2026

- GLB fornecido: `MAIA 10- VINHO.glb` (20.180.128 bytes).
- SHA-256: `08fa98000910bb901636983086aaa5cdd8d998f4a169f1090d5be877bd3f8b8d`.
- Oito PNGs originais conferidos contra as oito imagens embutidas no GLB: todos idênticos byte a byte e em pixels RGBA.
- Cada face oficial possui uma primitive, textura embutida e canal UV existente; nenhuma das oito Base Colors usa `KHR_texture_transform`.
- A cena inclui objetos adicionais; eles não integram o conjunto público das oito faces. A conferência acima se limita às faces oficiais.
- Nome solicitado: **Maia 10 — Vinho**. Categoria: **Veludo**.
- Próximo ID candidato na main `135a944274f6c0c4c3a01836b2a352fe98277263`: `fabric-kv-010`. Revalidar disponibilidade antes de publicar.
- `INFO.PNG` foi consultado; dados comerciais/privados não foram copiados para o contrato público. A largura comercial do tecido não deve ser confundida com a escala física da textura.

## UVs e integridade

| Mesh oficial | Fonte | Dimensões (px) | UV de origem | Destino | PNG = imagem no GLB |
| --- | --- | --- | --- | --- | --- |
| `ASSENTO` | `ASSENTO.png` | 3544 × 4725 | UV1 | UV0 | Sim |
| `ENCOSTO_FRONTAL` | `ENCOSTO FRONTAL.png` | 3544 × 2363 | UV1 | UV0 | Sim |
| `ENCOSTO_LATERAL` | `ENCOSTO LATERAL.png` | 1233 × 1253 | UV2 | UV0 | Sim |
| `ENCOSTO_TRASEIRO` | `ENCOSTO TRASEITO.png` | 3544 × 4725 | UV2 | UV0 | Sim |
| `LATERAL_EXTERNA` | `LATERAL EXTERNA.png` | 4395 × 2770 | UV1 | UV0 | Sim |
| `LATERAL_INTERNA` | `LATERAL INTERNA.png` | 2950 × 1047 | UV2 | UV0 | Sim |
| `LATERAL_REAR` | `LATERAL REAR.png` | 591 × 2599 | UV2 | UV0 | Sim |
| `LATERAL_TOP` | `LATERAL SUPERIOR.png` | 591 × 5907 | UV2 | UV0 | Sim |

Todas as oito faces precisam de bake offline para UV0. A lateral interna usa UV2; a lateral externa usa UV1. Copiar diretamente os PNGs para o face-set não preservaria a referência de escala do GLB.

A normalização dos nomes de saída deve mapear `ENCOSTO TRASEITO.png` para Encosto Traseiro e `LATERAL SUPERIOR.png` para `LATERAL_TOP.webp`, preservando os arquivos originais.

### SHA-256 dos PNGs (iguais aos embutidos)

- `ASSENTO.png`: `40756d5b02a700b1d0ef82c80d1b62f2e8b82c31e29adf070797b359c9a27102`
- `ENCOSTO FRONTAL.png`: `c0fdfbacd47048739815866ac3df0083285caa0ecfd44528e7efddd251e9c4d0`
- `ENCOSTO LATERAL.png`: `7e810d9d09b42333dfd25d60205b879b616e8c121f2aa386a0ee9aa7096e6b7a`
- `ENCOSTO TRASEITO.png`: `c6b62a25b2f0d668f7516bbcb5087f716b803d693430d89a078d4a747c2e60f3`
- `LATERAL EXTERNA.png`: `6ec67c16f6503eadb53e432637ec82d0b33e74a36d62258abe5ebe47dbd84750`
- `LATERAL INTERNA.png`: `35536c65b10cac4da6c5acb3d8fd4621a549bf51a858d2457e2c606b371859d7`
- `LATERAL REAR.png`: `0045327b389282d8199db152ad04d77b007b066f4da6a02145463d75a9494449`
- `LATERAL SUPERIOR.png`: `2f8bc2794fe93f4a30036ba3e065a10eb99a862741ce9f65f3bad929a3149cd9`

## Conversão autorizada em 29/10/2026

O usuário autorizou expressamente a conversão dos oito PNGs e das texturas de uma cópia técnica do GLB para WebP lossless, preservando os originais.

- Fontes convertidas sem redução de resolução, com `lossless=True`, `exact=True`, `method=6` (Pillow).
- Comparação após decodificação: **8/8 pixels RGBA, alpha e dimensões idênticos**.
- SHA-256 do original preservado: `08fa98000910bb901636983086aaa5cdd8d998f4a169f1090d5be877bd3f8b8d`.
- A cópia técnica altera apenas o armazenamento das oito imagens/texturas e adiciona `EXT_texture_webp`; meshes, accessors, UVs, materiais e nodes permanecem iguais.
- Arquivos e manifesto: `scale-masters/fabric-kv-010/`. O GLB técnico é transportado em quatro partes binárias; `assemble-reference.py` recompõe o arquivo e confere SHA-256 (ver README da pasta). São fontes técnicas, não assets públicos prontos para o configurador.
- Reprodução: `python scripts/prepare-maia-10-vinho.py INPUT_DIR scale-masters/fabric-kv-010` (requer Pillow). INPUT_DIR deve conter `reference.glb` original e os oito PNGs.

## Validação executada

- `node scripts/scale-master-audit.mjs scale-masters/fabric-kv-010/reference.glb scale-masters/fabric-kv-010/audit.json`: **PASS**. Todas as oito Base Colors WebP embutidas; UV1/UV2 presentes e sem transformações de textura nas oito faces oficiais.
- `node scripts/validate-public-catalog.mjs`: **PASS**, 7 Revestimentos existentes. Esse resultado ainda não valida uma inclusão do Maia.
- Conferência adicional em Blender 4.5.3 LTS: **BLOCKED** por cobertura geométrica incompleta em cinco superfícies. O relatório é `scale-masters/fabric-kv-010/geometry-comparison.json`.

## Bloqueador confirmado no Blender

O GLB de referência contém somente um lado nas cinco superfícies abaixo. A geometria canônica contém os dois lados. A diferença foi confirmada por contagem de triângulos e limites em coordenadas mundiais, não apenas por contagem de vértices.

| Superfície | Triângulos no canônico | Triângulos na referência |
| --- | ---: | ---: |
| Encosto lateral | 3.802 | 1.901 |
| Lateral externa | 41.900 | 20.950 |
| Lateral interna | 42.684 | 21.342 |
| Lateral traseira | 2.810 | 1.405 |
| Tira superior | 16.592 | 8.296 |

Assento, Encosto Frontal e Encosto Traseiro têm a mesma cobertura básica nesta conferência. Isso não equivale a aprovação visual.

Não foi executado bake parcial, espelhamento inferido nem publicação. A referência atual não fornece a correspondência do lado ausente. Publicar assim poderia reproduzir erros de escala/aplicação.

### Como reproduzir a verificação de cobertura

```sh
blender -b --python-exit-code 1 --python scripts/compare-scale-master-geometry.py -- CANONICAL_GLB scale-masters/fabric-kv-010/reference.glb scale-masters/fabric-kv-010/geometry-comparison.json
```

O comando deve falhar neste GLB. Canônico lido de `KARV-LP/configurador-3d`, `assets/geometry/karv-chair/v2/base.glb`, SHA-256 `923dabfc599034b87721b75abfe2da93149899128a0ba8a2cbc30502f3976a82`. O teste de cobertura é condição necessária, não aprovação completa de correspondência geométrica/UV/visual.

## Pendências para concluir no mesmo PR

1. Receber GLB Scale Master completo, com ambos os lados das cinco superfícies e Revestimento/UVs corretos. Conferir na exportação se os modificadores de espelhamento foram aplicados/exportados; esta é uma possível causa, não um diagnóstico do arquivo .blend.
2. Repetir conversão e auditorias no arquivo corrigido; confirmar visualmente o Scale Master.
3. Executar bake offline para UV0, gerar Normal OpenGL, AO, thumbnail do Assento e `piping` como cópia binária da tira superior.
4. Revalidar o próximo ID candidato `fabric-kv-010`, adicionar face-set, metadata e entrada no catálogo público no mesmo PR, e confirmar categoria Veludo no consumidor.
5. Executar validador e workflow após inclusão dos assets. Apresentar preview e validar cor, escala e continuidade 360° antes de merge.

O Revestimento Maia ainda não está publicado; o configurador e o GLB canônico permanecem intactos.
