# 🌳 PlantHere - Mapeamento Inteligente de Ilhas de Calor

Sistema web interativo para identificação de ilhas de calor urbanas e sugestão de áreas prioritárias para plantio de árvores, usando dados de satélite MODIS via Google Earth Engine.

## 🎯 Funcionalidades

- ✅ **Visualização de mapa de calor** sobre mapa da cidade
- ✅ **Seleção de múltiplas cidades brasileiras**
- ✅ **Dados em tempo real** do satélite MODIS (últimos 30 dias)
- ✅ **Identificação automática** de pontos prioritários para plantio
- ✅ **Estatísticas de temperatura** (mín, máx, média)
- ✅ **Interface moderna e responsiva**


## 🚀 Como Executar

### Pré-requisitos

1. **Python 3.8+** instalado
2. **Conta no Google Earth Engine** (gratuita)
   - Cadastre-se em: https://earthengine.google.com/signup/

### Passo 1: Instalar Dependências

```bash
cd greenpulse
pip install -r requirements.txt
```

### Passo 2: Autenticar no Google Earth Engine

Execute este comando uma única vez para autenticar:

```bash
python -c "import ee; ee.Authenticate()"
```

Isso abrirá uma janela do navegador. Faça login com sua conta Google e autorize o acesso.

### Passo 3: Iniciar o Servidor

```bash
cd backend
python app.py
```

O servidor iniciará em: **http://localhost:5000**

### Passo 4: Acessar a Aplicação

Abra seu navegador e acesse:

```
http://localhost:5000
```

## 📖 Como Usar

### 1. Selecionar Cidade

No painel lateral esquerdo, selecione uma cidade no menu dropdown.

O sistema irá:
- Processar dados MODIS dos últimos 30 dias
- Gerar o mapa de calor sobre a cidade
- Exibir estatísticas de temperatura

### 2. Visualizar Mapa de Calor

O mapa mostra a temperatura de superfície com uma paleta de cores:

- 🔵 **Azul**: Áreas mais frias (20-28°C)
- 🟢 **Verde/Amarelo**: Temperatura moderada (28-35°C)
- 🔴 **Laranja/Vermelho**: Ilhas de calor (35-45°C)

### 3. Identificar Pontos para Plantio

Clique no botão **"🎯 Identificar Pontos para Plantio"**.

O sistema irá:
- Analisar áreas com temperatura acima de 35°C
- Identificar até 30 pontos prioritários
- Adicionar marcadores no mapa
- Listar os pontos no painel lateral

### 4. Explorar Pontos

- **No mapa**: Clique nos marcadores para ver detalhes
- **Na lista**: Clique em um ponto para centralizar o mapa

## 🛠️ Estrutura do Projeto

```
greenpulse/
├── backend/
│   └── app.py              # API Flask + Google Earth Engine
├── frontend/
│   ├── static/
│   │   └── app.js          # JavaScript do frontend
│   └── templates/
│       └── index.html      # Interface HTML
├── requirements.txt        # Dependências Python
└── README.md              # Este arquivo
```

## 🔧 Arquitetura Técnica

### Backend (Flask + Google Earth Engine)

**Endpoints da API:**

- `GET /api/cities` - Lista cidades disponíveis
- `GET /api/heatmap/<city_id>` - Gera mapa de calor
- `GET /api/planting-points/<city_id>` - Identifica pontos para plantio

**Processamento de Dados:**

1. Filtra imagens MODIS (produto MOD11A1) para a área e período
2. Aplica máscara de qualidade para remover nuvens
3. Converte temperatura de Kelvin para Celsius
4. Calcula média temporal (30 dias)
5. Gera tiles para visualização no mapa

### Frontend (HTML + Leaflet.js)

**Componentes:**

- **Leaflet.js**: Biblioteca de mapas interativos
- **OpenStreetMap**: Camada base do mapa
- **Earth Engine Tiles**: Camada de temperatura sobreposta

**Fluxo de Dados:**

1. Usuário seleciona cidade
2. Frontend faz requisição à API
3. Backend processa dados no Earth Engine
4. Retorna URL dos tiles e estatísticas
5. Frontend renderiza mapa de calor

## 📊 Fonte de Dados

### MODIS Terra (MOD11A1)

- **Satélite**: Terra (NASA)
- **Produto**: Land Surface Temperature & Emissivity Daily Global 1km
- **Resolução Espacial**: 1 km
- **Resolução Temporal**: Diária
- **Banda Usada**: LST_Day_1km (temperatura diurna)

**Por que MODIS?**

- ✅ Dados diários desde 2000
- ✅ Cobertura global
- ✅ Processamento rápido
- ✅ Ideal para monitoramento urbano

## 🌍 Aplicações Práticas

### Para Governos

- Planejamento de políticas de arborização urbana
- Identificação de áreas vulneráveis a ondas de calor
- Monitoramento de efetividade de projetos de plantio

### Para ONGs

- Priorização de áreas para campanhas de plantio
- Engajamento comunitário com dados científicos
- Medição de impacto ambiental

### Para Cidadãos

- Visualização de ilhas de calor no bairro
- "Adoção" de árvores em áreas críticas
- Conscientização sobre conforto térmico urbano

## 🔮 Melhorias Futuras

- [ ] Integrar dados de vegetação (NDVI)
- [ ] Cruzar com mapas de uso do solo
- [ ] Calcular impacto estimado do plantio
- [ ] Exportar relatórios em PDF
- [ ] Versão mobile (app)
- [ ] Sistema de "adoção" de árvores
- [ ] Histórico temporal (comparar anos)

## 📝 Licença

Este projeto foi desenvolvido para o NASA Space Apps Challenge 2025.

## 🤝 Contribuindo

Sugestões e melhorias são bem-vindas! Abra uma issue ou pull request.

## 📧 Contato

Desenvolvido por: Codonautas
   - Felipe Paiva 
   - Matheus Padilha
   - Maria Eduarda Macedo Neves 
Data: Outubro 2025

---

**🌳 Juntos por cidades mais verdes e sustentáveis! 🌍**
