import argparse
import sys

from application.analyzer import run_analysis


def main():
    parser = argparse.ArgumentParser(
        description="Analisa seus treinos de corrida do Strava e gera um relatório para agente de IA."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Número de dias para analisar (padrão: 30)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Força nova busca na API do Strava, ignorando o cache local",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="report.md",
        help="Nome do arquivo de relatório gerado (padrão: report.md)",
    )
    args = parser.parse_args()

    try:
        run_analysis(days=args.days, force_refresh=args.refresh, output_path=args.output)
    except KeyError as e:
        print(f"\nErro: variável de ambiente {e} não encontrada.")
        print("Crie um arquivo .env com STRAVA_CLIENT_ID e STRAVA_CLIENT_SECRET.")
        print("Consulte o .env.example para referência.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
