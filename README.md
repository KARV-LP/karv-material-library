# KARV Material Library

Biblioteca oficial e versionada de tecidos e Estampas KARV.

## Regra obrigatória

Todo material novo e toda atualização de material existente devem ser implementados neste
repositório. O Configurador 3D apenas consome a Biblioteca e não deve armazenar cópias próprias dos
tecidos.

Uma alteração de material só está completa quando os arquivos finais estão em
`public/v1/assets/<material-id>/`, os mapas por face estão em
`public/v1/assets/<material-id>/face-set/` e `public/v1/catalog.json` foi atualizado no mesmo PR.
Consulte [AGENTS.md](AGENTS.md) para as regras técnicas obrigatórias.

- Google Drive: entrada e organização dos assets.
- GitHub: metadados e arquivos finais para uso pelo sistema.
- Masters: armazenamento local sob responsabilidade do usuário.

## Contrato público para aplicações

O diretório `public/v1/` é a única superfície destinada a consumo por aplicações públicas, incluindo o Configurador 3D KARV.

- `public/v1/catalog.json`: catálogo público sanitizado e versionado.
- `public/v1/assets/`: aliases públicos dos assets publicados, sem caminhos internos de fornecedor.
- `public/v1/assets/<material-id>/face-set/`: Base Color, Normal e AO por face; o vivo usa uma
  cópia binária da tira superior.
- `schemas/public-catalog.schema.json`: contrato estrutural da projeção pública.
- `scripts/validate-public-catalog.mjs`: valida publicação, compatibilidade, assets e ausência de campos privados.

Os diretórios `fabrics/`, `catalog/asset-sources.staging.json` e os `metadata.json` técnicos permanecem como camada editorial/técnica da Biblioteca e **não devem ser consumidos diretamente por interfaces públicas**.
