import argparse
from glob import glob
from evaluation.config import EvaluationConfig
from evaluation.pipeline import EvaluationPipeline
import traceback

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data", type=str, nargs="+", help="List of patient directories")
    parser.add_argument("-n", "--nums", type=str, help="patient numbers to process (in csv format)")
    parser.add_argument("-f", "--force", action='store_true', help="force run, deletes previous results and creates a new one. Otherwise skips the step if results already present")
    parser.add_argument("-a", "--all", action='store_true', help="run all the steps")
    parser.add_argument("-pw", "--pw-linear", action='store_true', help="run pw-linear transformation only")
    parser.add_argument("-s", "--seg", action='store_true', help="run segmentation only")
    parser.add_argument("-dm", "--dmap", action='store_true', help="run dmap calculation only")
    parser.add_argument("-c", "--cxt", action='store_true', help="run cxt conversion only")
    parser.add_argument("-fc", "--fcsv", action='store_true', help="run fcsv creation only")
    parser.add_argument("-p", "--params", action='store_true', help="run register params.txt creation only")
    parser.add_argument("-r", "--register", action='store_true', help="run plastimatch register only")
    parser.add_argument("-w", "--warp", action='store_true', help="run warp only")
    parser.add_argument("-m", "--metric", action='store_true', help="run calculate scores only")
    parser.add_argument("-fs", "--fiducial-sep", action='store_true', help="run calculate fiducial distance only")
    parser.add_argument("-v", "--variant", type=str, help="Run only the specified variant (e.g., genctall_extorgans)")

    args = parser.parse_args()
    data = [item for path in args.data for item in glob(path)]
    print(args)

    if args.nums:
        args.nums = [int(x.strip()) - 1 for x in args.nums.split(",") if x.strip()]
    else:
        args.nums = []

    flag_combinations = {
        "baseline": (False, False, False),
        "extorgans": (False, False, True),
        "genctseg": (False, True, False),
        "genctseg_extorgans": (False, True, True),
        "genctall": (True, False, False),
        "genctall_extorgans": (True, False, True),
    }
    
    shared_from = {
        "baseline": None,
        "extorgans": "baseline",
        "genctseg": "baseline",
        "genctseg_extorgans": "baseline",
        "genctall": None,
        "genctall_extorgans": None,
    }



    
    variants_to_run = [args.variant] if args.variant else flag_combinations.keys()

    for variant in variants_to_run:
        if variant not in flag_combinations:
            print(f"Variant '{variant}' not recognized. Skipping.")
            continue

        gen_ct_all, gen_ct_seg, ext_ts_organs = flag_combinations[variant]
        print(f"\nRunning variant: {variant}")
        configs = EvaluationConfig()
        configs.use_generated_ct_everywhere = gen_ct_all
        configs.use_generated_ct_for_segmentation = gen_ct_seg
        configs.use_extended_ts_organs = ext_ts_organs
        configs.VARIANT_TAG = variant
        print(configs)

        pipeline = EvaluationPipeline(configs=configs)
        shared_variant = shared_from.get(variant)

        try:
            pipeline.evaluate(
                data,
                args.force,
                args.nums,
                args.all,
                args.seg,
                args.pw_linear,
                args.dmap,
                args.cxt,
                args.fcsv,
                args.params,
                args.register,
                args.warp,
                args.metric,
                args.fiducial_sep,
                shared_variant=shared_variant
            )
        except Exception as e:
            print(f"[ERROR] Variant '{variant}' failed with error: {e}")
            traceback.print_exc()
            continue
