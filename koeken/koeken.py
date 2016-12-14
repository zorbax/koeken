#!/usr/bin/env python
"""
	koeken.py
	~~~~~~~~~
	A Linear Discriminant Analysis effect size (LEfSe) wrapper.
	:copyright: (c) 2016 by Thomas W. Battaglia.
	:license: BSD, see LICENSE for more details.
"""
__author__ = 'Thomas W. Battaglia'
__copyright__ = 'Copyright 2016'
__license__ = 'BSD'
__version__ = '0.3.0'
__email__ = 'tb1280@nyu.edu'
__status__ = 'Development'
description = """
Koeken (command-line LEfSe)
===========================
Run LEfSe on multiple times.
"""

import util
import sys
import re
import argparse
import pandas as pd


# ---------------------------------------------------------------
# utilities
# ---------------------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(
        description=description,
		add_help=True,
        formatter_class=argparse.RawTextHelpFormatter,
		prog="koeken")
    parser.add_argument(
        "-v", "--version",
        action="version",
		version="%(prog)s v"+ __version__)
    parser.add_argument(
        "-i", "--input",
		dest="input_fp",
        metavar="<path>",
		type=str,
        required=True,
        help="Path to OTU/PICRUSt or humann2 feature table.")
    parser.add_argument(
        "-o", "--output",
		dest="output_dir",
        metavar="<path>",
        type=str,
		required=True,
        help="Folder path to output files.")
    parser.add_argument(
        "-m", "--mapping",
        metavar="<path>",
		type=str,
        required=True,
        help="Path to sample metadata.")
    parser.add_argument(
        "-f", "--format",
        metavar="<str>",
		type=str,
		choices=["qiime", "picrust", "humann2"],
        required=True,
        help="Must specifiy the type of input. Can be of type <qiime, picrust, humann2> ")

	# Metadata Params
    parser.add_argument(
        "--class",
        metavar="<string>",
		dest="classid",
        type=str,
        help="Class-definition")
    parser.add_argument(
        "--subclass",
        metavar="<string>",
        type=str,
        help="Subclass-definition")
    parser.add_argument(
        "--subject",
        metavar="<string>",
        type=str,
		default='#SampleID',
        help="Subject-definition")

	# Splitting Params
    parser.add_argument(
		"--compare",
        metavar="<string>",
        type=str,
		default="",
		nargs='+',
        help="Compare-definition")
    parser.add_argument(
        "--split",
        metavar="<string>",
        type=str,
        help="Split-definition")
    parser.add_argument(
        "--no-split",
		dest="no_split",
		action="store_true",
        help="No-Split-definition")

	# QIIME Params
    parser.add_argument(
        "-l", "--level",
        metavar="<int>",
        type=int,
		choices=[2, 3, 4, 5, 6, 7],
		default=6,
        help="Level 1 = Kingdom (e.g Bacteria)\n"
			 "Level 2 = Phylum (e.g Actinobacteria)\n"
			 "Level 3 = Class (e.g Actinobacteria)\n"
			 "Level 4 = Order (e.g Actinomycetales)\n"
			 "Level 5 = Family (e.g Streptomycetaceae)\n"
			 "Level 6 = Genus (e.g Streptomyces)\n"
	    	 "Level 7 = Species (e.g mirabilis)\n")

	# LEfSe Options
    parser.add_argument(
        "--pvalue",
        metavar="<float>",
        type=float,
		default=0.05,
        help="Pvalue-definition")
    parser.add_argument(
        "--lda",
		metavar="<float>",
        type=float,
		default=2.0,
        help="LDA-definition")
    parser.add_argument(
        "--strictness",
		metavar="<int>",
        type=int,
		choices=[0,1],
		default=0,
        help="Strictness-definition")
    parser.add_argument(
        "--image-type",
		metavar="<str>",
		dest="image_type",
        type=str,
		choices=["png", "pdf", "svg"],
		default="pdf",
        help="Image-type definition")
    parser.add_argument(
        "--dpi",
		metavar="<int>",
		type=int,
    	default=300,
        help="DPI definition")
    args = parser.parse_args()
    return args


