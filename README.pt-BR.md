# Strava Training Analyzer

> 🇺🇸 [Read in English](README.md)

Ferramenta CLI local em Python que conecta à API do Strava, coleta seus dados de corrida e gera um relatório Markdown estruturado — projetado para ser consumido por um agente de IA que ajuda corredores a entender sua evolução e tirar dúvidas sobre os treinos.

## O que faz

- Autentica com sua conta do Strava via OAuth 2.0 (fluxo automático via browser)
- Coleta corridas dos últimos N dias (padrão: 30)
- Calcula estatísticas agregadas, tendências de pace e potência
- Projeta tempos de prova com sistema híbrido: **Best Efforts diretos** (quando disponíveis) ou **Fórmula de Riegel** como fallback
- Identifica corridas na **esteira vs ao ar livre**
- Mostra **tênis utilizados** com km do período e totais acumulados
- Exibe **splits por km** (pace + FC) de cada corrida
- Consolida seus **melhores tempos históricos** por distância padrão (400m, 1K, 5K, 10K, Meia, Maratona)
- Lista **segmentos Strava com PR** das corridas ao ar livre
- Gera `report.md` pronto para ser colado num agente de IA (Claude, ChatGPT, etc.)
- Cache local evita re-chamar a API em execuções repetidas

## Arquitetura

O projeto aplica **Arquitetura em Camadas** — as dependências fluem em uma única direção:

```
main.py           → entrada CLI (argparse)
application/      → caso de uso único: orquestra as camadas
domain/           → lógica pura (calculators, models) — zero dependências externas
infra/            → sistemas externos (API Strava, arquivos)
```

A regra de ouro: `domain/` pode ser testado sem internet e sem criar arquivos.

## Pré-requisitos

- Python 3.12+
- Conta no Strava
- App criado em [strava.com/settings/api](https://www.strava.com/settings/api)
  - **Authorization Callback Domain:** `localhost`

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/alvespedro/strava-analyzer.git
cd strava-analyzer

# 2. Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as credenciais
cp .env.example .env
# Edite .env com seu STRAVA_CLIENT_ID e STRAVA_CLIENT_SECRET
```

## Uso

```bash
# Análise padrão (últimos 30 dias)
python3 main.py

# Janela de tempo customizada
python3 main.py --days 60

# Forçar re-busca na API (ignorar cache)
python3 main.py --refresh

# Nome customizado para o relatório
python3 main.py --output meu_relatorio.md

# Combinando opções
python3 main.py --days 90 --refresh --output relatorio_trimestre.md
```

Na **primeira execução**, o browser abrirá automaticamente para você autorizar o acesso ao Strava. Após isso, o token é salvo localmente e renovado de forma silenciosa.

## Saída

O comando gera `report.md` com 14 seções:

| # | Seção | Conteúdo |
|---|-------|----------|
| 1 | Estatísticas Gerais | Totais de km, tempo, pace médio, FC, potência, calorias, conquistas e PRs |
| 2 | Tendência de Pace | Direção (melhorando/piorando/estável) com regressão linear |
| 3 | Esteira vs Rua | Distribuição das corridas por superfície |
| 4 | Tênis Utilizados | Km por tênis no período e total acumulado |
| 5 | Projeções de Prova | 5K, 10K, Meia e Maratona — Best Effort direto ou Riegel como fallback |
| 6 | Potência de Corrida | Média em watts e tendência (requer sensor compatível) |
| 7 | Log de Corridas | Tabela detalhada com todas as atividades do período |
| 8 | Breakdown Semanal | Volume e métricas agrupados por semana |
| 9 | Corridas Notáveis | Mais longa, mais rápida, maior elevação, maior FC |
| 10 | Carga de Treino | km/semana e consistência |
| 11 | Best Efforts Pessoais | Melhores tempos históricos por distância padrão, com marcação de PR |
| 12 | Segmentos Notáveis | PRs em segmentos Strava das corridas ao ar livre |
| 13 | Splits por Km | Pace + FC de cada quilômetro de cada corrida |
| 14 | Notas e Limitações | Contagem de atividades sem FC, cadência, splits |

### Sistema de projeções híbrido

A seção 5 usa dois métodos dependendo dos dados disponíveis:

- **✅ Best Effort (direto)** — tempo real registrado pelo Strava nessa distância. Aparece quando você correu aquela distância continuamente (ex: uma corrida de 10K completa). É o dado mais preciso.
- **📐 Riegel (estimado)** — projeção pela fórmula `T2 = T1 × (D2/D1)^1.06`, calculada a partir da corrida mais longa. Usado como fallback para distâncias sem Best Effort disponível.

### Como usar o relatório com um agente de IA

1. Execute `python3 main.py` para gerar o `report.md`
2. Abra o arquivo e copie todo o conteúdo
3. Cole numa conversa com Claude, ChatGPT ou outro agente
4. Faça perguntas como:
   - *"Como está minha evolução de pace?"*
   - *"Quando devo trocar o tênis?"*
   - *"Meu volume semanal está adequado para uma meia maratona?"*
   - *"Em qual km do longão meu pace cai mais?"*
   - *"Qual foi meu melhor 5K este mês?"*

## Estrutura de arquivos

```
strava-analyzer/
├── main.py                  # Entrada CLI
├── application/
│   └── analyzer.py          # Caso de uso principal
├── domain/
│   ├── models.py            # Dataclasses (Activity, Stats, Report...)
│   └── calculators.py       # Riegel, tendências, estatísticas
├── infra/
│   ├── strava_auth.py       # OAuth 2.0
│   ├── strava_fetcher.py    # Chamadas à API do Strava
│   ├── cache_repository.py  # Cache local (token.json)
│   └── report_writer.py     # Geração do Markdown
├── requirements.txt
├── .env.example
└── .gitignore
```

## Arquivos gerados (não versionados)

| Arquivo | Descrição |
|---------|-----------|
| `.env` | Suas credenciais do Strava — **nunca commite este arquivo** |
| `token.json` | Token OAuth e cache de atividades — regenerado automaticamente |
| `report.md` | Relatório gerado — contém dados pessoais (FC, localização, pace real); não versionado por padrão |

> Se quiser versionar seus relatórios, remova `report.md` do `.gitignore` e use nomes com data: `--output relatorio_2025-01.md`.

## Dependências

| Pacote | Versão | Uso |
|--------|--------|-----|
| `stravalib` | 1.6.0 | Wrapper da API do Strava |
| `python-dotenv` | 1.0.0 | Leitura do arquivo `.env` |
| `requests` | 2.31.0 | Requisições HTTP para OAuth |

Todo o resto (argparse, http.server, statistics, datetime) é da stdlib Python.

## Rate limits do Strava

A API do Strava permite 100 requisições/15min e 1.000/dia. Uma execução típica usa:

| Operação | Chamadas |
|----------|----------|
| Lista de atividades | 1 |
| Detalhes por atividade (splits + best efforts + segmentos) | ~20–60 (1 por corrida) |
| Resolução de tênis | 2–5 (IDs únicos) |
| **Total** | **< 70** |

O cache local evita re-chamar a API — use `--refresh` apenas quando quiser dados atualizados.
