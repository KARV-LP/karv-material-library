# Maia 10 — Vinho: conferência de entrada (issue #17)

Status: **pré-auditoria concluída; publicação bloqueada**.

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

## Validação executada

- `node scripts/validate-public-catalog.mjs`: **PASS**, 7 Revestimentos existentes. Esse resultado valida somente a situação atual; não valida a inclusão do Maia.
- `node scripts/scale-master-audit.mjs ../inputs/reference.glb ../inputs/scale-master.json`: **FAIL**, `seat: Scale Master V1 exige Base Color WebP embutida`.
- A leitura adicional de estrutura/UVs e comparação dos PNGs é uma pré-auditoria; não substitui o relatório oficial `karv.scale-master-audit/1`.

## Pendências para concluir no mesmo PR

1. Obter autorização expressa para converter os oito PNGs e as respectivas texturas embutidas numa cópia técnica do GLB para WebP lossless. O original deve permanecer intacto. Regra em `AGENTS.md`: “Fontes que não sejam WebP só podem ser convertidas com autorização do usuário.”
2. Validar dimensões, pixels visíveis, alpha e hashes; executar novamente a auditoria oficial no derivado técnico, sem relaxar o validador.
3. Validar visualmente o Scale Master; obter o GLB canônico `karv-chair@2` e executar o bake offline para UV0.
4. Gerar Normal OpenGL, AO, thumbnail do Assento e `piping` como cópia binária da tira superior.
5. Adicionar face-set, metadata e entrada no catálogo público no mesmo PR; confirmar a categoria Veludo no consumidor sem editar `configurador-3d`.
6. Executar validação do catálogo e workflow `Validate Public Material Contract` após a inclusão.
7. Apresentar preview e validar as oito faces, cor/escala e continuidade 360°, com atenção à lateral interna versus externa; aguardar aprovação visual antes de merge.

Nenhuma conversão, bake, publicação ou alteração do GLB canônico foi executada nesta etapa.
