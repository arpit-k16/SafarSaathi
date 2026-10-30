"""Command-line entry points for audit/training and API serving."""
from __future__ import annotations

import argparse
import json

from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="safarsaathi-ml")
    parser.add_argument("command", choices=("run", "serve", "data-readiness", "train", "evaluate", "predict", "models", "validate-artifacts"))
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", choices=("tourism_demand", "tourism_monthly_fta", "disaster_risk", "flood_segmentation", "destination_stress", "cyclone_count", "pm25"), default="tourism_demand")
    parser.add_argument("--destination", default="IND")
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument('--input-json', type=str)
    args = parser.parse_args()
    if args.command == "run":
        print(json.dumps(run(), indent=2, default=str))
    elif args.command == "serve":
        from .http_api import serve
        try: serve(args.port)
        except OSError: parser.exit(2,'Cannot start local API: selected port is unavailable. Choose an unused port; do not connect to a stale server.\n')
    else:
        from .config import settings
        from .readiness import data_readiness
        from .forecasting import train_forecast, evaluate_forecast, forecast
        from .persistence import list_models
        project = settings().project_root
        raw = project.parent / 'SafarSaathi_Datasets/raw'
        try:
            if args.command == 'data-readiness':
                result = data_readiness(project, raw)
                result = {k: v['readiness'] for k, v in result['models'].items()}
            elif args.command == 'models':
                result = [{'model_id': m['model_id'], 'task': m['task']} for m in list_models()]
            elif args.command == 'validate-artifacts':
                from .validation import validate_artifacts
                result = validate_artifacts(project)
            elif args.model in {'cyclone_count','pm25'}:
                from .scoped_forecasts import train_scoped,evaluate_scoped,predict_scoped,SPECS
                if args.command=='train':result=train_scoped(project,args.model)
                elif args.command=='evaluate':result=evaluate_scoped(project,args.model)
                else:result=predict_scoped(project,args.model,{'geography':args.destination,'horizon':args.horizon})
            elif args.model == 'tourism_monthly_fta':
                from .monthly_forecasting import train_monthly, evaluate_monthly, forecast_monthly
                if args.command == 'train': result = train_monthly(project,project/'data/processed/tourism_monthly_fta/20261025')
                elif args.command == 'evaluate': result = evaluate_monthly(project)
                else: result = forecast_monthly(project,args.destination,args.horizon)
            elif args.model == 'flood_segmentation' and args.command in {'train','predict','evaluate'}:
                from .flood_baseline import train_flood,load_flood,segment
                if args.command=='train':result=train_flood(project,project/'data/external/sturm_flood/12748983')
                elif args.command=='evaluate':result=load_flood(project)[0]['metrics']
                else:
                    from pathlib import Path
                    if not args.input_json or Path(args.input_json).stat().st_size>1_000_000:raise ValueError('A supported input JSON file <=1 MB is required.')
                    result=segment(project,json.loads(Path(args.input_json).read_text(encoding='utf-8')))
            elif args.model != 'tourism_demand':
                readiness = data_readiness(project, raw, write=False)['models'][args.model]
                raise ValueError(readiness['reason'])
            elif args.command == 'train':
                result = train_forecast(project, raw)
            elif args.command == 'evaluate':
                result = evaluate_forecast(project)
            else:
                result = forecast(project, args.destination, args.horizon)
            print(json.dumps(result, indent=2))
        except (ValueError, OSError, RuntimeError) as exc:
            parser.exit(2, f'{args.command} unavailable: {exc}\n')


if __name__ == "__main__":
    main()
