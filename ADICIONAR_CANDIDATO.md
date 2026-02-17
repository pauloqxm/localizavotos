# LocalizaVotos - Guia de Adição de Candidatos

## 🚀 Adicionar Novo Candidato (Automático)

Use o script `add_candidato.py` para criar automaticamente toda a estrutura necessária:

```bash
python add_candidato.py "Nome do Candidato" "Subtítulo opcional"
```

### Exemplo:
```bash
python add_candidato.py "Maria Santos" "Mapa de votos por local de votação"
```

### O que o script faz:
1. ✅ Cria a pasta `candidatos/maria_santos/`
2. ✅ Cria o arquivo Python `maria_santos.py` com toda a configuração
3. ✅ Cria a página Streamlit em `pages/N_maria_santos.py`
4. ✅ Cria um README com instruções específicas

### Após executar o script:
1. Adicione os arquivos GeoJSON na pasta do candidato:
   - `votos_fortaleza.geojson` (obrigatório)
   - `votos_municipios.geojson` (opcional)

2. Commit e push para o GitHub:
```bash
git add candidatos/ pages/
git commit -m "Adiciona candidato Maria Santos"
git push
```

3. Acesse a página em: `http://seu-dominio/maria_santos`

---

## 📋 Estrutura dos Arquivos GeoJSON

### votos_fortaleza.geojson
Arquivo com votos por local de votação. Deve conter pontos (Point) com as propriedades:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-38.5434, -3.7319]
      },
      "properties": {
        "NM_MUNICIPIO": "FORTALEZA",
        "NM_LOCAL_VOTACAO": "ESCOLA MUNICIPAL",
        "NM_VOTAVEL": "MARIA SANTOS",
        "NR_VOTAVEL": "12345",
        "QT_VOTOS": 150,
        "NR_ZONA": "001"
      }
    }
  ]
}
```

### votos_municipios.geojson (opcional)
Arquivo com votos agregados por município:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-38.5434, -3.7319]
      },
      "properties": {
        "NM_MUNICIPIO": "FORTALEZA",
        "NM_VOTAVEL": "MARIA SANTOS",
        "NR_VOTAVEL": "12345",
        "TOTAL_VOTOS_MUNICIPIO": 5000
      }
    }
  ]
}
```

---

## 🎨 Funcionalidades Automáticas

Cada candidato terá automaticamente:

- ✅ **Simbologia graduada**: Círculos com tamanhos baseados na quantidade de votos (5 classes)
- ✅ **Tooltips customizados**: Informações ao passar o mouse com emojis
- ✅ **Filtros**: Por município, bairro/distrito e local de votação
- ✅ **KPIs**: Total de votos, pontos mapeados, top local
- ✅ **Mapa interativo**: Com múltiplas camadas base e ferramentas de desenho
- ✅ **Gráficos**: Top locais, top bairros, distribuição de votos
- ✅ **Tabela**: Dados filtráveis e ordenáveis
- ✅ **Heatmap**: Mapa de calor opcional
- ✅ **Seleção por polígono**: Desenhe áreas para análise específica

---

## 🔧 Adição Manual (Avançado)

Se preferir adicionar manualmente:

1. Crie a pasta: `candidatos/nome_candidato/`
2. Crie o arquivo Python: `candidatos/nome_candidato/nome_candidato.py`
3. Crie a página: `pages/N_nome_candidato.py`
4. Adicione os arquivos GeoJSON

Use os arquivos existentes como template.

---

## 📞 Suporte

Para dúvidas ou problemas, consulte os exemplos em:
- `candidatos/candidato_teste/`
- `candidatos/larissa_gaspar/`
