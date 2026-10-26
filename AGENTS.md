# Regra obrigatória de materiais

- Este repositório é a única fonte oficial de tecidos, estampas e demais materiais KARV.
- Toda solicitação de material novo ou atualização de material existente deve ser implementada aqui, nunca no repositório do configurador.
- Material novo recebe um ID canônico e imutável no formato `fabric-kv-NNN` ou `design-kv-NNN`. Atualizações preservam o ID existente.
- Publique arquivos finais em `public/v1/assets/<material-id>/`, mapas por face em `public/v1/assets/<material-id>/face-set/` e atualize `public/v1/catalog.json` no mesmo PR.
- Não publique metadados privados, nomes de fornecedor, custos ou referências internas no contrato público.
- O conjunto por face deve conter Base Color, Normal OpenGL e AO. O vivo (`piping`) deve ser uma cópia binária de `LATERAL_TOP.webp`.
- Fontes que não sejam WebP só podem ser convertidas com autorização do usuário. Registre a conversão lossless e valide pixels visíveis, alpha, dimensões e hashes.
- Antes de concluir, execute `node scripts/validate-public-catalog.mjs` e confirme que o workflow `Validate Public Material Contract` passou.
