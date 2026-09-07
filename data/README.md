# Data policy

Este diretório separa dados locais não versionados de pequenos exemplos deliberadamente versionáveis.

```text
data/
├── raw/       # datasets originais, manifests e profiling locais; ignorados pelo Git
└── sample/    # somente amostras pequenas, derivadas ou sintéticas, aprovadas para versionamento
```

## Regras

- Nunca versionar datasets Olist, arquivos extraídos, archives, manifests locais ou outputs de profiling.
- Nunca armazenar credenciais Kaggle neste repositório.
- Preservar os arquivos raw sem sobrescrita silenciosa.
- Identificar explicitamente dados reais e dados sintéticos controlados.
- Não colocar PII ou dumps de registros nos relatórios versionados.

## Fluxo local

```powershell
python scripts/acquire_olist_data.py status
python scripts/acquire_olist_data.py download
python scripts/acquire_olist_data.py import-local --source-dir C:\path\to\download
python scripts/profile_olist_data.py
```

`download` utiliza somente o Kaggle CLI oficial quando disponível. `import-local` organiza CSVs ou archives obtidos manualmente das páginas oficiais. Ambos recusam sobrescrever conteúdo divergente. O profiling é gravado em `data/raw/_profiling/profile.json`.
