"""This sub command generates a sample schema and a blank template
for developer reference."""
import os


def initialize(args):
    print("Creating output directory...")

    package_path = (
        os.path.join(args.output_directory, "init")
        if args.output_directory is not None
        else "init"
    )
    os.system("mkdir -p " + package_path)

    print("Initializing sample schemas...")
    with open("uluru/templates/schema/schema_sample_cat.json") as template:
        with open(
            os.path.join(package_path, "out_schema_sample.json"), "w"
        ) as destination:
            for line in template:
                destination.write(line)

    with open("uluru/templates/schema/empty_schema.json") as template:
        with open(os.path.join(package_path, "empty_schema.json"), "w") as destination:
            for line in template:
                destination.write(line)

    print("Initialization SUCCESS")


def init_setup_subparser(subparsers):
    parser = subparsers.add_parser("init", description=__doc__)
    parser.set_defaults(command=initialize)
    parser.add_argument(
        "--output_directory", help="Output directory for sample schema."
    )
