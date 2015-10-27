import csv
import random
import yaml

from optparse import OptionParser

def main():
    parser = OptionParser()
    parser.add_option("--benchmark-list", dest="benchmarklist",
                  help="YAML structured input file")
    parser.add_option("--difference", dest="difference",
                  help="Amount of variation from base value in %. Default is +10%",
                  default="10")
    parser.add_option("--prefix", dest="prefix",
                  help="Prefix for the names of output files",
                  default="master")
    parser.add_option("--count", dest="count",
                  help="Number or runs. Default is 1",
                  default=1,
                  type="int")
    (options, args) = parser.parse_args()
    if not options.benchmarklist:
        parser.error("Benchmark list is mandatory")

    with open(options.benchmarklist, 'r') as infile:
        blist = yaml.load(infile.read())
        for iteration in range (0, options.count):
            for benchmark in blist.keys():
                filename = "%s_%s_%s.csv" % (options.prefix, benchmark.replace(" ", "_"), iteration)
                f = open(filename, "w")
                csvwriter = csv.writer(f)
                for score in blist[benchmark]:
                    scorename = score.keys()[0]
                    basevalue = score[scorename]['base']
                    variation = float(options.difference)/100
                    value = random.uniform(basevalue, (1 + variation) * basevalue)
                    if score[scorename]['type'] == "int":
                        value = int(value)
                    csvwriter.writerow([scorename, value])
                f.close()


if __name__ == "__main__":
    main()
