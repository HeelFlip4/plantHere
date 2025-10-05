#!/bin/bash
#script em bash para hospedagem da aplicacao remotamente

echo "================================================"
echo "🌳 PlantHere - Iniciando Aplicação"
echo "================================================"
echo ""

# Verifica se está no diretório correto
if [ ! -f "requirements.txt" ]; then
    echo "❌ Erro: Execute este script do diretório greenpulse/"
    exit 1
fi

# Verifica se as dependências estão instaladas
echo "📦 Verificando dependências..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Dependências não encontradas. Instalando..."
    pip3 install -r requirements.txt
else
    echo "✓ Dependências OK"
fi

echo ""
echo "🔐 Verificando autenticação do Earth Engine..."
if ! python3 -c "import ee; ee.Initialize()" 2>/dev/null; then
    echo "⚠️  Earth Engine não autenticado!"
    echo ""
    echo "Execute o comando abaixo para autenticar:"
    echo "  python3 -c 'import ee; ee.Authenticate()'"
    echo ""
    echo "Depois execute este script novamente."
    exit 1
else
    echo "✓ Earth Engine autenticado"
fi

echo ""
echo "🚀 Iniciando servidor Flask..."
echo ""
echo "================================================"
echo "Acesse a aplicação em:"
echo "  http://localhost:5000"
echo ""
echo "Pressione Ctrl+C para parar o servidor"
echo "================================================"
echo ""

cd backend
python3 app.py
