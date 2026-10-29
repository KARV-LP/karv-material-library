# Maia 10 — Vinho: entrada atualizada (issue #17 / PR #18)

Status: **fontes atualizadas; conversão lossless e auditoria de texturas PASS; organização VELUDO/MAIA e aplicação preparadas; revisão visual pendente**.

## Arquivos atuais

Recebida a atualização do Drive em 29/10/2026. As oito imagens PNG e o GLB anteriores foram substituídos pelas novas fontes neste PR. O novo GLB original tem 17.451.172 bytes.

- SHA-256 do novo GLB original: `28869ac16704dc07ffe4f8881f65d16e9b04515e077f2681c1563f2dc4dbe3ed`.
- SHA-256 da cópia técnica WebP: `b1cce4cb3aa63fb0f31418d30c727829b06791564e9f09e086a3431e2e6733d8`.
- Nome: **Maia 10 — Vinho**, categoria **Veludo**, coleção **MAIA**. Organização aprovada: **Tecidos → VELUDO → MAIA → Maia 10 — Vinho**. ID candidato: `fabric-kv-010`; revalidar antes de publicar.
- O usuário autorizou a conversão PNG → WebP lossless e o envio dos WebPs/GLB técnico para a branch do PR, sem merge.
- Os oito PNGs correspondem byte a byte às imagens embutidas no novo GLB. Após a conversão: **8/8 pixels RGBA, alpha e dimensões idênticos**. Hashes em `conversion.json`.
- Fontes técnicas em `scale-masters/fabric-kv-010/`; as fontes originais permanecem separadas dos mapas preparados para o frame público de cada face.
- O GLB técnico está em três partes binárias por limite de envio do conector. `assemble-reference.py` recompõe o arquivo e valida hashes das partes e do GLB completo; ver README da pasta.
- Original preservado. Apenas as oito imagens foram convertidas na cópia técnica; meshes, accessors, UVs, materiais e nodes permanecem iguais.

## Aplicação preparada para o consumidor atual

O código atual de `configurador-3d/src/3d/pbr-material-controller.ts` escolhe `artUvSet` por superfície quando recebe `faceAssets`. UV0 é o fallback, não o destino universal deste face-set. Essa verificação substitui a orientação anterior de bake universal para UV0.

- UV0 compartilhado foi usado para estabelecer correspondência de geometria/cantos entre referência e canônico, incluindo as posições refletidas. Todos os cantos canônicos têm correspondência de UV0; erro de UV0 máximo zero. Ver `shared-uv0-check.json`.
- Igualdade do índice de UV não implica igualdade de coordenadas: sete faces foram transferidas offline do Scale Master para o frame de arte do canônico. A tira superior usa cópia direta após verificação de correspondência em todos os cantos; erro máximo de UV 0,000123.
- Destinos conforme `surface-map.json`: UV1 para Assento, Encosto Frontal e Lateral Externa; UV2 para as outras cinco faces. Não houve exportação ou alteração da geometria, dos UVs ou de transforms no navegador.
- `face-bake.json` registra os vínculos e tolerâncias. `source-frame-check.json` registra a diferença do frame original, antes da transferência (diferença nas sete faces é esperada e foi corrigida pelo bake).
- Os mapas finais estão em `public/v1/assets/fabric-kv-010/face-set/`: nove vínculos (oito faces + piping), Base Color WebP, Normal OpenGL PNG e AO WebP, com hashes e dimensões. `piping` é cópia binária dos mapas da tira superior.
- Thumbnail derivado do Assento original. Categoria `Veludo`; coleção `MAIA`; fontes mantidas em `fabrics/VELUDO/MAIA/maia-10-vinho/`.
- A entrada foi adicionada a `public/v1/catalog.json` nesta branch. O campo opcional `category` foi alinhado ao schema/validador da Biblioteca; o consumidor já o suporta.

## Validação

- Conversão das fontes: 8/8 RGBA, alpha e dimensões idênticos (manifesto `conversion.json`).
- Auditoria oficial de texturas: PASS (oito WebPs embutidos, UVs existentes e sem transforms nas faces oficiais).
- Validador do catálogo: PASS, oito Revestimentos.
- Build do configurador sem alterações de código: PASS.
- Testes existentes do consumidor de catálogo/PBR e controlador de aplicação: 13 PASS.
- Preview local: categoria Veludo e seleção de Maia 10 — Vinho confirmadas na interface.
- Limite da verificação visual: o navegador da sessão não conseguiu criar contexto WebGL; a aplicação visual 3D não pôde ser aprovada nele. Não marcar gate visual como aprovado.
- Preview externo: preparado; Vercel requer autorização da conexão para a equipe do projeto. Não houve deploy nem merge nesta etapa.

## Reprodução da transferência

```sh
python scale-masters/fabric-kv-010/assemble-reference.py
blender -b -t 4 --python-exit-code 1 --python scripts/blender-face-frame-bake.py -- CANONICAL_GLB scale-masters/fabric-kv-010/reference.glb scale-masters/fabric-kv-010/audit.json scale-masters/fabric-kv-010/surface-map.json OUTPUT_DIR scale-masters/fabric-kv-010/source-frame-check.json
```

O script verifica hashes dos GLBs e rejeita correspondências ausentes/ambíguas. UV0 é somente a chave de correspondência; o destino de cada face é lido do mapa do consumidor. Os PNGs intermediários são convertidos lossless antes da pipeline normal de Normal/AO. As fontes fornecidas ficam intactas.

## Revisão pendente

Abrir preview externo, selecionar Tecidos → Veludo → Maia 10 — Vinho e aplicar na poltrona. Conferir cor, escala, as oito faces, os lados simétricos, costuras e continuidade em 360°. Aprovação visual necessária antes de merge. Sem alteração em `main` ou no GLB oficial.