# ---------------------------------------------------------------
# main
# ---------------------------------------------------------------
def main():
	print("\n=================================================================")
	print("koeken" + ' v' + __version__)
	print('Written by ' + __author__ + ' (' + __email__ + ')' + '\n')
	print('LEfSe Publication: "Metagenomic biomarker discovery and explanation"')
	print('Nicola Segata, Jacques Izard, Levi Waldron, Dirk Gevers, \n' +
	'Larisa Miropolsky, Wendy S Garrett, and Curtis Huttenhower')
	print('Genome Biology, 12:R60, 2011')
	print("==================================================================\n")

	# Get arguments
	args = parse_arguments()
	print(args)

	# Check data for errors
	util.check_map(args)

	# Create folders to store output
	util.create_dir(args.output_dir)
	util.create_dir(args.output_dir + "/formatted")
	util.create_dir(args.output_dir + "/results")
	util.create_dir(args.output_dir + "/split_tables")
	util.create_dir(args.output_dir + "/cladograms")

	# Run summarize taxa on BIOM file
	if args.format == "qiime" or args.format == "picrust":
		util.summarize_taxa(args)

		# Import data as a pandas dataframe
		sumtbl_df = pd.read_table(args.output_dir + "/summarize_table.txt")
		map_df = pd.read_table(args.mapping)

		# Find the cols and respective positions for input variables in the table.
		### Row 1 = Subject
		### Row 2 = Class
		### Row 3 = Subclass/None
		### Row 4-: = Bacteria/Features...
		subjectID_pos = sumtbl_df.columns.get_loc(args.subject)
		classID_pos = sumtbl_df.columns.get_loc(args.classid)
		bacteria_pos = range(( len(map_df.columns) ), len(sumtbl_df.columns))

		# Cases for addition of subject class
		if args.subclass is None:
			to_keep = [subjectID_pos, classID_pos] + bacteria_pos
		else:
			subclassID_pos = sumtbl_df.columns.get_loc(args.subclass)
			to_keep = [subjectID_pos, classID_pos, subclassID_pos] + bacteria_pos

		# Subset the data if particular group comparisons are given
		if args.compare != "":
			sumtbl_df=sumtbl_df[sumtbl_df[args.classid].isin(args.compare)]

		# Remove greengenes taxa names to make it prettier
		# TODO fix the double || error
		if args.format=="qiime":
			sumtbl_df=sumtbl_df.rename(columns=lambda x: re.sub('__$', "__unclassified", x))
			sumtbl_df=sumtbl_df.rename(columns=lambda x: re.sub('.__', '', x))
			#sumtbl_df=sumtbl_df.rename(columns=lambda x: re.sub('|', '|', x))

		# Run the analysis with all timepoints merged
		all_split=args.output_dir + "/split_tables/all_timepoints.txt"
		all_format=args.output_dir + "/formatted/all_timepoints.txt"
		all_results=args.output_dir + "/results/all_timepoints.txt"
		all_clade=args.output_dir + "/cladograms/all_timepoints."+args.image_type

		sumtbl_df_tsp = sumtbl_df.iloc[:,to_keep].transpose()
		sumtbl_df_tsp.to_csv(all_split, sep='\t', header=False, index=True)

		# Format data step
		# TODO add conditonal for subclass
		util.format_lefse(input_fp = all_split,
						  output_fp = all_format,
						  name = "all samples",
						  subclass = None)

		# Running lefse step
		util.run_lefse(input_fp = all_format,
					   output_fp = all_results,
					   name = "all samples",
					   args = args)

		# Plot cladogram step
		util.plot_cladogram(input_fp = all_results,
							output_fp = all_clade,
							name = "all samples",
							args = args)

		# Aesthetically pleasing
		print('=========================================================\n')

		if not args.no_split:
			# Split table to iterate over multiple timepoints
			grouped_df = sumtbl_df.groupby(str(args.split))

			# Iterate over each splitted mapping file
			for name, group in grouped_df:
				# Set vars
				current_split=args.output_dir + "/split_tables/" + str(name) + "_split.txt"
				current_format=args.output_dir + "/formatted/" + str(name) + "_format.txt"
				current_results=args.output_dir + "/results/" + str(name) + ".txt"
				current_clado=args.output_dir + "/cladograms/" + str(name) +'.' + args.image_type

				# Subset table to current working timepoint
				table = group.iloc[:,to_keep].transpose()

				# Remove any rows with 0 sums
				table_filtered = table.loc[~(table==0).all(axis=1)]

				# Write Input tables to file
				table_filtered.to_csv(current_split,
									  sep = '\t',
									  header = False,
									  index = True)

				# Formatting step
				# TODO add conditonal for subclass
				util.format_lefse(input_fp = current_split,
								  output_fp = current_format,
								  name = name,
								  subclass = None)

				# Run lefse step
				util.run_lefse(input_fp = current_format,
							   output_fp = current_results,
							   name = name,
							   args = args)

				# Plot cladogram step
				util.plot_cladogram(input_fp = current_results,
									output_fp = current_clado,
									name = name,
									args = args)

				# Aesthetically pleasing
				print('=========================================================\n')
	else:
		print("Running humann2 workflow")
