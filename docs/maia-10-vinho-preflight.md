# Maia 10 — Vinho: entrada atualizada (issue #17 / PR #18)

Status: **fontes atualizadas; conversão lossless e auditoria de texturas PASS; bake bloqueado por cobertura geométrica incompleta**.

## Arquivos atuais

Recebida a atualização do Drive em 29/10/2026. As oito imagens PNG e o GLB anteriores foram substituídos pelas novas fontes neste PR. O novo GLB original tem 17.451.172 bytes.

- SHA-256 do novo GLB original: `28869ac16704dc07ffe4f8881f65d16e9b04515e077f2681c1563f2dc4dbe3ed`.
- SHA-256 da cópia técnica WebP: `b1cce4cb3aa63fb0f31418d30c727829b06791564e9f09e086a3431e2e6733d8`.
- Nome: **Maia 10 — Vinho**, categoria **Veludo**. ID candidato: `fabric-kv-010`; revalidar antes de publicar.
- O usuário autorizou a conversão PNG → WebP lossless e o envio dos WebPs/GLB técnico para a branch do PR, sem merge.
- Os oito PNGs correspondem byte a byte às imagens embutidas no novo GLB. Após a conversão: **8/8 pixels RGBA, alpha e dimensões idênticos**. Hashes em `conversion.json`.
- Fontes técnicas em `scale-masters/fabric-kv-010/`; não são assets públicos bakeados para UV0.
- O GLB técnico está em três partes binárias por limite de envio do conector. `assemble-reference.py` recompõe o arquivo e valida hashes das partes e do GLB completo; ver README da pasta.
- Original preservado. Apenas as oito imagens foram convertidas na cópia técnica; meshes, accessors, UVs, materiais e nodes permanecem iguais.

## UVs e resoluções das fontes atuais

| Mesh | Dimensões (px) | UV de origem | Destino |
| --- | --- | --- | --- |
| `ASSENTO` | 1701 × 2269 | UV1 | UV0 |
| `ENCOSTO_FRONTAL` | 1701 × 1135 | UV1 | UV0 |
| `ENCOSTO_LATERAL` | 593 × 602 | UV2 | UV0 |
| `ENCOSTO_TRASEIRO` | 1701 × 2269 | UV2 | UV0 |
| `LATERAL_EXTERNA` | 2110 × 1331 | UV1 | UV0 |
| `LATERAL_INTERNA` | 1417 × 504 | UV2 | UV0 |
| `LATERAL_REAR` | 284 × 1248 | UV2 | UV0 |
| `LATERAL_TOP` | 284 × 2836 | UV2 | UV0 |

A lateral interna usa UV2; a lateral externa usa UV1. Todas as oito faces precisam de bake offline para UV0. Os nomes de saída normalizam TRASEITO para TRASEIRO e LATERAL SUPERIOR para LATERAL_TOP.

## Bloqueador persistente no novo GLB

A verificação no Blender 4.5.3 LTS confirmou que o novo GLB ainda tem somente um lado em cinco superfícies, enquanto o canônico contém ambos. A constatação combina contagem de triângulos com limites em coordenadas mundiais; ver `geometry-comparison.json`.

| Superfície | Triângulos no canônico | Triângulos no novo GLB |
| --- | ---: | ---: |
| `ENCOSTO_LATERAL` | 3802 | 1901 |
| `LATERAL_EXTERNA` | 41900 | 20950 |
| `LATERAL_INTERNA` | 42684 | 21342 |
| `LATERAL_REAR` | 2810 | 1405 |
| `LATERAL_TOP` | 16592 | 8296 |

Não foi feito bake parcial nem espelhamento inferido. Não há correspondência fornecida para o lado ausente. Verificar na origem se modificadores de espelhamento foram aplicados/exportados é uma possível investigação, não um diagnóstico do .blend.

## Validação

- Conversão lossless: **PASS**, oito imagens, sem redução de resolução nesta etapa.
- Auditoria oficial `scale-master-audit.mjs`: **PASS**, oito WebPs embutidos, canais UV existentes, sem `KHR_texture_transform` nas oito faces.
- Recomposição do GLB: **PASS**, SHA-256 idêntico ao técnico auditado.
- Comparação de cobertura no Blender: **BLOCKED** nas cinco superfícies acima.
- `node scripts/validate-public-catalog.mjs`: **PASS**, sete Revestimentos existentes; não equivale à validação de uma publicação do Maia.

## Reprodução

```sh
python scripts/prepare-maia-10-vinho.py INPUT_DIR scale-masters/fabric-kv-010
python scale-masters/fabric-kv-010/assemble-reference.py
node scripts/scale-master-audit.mjs scale-masters/fabric-kv-010/reference.glb
blender -b --python-exit-code 1 --python scripts/compare-scale-master-geometry.py -- CANONICAL_GLB scale-masters/fabric-kv-010/reference.glb scale-masters/fabric-kv-010/geometry-comparison.json
```

O último comando deve falhar neste GLB. INPUT_DIR contém o novo `reference.glb` original e os oito PNGs. A conversão requer Pillow. O teste de cobertura é condição necessária, não aprovação completa geométrica/UV/visual.

Canônico lido de `KARV-LP/configurador-3d`, `assets/geometry/karv-chair/v2/base.glb`, SHA-256 `923dabfc599034b87721b75abfe2da93149899128a0ba8a2cbc30502f3976a82`.

## Para concluir

1. Receber o Scale Master completo com ambos os lados das cinco superfícies, UVs e Revestimento corretos.
2. Repetir as auditorias e confirmar visualmente o Scale Master.
3. Executar bake para UV0; gerar Normal OpenGL, AO, thumbnail do Assento e piping como cópia binária da tira superior.
4. Adicionar assets públicos, metadata e catálogo no mesmo PR; executar validador/workflow e apresentar preview para aprovação antes de merge.

O Maia ainda não está publicado. Configurador e GLB canônico permanecem intactos.
