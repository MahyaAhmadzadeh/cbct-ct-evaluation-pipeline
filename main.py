import argparse
from glob import glob
from evaluation.pipeline import EvaluationPipeline


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data", type=str, help="all patient dirs in glob format")
    parser.add_argument("-n", "--nums", type=str, help="patient numbers to process (in csv format)")
    parser.add_argument("-f", "--force", action='store_true', help="force run, deletes previous results and creates a new one. Otherwise skips the step if results already present")
    parser.add_argument("-a", "--all", action='store_true', help="run all the steps")
    parser.add_argument("-s", "--seg", action='store_true', help="run segmentation only")
    parser.add_argument("-pw", "--pw-linear", action='store_true', help="run pw-linear transformation only")
    parser.add_argument("-dm", "--dmap", action='store_true', help="run dmap calculation only")
    parser.add_argument("-c", "--cxt", action='store_true', help="run cxt conversion only")
    parser.add_argument("-fc", "--fcsv", action='store_true', help="run fcsv creation only")
    parser.add_argument("-p", "--params", action='store_true', help="run register params.txt creation only")
    parser.add_argument("-r", "--register", action='store_true', help="run plastimatch register only")
    parser.add_argument("-w", "--warp", action='store_true', help="run warp only")
    parser.add_argument("-m", "--metric", action='store_true', help="run calculate scores only")
    parser.add_argument("-fs", "--fiducial-sep", action='store_true', help="run calculate fiducial distance only")

    args = parser.parse_args()
    data =  glob(args.data)
    print(args)
    if args.nums:
        args.nums = list(filter(lambda x: len(x)!=0, args.nums.split(",")))
        args.nums = list(map(lambda x: int(x.strip())-1, args.nums))
    else:
        args.nums = []

    pipeline = EvaluationPipeline()
    pipeline.evaluate(data, args.force, args.nums, args.all, args.seg, args.pw_linear,
                        args.dmap, args.cxt, args.fcsv, args.params, args.register,
                        args.warp, args.metric, args.fiducial_sep)